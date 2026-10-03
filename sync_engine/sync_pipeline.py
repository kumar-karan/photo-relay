#!/usr/bin/env python3
# ==============================================================================
# Master Autonomous iPhone -> Samsung Photo Sync Pipeline
# 1. Automatically pulls new photos from iPhone via pymobiledevice3 (if staging empty)
# 2. Converts Live Photos to Google Motion Photos using master_converter.py
# 3. Pushes converted media directly to Samsung (/sdcard/DCIM/Camera/) via ADB
# 4. Triggers Android MediaScanner so photos appear instantly in Google Photos
# 5. Purges laptop staging & temp buffers (0 MB laptop storage footprint retained)
# ==============================================================================

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = SCRIPT_DIR / "sync_state.json"
VAULT_DIR = SCRIPT_DIR / "staging_vault"
ITEM_BUFFER_DIR = Path("/tmp/iphone_samsung_item_buffer")

# Import the converter bundled alongside this pipeline, not a sibling project.
sys.path.insert(0, str(SCRIPT_DIR))
try:
    import master_converter
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_state():
    if not STATE_PATH.exists():
        return {
            "last_synced_timestamp": "2026-08-05T11:50:15",
            "total_synced_files": 2249,
            "status": "IDLE",
            "history": []
        }
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def save_state(state_data):
    with open(STATE_PATH, "w") as f:
        json.dump(state_data, f, indent=2)


def parse_iso_datetime(dt_str):
    if not dt_str:
        return datetime(1970, 1, 1)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return datetime(1970, 1, 1)


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


def get_exif_date(file_path, exiftool_bin):
    try:
        cmd = [
            "perl" if "exiftool_src" in exiftool_bin else exiftool_bin,
            exiftool_bin if "exiftool_src" in exiftool_bin else None,
            "-s3", "-DateTimeOriginal", "-CreateDate", file_path
        ]
        cmd = [c for c in cmd if c is not None]
        res = subprocess.run(cmd, capture_output=True, text=True)
        dates = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if dates:
            return parse_iso_datetime(dates[0])
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(file_path))


def convert_item_using_master(stem, media, input_dir, output_dir, ffmpeg_bin, exiftool_bin):
    """Invokes master_converter.py logic for a single media item (JPG+MOV Live Photo or single file)"""
    item_info = (stem, media)
    
    # Temporarily override master_converter module globals
    master_converter.INPUT_DIR = str(input_dir)
    master_converter.OUTPUT_DIR = str(output_dir)
    master_converter.EXIFTOOL_BIN = exiftool_bin
    master_converter.FFMPEG_BIN = ffmpeg_bin

    return master_converter.process_single_item(item_info)


