//! Parser tests pin the engine's log format so UI progress never silently breaks.
//! Each case mirrors a real line shape from `logs/sync_*.log`, with device
//! identifiers redacted.

use super::*;

fn parse(line: &str) -> (RunState, Option<RelayEvent>) {
    let mut state = RunState::default();
    state.begin();
    let event = parse_line(line, &mut state);
    (state, event)
}

#[test]
fn parses_device_status_lines() {
    let (state, event) = parse("[2026-10-03 11:27:03.929] [INFO   ] 📱 iPhone Status       : ✅ DETECTED (UDID-REDACTED (Connection: USB))");
    assert_eq!(event.expect("expected an event").kind, "info");
    assert_eq!(state.devices.get("📱 iPhone Status").map(String::as_str), Some("✅ DETECTED (UDID-REDACTED (Connection: USB))"));
}

#[test]
fn parses_stream_totals() {
    let (state, event) = parse("[2026-10-03 11:27:09.469] [INFO   ] Pipelined Transfer: Streaming 163 files (1984.1 MB) from iPhone while pushing to Samsung...");
    let event = event.expect("expected an event");
    assert_eq!(event.total_files, Some(163));
    assert_eq!(state.total_files, 163);
    assert_eq!(state.total_bytes, 1_984_100_000);
    assert_eq!(event.phase.as_deref(), Some("transferring"));
}

#[test]
fn parses_download_progress() {
    let (state, event) = parse("[2026-10-03 11:27:09.523] [INFO   ]   [  1/163] (  0.6%) Downloaded: IMG_0964.MOV (2.0 MB @ 37.5 MB/s)");
    let event = event.expect("expected an event");
    assert_eq!(event.file.as_deref(), Some("IMG_0964.MOV"));
    assert_eq!(event.completed_files, Some(1));
    assert_eq!(event.total_files, Some(163));
    assert_eq!(event.rate_mbps, Some(37.5));
    assert_eq!(event.size_mb, Some(2.0));
    assert_eq!(event.phase.as_deref(), Some("downloading"));
    assert_eq!(state.current_file, "IMG_0964.MOV");
}

#[test]
fn parses_pushed_line_and_counts_progress() {
    let (state, event) = parse("[2026-10-03 11:28:14.654] [SUCCESS]        ✅ Pushed + timestamp set: IMG_1077.JPG (2.2 MB @ 23.2 MB/s) → 2026-09-27 17:16:41");
    let event = event.expect("expected an event");
    assert_eq!(event.kind, "success");
    assert_eq!(event.file.as_deref(), Some("IMG_1077.JPG"));
    assert_eq!(event.completed_files, Some(1));
    assert_eq!(event.captured_at.as_deref(), Some("2026-09-27 17:16:41"));
    assert_eq!(event.phase.as_deref(), Some("pushing"));
    assert_eq!(event.size_bytes(), Some(2_200_000));
    assert_eq!(state.transferred_bytes, 2_200_000);
}

#[test]
fn parses_conversion_line() {
    let (_, event) = parse("[2026-10-03 11:27:10.279] [INFO   ]        Conversion status: converted (0.73s) -> IMG_0964.JPG");
    let event = event.expect("expected an event");
    assert_eq!(event.phase.as_deref(), Some("converting"));
    assert_eq!(event.file.as_deref(), Some("IMG_0964.JPG"));
}

#[test]
fn parses_media_scanner_phase() {
    let (state, event) = parse("[2026-10-03 11:28:27.231] [INFO   ] 📡 Triggering MediaScanner for 138 files (batch)...");
    assert_eq!(event.expect("expected an event").phase.as_deref(), Some("indexing"));
    assert_eq!(state.phase, "indexing");
}

#[test]
fn parses_final_summary_counts() {
    let (state, event) = parse("[2026-10-03 11:28:31.429] [INFO   ]   ├── Files Pushed to Samsung: 138");
    let event = event.expect("expected an event");
    assert_eq!(event.completed_files, Some(138));
    assert_eq!(state.completed_files, 138);
}

#[test]
fn tracks_errors_separately() {
    let (state, event) = parse("[2026-10-03 11:28:14.654] [ERROR  ] ❌ Failed to push IMG_0001.MOV");
    assert_eq!(event.expect("expected an event").kind, "error");
    assert_eq!(state.errors, 1);
}

#[test]
fn ignores_banner_and_blank_lines() {
    let mut state = RunState::default();
    assert!(parse_line("", &mut state).is_none());
    assert!(parse_line("   ", &mut state).is_none());
}

#[test]
fn unknown_lines_still_surface_as_info() {
    let (_, event) = parse("[2026-10-03 11:27:05.400] [INFO   ] Samsung target contains 4706 existing files.");
    let event = event.expect("expected an event");
    assert_eq!(event.kind, "info");
    assert_eq!(event.message, "Samsung target contains 4706 existing files.");
}
// ---------------------------------------------------------------------------
// End-to-end: replay a real (redacted) run log and assert the UI's view of it.
// ---------------------------------------------------------------------------

