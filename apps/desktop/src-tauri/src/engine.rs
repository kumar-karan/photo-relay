use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

// ---------------------------------------------------------------------------
// Structured events emitted to the UI and appended to runtime/events.jsonl.
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RelayEvent {
    pub kind: String,
    pub message: String,
    pub at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_files: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub completed_files: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transferred_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rate_mbps: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub captured_at: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub live_photo: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size_mb: Option<f64>,
}

impl RelayEvent {
    pub fn new(kind: &str, message: impl Into<String>) -> Self {
        Self {
            kind: kind.into(),
            message: message.into(),
            at: crate::timestamp(),
            phase: None,
            file: None,
            total_files: None,
            completed_files: None,
            total_bytes: None,
            transferred_bytes: None,
            rate_mbps: None,
            captured_at: None,
            live_photo: None,
            size_mb: None,
        }
    }

    pub fn size_mb(mut self, value: f64) -> Self {
        self.size_mb = Some(value);
        self
    }

    pub fn message(mut self, value: impl Into<String>) -> Self {
        self.message = value.into();
        self
    }

    pub fn size_bytes(&self) -> Option<u64> {
        self.size_mb.map(|mb| (mb * 1_000_000.0) as u64)
    }

    pub fn phase(mut self, phase: &str) -> Self {
        self.phase = Some(phase.into());
        self
    }
    pub fn file(mut self, file: &str) -> Self {
        self.file = Some(file.into());
        self
    }
    pub fn total_files(mut self, value: u64) -> Self {
        self.total_files = Some(value);
        self
    }
    pub fn completed_files(mut self, value: u64) -> Self {
        self.completed_files = Some(value);
        self
    }
    pub fn total_bytes(mut self, value: u64) -> Self {
        self.total_bytes = Some(value);
        self
    }
    pub fn transferred_bytes(mut self, value: u64) -> Self {
        self.transferred_bytes = Some(value);
        self
    }
    pub fn rate_mbps(mut self, value: f64) -> Self {
        self.rate_mbps = Some(value);
        self
    }
    pub fn captured_at(mut self, value: &str) -> Self {
        self.captured_at = Some(value.into());
        self
    }
    pub fn live_photo(mut self, value: bool) -> Self {
        self.live_photo = Some(value);
        self
    }
}

// ---------------------------------------------------------------------------
// Live run state accumulated while a sync is running.
// ---------------------------------------------------------------------------

#[derive(Default)]
pub struct RunState {
    pub phase: String,
    pub total_files: u64,
    pub completed_files: u64,
    pub total_bytes: u64,
    pub transferred_bytes: u64,
    pub current_file: String,
    pub last_rate_mbps: f64,
    pub started_at: Option<std::time::SystemTime>,
    pub devices: BTreeMap<String, String>,
    pub errors: u64,
}

impl RunState {
    pub fn begin(&mut self) {
        *self = RunState {
            phase: "starting".into(),
            started_at: Some(std::time::SystemTime::now()),
            ..RunState::default()
        };
    }
}

// ---------------------------------------------------------------------------
// Engine log parser: converts raw run_sync.sh output lines into typed events.
// The engine emits a stable, greppable format, e.g.
//   [INFO   ]   [ 12/163] (  7.4%) Downloaded: IMG_0972.PNG (1.2 MB @ 33.2 MB/s)
//   [SUCCESS]        ✅ Pushed + timestamp set: IMG_0977.JPG (2.7 MB @ 30.9 MB/s)
//   [INFO   ]        Conversion status: converted (0.73s) -> IMG_0964.JPG
// ---------------------------------------------------------------------------