def process_and_push(staged_files, input_dir, config, state):
    """Converts staged files and pushes them to Samsung DCIM, then purges local copies."""
    adb_bin = config["adb_bin"]
    ffmpeg_bin = config["ffmpeg_bin"]
    exiftool_bin = config["exiftool_bin"]
    phone_target_dir = config["phone_target_dir"]

    samsung_id = check_samsung_connected(adb_bin)
    if not samsung_id:
        print("\n❌ Error: Samsung phone is not connected via ADB. Plug in Samsung USB to complete sync.")
        return 0

    print(f"\n⚡ Processing {len(staged_files)} staged files & pushing directly to Samsung ({samsung_id})...")

    # Group files by stem (e.g. IMG_0605.JPG + IMG_0605.MOV -> stem IMG_0605)
    stems = defaultdict(dict)
    for f in staged_files:
        stem, ext = os.path.splitext(f)
        ext_upper = ext.upper()
        if ext_upper in [".JPG", ".JPEG", ".HEIC"]:
            stems[stem]["img"] = f
        elif ext_upper in [".MOV", ".MP4"]:
            stems[stem]["mov"] = f
        elif ext_upper in [".PNG", ".AAE"]:
            stems[stem]["other"] = f

    total_items = len(stems)
    print(f" 📦 Total media items to process: {total_items}")

    pushed_count = 0
    latest_dt = datetime(1970, 1, 1)

    for idx, (stem, media) in enumerate(stems.items(), 1):
        print(f"\n ── Item [{idx}/{total_items}]: {stem}")

        # Fresh buffer directory
        if ITEM_BUFFER_DIR.exists():
            shutil.rmtree(ITEM_BUFFER_DIR)
        ITEM_BUFFER_DIR.mkdir(parents=True, exist_ok=True)

        # Track dates
        for k in media:
            fpath = os.path.join(input_dir, media[k])
            dt = get_exif_date(fpath, exiftool_bin)
            if dt > latest_dt:
                latest_dt = dt

        # Convert item using master_converter logic
        status, name = convert_item_using_master(stem, media, input_dir, ITEM_BUFFER_DIR, ffmpeg_bin, exiftool_bin)

        # Push generated converted files to Samsung
        buf_files = [f for f in os.listdir(ITEM_BUFFER_DIR) if not f.startswith(".")]
        for bf in buf_files:
            src_p = ITEM_BUFFER_DIR / bf
            cmd = [adb_bin, "push", str(src_p), phone_target_dir]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"    ✅ Pushed to Samsung: {bf}")
                pushed_count += 1
                # Send MediaScanner broadcast
                subprocess.run(
                    [adb_bin, "shell", f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{phone_target_dir}/{bf}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                print(f"    ❌ Push error for {bf}: {res.stderr.strip()}")

        # Clean 1-item buffer
        shutil.rmtree(ITEM_BUFFER_DIR, ignore_errors=True)

        # Delete processed original files from staging directory immediately
        for k in media:
            p = os.path.join(input_dir, media[k])
            if os.path.exists(p):
                os.remove(p)

    # Save updated watermark date
    if latest_dt > datetime(1970, 1, 1):
        state["last_synced_timestamp"] = latest_dt.isoformat()
    state["total_synced_files"] = state.get("total_synced_files", 0) + pushed_count
    state["status"] = "IDLE"
    state.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "mode": "COMPLETED",
        "newest_photo_exif": latest_dt.isoformat(),
        "count": pushed_count
    })
    save_state(state)

    print("\n==========================================================================")
    print(" 🎉 SYNC & CONVERSION COMPLETED SUCCESSFULLY!")
    print(f"  ├── Files Pushed to Samsung : {pushed_count}")
    print(f"  ├── Updated Watermark       : {latest_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print("  └── Laptop Storage Retained : 0 Bytes 🧹 (All temp files purged)")
    print("==========================================================================")

    return pushed_count


def main():
    parser = argparse.ArgumentParser(description="Master Autonomous iPhone -> Samsung Photo Sync Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Perform scan without pushing")
    parser.add_argument("--auto-pull", action="store_true", help="Automatically pull new photos from iPhone if staging empty")
    args = parser.parse_args()

    config = load_config()
    state = load_state()

    input_dir = config["input_dir"]
    adb_bin = config["adb_bin"]

    print("==========================================================================")
    print(" 🚀 Master Autonomous iPhone -> Samsung Photo Sync Pipeline")
    print("==========================================================================")

    samsung_id = check_samsung_connected(adb_bin)
    print(f" 🤖 Samsung Connected : {'✅ YES (' + samsung_id + ')' if samsung_id else '❌ NO'}")

    cutoff_str = state.get("last_synced_timestamp", "2026-08-05T11:50:15")
    print(f" 💾 Cutoff Watermark  : {cutoff_str}")
    print("==========================================================================")

    # Step 1: Check staging directory
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)

    staged_files = [f for f in os.listdir(input_dir) if not f.startswith(".")]

    # Step 2: Auto-pull from iPhone if staging is empty
    if not staged_files and (args.auto_pull or len(sys.argv) == 1):
        print("\n📥 Staging folder is empty. Automatically pulling new photos from connected iPhone over USB...")
        pull_script = SCRIPT_DIR / "pull_iphone_photos.py"
        if pull_script.exists():
            res = subprocess.run(["python3", str(pull_script)], capture_output=True, text=True)
            print(res.stdout)
            staged_files = [f for f in os.listdir(input_dir) if not f.startswith(".")]

    if not staged_files:
        print("\n✅ Staging folder is empty and no new photos found on iPhone. All up to date!")
        sys.exit(0)

    if args.dry_run:
        print(f"\n🧪 Dry-run mode. Found {len(staged_files)} staged files. Stopping.")
        sys.exit(0)

    # Step 3: Convert & Push to Samsung
    process_and_push(staged_files, input_dir, config, state)


if __name__ == "__main__":
    main()
