#!/usr/bin/env python3
# ==============================================================================
# Device Auto-Detector for iPhone & Samsung
# Detects dual connection vs sequential single connection
# ==============================================================================

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"

def load_config():
    # A fresh clone has only config.example.json, so a missing or unreadable
    # config must fall back to defaults rather than crash detection.
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def pymobiledevice3_command():
    """Resolve the pymobiledevice3 entry point without relying on PATH.

    A .app bundle launched from Finder inherits a minimal PATH that excludes
    Homebrew, so a bare "pymobiledevice3" call reported no iPhone even while
    one was plugged in. Try PATH first, then the usual install locations, then
    the module itself under the interpreter running this script.
    """
    configured = load_config().get("pymobiledevice3_bin")
    if configured and Path(configured).exists():
        return [configured]

    found = shutil.which("pymobiledevice3")
    if found:
        return [found]

    for candidate in ("/opt/homebrew/bin/pymobiledevice3", "/usr/local/bin/pymobiledevice3"):
        if Path(candidate).exists():
            return [candidate]

    return [sys.executable, "-m", "pymobiledevice3"]


def list_iphone_devices():
    # usbmux is the authoritative source: it is the same channel the photo
    # puller uses, so the UI can never disagree with what AFC can actually
    # reach. `system_profiler SPUSBDataType` returns empty output on some
    # macOS releases, which made a connected phone look absent.
    try:
        res = subprocess.run(
            pymobiledevice3_command() + ["usbmux", "list"],
            capture_output=True, text=True, timeout=15,
        )
        if res.returncode != 0:
            return []
        devices = json.loads(res.stdout)
    except Exception:
        return []

    found = []
    for dev in devices if isinstance(devices, list) else []:
        if str(dev.get("DeviceClass", "")).lower() not in ("iphone", "ipad", "ipod"):
            continue
        found.append({
            "name": dev.get("DeviceName", "iPhone"),
            "identifier": dev.get("Identifier", ""),
            "product_type": dev.get("ProductType", ""),
            "connection": dev.get("ConnectionType", "Unknown"),
        })
    return found


def check_iphone_connected(devices=None):
    return bool(list_iphone_devices() if devices is None else devices)


def iphone_connection_label(devices):
    if not devices:
        return ""
    kinds = {d["connection"] for d in devices}
    name = devices[0]["name"]
    if kinds == {"USB"}:
        return f"{name} (USB)"
    if kinds == {"Network"}:
        return f"{name} (Wi-Fi)"
    return f"{name} ({'/'.join(sorted(kinds))})"

def check_samsung_connected(adb_bin):
    try:
        res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=5)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List")]
        devices = [l.split()[0] for l in lines if "device" in l]
        if devices:
            return devices[0]
        return None
    except Exception:
        return None

def detect_scenario():
    config = load_config()
    adb_bin = config.get("adb_bin", "/opt/homebrew/bin/adb")

    iphone_devices = list_iphone_devices()
    iphone_present = bool(iphone_devices)
    samsung_id = check_samsung_connected(adb_bin)

    print("==========================================================================")
    print(" 🔍 USB Device Auto-Detector Results")
    print("==========================================================================")
    iphone_label = iphone_connection_label(iphone_devices)
    print(f" 📱 iPhone 17 Pro Connected : {'✅ YES (' + iphone_label + ')' if iphone_present else '❌ NO'}")
    print(f" 🤖 Samsung Phone Connected : {'✅ YES (' + samsung_id + ')' if samsung_id else '❌ NO'}")
    print("==========================================================================")

    if iphone_present and samsung_id:
        scenario = "SCENARIO_A_DUAL"
        print(" 🎯 Detected Mode: SCENARIO A (Both Devices Connected - Direct 1-by-1 Stream)")
    elif iphone_present and not samsung_id:
        scenario = "SCENARIO_B_IPHONE_ONLY"
        print(" 🎯 Detected Mode: SCENARIO B Phase 1 (iPhone Only Connected - Stage to Temp Vault)")
    elif not iphone_present and samsung_id:
        scenario = "SCENARIO_B_SAMSUNG_ONLY"
        print(" 🎯 Detected Mode: SCENARIO B Phase 2 (Samsung Only Connected - Push Staged & Purge)")
    else:
        scenario = "NO_DEVICES"
        print(" ℹ️ Detected Mode: No syncing devices connected.")
    print("==========================================================================")
    
    return {
        "scenario": scenario,
        "iphone_connected": iphone_present,
        "samsung_id": samsung_id
    }

if __name__ == "__main__":
    detect_scenario()
