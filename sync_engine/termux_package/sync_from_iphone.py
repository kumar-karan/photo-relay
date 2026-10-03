#!/usr/bin/env python3
"""
==============================================================================
 Samsung Termux PhotoSync Client (Mac-Relay Engine)
 Open Termux on Samsung, run `photosync` or `psync` anytime.
 Seamlessly connects to Mac sync server over Wi-Fi/Hotspot/USB.
 Mac handles iPhone pulling + Live Photo conversion + ADB pushing.
 Samsung Gallery and Google Photos update automatically.
==============================================================================
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# ANSI Colors
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

BASE_DIR = Path("/sdcard/TermuxSync")
CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_PORT = 8765
DEFAULT_MAC_IP = "192.168.31.170"


def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                return cfg.get("mac_ip", DEFAULT_MAC_IP), cfg.get("mac_port", DEFAULT_PORT)
        except Exception:
            pass
    return DEFAULT_MAC_IP, DEFAULT_PORT


def save_config(mac_ip, mac_port):
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["mac_ip"] = mac_ip
    cfg["mac_port"] = mac_port
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def curl_json(url, timeout=3):
    try:
        res = subprocess.run(
            ["curl", "-s", "--connect-timeout", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 2
        )
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception:
        pass
    return None


def locate_mac():
    mac_ip, mac_port = load_config()

    # 1. Try USB reverse tethering IP first (when plugged via cable)
    for candidate in ["127.0.0.1", "10.0.2.2", mac_ip]:
        resp = curl_json(f"http://{candidate}:{mac_port}/ping", timeout=1)
        if resp and resp.get("pong"):
            save_config(candidate, mac_port)
            return candidate, mac_port

    print(f"{C_YELLOW}⚠️  Mac not responding at {mac_ip}:{mac_port}{C_RESET}")
    print(f"{C_CYAN}🔍 Discovering Mac on local Wi-Fi subnet...{C_RESET}")

    # Subnet probe
    parts = mac_ip.split(".")
    if len(parts) == 4:
        subnet = ".".join(parts[:3])
        for i in range(1, 255):
            target = f"{subnet}.{i}"
            if target == mac_ip:
                continue
            r = curl_json(f"http://target:{mac_port}/ping", timeout=1)
            if r and r.get("pong"):
                print(f"{C_GREEN}✅ Discovered Mac at {target}:{mac_port}!{C_RESET}")
                save_config(target, mac_port)
                return target, mac_port

    return None, None


def main():
    print(f"\n{C_BOLD}{'=' * 75}{C_RESET}")
    print(f"{C_BOLD} 📱➡️🤖 IPHONE -> SAMSUNG AUTONOMOUS PHOTO SYNC (TERMUX LAUNCHER){C_RESET}")
    print(f"{C_BOLD}{'=' * 75}{C_RESET}")
    print(f"{C_DIM} Triggered from Samsung Termux at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C_RESET}")
    print()

    mac_ip, mac_port = locate_mac()

    if not mac_ip:
        print(f"\n{C_RED}{'=' * 75}{C_RESET}")
        print(f"{C_RED} ❌ CANNOT REACH MAC SYNC SERVER{C_RESET}")
        print(f"{C_RED}{'=' * 75}{C_RESET}")
        print(f" Ensure:")
        print(f"   1. Samsung and Mac are on the same Wi-Fi / Hotspot or connected via USB")
        print(f"   2. Sync daemon is running on Mac:")
        print(f"      {C_CYAN}python3 ~/Funk/agents/playground/iphone_samsung_sync/sync_server.py{C_RESET}")
        print(f"{'=' * 75}\n")
        return 1

    print(f"{C_GREEN}✅ Connected to Mac Sync Engine ({mac_ip}:{mac_port}){C_RESET}")
    print(f"{C_CYAN}🚀 Triggering sync pipeline...{C_RESET}")

    trigger = curl_json(f"http://{mac_ip}:{mac_port}/sync", timeout=5)
    if not trigger:
        print(f"{C_RED}❌ Failed to send trigger signal to Mac.{C_RESET}")
        return 1

    if trigger.get("error"):
        print(f"{C_YELLOW}⚠️  Note: {trigger['error']}{C_RESET}")

    print(f"{C_GREEN}✅ Sync initiated on Mac! Monitoring progress...{C_RESET}\n")

    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    start = time.time()

    while True:
        time.sleep(2.5)
        st = curl_json(f"http://{mac_ip}:{mac_port}/status", timeout=4)
        if not st:
            continue

        if not st.get("running", False):
            res = st.get("last_result", {})
            status = res.get("status")
            print("\r" + " " * 75 + "\r", end="")

            if status == "success":
                print(f"\n{C_BOLD}{'=' * 75}{C_RESET}")
                print(f"{C_GREEN}{C_BOLD} 🎉 SYNC COMPLETED SUCCESSFULLY ON SAMSUNG!{C_RESET}")
                print(f"{C_BOLD}{'=' * 75}{C_RESET}")
                stdout = res.get("stdout_tail", "")
                for l in stdout.split("\n")[-15:]:
                    if l.strip():
                        print(f"  {l}")
                print(f"{'=' * 75}\n")
                return 0
            else:
                print(f"\n{C_RED}{'=' * 75}{C_RESET}")
                print(f"{C_RED} ❌ SYNC ENCOUNTERED AN ISSUE{C_RESET}")
                print(f"{C_RED}{'=' * 75}{C_RESET}")
                for l in res.get("stderr_tail", "").split("\n")[-10:]:
                    if l.strip():
                        print(f"  {C_RED}{l}{C_RESET}")
                print(f"{'=' * 75}\n")
                return 1

        elapsed = int(time.time() - start)
        m, s = divmod(elapsed, 60)
        c = spinner[idx % len(spinner)]
        idx += 1
        print(f"\r  {C_CYAN}{c} Pulling from iPhone & indexing to Samsung Gallery... ({m:02d}m:{s:02d}s){C_RESET}", end="", flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
