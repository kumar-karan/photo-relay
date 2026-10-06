#!/usr/bin/env python3
# ==============================================================================
# Device Auto-Detector for iPhone & Samsung
# Detects dual connection vs sequential single connection
# ==============================================================================

import os
import sys
import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def list_iphone_devices():
    # usbmux is the authoritative source: it is the same channel the photo
    # puller uses, so the UI can never disagree with what AFC can actually
    # reach. `system_profiler SPUSBDataType` returns empty output on some
    # macOS releases, which made a connected phone look absent.
    try:
        res = subprocess.run(
            ["pymobiledevice3", "usbmux", "list"],
            capture_output=True, text=True, timeout=15,
        )
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


def check_iphone_connected():
    return bool(list_iphone_devices())


def iphone_connection_label():
    devices = list_iphone_devices()
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

    iphone_present = check_iphone_connected()
    samsung_id = check_samsung_connected(adb_bin)

    print("==========================================================================")
    print(" 🔍 USB Device Auto-Detector Results")
    print("==========================================================================")
    iphone_label = iphone_connection_label()
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
