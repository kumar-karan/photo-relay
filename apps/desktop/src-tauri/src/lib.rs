mod engine;
#[cfg(test)]
mod engine_test;

use engine::{parse_line, read_events, read_run_history, read_transfers, RelayEvent, RunState, RunSummary, TransferRecord};
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::{
    fs, io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant, SystemTime},
};
use tauri::{AppHandle, Emitter, State};

#[derive(Default)]
struct RelayRuntime {
    running: AtomicBool,
    run: Mutex<RunState>,
    /// Device detection shells out to the engine's USB probe, which is far too
    /// expensive to run on every dashboard poll. Cache it briefly instead.
    devices: Mutex<DeviceCache>,
    /// Pid of the running engine, so a long transfer can be stopped.
    child: Mutex<Option<u32>>,
}

#[derive(Default)]
struct DeviceCache {
    checked_at: Option<Instant>,
    map: BTreeMap<String, DeviceStatus>,
}

/// Device detection is cached for this long, and the explicit device check
/// button bypasses the cache entirely.
const DEVICE_TTL: Duration = Duration::from_secs(6);

#[derive(Clone, Default)]
struct RunSnapshot {
    phase: String,
    total_files: u64,
    total_media: u64,
    completed_files: u64,
    progress_total: u64,
    total_bytes: u64,
    transferred_bytes: u64,
    rate_mbps: f64,
    elapsed_seconds: f64,
    errors: u64,
    current_file: String,
    devices: BTreeMap<String, DeviceStatus>,
}

impl RelayRuntime {
    fn snapshot(&self) -> RunSnapshot {
        let build = |state: &RunState| {
            let (done, total) = state.progress();
            RunSnapshot {
                phase: state.phase.clone(),
                total_files: state.total_files,
                total_media: state.total_media,
                completed_files: done,
                progress_total: total,
                total_bytes: state.total_bytes,
                transferred_bytes: state.bytes_moved(),
                rate_mbps: state.last_rate_mbps,
                elapsed_seconds: engine::elapsed_seconds(state).unwrap_or_default(),
                errors: state.errors,
                current_file: state.current_file.clone(),
                devices: state.devices.iter().map(|(key, line)| (key.clone(), status_from_line(line))).collect(),
            }
        };
        match self.run.lock() {
            Ok(state) => build(&state),
            Err(poisoned) => build(&poisoned.into_inner()),
        }
    }

    /// Return cached devices, refreshing them when the cache has gone stale.
    fn devices(&self, engine: &Path, force: bool) -> BTreeMap<String, DeviceStatus> {
        let stale = match self.devices.lock() {
            Ok(cache) => match cache.checked_at {
                Some(at) if !force && at.elapsed() < DEVICE_TTL => return cache.map.clone(),
                _ => true,
            },
            Err(_) => true,
        };
        if !stale {
            return BTreeMap::new();
        }
        let map = discover_devices(engine);
        match self.devices.lock() {
            Ok(mut cache) => {
                cache.checked_at = Some(Instant::now());
                cache.map = map.clone();
            }
            Err(_) => {}
        }
        map
    }