pub fn parse_line(line: &str, state: &mut RunState) -> Option<RelayEvent> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return None;
    }

    // Strip the leading "[LEVEL   ]" tag when present to classify severity.
    let (level, body) = split_level(trimmed);
    let body = body.trim();
    if body.is_empty() {
        return None;
    }

    let kind = match level {
        Some("SUCCESS") => "success",
        Some("WARNING") => "warning",
        Some("ERROR") => "error",
        _ => "info",
    };

    if kind == "error" {
        state.errors += 1;
    }

    // Pure separator banners ("======", "------") carry no information and
    // would only add noise to the activity feed.
    if !body.is_empty() && body.chars().all(|char| matches!(char, '=' | '-' | ' ')) {
        return None;
    }

    if let Some(pushed) = parse_summary_counts(body) {
        state.completed_files = pushed;
        state.phase = "done".into();
        return Some(RelayEvent::new("success", body.trim().to_string())
            .phase("done")
            .completed_files(pushed)
            .total_files(state.total_files));
    }

    // Pushed line: "✅ Pushed + timestamp set: FILE (SIZE MB @ RATE MB/s) → DATE"
    if let Some(event) = parse_pushed(body, state) {
        return Some(event);
    }

    // Download line: "[ 12/163] ( 7.4%) Downloaded: FILE (SIZE MB @ RATE MB/s)"
    if let Some(event) = parse_download(body, state) {
        return Some(event);
    }

    // Conversion line: "Conversion status: converted (0.73s) -> FILE"
    if body.contains("Conversion status:") {
        let file = body
            .rsplit("->")
            .next()
            .map(|s| s.trim().to_string())
            .unwrap_or_default();
        let live = !file.is_empty();
        return Some(
            RelayEvent::new("info", format!("Converted Live Photo → {}", file))
                .phase("converting")
                .live_photo(live)
                .file(&file),
        );
    }

    // Device status lines carry connection and free space info.
    if let Some(event) = parse_device(body, state) {
        return Some(event);
    }

    // Phase transitions.
    if body.contains("Connecting to iPhone") {
        state.phase = "connecting".into();
        return Some(RelayEvent::new("info", "Connecting to iPhone over USB…").phase("connecting"));
    }
    if body.contains("Scan Complete") || body.contains("Scanning") && body.contains("DCIM") {
        state.phase = "scanning".into();
        return Some(RelayEvent::new("info", body.to_string()).phase("scanning"));
    }
    if body.contains("New files found") {
        return Some(RelayEvent::new("info", body.to_string()).phase("scanning"));
    }
    if body.contains("Grouping:") {
        return Some(RelayEvent::new("info", body.to_string()).phase("scanning"));
    }
    if body.contains("Pipelined Transfer: Streaming") {
        if let Some((files, bytes)) = parse_stream_totals(body) {
            state.total_files = files;
            state.total_bytes = bytes;
            state.phase = "transferring".into();
            return Some(
                RelayEvent::new("info", body.to_string())
                    .phase("transferring")
                    .total_files(files)
                    .total_bytes(bytes),
            );
        }
    }
    if body.contains("Triggering MediaScanner") {
        state.phase = "indexing".into();
        return Some(RelayEvent::new("info", body.to_string()).phase("indexing"));
    }
    if body.contains("broadcast completed") {
        return Some(RelayEvent::new("success", body.to_string()).phase("indexing"));
    }
    // The engine's closing summary block is drawn as a tree:
    //   ├── Files Pushed to Samsung: 138
    //   └── Run Log Location       : ...
    if body.starts_with('├') || body.starts_with('└') {
        let cleaned = body.trim_start_matches(['├', '└', '─', ' ']).trim();
        let mut event = RelayEvent::new("info", cleaned.to_string()).phase("done");
        if let Some(pushed) = parse_summary_counts(body) {
            state.completed_files = pushed;
            event = event.completed_files(pushed).total_files(state.total_files);
        }
        return Some(event);
    }

    if body.starts_with("Completed!") {
        state.phase = "done".into();
        return Some(RelayEvent::new("success", body.to_string()).phase("done").completed_files(state.completed_files));
    }

    Some(RelayEvent::new(kind, body.to_string()))
}

/// Strip the engine's `[timestamp] [LEVEL   ]` prefix.
///
/// Real lines look like `[2026-10-03 11:27:03.663] [INFO   ] body`, but some
/// helpers emit `[INFO   ] body`, so both shapes are accepted.
fn split_level(line: &str) -> (Option<&str>, &str) {
    const KNOWN: [&str; 5] = ["INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG"];

    let mut rest = line.trim_start();
    if rest.starts_with('[') {
        if let Some(close) = rest.find(']') {
            let inner = &rest[1..close];
            if inner.contains(':') || inner.contains('-') {
                rest = rest[close + 1..].trim_start();
            }
        }
    }

    if rest.starts_with('[') {
        if let Some(close) = rest.find(']') {
            let level = rest[1..close].split_whitespace().next().unwrap_or("");
            if KNOWN.contains(&level) {
                return (Some(level), &rest[close + 1..]);
            }
        }
    }

    (None, rest)
}

