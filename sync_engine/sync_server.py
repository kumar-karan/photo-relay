#!/usr/bin/env python3
"""
==============================================================================
 Lightweight Sync Trigger Server (runs on Mac)
 Listens on port 8765 for sync requests from Samsung Termux.
 Usage: python3 sync_server.py
==============================================================================
"""

import os
import sys
import json
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
SYNC_SCRIPT = SCRIPT_DIR / "sync.py"
MAC_IP = "0.0.0.0"
PORT = 8765

# Track running sync
sync_lock = threading.Lock()
sync_running = False
last_result = {"status": "idle", "message": "No sync has been run yet."}


class SyncHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        global sync_running, last_result

        if self.path == "/status":
            self._send_json(200, {
                "running": sync_running,
                "last_result": last_result
            })

        elif self.path == "/sync":
            if sync_running:
                self._send_json(409, {"error": "Sync already in progress"})
                return

            # Start sync in background thread
            def run_sync():
                global sync_running, last_result
                with sync_lock:
                    sync_running = True
                    last_result = {"status": "running", "started": datetime.now().isoformat()}

                try:
                    python_bin = "/opt/homebrew/bin/python3" if os.path.exists("/opt/homebrew/bin/python3") else sys.executable
                    result = subprocess.run(
                        [python_bin, str(SYNC_SCRIPT)],
                        cwd=str(SCRIPT_DIR),
                        capture_output=True, text=True, timeout=600
                    )
                    last_result = {
                        "status": "success" if result.returncode == 0 else "error",
                        "returncode": result.returncode,
                        "stdout_tail": result.stdout[-2000:] if result.stdout else "",
                        "stderr_tail": result.stderr[-500:] if result.stderr else "",
                        "finished": datetime.now().isoformat()
                    }
                except subprocess.TimeoutExpired:
                    last_result = {"status": "timeout", "message": "Sync timed out after 10 minutes"}
                except Exception as e:
                    last_result = {"status": "error", "message": str(e)}
                finally:
                    sync_running = False

            t = threading.Thread(target=run_sync, daemon=True)
            t.start()
            self._send_json(200, {"message": "Sync started!", "status": "running"})

        elif self.path == "/ping":
            self._send_json(200, {"pong": True, "time": datetime.now().isoformat()})

        else:
            self._send_json(404, {"error": "Unknown endpoint. Use /sync, /status, or /ping"})


def main():
    server = HTTPServer((MAC_IP, PORT), SyncHandler)
    print(f"{'=' * 60}")
    print(f" 📱➡️🤖 Sync Trigger Server Running")
    print(f"{'=' * 60}")
    print(f" Listening on : http://0.0.0.0:{PORT}")
    print(f" Endpoints    : /sync   - Trigger a sync")
    print(f"              : /status - Check sync status")
    print(f"              : /ping   - Health check")
    print(f" Sync Script  : {SYNC_SCRIPT}")
    print(f"{'=' * 60}")
    print(f" From Samsung Termux, run: photosync")
    print(f"{'=' * 60}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
