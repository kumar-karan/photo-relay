#!/usr/bin/env python3
"""Local command center for the iPhone → Samsung sync engine.

Runs on localhost by default, with no third-party dependencies.  It exposes a
small browser dashboard for safe device preflight checks, starting one sync at
a time, viewing state/history, and reading the current run log.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
STATE_FILE = ROOT / "sync_state.json"
HISTORY_FILE = LOGS / "run_history.json"
RUN_SCRIPT = ROOT / "run_sync.sh"
PREFLIGHT_SCRIPT = ROOT / "detect_devices.py"

runtime_lock = threading.Lock()
runtime = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "result": None,
    "returncode": None,
    "error": None,
}


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback


def tail(path: Path, lines: int = 160) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except OSError:
        return "No log available yet."


def latest_run_log() -> Path | None:
    candidates = sorted(LOGS.glob("sync_[0-9]*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def dashboard_data() -> dict:
    state = read_json(STATE_FILE, {})
    history = read_json(HISTORY_FILE, [])
    log_path = latest_run_log()
    with runtime_lock:
        run = dict(runtime)
    return {
        "state": state,
        "history": history[-12:] if isinstance(history, list) else [],
        "runtime": run,
        "latest_log": log_path.name if log_path else None,
        "log_tail": tail(log_path) if log_path else "No sync run logs have been created yet.",
        "engine_path": str(ROOT),
    }


def run_sync() -> None:
    with runtime_lock:
        runtime.update({
            "running": True,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "result": None,
            "returncode": None,
            "error": None,
        })
    try:
        result = subprocess.run(
            ["bash", str(RUN_SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
        with runtime_lock:
            runtime.update({
                "result": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "error": (result.stderr or result.stdout)[-1200:] or None,
            })
    except subprocess.TimeoutExpired:
        with runtime_lock:
            runtime.update({"result": "timeout", "error": "Sync exceeded the one-hour command-center limit."})
    except Exception as exc:  # keep the dashboard usable if the runner breaks
        with runtime_lock:
            runtime.update({"result": "error", "error": str(exc)})
    finally:
        with runtime_lock:
            runtime.update({"running": False, "finished_at": datetime.now().isoformat(timespec="seconds")})


def run_preflight() -> dict:
    result = subprocess.run(
        [os.environ.get("PYTHON", "python3"), str(PREFLIGHT_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


class CommandCenterHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = DASHBOARD.encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/dashboard":
            self.send_json(dashboard_data())
        else:
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/preflight":
            try:
                self.send_json(run_preflight())
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/sync":
            with runtime_lock:
                if runtime["running"]:
                    self.send_json({"error": "A sync is already running."}, HTTPStatus.CONFLICT)
                    return
                # Mark it busy before creating the thread so two quick browser
                # clicks cannot launch two independent sync processes.
                runtime["running"] = True
                runtime["started_at"] = datetime.now().isoformat(timespec="seconds")
                thread = threading.Thread(target=run_sync, daemon=True)
                thread.start()
            self.send_json({"accepted": True, "message": "Sync started. The dashboard will update automatically."}, HTTPStatus.ACCEPTED)
            return

        self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


DASHBOARD = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Photo Sync Command Center</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#141b31;--line:#283454;--ink:#eef3ff;--muted:#9eabc9;--blue:#6da8ff;--green:#5bddaa;--amber:#ffce71;--red:#ff8383}*{box-sizing:border-box}body{margin:0;font:15px/1.5 ui-sans-serif,system-ui,sans-serif;background:radial-gradient(circle at 75% 0,#1b315b 0,transparent 35%),var(--bg);color:var(--ink)}main{max-width:1180px;margin:auto;padding:36px 20px 64px}h1{margin:0;font-size:30px}.sub{color:var(--muted);margin:4px 0 24px}.grid{display:grid;gap:14px;grid-template-columns:repeat(4,minmax(0,1fr))}.card{background:#141b31dd;border:1px solid var(--line);border-radius:14px;padding:16px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.07em}.value{font-size:22px;font-weight:700;margin-top:5px}.wide{margin-top:14px}.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}button{border:0;border-radius:9px;padding:10px 15px;color:#07101f;background:var(--blue);font-weight:700;cursor:pointer}button.secondary{background:#263757;color:var(--ink)}button:disabled{opacity:.5;cursor:wait}.notice{color:var(--muted)}.ok{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}pre{margin:0;min-height:250px;max-height:520px;overflow:auto;background:#090e1c;border:1px solid var(--line);border-radius:10px;padding:14px;color:#d5e1ff;font:12px/1.5 ui-monospace,SFMono-Regular,monospace}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:9px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){.grid{grid-template-columns:1fr}main{padding-top:22px}}
</style></head><body><main>
<h1>iPhone → Samsung Photo Sync</h1><p class="sub">Local command center · engine state and logs remain on this Mac.</p>
<section class="grid"><div class="card"><div class="label">Engine status</div><div class="value" id="status">Loading…</div></div><div class="card"><div class="label">Synced files</div><div class="value" id="total">—</div></div><div class="card"><div class="label">Watermark</div><div class="value" id="watermark">—</div></div><div class="card"><div class="label">Last run</div><div class="value" id="last">—</div></div></section>
<section class="card wide"><div class="controls"><button class="secondary" id="preflight">Run device preflight</button><button id="sync">Start sync</button><span class="notice" id="message">Start only after both phones are connected and unlocked.</span></div></section>
<section class="card wide"><div class="label" style="margin-bottom:10px">Recent runs</div><div style="overflow:auto"><table><thead><tr><th>Time</th><th>Status</th><th>Pushed</th><th>Duration</th><th>Watermark</th></tr></thead><tbody id="history"></tbody></table></div></section>
<section class="card wide"><div class="label" style="margin-bottom:10px">Live log · <span id="logname">—</span></div><pre id="log">Loading…</pre></section>
</main><script>
const $=id=>document.getElementById(id);const fmt=n=>n==null?'—':Number(n).toLocaleString();
function esc(s){const d=document.createElement('div');d.textContent=s??'—';return d.innerHTML}
async function load(){try{const d=await (await fetch('/api/dashboard')).json(),s=d.state||{},r=d.runtime||{};$('status').textContent=r.running?'SYNC RUNNING':(r.result==='error'?'LAST RUN ERROR':'IDLE');$('status').className='value '+(r.running?'warn':r.result==='error'?'bad':'ok');$('total').textContent=fmt(s.total_synced_files);$('watermark').textContent=(s.last_synced_timestamp||'—').replace('T',' ').slice(0,19);const h=d.history||[],last=h.at(-1)||{};$('last').textContent=last.timestamp?(last.status||last.mode||'completed'):'—';$('logname').textContent=d.latest_log||'no run log';$('log').textContent=d.log_tail||'';$('history').innerHTML=h.slice().reverse().map(x=>`<tr><td>${esc((x.timestamp||'').replace('T',' ').slice(0,19))}</td><td>${esc(x.status||x.mode||'—')}</td><td>${fmt(x.files_pushed??x.count)}</td><td>${x.elapsed_seconds?x.elapsed_seconds+'s':'—'}</td><td>${esc((x.watermark||x.newest_photo_exif||'—').replace('T',' ').slice(0,19))}</td></tr>`).join('');$('sync').disabled=r.running;if(r.running)$('message').textContent='Sync in progress — refreshing every 3 seconds.'}catch(e){$('message').textContent='Dashboard connection failed: '+e.message;$('message').className='bad'}}
$('preflight').onclick=async()=>{const b=$('preflight');b.disabled=true;$('message').textContent='Checking devices…';try{const d=await (await fetch('/api/preflight',{method:'POST'})).json();$('message').textContent=d.ok?'Preflight complete: '+d.output:'Preflight failed: '+(d.output||d.error||'unknown error');$('message').className=d.ok?'ok':'bad'}finally{b.disabled=false}};
$('sync').onclick=async()=>{if(!confirm('Start a real sync now? This may transfer photos and remove successfully processed staging files.'))return;const d=await (await fetch('/api/sync',{method:'POST'})).json();$('message').textContent=d.message||d.error||'Request sent';load()};load();setInterval(load,3000);
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Photo Sync Command Center")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; localhost is the secure default")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), CommandCenterHandler)
    print(f"Photo Sync Command Center: http://{args.host}:{args.port}")
    print("Default binding is localhost; do not expose it publicly.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCommand center stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