    /// Feed one engine log line through the parser and keep the run state fresh.
    fn absorb(&self, line: &str) -> Option<RelayEvent> {
        match self.run.lock() {
            Ok(mut state) => parse_line(line, &mut state),
            Err(poisoned) => parse_line(line, &mut poisoned.into_inner()),
        }
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Dashboard {
    running: bool,
    engine_found: bool,
    phase: String,
    total_files: u64,
    total_media: u64,
    completed_files: u64,
    total_bytes: u64,
    transferred_bytes: u64,
    rate_mbps: f64,
    elapsed_seconds: f64,
    errors: u64,
    /// Denominator for the progress bar: source files while downloading,
    /// media items while pushing.
    progress_total: u64,
    current_file: String,
    devices: BTreeMap<String, DeviceStatus>,
    status: String,
    total_synced_files: u64,
    last_synced_timestamp: String,
    history: Vec<RunSummary>,
    transfers: Vec<Value>,
    recent_events: Vec<Value>,
    latest_log: String,
    project_root: String,
    engine_version: String,
}

fn timestamp() -> String {
    engine::iso8601(SystemTime::now())
}

/// Where the app records its project folder between launches.
///
/// A packaged `.app` in /Applications cannot walk up to the repository, and a
/// path baked in at compile time breaks the moment the project moves. So the
/// resolved folder is remembered here and re-read on every launch.
fn home_pointer_path() -> Option<PathBuf> {
    std::env::var("HOME").ok().map(|home| PathBuf::from(home).join("Library/Application Support/Photo Relay/project-home"))
}

/// Resolve the project root at runtime.
///
/// Priority: explicit override, remembered location, walk up from the
/// executable (development and in-tree bundles), then the build-time path.
fn project_root() -> PathBuf {
    if let Ok(configured) = std::env::var("PHOTO_RELAY_HOME") {
        return PathBuf::from(configured);
    }
    if let Some(pointer) = home_pointer_path() {
        if let Ok(remembered) = fs::read_to_string(&pointer) {
            let candidate = PathBuf::from(remembered.trim());
            if candidate.join("sync_engine").is_dir() {
                return candidate;
            }
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(found) = exe.ancestors().find(|dir| dir.join("runtime").is_dir() && dir.join("sync_engine").is_dir()) {
            return found.to_path_buf();
        }
    }
    let baked = Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .map(Path::to_path_buf)
        .filter(|dir| dir.join("sync_engine").is_dir());
    match baked {
        Some(dir) => {
            // Remember it so a future launch from /Applications still works.
            if let Some(pointer) = home_pointer_path() {
                if let Some(parent) = pointer.parent() {
                    let _ = fs::create_dir_all(parent);
                    let _ = fs::write(&pointer, dir.to_string_lossy().as_bytes());
                }
            }
            dir
        }
        None => PathBuf::from("."),
    }
}

fn engine_root() -> PathBuf {
    project_root().join("sync_engine")
}

fn runtime_root() -> PathBuf {
    project_root().join("runtime")
}

fn read_json(path: PathBuf, fallback: Value) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|raw| serde_json::from_str(&raw).ok())
        .unwrap_or(fallback)
}

fn append_event(event: &RelayEvent) {
    let root = runtime_root();
    let _ = fs::create_dir_all(&root);
    if let Ok(line) = serde_json::to_string(event) {
        if let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(root.join("events.jsonl")) {
            let _ = writeln!(file, "{line}");
        }
    }
}

fn emit(app: &AppHandle, event: RelayEvent) {
    append_event(&event);
    let _ = app.emit("relay-event", &event);
}

fn latest_log(logs: &Path) -> String {
    fs::read_dir(logs)
        .ok()
        .into_iter()
        .flatten()
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.file_name().to_string_lossy().starts_with("sync_"))
        .max_by_key(|entry| {
            entry
                .metadata()
                .and_then(|meta| meta.modified())
                .unwrap_or(SystemTime::UNIX_EPOCH)
        })
        .map(|entry| {
            engine::tail_lines(&entry.path(), 120, 128 * 1024)
                .iter()
                .map(|line| strip_emoji(line))
                .filter(|line| !line.is_empty())
                .collect::<Vec<_>>()
                .join("\n")
        })
        .unwrap_or_default()
}

/// Read the engine's advertised version from its start-up banner.
///
/// The banner lives in a `logger.log(...)` call, so splitting on a bare "v"
/// would match the `v` in `level=""`. Scope the search to the parenthesised
/// part after "PIPELINE" and take the leading token only.
fn engine_version(engine: &Path) -> String {
    let Ok(text) = fs::read_to_string(engine.join("sync.py")) else {
        return "unknown".into();
    };
    for line in text.lines() {
        let Some(rest) = line.split_once("PIPELINE").map(|(_, tail)| tail) else {
            continue;
        };
        let Some(inner) = rest.split_once('(').and_then(|(_, tail)| tail.split_once(')')).map(|(head, _)| head) else {
            continue;
        };
        let token: String = inner
            .trim()
            .chars()
            .take_while(|char| char.is_ascii_alphanumeric() || matches!(char, '.' | '-'))
            .collect();
        if let Some(number) = token.strip_prefix('v') {
            if !number.is_empty() {
                return format!("v{number}");
            }
        }
    }
    "unknown".into()
}