fn parse_pushed(body: &str, state: &mut RunState) -> Option<RelayEvent> {
    // Guard against the summary line "Files Pushed to Samsung: 138", which
    // also contains the word "Pushed" but is not a per-file transfer.
    if !(body.contains("Pushed + timestamp set") || body.contains("Pushed:")) {
        return None;
    }
    let after = body.split("Pushed").nth(1)?;
    let name_part = after.split_once(':')?.1;
    let file = name_part.split('(').next()?.trim().to_string();
    let (size_mb, rate) = parse_size_rate(name_part);
    let captured = body.split("→").nth(1).map(|s| s.trim().to_string());

    state.completed_files += 1;
    state.phase = "pushing".into();
    if let Some(mb) = size_mb {
        state.transferred_bytes += (mb * 1_000_000.0) as u64;
    }
    if let Some(rate) = rate {
        state.last_rate_mbps = rate;
    }

    let mut event = RelayEvent::new("success", format!("Pushed {}", file))
        .phase("pushing")
        .file(&file)
        .completed_files(state.completed_files);
    if state.total_files > 0 {
        event = event.total_files(state.total_files);
    }
    if state.total_bytes > 0 {
        event = event.total_bytes(state.total_bytes);
    }
    event = event.transferred_bytes(state.transferred_bytes);
    if let Some(rate) = rate {
        event = event.rate_mbps(rate);
    }
    if let Some(size) = size_mb {
        event = event.message(format!("Pushed {} · {:.1} MB", file, size)).size_mb(size);
    }
    if let Some(captured) = captured {
        event = event.captured_at(&captured);
    }
    Some(event)
}

fn parse_download(body: &str, state: &mut RunState) -> Option<RelayEvent> {
    if !body.contains("Downloaded:") && !body.contains("Downloading:") {
        return None;
    }
    let (index, total) = parse_index_total(body);
    let name_part = body.split_once("Downloaded:").or_else(|| body.split_once("Downloading:"))?.1;
    let file = name_part.split('(').next()?.trim().to_string();
    let (size_mb, rate) = parse_size_rate(name_part);

    state.phase = "downloading".into();
    state.current_file = file.clone();
    if let Some(value) = total {
        state.total_files = value;
    }

    let mut event = RelayEvent::new("info", format!("Pulling {}", file))
        .phase("downloading")
        .file(&file)
        .completed_files(index.unwrap_or(0));
    if let Some(value) = total {
        event = event.total_files(value);
    }
    if let Some(rate) = rate {
        state.last_rate_mbps = rate;
        event = event.rate_mbps(rate);
    }
    if let Some(size) = size_mb {
        state.transferred_bytes = state.transferred_bytes.max((size * 1_000_000.0) as u64);
        event = event.size_mb(size).message(format!("Pulling {} · {:.1} MB", file, size));
    }
    if state.total_bytes > 0 {
        event = event.total_bytes(state.total_bytes).transferred_bytes(state.transferred_bytes);
    }
    Some(event)
}

fn parse_device(body: &str, state: &mut RunState) -> Option<RelayEvent> {
    if !(body.contains("iPhone Status") || body.contains("Samsung Status") || body.contains("Connected to iPhone")) {
        return None;
    }
    if let Some((key, value)) = body.split_once(':') {
        let key = key.trim();
        let value = value.trim();
        if !key.is_empty() {
            state.devices.insert(key.to_string(), value.to_string());
        }
    }
    Some(RelayEvent::new("info", body.to_string()).phase("preflight"))
}

fn parse_index_total(body: &str) -> (Option<u64>, Option<u64>) {
    // Matches "[ 12/163]" or "12/163"
    let mut index = None;
    let mut total = None;
    if let Some(start) = body.find('[') {
        if let Some(end) = body[start..].find(']') {
            let inner = &body[start + 1..start + end];
            if let Some((a, b)) = inner.split_once('/') {
                index = a.trim().parse().ok();
                total = b.trim().parse().ok();
            }
        }
    }
    (index, total)
}

fn parse_size_rate(segment: &str) -> (Option<f64>, Option<f64>) {
    // "(2.2 MB @ 23.2 MB/s)" -> size, rate
    let mut size = None;
    let mut rate = None;
    let inner = segment.split_once('(').map(|(_, rest)| rest).unwrap_or(segment);
    let inner = inner.split(')').next().unwrap_or(inner);
    for piece in inner.split('@') {
        let piece = piece.trim();
        if piece.ends_with("MB/s") {
            rate = piece.trim_end_matches("MB/s").trim().parse().ok();
        } else if piece.ends_with("MB") {
            size = piece.trim_end_matches("MB").trim().parse().ok();
        } else if piece.ends_with("KB") {
            if let Ok(kb) = piece.trim_end_matches("KB").trim().parse::<f64>() {
                size = Some(kb / 1024.0);
            }
        }
    }
    (size, rate)
}

