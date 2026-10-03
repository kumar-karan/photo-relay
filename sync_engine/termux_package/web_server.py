#!/usr/bin/env python3
"""
==============================================================================
 Photo Sync Web Server & Mobile Dashboard (Termux Native)
 Runs on Samsung Phone at http://localhost:8080
 Can be added to Home Screen as a standalone web app icon!
==============================================================================
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).parent.resolve()
STATE_PATH = SCRIPT_DIR / "sync_state.json"
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MASTER_LOG = LOGS_DIR / "termux_sync_master.log"

SYNC_PROCESS = None
IS_SYNCING = False
LAST_LOG_LINES = []

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <meta name="theme-color" content="#121212">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <title>Photo Sync</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    body { background: #0f1117; color: #e6edf3; padding: 16px; display: flex; flex-direction: column; min-height: 100vh; }
    .header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 16px; border-bottom: 1px solid #30363d; margin-bottom: 16px; }
    .title { font-size: 20px; font-weight: 700; color: #58a6ff; display: flex; align-items: center; gap: 8px; }
    .status-badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; font-weight: 600; text-transform: uppercase; }
    .badge-idle { background: #238636; color: #fff; }
    .badge-running { background: #d29922; color: #fff; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
    .stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
    .stat-label { color: #8b949e; }
    .stat-val { font-weight: 600; color: #f0f6fc; }
    
    .btn { width: 100%; padding: 16px; font-size: 16px; font-weight: 700; border: none; border-radius: 12px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }
    .btn-sync { background: #1f6feb; color: #ffffff; box-shadow: 0 4px 12px rgba(31, 111, 235, 0.4); }
    .btn-sync:active { transform: scale(0.98); background: #388bfd; }
    .btn-sync:disabled { background: #30363d; color: #8b949e; box-shadow: none; cursor: not-allowed; }
    
    .logs-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .logs-title { font-size: 14px; font-weight: 600; color: #8b949e; }
    .log-box { background: #090d13; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px; color: #7ee787; height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">📱➡️🤖 Photo Sync</div>
    <div id="statusBadge" class="status-badge badge-idle">IDLE</div>
  </div>

  <div class="card">
    <div class="stat-row">
      <span class="stat-label">Last Synced Date</span>
      <span id="lastSynced" class="stat-val">Loading...</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Total Synced Files</span>
      <span id="totalSynced" class="stat-val">Loading...</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">Storage Retained</span>
      <span class="stat-val" style="color: #3fb950;">0 MB (Auto-purged)</span>
    </div>
  </div>

  <button id="syncBtn" class="btn btn-sync" onclick="startSync()">
    <span>🚀</span>
    <span>Start Photo Sync</span>
  </button>

  <div style="margin-top: 16px;">
    <div class="logs-header">
      <span class="logs-title">LIVE EXECUTION LOGS</span>
      <span id="logCounter" style="font-size: 11px; color: #8b949e;">0 lines</span>
    </div>
    <div id="logBox" class="log-box">Awaiting sync execution...</div>
  </div>

  <script>
    let isSyncing = false;

    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        document.getElementById('lastSynced').innerText = data.last_synced_timestamp ? data.last_synced_timestamp.replace('T', ' ').split('.')[0] : 'None';
        document.getElementById('totalSynced').innerText = data.total_synced_files || '0';
        
        isSyncing = data.is_syncing;
        const btn = document.getElementById('syncBtn');
        const badge = document.getElementById('statusBadge');
        
        if (isSyncing) {
          btn.disabled = true;
          btn.innerHTML = '<span>⏳</span><span>Syncing Photos...</span>';
          badge.className = 'status-badge badge-running';
          badge.innerText = 'SYNCING';
        } else {
          btn.disabled = false;
          btn.innerHTML = '<span>🚀</span><span>Start Photo Sync</span>';
          badge.className = 'status-badge badge-idle';
          badge.innerText = 'IDLE';
        }
      } catch (e) {}
    }

    async function fetchLogs() {
      try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        const box = document.getElementById('logBox');
        if (data.logs && data.logs.length > 0) {
          box.innerText = data.logs.join('\\n');
          box.scrollTop = box.scrollHeight;
          document.getElementById('logCounter').innerText = data.logs.length + ' lines';
        }
      } catch (e) {}
    }

    async function startSync() {
      try {
        const res = await fetch('/api/sync', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'started') {
          fetchStatus();
          fetchLogs();
        } else {
          alert(data.message || 'Error starting sync');
        }
      } catch (e) {
        alert('Failed to trigger sync: ' + e);
      }
    }

    setInterval(() => {
      fetchStatus();
      if (isSyncing) {
        fetchLogs();
      }
    }, 1000);

    fetchStatus();
    fetchLogs();
  </script>
</body>
</html>
"""

def load_state():
    if not STATE_PATH.exists():
        return {"last_synced_timestamp": "None", "total_synced_files": 0}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"last_synced_timestamp": "None", "total_synced_files": 0}

def run_sync_worker():
    global IS_SYNCING, SYNC_PROCESS
    IS_SYNCING = True
    script_path = SCRIPT_DIR / "sync_from_iphone.py"
    try:
        SYNC_PROCESS = subprocess.Popen(
            ["python3", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(SCRIPT_DIR)
        )
        for line in iter(SYNC_PROCESS.stdout.readline, ""):
            if line:
                LAST_LOG_LINES.append(line.rstrip())
                if len(LAST_LOG_LINES) > 500:
                    LAST_LOG_LINES.pop(0)
        SYNC_PROCESS.wait()
    except Exception as e:
        LAST_LOG_LINES.append(f"[ERROR] Sync worker error: {e}")
    finally:
        IS_SYNCING = False
        SYNC_PROCESS = None

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/status":
            state = load_state()
            state["is_syncing"] = IS_SYNCING
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(state).encode("utf-8"))
        elif parsed.path == "/api/logs":
            # Read latest lines from MASTER_LOG if LAST_LOG_LINES is empty
            logs = list(LAST_LOG_LINES)
            if not logs and MASTER_LOG.exists():
                try:
                    with open(MASTER_LOG, "r") as f:
                        lines = f.readlines()
                        logs = [l.rstrip() for l in lines[-100:]]
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"logs": logs}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/sync":
            global IS_SYNCING
            if IS_SYNCING:
                self.send_response(409)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "busy", "message": "Sync is already in progress!"}).encode("utf-8"))
                return

            LAST_LOG_LINES.clear()
            t = threading.Thread(target=run_sync_worker, daemon=True)
            t.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet HTTP request logs

def main():
    port = 8080
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🚀 Photo Sync Mobile Dashboard running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        server.server_close()

if __name__ == "__main__":
    main()