/// A device's live state. Sent as structured data rather than a display string
/// so the UI never has to substring-match words like "Not detected".
#[derive(Serialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
struct DeviceStatus {
    online: bool,
    detail: String,
}

/// Interpret a raw engine device line captured during a run.
fn status_from_line(line: &str) -> DeviceStatus {
    let online = line_is_online(line);
    DeviceStatus {
        online,
        detail: if online { free_space(line).unwrap_or_else(|| "Connected".into()) } else { "Not detected".into() },
    }
}

/// Pull "43.46GB free" out of an engine device-status line.
///
/// The amount sits immediately before the word "free", so read the preceding
/// token and require it to parse as a number — otherwise a device serial would
/// be picked up instead.
fn free_space(line: &str) -> Option<String> {
    let head = line.split("free").next()?;
    let token = head.split_whitespace().next_back()?;
    let value = token.trim_end_matches("GB").trim();
    value.parse::<f64>().ok()?;
    Some(format!("{value} GB free"))
}

/// Decide whether a raw engine device line reports a working connection.
fn line_is_online(line: &str) -> bool {
    !line.contains('❌') && (line.contains('✅') || line.to_lowercase().contains("detected") || line.to_lowercase().contains("ready"))
}

/// Strip emoji and other pictographs out of engine text.
///
/// The Python engine decorates its console output with emoji. Those glyphs are
/// useful in a terminal but not in a desktop UI, where the frontend draws its
/// own icons, so every engine-derived string is cleaned before it is shown.
fn strip_emoji(text: &str) -> String {
    // A removed glyph behaves like a word separator, so "Pushed ✅ 12 files"
    // stays readable once the glyph is gone.
    let mut out = String::with_capacity(text.len());
    let mut pending_space = false;
    for ch in text.chars() {
        if is_emoji(ch) {
            pending_space = !out.is_empty() && !out.ends_with(' ');
            continue;
        }
        if pending_space {
            out.push(' ');
            pending_space = false;
        }
        out.push(ch);
    }
    if pending_space {
        out.push(' ');
    }

    // Collapse whitespace runs introduced by the removals, then trim.
    let mut collapsed = String::with_capacity(out.len());
    let mut space = false;
    for ch in out.chars() {
        if ch.is_whitespace() {
            space = true;
            continue;
        }
        if space && !collapsed.is_empty() {
            collapsed.push(' ');
        }
        space = false;
        collapsed.push(ch);
    }
    collapsed.trim().to_string()
}

/// Whether a character is an emoji or pictograph the UI should not render.
///
/// Matched by Unicode block rather than by an allow-list of punctuation, so
/// real text survives: a typographic apostrophe in "Karan’s iPhone" and the
/// spaces the engine puts around a colon must both be left alone.
fn is_emoji(ch: char) -> bool {
    let code = ch as u32;
    matches!(
        code,
        // Emoticons, pictographs, transport, symbols and supplemental symbols.
        0x1F000..=0x1FAFF
            | 0x2600..=0x27BF
            | 0x2B00..=0x2BFF
            | 0x25A0..=0x25FF
            | 0x2190..=0x21FF
            // Regional indicators, which form flag sequences.
            | 0x1F1E6..=0x1F1FF
            // Variation selectors, zero-width joiner and the keycap mark.
            | 0xFE00..=0xFE0F
            | 0x200D
            | 0x20E3
            // Standalone symbols the engine uses as status prefixes.
            | 0x2139
            | 0x203C
            | 0x2049
            | 0x2122
            | 0x3030
            | 0x303D
            | 0x3297
            | 0x3299
    )
}