fn parse_stream_totals(body: &str) -> Option<(u64, u64)> {
    // "Streaming 163 files (1984.1 MB) from iPhone"
    let after = body.split("Streaming").nth(1)?;
    let files = after.split_whitespace().next()?.parse().ok()?;
    let bytes = parse_size_rate(after).0.map(|mb| (mb * 1_000_000.0) as u64).unwrap_or(0);
    Some((files, bytes))
}

// ---------------------------------------------------------------------------
// Transfer journal: append-only JSONL of verified (or failed) file outcomes.
// ---------------------------------------------------------------------------

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TransferRecord {
    pub at: String,
    pub file: String,
    pub size_bytes: u64,
    pub captured_at: Option<String>,
    pub live_photo: bool,
    pub verified: bool,
    pub error: Option<String>,
}

pub fn append_transfer(runtime_root: &Path, record: &TransferRecord) {
    let path = runtime_root.join("transfers.jsonl");
    let _ = fs::create_dir_all(runtime_root);
    if let Ok(line) = serde_json::to_string(record) {
        if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(path) {
            use std::io::Write;
            let _ = writeln!(file, "{line}");
        }
    }
}

pub fn read_transfers(runtime_root: &Path, limit: usize) -> Vec<Value> {
    let path = runtime_root.join("transfers.jsonl");
    let Ok(contents) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let mut records: Vec<Value> = contents
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .collect();
    if records.len() > limit {
        records.drain(..records.len() - limit);
    }
    records
}

// ---------------------------------------------------------------------------
// Event log reader (used to restore the activity feed on launch).
// ---------------------------------------------------------------------------

pub fn read_events(runtime_root: &Path, limit: usize) -> Vec<Value> {
    let path = runtime_root.join("events.jsonl");
    let Ok(contents) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let mut events: Vec<Value> = contents
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .collect();
    if events.len() > limit {
        events.drain(..events.len() - limit);
    }
    events
}

// ---------------------------------------------------------------------------
// Parse the engine's structured run_history.json into UI-friendly summaries.
// ---------------------------------------------------------------------------

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct RunSummary {
    pub run_id: String,
    pub started_at: String,
    #[serde(default)]
    pub finished_at: Option<String>,
    pub files_pushed: u64,
    #[serde(default)]
    pub files_skipped: u64,
    #[serde(default)]
    pub errors: u64,
    #[serde(default)]
    pub bytes_transferred: u64,
    #[serde(default)]
    pub duration_seconds: f64,
    #[serde(default)]
    pub new_watermark: Option<String>,
    #[serde(default)]
    pub status: String,
}

pub fn read_run_history(engine_root: &Path, limit: usize) -> Vec<RunSummary> {
    let path = engine_root.join("logs").join("run_history.json");
    let Ok(contents) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let Ok(Value::Array(items)) = serde_json::from_str::<Value>(&contents) else {
        return Vec::new();
    };
    let mut runs: Vec<RunSummary> = items
        .into_iter()
        .rev()
        .take(limit)
        .map(|item| {
            serde_json::from_value::<RunSummary>(item.clone()).unwrap_or_else(|_| RunSummary {
                run_id: String::new(),
                started_at: item.get("timestamp").and_then(|v| v.as_str()).unwrap_or_default().to_string(),
                finished_at: None,
                files_pushed: item.get("files_pushed").and_then(|v| v.as_u64()).unwrap_or(0),
                files_skipped: item.get("skipped").and_then(|v| v.as_u64()).unwrap_or(0),
                errors: item.get("errors").and_then(|v| v.as_u64()).unwrap_or(0),
                bytes_transferred: 0,
                duration_seconds: item.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.0),
                new_watermark: item.get("watermark").and_then(|v| v.as_str()).map(str::to_string),
                status: item.get("status").and_then(|v| v.as_str()).unwrap_or("success").to_string(),
            })
        })
        .collect();
    runs.reverse();
    runs
}

// ---------------------------------------------------------------------------
// Shared helper for building a snapshot the UI polls on an interval.
// ---------------------------------------------------------------------------

/// Extract the per-file push count reported in the final summary block.
pub fn parse_summary_counts(body: &str) -> Option<u64> {
    let after = body.split("Files Pushed to Samsung").nth(1)?;
    after
        .trim_start_matches([' ', ':', '\u{2502}'])
        .trim()
        .split_whitespace()
        .next()?
        .parse()
        .ok()
}

/// Seconds elapsed since the active run began, if a run is in flight.
pub fn elapsed_seconds(state: &RunState) -> Option<f64> {
    state
        .started_at
        .map(|started| started.elapsed().map(|value| value.as_secs_f64()).unwrap_or_default())
}