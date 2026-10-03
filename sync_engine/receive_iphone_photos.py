#!/usr/bin/env python3
# ==============================================================================
# Lightweight HTTP Upload Receiver for iOS Shortcuts
# Receives ONLY new photos directly from iPhone over Wi-Fi
# ==============================================================================

import os
import sys
import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = SCRIPT_DIR / "sync_state.json"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class PhotoUploadHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_GET(self):
        if self.path == "/cutoff":
            self._set_headers(200)
            cutoff = "2026-08-05T11:50:15"
            if STATE_PATH.exists():
                try:
                    with open(STATE_PATH, "r") as f:
                        data = json.load(f)
                        cutoff = data.get("last_synced_timestamp", cutoff)
                except Exception:
                    pass
            response = {"cutoff_date": cutoff, "status": "ok"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers.get('Content-Length', 0))
            filename = self.headers.get('X-File-Name', f"iphone_photo_{int(os.path.getmtime(STATE_PATH))}.jpg")
            
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            staging_dir = Path(cfg["input_dir"])
            staging_dir.mkdir(parents=True, exist_ok=True)

            out_path = staging_dir / filename
            with open(out_path, 'wb') as f_out:
                f_out.write(self.rfile.read(content_length))

            print(f"📥 Received file from iPhone: {filename} ({content_length} bytes)")
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "success", "file": filename}).encode('utf-8'))
        elif self.path == "/trigger_sync":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "sync_started"}).encode('utf-8'))
            print("\n🚀 Triggering Samsung sync pipeline...")
            subprocess.Popen(["python3", str(SCRIPT_DIR / "sync_pipeline.py")])
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

def main():
    port = 8500
    local_ip = get_local_ip()
    print("==========================================================================")
    print(" 📡 iOS Direct Photo Receiver Server")
    print("==========================================================================")
    print(f" Local Mac IP : {local_ip}")
    print(f" Listening Port: {port}")
    print(f" Cutoff API   : http://{local_ip}:{port}/cutoff")
    print(f" Upload API   : http://{local_ip}:{port}/upload")
    print("==========================================================================")
    print(" 📱 On your iPhone, run the iOS Shortcut to automatically send ONLY new photos!")
    print("==========================================================================")

    server = HTTPServer(('0.0.0.0', port), PhotoUploadHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.server_close()

if __name__ == "__main__":
    main()