/// Ask the engine which devices it can see, without transferring anything.
fn discover_devices(engine: &Path) -> BTreeMap<String, DeviceStatus> {
    let mut devices = BTreeMap::new();
    if !engine.join("detect_devices.py").exists() {
        return devices;
    }
    let Ok(output) = Command::new("python3")
        .arg(engine.join("detect_devices.py"))
        .current_dir(engine)
        .output()
    else {
        return devices;
    };
    let text = format!("{}{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
    for line in text.lines() {
        let lower = line.to_lowercase();
        let key = if lower.contains("samsung") || lower.contains("android") {
            "Samsung"
        } else if lower.contains("iphone") {
            "iPhone"
        } else {
            continue;
        };
        let online = line_is_online(line);
        let detail = if online {
            free_space(line).unwrap_or_else(|| "Connected".into())
        } else {
            "Not detected".into()
        };
        devices.insert(key.into(), DeviceStatus { online, detail });
    }
    devices
}

#[tauri::command]
fn dashboard(runtime: State<'_, Arc<RelayRuntime>>) -> Dashboard {
    let engine = engine_root();
    let root = runtime_root();
    let run = runtime.snapshot();

    let state = read_json(engine.join("sync_state.json"), json!({}));

    Dashboard {
        running: runtime.running.load(Ordering::SeqCst),
        engine_found: engine.join("run_sync.sh").exists(),
        phase: run.phase,
        total_files: run.total_files,
        total_media: run.total_media,
        completed_files: run.completed_files,
        progress_total: run.progress_total,
        total_bytes: run.total_bytes,
        transferred_bytes: run.transferred_bytes,
        rate_mbps: run.rate_mbps,
        elapsed_seconds: run.elapsed_seconds,
        errors: run.errors,
        current_file: run.current_file,
        // While a relay is in flight the engine's own device lines are newer
        // and more accurate than a fresh USB probe, so prefer them.
        devices: if run.devices.is_empty() { runtime.devices(&engine, false) } else { run.devices },
        status: state.get("status").and_then(|v| v.as_str()).unwrap_or("idle").to_string(),
        total_synced_files: state.get("total_synced_files").and_then(|v| v.as_u64()).unwrap_or(0),
        last_synced_timestamp: state.get("last_synced_timestamp").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        history: read_run_history(&engine, 12),
        transfers: read_transfers(&root, 40),
        recent_events: read_events(&root, 60),
        latest_log: latest_log(&engine.join("logs")),
        project_root: project_root().to_string_lossy().to_string(),
        engine_version: engine_version(&engine),
    }
}

/// Run the engine's USB probe on demand, bypassing the dashboard's cache so the
/// relay diagram reflects reality immediately after the user clicks the button.
#[tauri::command]
fn preflight(runtime: State<'_, Arc<RelayRuntime>>) -> Result<Vec<String>, String> {
    let engine = engine_root();
    let _ = runtime.devices(&engine, true);
    if !engine.join("detect_devices.py").exists() {
        return Err("The sync engine was not found. Keep sync_engine/ inside this project folder.".into());
    }
    let output = Command::new("python3")
        .arg(engine.join("detect_devices.py"))
        .current_dir(&engine)
        .output()
        .map_err(|error| error.to_string())?;

    let text = format!("{}{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
    Ok(text
        .lines()
        .map(strip_emoji)
        .filter(|line| !line.is_empty() && !line.starts_with('='))
        .collect())
}

#[tauri::command]
fn start_sync(app: AppHandle, runtime: State<'_, Arc<RelayRuntime>>) -> Result<(), String> {
    if runtime.running.swap(true, Ordering::SeqCst) {
        return Err("A relay is already running.".into());
    }
    let engine = engine_root();
    if !engine.join("run_sync.sh").exists() {
        runtime.running.store(false, Ordering::SeqCst);
        return Err("The sync engine was not found.".into());
    }

    if let Ok(mut run) = runtime.run.lock() {
        run.begin();
    }

    let worker = Arc::clone(runtime.inner());
    thread::spawn(move || {
        let root = runtime_root();
        emit(&app, RelayEvent::new("info", "Preparing the iPhone to Samsung relay…").phase("starting"));

        let spawned = Command::new("bash")
            .arg("run_sync.sh")
            .current_dir(&engine)
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn();

        match spawned {
            Ok(mut child) => {
                if let Ok(mut slot) = worker.child.lock() {
                    *slot = Some(child.id());
                }
                if let Some(stdout) = child.stdout.take() {
                    for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                        if let Some(event) = worker.absorb(&line) {
                            if event.phase.as_deref() == Some("pushing") && event.kind == "success" {
                                engine::append_transfer(
                                    &root,
                                    &TransferRecord {
                                        at: event.at.clone(),
                                        file: event.file.clone().unwrap_or_default(),
                                        size_bytes: event.size_bytes().unwrap_or(0),
                                        captured_at: event.captured_at.clone(),
                                        live_photo: event.live_photo.unwrap_or(false),
                                        verified: true,
                                        error: None,
                                    },
                                );
                            }
                            emit(&app, event);
                        }
                    }
                }

                match child.wait() {
                    Ok(status) if status.success() => {
                        emit(&app, RelayEvent::new("success", "Relay complete. Samsung media is indexed and ready for backup.").phase("done"))
                    }
                    Ok(status) => emit(&app, RelayEvent::new("error", format!("Relay stopped with exit code {}.", status.code().unwrap_or(-1))).phase("failed")),
                    Err(error) => emit(&app, RelayEvent::new("error", error.to_string()).phase("failed")),
                }
            }
            Err(error) => emit(&app, RelayEvent::new("error", format!("Unable to start the relay: {error}")).phase("failed")),
        }

        if let Ok(mut slot) = worker.child.lock() {
            *slot = None;
        }
        if let Ok(mut run) = worker.run.lock() {
            run.phase = "idle".into();
        }
        worker.running.store(false, Ordering::SeqCst);
    });

    Ok(())
}

/// Ask the running engine to stop.
///
/// The engine removes a staged file only after confirming it on the Samsung,
/// so interrupting mid-transfer leaves the remaining files staged and the
/// watermark untouched — the next run picks up exactly where this one stopped.
#[tauri::command]
fn stop_sync(app: AppHandle, runtime: State<'_, Arc<RelayRuntime>>) -> Result<(), String> {
    if !runtime.running.load(Ordering::SeqCst) {
        return Err("No relay is running.".into());
    }
    let pid = runtime.child.lock().ok().and_then(|slot| *slot);
    let Some(pid) = pid else {
        return Err("The engine process is not available to stop.".into());
    };
    // SIGTERM first so the engine can unwind cleanly.
    let signalled = Command::new("kill")
        .args(["-TERM", &pid.to_string()])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false);
    if !signalled {
        return Err("Could not signal the running engine.".into());
    }
    emit(&app, RelayEvent::new("warning", "Stop requested — finishing the current file, then standing down.").phase("stopping"));
    Ok(())
}

#[tauri::command]
fn reveal(path: String) -> Result<(), String> {
    let target = match path.as_str() {
        "runtime" => runtime_root(),
        "logs" => engine_root().join("logs"),
        "engine" => engine_root(),
        other => PathBuf::from(other),
    };
    if !target.exists() {
        return Err(format!("{} does not exist yet.", target.display()));
    }
    Command::new("open").arg(&target).spawn().map(|_| ()).map_err(|error| error.to_string())
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(Arc::new(RelayRuntime::default()))
        .invoke_handler(tauri::generate_handler![dashboard, preflight, start_sync, stop_sync, reveal])
        .run(tauri::generate_context!())
        .expect("error while running Photo Relay");
}