/// A trimmed, redacted excerpt of an actual `logs/sync_*.log` run.
const SAMPLE_RUN: &str = include_str!("sample_run.txt");

#[test]
fn replays_a_real_run_into_ui_events() {
    let mut state = RunState::default();
    state.begin();

    let events: Vec<RelayEvent> = SAMPLE_RUN.lines().filter_map(|line| parse_line(line, &mut state)).collect();

    // Every phase the dashboard renders must appear, in pipeline order.
    let phases: Vec<&str> = events.iter().filter_map(|event| event.phase.as_deref()).collect();
    for expected in ["connecting", "scanning", "transferring", "downloading", "converting", "pushing", "indexing", "done"] {
        assert!(phases.contains(&expected), "missing phase {expected} in {phases:?}");
    }

    // Totals come from the "Streaming 163 files (1984.1 MB)" line.
    assert_eq!(state.total_files, 163);
    assert_eq!(state.total_bytes, 1_984_100_000);
    assert!(state.transferred_bytes > 0, "expected bytes to accumulate");
    assert!(state.last_rate_mbps > 0.0, "expected a measured throughput");
    assert_eq!(state.errors, 0);

    // Both devices are reported, and the summary block sets the final count.
    assert!(state.devices.values().any(|value| value.contains("DETECTED")));
    assert!(state.devices.values().any(|value| value.contains("READY")));
    assert_eq!(state.completed_files, 138, "summary block should report 138 pushed files");

    // Live Photos are flagged so the UI can label them.
    assert!(events.iter().any(|event| event.live_photo == Some(true)));

    // The run finishes in the "done" phase and its summary reports the count.
    let last = events.last().expect("expected trailing events");
    assert_eq!(last.phase.as_deref(), Some("done"));
    assert!(
        events.iter().any(|event| event.phase.as_deref() == Some("done") && event.message.contains("Files Pushed to Samsung")),
        "expected the summary block to surface the pushed count"
    );

    // Pure separator banners must not pollute the activity feed.
    assert!(
        !events.iter().any(|event| event.message.trim_start_matches(['=', '-']).is_empty()),
        "separator lines should be filtered out"
    );
}

#[test]
fn sample_fixture_has_no_device_identifiers() {
    assert!(!SAMPLE_RUN.contains("00008150"), "fixture must stay redacted");
    assert!(!SAMPLE_RUN.contains("/Users/"), "fixture must not contain personal paths");
}

// ---------------------------------------------------------------------------
// Project layout assumptions the desktop shell depends on.
// ---------------------------------------------------------------------------

#[test]
fn project_root_resolves_to_this_checkout() {
    let root = crate::project_root();
    assert!(root.join("apps/desktop").is_dir(), "expected apps/desktop under {root:?}");
    assert!(root.join("sync_engine").is_dir(), "expected sync_engine under {root:?}");
    assert!(root.join("runtime").is_dir(), "expected runtime under {root:?}");
}

#[test]
fn project_root_honours_the_env_override() {
    let previous = std::env::var("PHOTO_RELAY_HOME").ok();
    // SAFETY: single-threaded assertion block for this test process.
    unsafe { std::env::set_var("PHOTO_RELAY_HOME", "/tmp/photo-relay-test-home") };
    assert_eq!(crate::project_root(), std::path::PathBuf::from("/tmp/photo-relay-test-home"));
    match previous {
        Some(value) => unsafe { std::env::set_var("PHOTO_RELAY_HOME", value) },
        None => unsafe { std::env::remove_var("PHOTO_RELAY_HOME") },
    }
}

#[test]
fn engine_manifest_and_journal_paths_exist() {
    let engine = crate::engine_root();
    assert!(engine.join("run_sync.sh").exists(), "run_sync.sh must ship with the repo");
    assert!(engine.join("sync.py").exists(), "sync.py must ship with the repo");
    assert!(engine.join("detect_devices.py").exists(), "detect_devices.py must ship with the repo");
    assert!(engine.join("config.example.json").exists(), "config.example.json must ship with the repo");
}

#[test]
fn engine_version_reads_the_pipeline_banner() {
    // Regression: the banner is a logger.log(...) call, so splitting on a bare
    // "v" used to match the one in `level=""` and render `el=""`.
    let version = crate::engine_version(&crate::engine_root());
    assert_eq!(version, "v3", "expected the engine banner version");
    assert!(!version.contains('='), "version must not leak source code: {version}");
}

#[test]
fn offline_devices_are_not_reported_as_connected() {
    // Regression: the UI used to substring-match, and "Not detected" contains
    // "detected", so unplugged phones appeared connected.
    let offline = crate::status_from_line("📱 iPhone 17 Pro Connected : ❌ NO");
    assert!(!offline.online);
    assert_eq!(offline.detail, "Not detected");

    let online = crate::status_from_line("🤖 Samsung Status      : ✅ READY (RZCWXXXXXXX, 43.46GB free)");
    assert!(online.online);
    assert_eq!(online.detail, "43.46 GB free");
}
