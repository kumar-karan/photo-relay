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
    time::SystemTime,
};
use tauri::{AppHandle, Emitter, State};

#[derive(Default)]
struct RelayRuntime {
    running: AtomicBool,
    run: Mutex<RunState>,
}

#[derive(Clone, Default)]
struct RunSnapshot {
    phase: String,
    total_files: u64,
    completed_files: u64,
    total_bytes: u64,
    transferred_bytes: u64,
    rate_mbps: f64,
    elapsed_seconds: f64,
    errors: u64,
    current_file: String,
    devices: BTreeMap<String, String>,
}

impl RelayRuntime {
    fn snapshot(&self) -> RunSnapshot {
        let build = |state: &RunState| RunSnapshot {
            phase: state.phase.clone(),
            total_files: state.total_files,
            completed_files: state.completed_files,
            total_bytes: state.total_bytes,
            transferred_bytes: state.transferred_bytes,
            rate_mbps: state.last_rate_mbps,
            elapsed_seconds: engine::elapsed_seconds(state).unwrap_or_default(),
            errors: state.errors,
            current_file: state.current_file.clone(),
            devices: state.devices.clone(),
        };
        match self.run.lock() {
            Ok(state) => build(&state),
            Err(poisoned) => build(&poisoned.into_inner()),
        }
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
    completed_files: u64,
    total_bytes: u64,
    transferred_bytes: u64,
    rate_mbps: f64,
    elapsed_seconds: f64,
    errors: u64,
    current_file: String,
    devices: BTreeMap<String, String>,
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
    format!("{:?}", SystemTime::now())
}

/// Resolve the project root at runtime so a packaged `.app` still finds it.
/// Order: explicit env override, walk up from the executable, then build path.
fn project_root() -> PathBuf {
    if let Ok(configured) = std::env::var("PHOTO_RELAY_HOME") {
        return PathBuf::from(configured);
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(found) = exe
            .ancestors()
            .find(|dir| dir.join("runtime").is_dir() && dir.join("apps").is_dir())
        {
            return found.to_path_buf();
        }
    }
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .unwrap()
        .to_path_buf()
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
        .and_then(|entry| fs::read_to_string(entry.path()).ok())
        .map(|text| {
            text.lines()
                .rev()
                .take(120)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .collect::<Vec<_>>()
                .join("\n")
        })
        .unwrap_or_default()
}

fn engine_version(engine: &Path) -> String {
    fs::read_to_string(engine.join("sync.py"))
        .ok()
        .and_then(|text| {
            text.lines()
                .find(|line| line.contains("MASTER AUTONOMOUS"))
                .map(|line| {
                    line.rsplit('v')
                        .next()
                        .unwrap_or("")
                        .trim_matches(|c| c == ')' || c == ' ' || c == '—')
                        .trim()
                        .to_string()
                })
        })
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "unknown".into())
}

/// Ask the engine which devices it can see, without transferring anything.
fn discover_devices(engine: &Path) -> BTreeMap<String, String> {
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
        if lower.contains("samsung") || lower.contains("android") {
            let online = lower.contains("yes") || (lower.contains('✅') && !lower.contains("no"));
            devices.insert("Samsung".into(), if online { "Connected".into() } else { "Not detected".into() });
        } else if lower.contains("iphone") {
            let online = lower.contains("yes") || (lower.contains('✅') && !lower.contains('❌'));
            devices.insert("iPhone".into(), if online { "Connected".into() } else { "Not detected".into() });
        }
    }
    devices
}

#[tauri::command]
fn dashboard(runtime: State<'_, Arc<RelayRuntime>>) -> Dashboard {
    let engine = engine_root();
    let root = runtime_root();
    let run = runtime.snapshot();

    let state = read_json(engine.join("sync_state.json"), json!({}));
    let devices = if run.devices.is_empty() { discover_devices(&engine) } else { run.devices };

    Dashboard {
        running: runtime.running.load(Ordering::SeqCst),
        engine_found: engine.join("run_sync.sh").exists(),
        phase: run.phase,
        total_files: run.total_files,
        completed_files: run.completed_files,
        total_bytes: run.total_bytes,
        transferred_bytes: run.transferred_bytes,
        rate_mbps: run.rate_mbps,
        elapsed_seconds: run.elapsed_seconds,
        errors: run.errors,
        current_file: run.current_file,
        devices,
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

#[tauri::command]
fn preflight() -> Result<Vec<String>, String> {
    let engine = engine_root();
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
        .map(|line| line.trim_end().to_string())
        .filter(|line| !line.trim().is_empty() && !line.trim_start().starts_with('='))
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

        if let Ok(mut run) = worker.run.lock() {
            run.phase = "idle".into();
        }
        worker.running.store(false, Ordering::SeqCst);
    });

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
        .invoke_handler(tauri::generate_handler![dashboard, preflight, start_sync, reveal])
        .run(tauri::generate_context!())
        .expect("error while running Photo Relay");
}