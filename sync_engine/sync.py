#!/usr/bin/env python3
"""
==============================================================================
 Master Autonomous iPhone -> Samsung Photo Sync Pipeline (v3 — Optimized)
==============================================================================
 Changelog (v3):
 1. GALLERY FIX: Sets correct file mtime on Samsung via `touch -t` after each
    adb push, using the original photo creation date — so photos, videos, and
    screenshots sort chronologically in Samsung Gallery & Google Photos.
 2. DATES SIDECAR: Saves iPhone st_birthtime for every file into dates.json
    during download. This is the ONLY reliable date source for PNGs/screenshots.
 3. SKIP EXIFTOOL ON PUSH: Uses dates.json instead of spawning ExifTool per file
    during the push phase. ExifTool is still used inside master_converter.py for
    XMP embedding (untouched).
 4. BATCH MEDIASCANNER: Triggers a single `adb shell` script at the end to
    broadcast MEDIA_SCANNER_SCAN_FILE for all pushed files at once.
 5. All prior features retained: Dual logging, atomic downloads, resume, Samsung
    duplicate guard, device unlock checks, per-run + master + JSON logs.
==============================================================================
"""

import os
import sys
import json
import time
import shutil
import asyncio
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = SCRIPT_DIR / "sync_state.json"
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

MASTER_LOG_PATH = LOGS_DIR / "sync_master.log"
HISTORY_JSON_PATH = LOGS_DIR / "run_history.json"
ITEM_BUFFER_DIR = Path("/tmp/iphone_samsung_item_buffer")

# The Live Photo converter is bundled with this project.  Keeping this import
# local means this copy remains runnable outside the old playground directory.
sys.path.insert(0, str(SCRIPT_DIR))
try:
    import master_converter
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False

MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.heif', '.png', '.mov', '.mp4', '.aae', '.dng'}


class DeepLogger:
    """Logs simultaneously to console, master log, and run-specific log file."""
    def __init__(self, run_log_path):
        self.run_log_path = run_log_path

    def log(self, message="", level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        prefix = f"[{timestamp}] [{level:7s}]" if level else ""
        formatted = f"{prefix} {message}".strip() if prefix else message
        print(formatted, flush=True)
        try:
            with open(self.run_log_path, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass
        try:
            with open(MASTER_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception:
            pass

RUN_TIMESTAMP_STR = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_LOG = LOGS_DIR / f"sync_{RUN_TIMESTAMP_STR}.log"
logger = DeepLogger(CURRENT_RUN_LOG)


# ==============================================================================
# Utility Functions
# ==============================================================================

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def load_state():
    if not STATE_PATH.exists():
        return {
            "last_synced_timestamp": "2026-08-05T11:50:15",
            "total_synced_files": 0,
            "status": "IDLE",
            "history": []
        }
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def save_state(state_data):
    with open(STATE_PATH, "w") as f:
        json.dump(state_data, f, indent=2)

def append_history_json(run_entry):
    history = []
    if HISTORY_JSON_PATH.exists():
        try:
            with open(HISTORY_JSON_PATH, "r") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(run_entry)
    with open(HISTORY_JSON_PATH, "w") as f:
        json.dump(history, f, indent=2)

def parse_iso_datetime(dt_str):
    if not dt_str:
        return datetime(1970, 1, 1)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return datetime(1970, 1, 1)

def datetime_to_touch_format(dt):
    """Convert datetime to Android touch -t format: YYYYMMDDhhmm.ss"""
    return dt.strftime("%Y%m%d%H%M.%S")

def parse_afc_time(time_val):
    if isinstance(time_val, datetime):
        return time_val
    if isinstance(time_val, str):
        for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(time_val, fmt)
            except ValueError:
                continue
    if isinstance(time_val, (int, float)):
        try:
            if time_val > 1e15:
                return datetime.fromtimestamp(time_val / 1e9)
            elif time_val > 1e9:
                return datetime.fromtimestamp(time_val)
        except (ValueError, OSError):
            pass
    return None


# ==============================================================================
# Samsung ADB Helpers
# ==============================================================================

def check_samsung_connected(adb_bin):
    """Verifies Samsung ADB status and returns (device_id, state, avail_gb)"""
    try:
        res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=5)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List")]
        if not lines:
            return None, "NO_DEVICE", 0.0
        dev_info = lines[0].split()
        dev_id = dev_info[0]
        dev_state = dev_info[1] if len(dev_info) > 1 else "unknown"
        if dev_state != "device":
            return dev_id, dev_state, 0.0
        df_res = subprocess.run([adb_bin, "shell", "df /sdcard"], capture_output=True, text=True, timeout=5)
        avail_gb = 0.0
        for l in df_res.stdout.splitlines():
            if "/storage/emulated" in l or "/sdcard" in l:
                parts = l.split()
                if len(parts) >= 4:
                    try:
                        avail_gb = int(parts[3]) / (1024 * 1024)
                    except ValueError:
                        pass
        return dev_id, dev_state, avail_gb
    except Exception as e:
        logger.log(f"Samsung ADB check error: {e}", level="WARNING")
        return None, "ERROR", 0.0

def get_samsung_existing_files(adb_bin, target_dir):
    """Retrieves set of existing filenames on Samsung to avoid re-pushing."""
    try:
        res = subprocess.run([adb_bin, "shell", f"ls {target_dir}"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return set(f.strip() for f in res.stdout.splitlines() if f.strip())
    except Exception as e:
        logger.log(f"Could not read Samsung directory listing: {e}", level="WARNING")
    return set()


# ==============================================================================
# Dates Sidecar (dates.json)
# ==============================================================================

DATES_SIDECAR_NAME = "dates.json"

def save_dates_sidecar(staging_dir, dates_map):
    """Save {filename: iso_datetime} map to staging_dir/dates.json"""
    sidecar_path = Path(staging_dir) / DATES_SIDECAR_NAME
    with open(sidecar_path, "w") as f:
        json.dump(dates_map, f, indent=2)

def load_dates_sidecar(staging_dir):
    """Load {filename: iso_datetime} map from staging_dir/dates.json"""
    sidecar_path = Path(staging_dir) / DATES_SIDECAR_NAME
    if sidecar_path.exists():
        try:
            with open(sidecar_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_file_original_date(filename, dates_map, input_dir, exiftool_bin):
    """Get original creation date for a file.
    Priority: dates.json (iPhone st_birthtime) > ExifTool EXIF > file mtime.
    """
    # 1. Try dates.json sidecar (iPhone st_birthtime — works for ALL file types including PNG)
    if filename in dates_map:
        dt = parse_iso_datetime(dates_map[filename])
        if dt > datetime(1970, 1, 1):
            return dt

    # 2. Fallback: Try ExifTool (only works for JPG/HEIC/MOV/MP4, NOT PNG)
    fpath = os.path.join(input_dir, filename)
    if os.path.exists(fpath):
        try:
            cmd_parts = [
                "perl" if "exiftool_src" in exiftool_bin else exiftool_bin,
                exiftool_bin if "exiftool_src" in exiftool_bin else None,
                "-s3", "-DateTimeOriginal", "-CreateDate", fpath
            ]
            cmd_parts = [c for c in cmd_parts if c is not None]
            res = subprocess.run(cmd_parts, capture_output=True, text=True)
            dates = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if dates:
                dt = parse_iso_datetime(dates[0])
                if dt > datetime(1970, 1, 1):
                    return dt
        except Exception:
            pass

        # 3. Last resort: file modification time
        return datetime.fromtimestamp(os.path.getmtime(fpath))

    return datetime(1970, 1, 1)


# ==============================================================================
async def scan_dcim_folders_concurrently(afc, cutoff_dt, concurrency=8):
    """Concurrently scans all DCIM folders on iPhone with bounded semaphore concurrency."""
    dcim_contents = sorted([
        d for d in await afc.listdir('/DCIM/')
        if d not in ('.', '..', '.MISC')
    ])
    logger.log(f"Scanning {len(dcim_contents)} DCIM folders on iPhone (concurrency={concurrency})...", level="INFO")

    sem = asyncio.Semaphore(concurrency)
    scan_start_time = time.time()

    async def scan_single_folder(folder):
        folder_path = f'/DCIM/{folder}'
        try:
            async with sem:
                files = [f for f in await afc.listdir(folder_path) if f not in ('.', '..')]
        except Exception:
            return 0, []

        folder_scanned = 0
        folder_new = []
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue

            folder_scanned += 1
            fpath = f'{folder_path}/{fname}'
            try:
                async with sem:
                    stat = await afc.stat(fpath)
                time_val = stat.get('st_birthtime') or stat.get('st_mtime')
                file_time = parse_afc_time(time_val)

                if file_time and file_time > cutoff_dt:
                    size_bytes = int(stat.get('st_size', 0))
                    folder_new.append({
                        'path': fpath,
                        'name': fname,
                        'folder': folder,
                        'time': file_time,
                        'size': size_bytes,
                        'size_mb': size_bytes / (1024 * 1024)
                    })
            except Exception as e:
                logger.log(f"Stat warning on {fpath}: {e}", level="WARNING")

        return folder_scanned, folder_new

    results = await asyncio.gather(*(scan_single_folder(f) for f in dcim_contents))
    total_scanned = sum(r[0] for r in results)
    new_files = []
    for r in results:
        new_files.extend(r[1])

    scan_duration = time.time() - scan_start_time
    logger.log(f"Scan Complete in {scan_duration:.2f}s: Examined {total_scanned} files across {len(dcim_contents)} folders.", level="INFO")
    logger.log(f"New files found taken after {cutoff_dt}: {len(new_files)}", level="SUCCESS")

    new_files.sort(key=lambda x: x['time'])
    return new_files, total_scanned, len(dcim_contents)


async def pull_from_iphone(cutoff_dt, staging_dir):
    """Pulls new photos from iPhone over USB. Saves dates.json sidecar for timestamp correction."""
    logger.log("Connecting to iPhone over USB...", level="INFO")
    try:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.afc import AfcService
        from pymobiledevice3.exceptions import (
            PasswordRequiredError,
            DeviceHasPasscodeSetError,
            NotPairedError,
            NotTrustedError,
            PairingError,
            PairingDialogResponsePendingError,
            UserDeniedPairingError,
            NoDeviceConnectedError,
            DeviceNotFoundError,
            ConnectionTerminatedError
        )

        try:
            lockdown = await create_using_usbmux()
        except (NoDeviceConnectedError, DeviceNotFoundError, ConnectionTerminatedError):
            logger.log("⚠️  NO IPHONE DETECTED (or disconnected)! Please connect and unlock your iPhone over USB.", level="WARNING")
            return []
        except (PasswordRequiredError, DeviceHasPasscodeSetError):
            logger.log("⚠️  IPHONE IS LOCKED! Please enter your passcode on your iPhone screen to unlock it.", level="ERROR")
            return []
        except (NotPairedError, NotTrustedError, PairingError, PairingDialogResponsePendingError, UserDeniedPairingError) as pe:
            logger.log(f"⚠️  IPHONE PAIRING / TRUST PROMPT PENDING! Please tap 'Trust This Computer' on your iPhone screen. Details: {pe}", level="ERROR")
            return []

        logger.log(f"✅ Connected to iPhone: {lockdown.display_name} (UDID: {lockdown.udid})", level="SUCCESS")

        afc = AfcService(lockdown)
        await afc.connect()

        new_files, total_scanned, total_folders = await scan_dcim_folders_concurrently(afc, cutoff_dt)
        if not new_files:
            return []

        new_files.sort(key=lambda x: x['time'])
        total_mb = sum(f['size_mb'] for f in new_files)
        logger.log(f"Downloading {len(new_files)} new files ({total_mb:.1f} MB total) to staging...", level="INFO")

        downloaded = []
        dates_map = {}  # {filename: iso_datetime_string} — sidecar for timestamp correction
        dl_start_time = time.time()

        for idx, f in enumerate(new_files, 1):
            dest = staging_dir / f['name']
            tmp_dest = staging_dir / f"{f['name']}.tmp"

            # Record the iPhone creation date for this file (used for touch -t on Samsung)
            dates_map[f['name']] = f['time'].isoformat()

            # Skip if already exists with correct size
            if dest.exists() and dest.stat().st_size == f['size']:
                downloaded.append(str(dest))
                logger.log(f"  [{idx:3d}/{len(new_files):3d}] Skipped (Already staged): {f['name']}", level="INFO")
                continue

            file_dl_start = time.time()
            try:
                try:
                    data = await afc.get_file_contents(f['path'])
                    with open(tmp_dest, 'wb') as out:
                        out.write(data)
                except (MemoryError, Exception):
                    with open(tmp_dest, 'wb') as out:
                        handle = await afc.fopen(f['path'], 'r')
                        try:
                            while True:
                                chunk = await handle.read(1024 * 1024)
                                if not chunk:
                                    break
                                out.write(chunk)
                        finally:
                            await handle.close()

                if tmp_dest.exists():
                    os.replace(tmp_dest, dest)

                file_dl_time = time.time() - file_dl_start
                speed_mbps = (f['size_mb'] / file_dl_time) if file_dl_time > 0 else 0
                downloaded.append(str(dest))
                pct = (idx / len(new_files)) * 100
                logger.log(f"  [{idx:3d}/{len(new_files):3d}] ({pct:5.1f}%) Downloaded: {f['name']} ({f['size_mb']:.1f} MB @ {speed_mbps:.1f} MB/s)", level="INFO")
            except Exception as e:
                logger.log(f"  ❌ Download failed for {f['name']}: {e}", level="ERROR")
                if tmp_dest.exists():
                    os.remove(tmp_dest)

        # Save dates sidecar for the push phase
        save_dates_sidecar(staging_dir, dates_map)
        logger.log(f"📋 Saved dates.json sidecar with {len(dates_map)} file dates for Samsung timestamp correction.", level="INFO")

        total_dl_time = time.time() - dl_start_time
        avg_speed = (total_mb / total_dl_time) if total_dl_time > 0 else 0
        logger.log(f"Successfully pulled {len(downloaded)} files ({total_mb:.1f} MB) in {total_dl_time:.2f}s (Avg: {avg_speed:.1f} MB/s).", level="SUCCESS")
        return downloaded

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.log(f"iPhone USB pull error: {e}\n{err_msg}", level="ERROR")
        return []


# ==============================================================================
# Convert & Push to Samsung
# ==============================================================================

def convert_and_push_to_samsung(staged_files, input_dir, config, state):
    """Converts Live Photos to Google Motion Photos, pushes to Samsung,
    sets correct file timestamps, and triggers MediaScanner."""
    adb_bin = config["adb_bin"]
    ffmpeg_bin = config["ffmpeg_bin"]
    exiftool_bin = config["exiftool_bin"]
    phone_target_dir = config["phone_target_dir"]

    dev_id, dev_state, avail_gb = check_samsung_connected(adb_bin)
    if not dev_id or dev_state != "device":
        if dev_state == "unauthorized":
            logger.log("⚠️  SAMSUNG IS UNAUTHORIZED! Please check your Samsung phone screen and tap 'Allow USB Debugging'.", level="ERROR")
        elif dev_state == "offline":
            logger.log("⚠️  SAMSUNG IS OFFLINE! Re-plug Samsung USB cable.", level="ERROR")
        else:
            logger.log("⚠️  SAMSUNG NOT CONNECTED! Please connect your Samsung phone via USB.", level="WARNING")
        return 0, 0, []

    logger.log(f"Connected to Samsung: {dev_id} (State: {dev_state}, Free Space: {avail_gb:.2f} GB)", level="SUCCESS")

    existing_samsung_files = get_samsung_existing_files(adb_bin, phone_target_dir)
    logger.log(f"Samsung target contains {len(existing_samsung_files)} existing files.", level="INFO")

    # Load dates sidecar (iPhone st_birthtime dates for timestamp correction)
    dates_map = load_dates_sidecar(input_dir)
    if dates_map:
        logger.log(f"📋 Loaded dates.json sidecar with {len(dates_map)} file dates. Will skip ExifTool for date lookups.", level="INFO")
    else:
        logger.log("📋 No dates.json sidecar found. Will use ExifTool for date lookups (slower).", level="INFO")

    # Group files by stem
    stems = defaultdict(dict)
    for f in staged_files:
        stem, ext = os.path.splitext(f)
        ext_upper = ext.upper()
        if ext_upper in [".JPG", ".JPEG", ".HEIC", ".HEIF", ".DNG"]:
            stems[stem]["img"] = f
        elif ext_upper in [".MOV", ".MP4"]:
            stems[stem]["mov"] = f
        else:
            stems[stem]["other"] = f

    total_items = len(stems)
    logger.log(f"Grouping: {len(staged_files)} files mapped into {total_items} distinct media items.", level="INFO")

    pushed_count = 0
    skipped_count = 0
    errors_list = []
    latest_dt = parse_iso_datetime(state.get("last_synced_timestamp"))
    pushed_files_for_mediascan = []  # Collect for batch MediaScanner at end

    for idx, (stem, media) in enumerate(stems.items(), 1):
        pct = (idx / total_items) * 100
        is_live_photo = ("img" in media and "mov" in media)
        item_type = "Google Motion Photo (Live Photo)" if is_live_photo else "Standard Media"

        logger.log(f"[{idx:3d}/{total_items:3d}] ({pct:5.1f}%) Processing {stem} ({item_type})...", level="INFO")

        if ITEM_BUFFER_DIR.exists():
            shutil.rmtree(ITEM_BUFFER_DIR)
        ITEM_BUFFER_DIR.mkdir(parents=True, exist_ok=True)

        # Determine original date for this item (from dates.json or ExifTool fallback)
        item_original_date = datetime(1970, 1, 1)
        for k in media:
            fname = media[k]
            dt = get_file_original_date(fname, dates_map, str(input_dir), exiftool_bin)
            if dt > item_original_date:
                item_original_date = dt
        if item_original_date > latest_dt:
            latest_dt = item_original_date

        # Convert using master_converter logic
        master_converter.INPUT_DIR = str(input_dir)
        master_converter.OUTPUT_DIR = str(ITEM_BUFFER_DIR)
        master_converter.EXIFTOOL_BIN = exiftool_bin
        master_converter.FFMPEG_BIN = ffmpeg_bin

        conv_start = time.time()
        try:
            status, name = master_converter.process_single_item((stem, media))
            conv_time = time.time() - conv_start
            logger.log(f"       Conversion status: {status} ({conv_time:.2f}s) -> {name}", level="INFO")
        except Exception as ce:
            err = f"Conversion error on {stem}: {ce}"
            logger.log(f"       ❌ {err}", level="ERROR")
            errors_list.append(err)
            continue

        # Push each converted file to Samsung + immediately fix timestamp
        buf_files = [f for f in os.listdir(ITEM_BUFFER_DIR) if not f.startswith(".")]
        for bf in buf_files:
            if bf in existing_samsung_files:
                skipped_count += 1
                logger.log(f"       ℹ️ Skipped (Already on Samsung): {bf}", level="INFO")
                continue

            src_p = ITEM_BUFFER_DIR / bf
            file_sz_mb = src_p.stat().st_size / (1024 * 1024)
            push_start = time.time()
            cmd = [adb_bin, "push", str(src_p), phone_target_dir]
            res = subprocess.run(cmd, capture_output=True, text=True)
            push_time = time.time() - push_start
            push_speed = (file_sz_mb / push_time) if push_time > 0 else 0

            if res.returncode == 0:
                pushed_count += 1
                existing_samsung_files.add(bf)

                # === GALLERY FIX: Set correct file mtime on Samsung ===
                remote_path = f"{phone_target_dir}/{bf}"
                touch_ts = datetime_to_touch_format(item_original_date)
                touch_cmd = [adb_bin, "shell", f"touch -t {touch_ts} {remote_path}"]
                touch_res = subprocess.run(touch_cmd, capture_output=True, text=True)

                if touch_res.returncode == 0:
                    logger.log(f"       ✅ Pushed + timestamp set: {bf} ({file_sz_mb:.1f} MB @ {push_speed:.1f} MB/s) → {item_original_date.strftime('%Y-%m-%d %H:%M:%S')}", level="SUCCESS")
                else:
                    logger.log(f"       ✅ Pushed: {bf} ({file_sz_mb:.1f} MB @ {push_speed:.1f} MB/s) ⚠️ touch -t failed: {touch_res.stderr.strip()}", level="WARNING")

                # Collect for batch MediaScanner
                pushed_files_for_mediascan.append(bf)
            else:
                err = f"Push error for {bf}: {res.stderr.strip()}"
                logger.log(f"       ❌ {err}", level="ERROR")
                errors_list.append(err)

        # Instant buffer purge
        shutil.rmtree(ITEM_BUFFER_DIR, ignore_errors=True)

        # Delete original staging files
        for k in media:
            p = os.path.join(input_dir, media[k])
            if os.path.exists(p):
                os.remove(p)

    # === BATCH MEDIASCANNER: Single adb shell script for all pushed files ===
    if pushed_files_for_mediascan:
        logger.log(f"📡 Triggering MediaScanner for {len(pushed_files_for_mediascan)} files (batch)...", level="INFO")
        ms_start = time.time()
        # Build a single shell script with all broadcast commands
        broadcast_cmds = []
        for bf in pushed_files_for_mediascan:
            broadcast_cmds.append(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{phone_target_dir}/{bf} > /dev/null 2>&1")
        # Execute in batches of 50 to avoid command-line length limits
        batch_size = 50
        for i in range(0, len(broadcast_cmds), batch_size):
            batch = broadcast_cmds[i:i + batch_size]
            shell_script = " && ".join(batch)
            subprocess.run(
                [adb_bin, "shell", shell_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        ms_time = time.time() - ms_start
        logger.log(f"📡 MediaScanner broadcast completed for {len(pushed_files_for_mediascan)} files in {ms_time:.2f}s.", level="SUCCESS")

    # Clean up dates.json sidecar
    dates_sidecar_path = Path(input_dir) / DATES_SIDECAR_NAME
    if dates_sidecar_path.exists():
        os.remove(dates_sidecar_path)

    # Save state
    if latest_dt > datetime(1970, 1, 1):
        state["last_synced_timestamp"] = latest_dt.isoformat()
    state["total_synced_files"] = state.get("total_synced_files", 0) + pushed_count
    state["status"] = "IDLE"
    state.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "mode": "COMPLETED",
        "newest_photo_exif": latest_dt.isoformat(),
        "count": pushed_count,
        "skipped": skipped_count,
        "errors": len(errors_list)
    })
    save_state(state)

    logger.log(f"Completed! Pushed: {pushed_count}, Skipped: {skipped_count}, Errors: {len(errors_list)}. Watermark updated to {latest_dt}.", level="SUCCESS")
    return pushed_count, skipped_count, errors_list


# ==============================================================================
# Overlapped Pipeline: Push Worker & Pipeline Runner
# ==============================================================================

def push_single_item_to_samsung(item, adb_bin, phone_target_dir, existing_samsung_files, pushed_files_for_mediascan, errors_list, stats):
    """Pushes a single media file to Samsung over ADB, sets its touch timestamp, and cleans up local staging."""
    bf = item["dest_filename"]
    src_p = Path(item["src_path"])
    item_original_date = item["original_date"]
    cleanup_paths = item.get("cleanup_paths", [])

    if bf in existing_samsung_files:
        stats["skipped_count"] += 1
        logger.log(f"       ℹ️ Skipped (Already on Samsung): {bf}", level="INFO")
        for cp in cleanup_paths:
            if os.path.exists(cp):
                try:
                    os.remove(cp)
                except Exception:
                    pass
        return

    if not src_p.exists():
        err = f"Push error: source file does not exist: {src_p}"
        logger.log(f"       ❌ {err}", level="ERROR")
        errors_list.append(err)
        return

    file_sz_mb = src_p.stat().st_size / (1024 * 1024)
    push_start = time.time()
    cmd = [adb_bin, "push", str(src_p), phone_target_dir]
    res = subprocess.run(cmd, capture_output=True, text=True)
    push_time = time.time() - push_start
    push_speed = (file_sz_mb / push_time) if push_time > 0 else 0

    if res.returncode == 0:
        stats["pushed_count"] += 1
        existing_samsung_files.add(bf)

        # GALLERY FIX: Set correct file mtime on Samsung via touch -t
        remote_path = f"{phone_target_dir}/{bf}"
        touch_ts = datetime_to_touch_format(item_original_date)
        touch_cmd = [adb_bin, "shell", f"touch -t {touch_ts} {remote_path}"]
        touch_res = subprocess.run(touch_cmd, capture_output=True, text=True)

        if touch_res.returncode == 0:
            logger.log(f"       ✅ Pushed + timestamp set: {bf} ({file_sz_mb:.1f} MB @ {push_speed:.1f} MB/s) → {item_original_date.strftime('%Y-%m-%d %H:%M:%S')}", level="SUCCESS")
        else:
            logger.log(f"       ✅ Pushed: {bf} ({file_sz_mb:.1f} MB @ {push_speed:.1f} MB/s) ⚠️ touch -t failed: {touch_res.stderr.strip()}", level="WARNING")

        pushed_files_for_mediascan.append(bf)
        if item_original_date > stats["latest_dt"]:
            stats["latest_dt"] = item_original_date
    else:
        err = f"Push error for {bf}: {res.stderr.strip()}"
        logger.log(f"       ❌ {err}", level="ERROR")
        errors_list.append(err)

    # Purge local files
    for cp in cleanup_paths:
        if os.path.exists(cp):
            try:
                os.remove(cp)
            except Exception:
                pass


async def run_sync_pipeline(cutoff_dt, staging_dir, config, state, existing_staged_files):
    """
    High-Performance Overlapped Sync Pipeline:
    1. Concurrent DCIM folder scan (Semaphore bounded).
    2. Overlapped iPhone USB download + background Samsung ADB push queue.
    3. ThreadPool-based Live Photo conversion (Google Motion Photos).
    4. Accurate timestamping (touch -t) & batch MediaScanner broadcast.
    """
    adb_bin = config["adb_bin"]
    ffmpeg_bin = config["ffmpeg_bin"]
    exiftool_bin = config["exiftool_bin"]
    phone_target_dir = config["phone_target_dir"]
    converted_dir = Path(config.get("converted_dir", "/tmp/iphone_samsung_converted"))
    converted_dir.mkdir(parents=True, exist_ok=True)

    existing_samsung_files = get_samsung_existing_files(adb_bin, phone_target_dir)
    logger.log(f"Samsung target contains {len(existing_samsung_files)} existing files.", level="INFO")

    dates_map = load_dates_sidecar(staging_dir)

    # Step 1: Connect to iPhone & perform concurrent DCIM scan
    logger.log("Connecting to iPhone over USB...", level="INFO")
    try:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.afc import AfcService
        from pymobiledevice3.exceptions import (
            PasswordRequiredError,
            DeviceHasPasscodeSetError,
            NotPairedError,
            NotTrustedError,
            PairingError,
            PairingDialogResponsePendingError,
            UserDeniedPairingError,
            NoDeviceConnectedError,
            DeviceNotFoundError,
            ConnectionTerminatedError
        )

        try:
            lockdown = await create_using_usbmux()
        except (NoDeviceConnectedError, DeviceNotFoundError, ConnectionTerminatedError):
            logger.log("⚠️  NO IPHONE DETECTED (or disconnected)! Please connect and unlock your iPhone over USB.", level="WARNING")
            lockdown = None
        except (PasswordRequiredError, DeviceHasPasscodeSetError):
            logger.log("⚠️  IPHONE IS LOCKED! Please enter your passcode on your iPhone screen to unlock it.", level="ERROR")
            lockdown = None
        except (NotPairedError, NotTrustedError, PairingError, PairingDialogResponsePendingError, UserDeniedPairingError) as pe:
            logger.log(f"⚠️  IPHONE PAIRING / TRUST PROMPT PENDING! Details: {pe}", level="ERROR")
            lockdown = None

        new_files = []
        afc = None
        if lockdown:
            logger.log(f"✅ Connected to iPhone: {lockdown.display_name} (UDID: {lockdown.udid})", level="SUCCESS")
            afc = AfcService(lockdown)
            await afc.connect()
            new_files, _, _ = await scan_dcim_folders_concurrently(afc, cutoff_dt)

            for f in new_files:
                dates_map[f['name']] = f['time'].isoformat()
            save_dates_sidecar(staging_dir, dates_map)

        all_candidate_files = set(existing_staged_files) | {f['name'] for f in new_files}
        if not all_candidate_files:
            return 0, 0, []

        # Plan stems
        planned_stems = defaultdict(dict)
        for fname in all_candidate_files:
            stem, ext = os.path.splitext(fname)
            ext_upper = ext.upper()
            if ext_upper in [".JPG", ".JPEG", ".HEIC", ".HEIF", ".DNG"]:
                planned_stems[stem]["img"] = fname
            elif ext_upper in [".MOV", ".MP4"]:
                planned_stems[stem]["mov"] = fname
            else:
                planned_stems[stem]["other"] = fname

        total_items = len(planned_stems)
        logger.log(f"Grouping: {len(all_candidate_files)} files mapped into {total_items} distinct media items.", level="INFO")

        push_queue = asyncio.Queue()
        pushed_files_for_mediascan = []
        errors_list = []
        stats = {
            "pushed_count": 0,
            "skipped_count": 0,
            "latest_dt": parse_iso_datetime(state.get("last_synced_timestamp"))
        }

        # Background consumer task for Samsung ADB push
        async def pusher_worker():
            while True:
                item = await push_queue.get()
                if item is None:
                    push_queue.task_done()
                    break
                try:
                    await asyncio.to_thread(
                        push_single_item_to_samsung,
                        item, adb_bin, phone_target_dir, existing_samsung_files,
                        pushed_files_for_mediascan, errors_list, stats
                    )
                except Exception as pe:
                    logger.log(f"Pusher error on {item.get('dest_filename')}: {pe}", level="ERROR")
                    errors_list.append(str(pe))
                finally:
                    push_queue.task_done()

        pusher_task = asyncio.create_task(pusher_worker())

        # Live Photo conversion handling
        files_ready = set(existing_staged_files)
        submitted_stems = set()
        active_conversion_tasks = []

        def do_convert_sync(stem, media_dict, orig_date):
            master_converter.INPUT_DIR = str(staging_dir)
            master_converter.OUTPUT_DIR = str(converted_dir)
            master_converter.EXIFTOOL_BIN = exiftool_bin
            master_converter.FFMPEG_BIN = ffmpeg_bin
            t0 = time.time()
            try:
                status, out_name = master_converter.process_single_item((stem, media_dict))
                dt = time.time() - t0
                return status, out_name, dt, None
            except Exception as ce:
                return "error", media_dict.get("img", stem), time.time() - t0, ce

        async def run_conversion_and_enqueue(stem, media_dict, orig_date):
            status, out_name, dt, err = await asyncio.to_thread(do_convert_sync, stem, media_dict, orig_date)
            if err:
                logger.log(f"       ❌ Conversion error on {stem}: {err}", level="ERROR")
                errors_list.append(f"Conversion error on {stem}: {err}")
                out_file = converted_dir / out_name
                if not out_file.exists():
                    out_file = staging_dir / media_dict.get("img", "")
            else:
                logger.log(f"       Conversion status: {status} ({dt:.2f}s) -> {out_name}", level="INFO")
                out_file = converted_dir / out_name

            cleanup = [out_file]
            for k in media_dict:
                p = staging_dir / media_dict[k]
                if p != out_file:
                    cleanup.append(p)
            aae_file = staging_dir / f"{stem}.AAE"
            if aae_file.exists():
                cleanup.append(aae_file)

            await push_queue.put({
                "src_path": out_file,
                "dest_filename": out_name,
                "original_date": orig_date,
                "cleanup_paths": cleanup
            })

        def check_stem_ready_and_enqueue(stem):
            if stem in submitted_stems:
                return
            media = planned_stems[stem]
            is_live = ("img" in media and "mov" in media)

            item_orig_dt = datetime(1970, 1, 1)
            for k in media:
                dt = get_file_original_date(media[k], dates_map, str(staging_dir), exiftool_bin)
                if dt > item_orig_dt:
                    item_orig_dt = dt

            if is_live:
                if media["img"] in files_ready and media["mov"] in files_ready:
                    submitted_stems.add(stem)
                    task = asyncio.create_task(run_conversion_and_enqueue(stem, media, item_orig_dt))
                    active_conversion_tasks.append(task)
            else:
                for k in ["img", "mov", "other"]:
                    if k in media and media[k] in files_ready:
                        submitted_stems.add(stem)
                        fname = media[k]
                        cleanup = [staging_dir / fname]
                        aae_file = staging_dir / f"{stem}.AAE"
                        if aae_file.exists():
                            cleanup.append(aae_file)

                        push_queue.put_nowait({
                            "src_path": staging_dir / fname,
                            "dest_filename": fname,
                            "original_date": item_orig_dt,
                            "cleanup_paths": cleanup
                        })
                        break

        # Process any files already in staging
        for stem in list(planned_stems.keys()):
            check_stem_ready_and_enqueue(stem)

        # Overlapped Download loop
        if new_files and afc:
            total_mb = sum(f['size_mb'] for f in new_files)
            logger.log(f"Pipelined Transfer: Streaming {len(new_files)} files ({total_mb:.1f} MB) from iPhone while pushing to Samsung...", level="INFO")
            dl_start_time = time.time()

            for idx, f in enumerate(new_files, 1):
                dest = staging_dir / f['name']
                tmp_dest = staging_dir / f"{f['name']}.tmp"

                if dest.exists() and dest.stat().st_size == f['size']:
                    files_ready.add(f['name'])
                    check_stem_ready_and_enqueue(os.path.splitext(f['name'])[0])
                    logger.log(f"  [{idx:3d}/{len(new_files):3d}] Skipped (Already staged): {f['name']}", level="INFO")
                    continue

                file_dl_start = time.time()
                try:
                    try:
                        data = await afc.get_file_contents(f['path'])
                        with open(tmp_dest, 'wb') as out:
                            out.write(data)
                    except (MemoryError, Exception):
                        with open(tmp_dest, 'wb') as out:
                            handle = await afc.fopen(f['path'], 'r')
                            try:
                                while True:
                                    chunk = await handle.read(1024 * 1024)
                                    if not chunk:
                                        break
                                    out.write(chunk)
                            finally:
                                await handle.close()

                    if tmp_dest.exists():
                        os.replace(tmp_dest, dest)

                    file_dl_time = time.time() - file_dl_start
                    speed_mbps = (f['size_mb'] / file_dl_time) if file_dl_time > 0 else 0
                    pct = (idx / len(new_files)) * 100
                    logger.log(f"  [{idx:3d}/{len(new_files):3d}] ({pct:5.1f}%) Downloaded: {f['name']} ({f['size_mb']:.1f} MB @ {speed_mbps:.1f} MB/s)", level="INFO")

                    files_ready.add(f['name'])
                    stem = os.path.splitext(f['name'])[0]
                    check_stem_ready_and_enqueue(stem)
                except Exception as e:
                    logger.log(f"  ❌ Download failed for {f['name']}: {e}", level="ERROR")
                    if tmp_dest.exists():
                        os.remove(tmp_dest)

            total_dl_time = time.time() - dl_start_time
            avg_speed = (total_mb / total_dl_time) if total_dl_time > 0 else 0
            logger.log(f"Downloads Complete: {len(new_files)} files ({total_mb:.1f} MB) in {total_dl_time:.2f}s (Avg: {avg_speed:.1f} MB/s).", level="SUCCESS")

        # Catch any stranded stems if a companion file failed to download
        for stem, media in planned_stems.items():
            if stem not in submitted_stems:
                for k in ["img", "mov", "other"]:
                    if k in media and media[k] in files_ready:
                        fname = media[k]
                        submitted_stems.add(stem)
                        logger.log(f"  ⚠️ Stem {stem} incomplete; pushing available part {fname} as standalone", level="WARNING")
                        push_queue.put_nowait({
                            "src_path": staging_dir / fname,
                            "dest_filename": fname,
                            "original_date": get_file_original_date(fname, dates_map, str(staging_dir), exiftool_bin),
                            "cleanup_paths": [staging_dir / fname]
                        })

        # Wait for all background conversions to complete
        if active_conversion_tasks:
            logger.log(f"Waiting for {len(active_conversion_tasks)} background Live Photo conversions to complete...", level="INFO")
            await asyncio.gather(*active_conversion_tasks)

        # Signal pusher completion and await drain
        await push_queue.put(None)
        await pusher_task

        # Batch MediaScanner
        if pushed_files_for_mediascan:
            logger.log(f"📡 Triggering MediaScanner for {len(pushed_files_for_mediascan)} files (batch)...", level="INFO")
            ms_start = time.time()
            broadcast_cmds = []
            for bf in pushed_files_for_mediascan:
                broadcast_cmds.append(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{phone_target_dir}/{bf} > /dev/null 2>&1")
            batch_size = 50
            for i in range(0, len(broadcast_cmds), batch_size):
                batch = broadcast_cmds[i:i + batch_size]
                shell_script = " && ".join(batch)
                subprocess.run(
                    [adb_bin, "shell", shell_script],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            ms_time = time.time() - ms_start
            logger.log(f"📡 MediaScanner broadcast completed for {len(pushed_files_for_mediascan)} files in {ms_time:.2f}s.", level="SUCCESS")

        # Clean up sidecar & converted buffer
        dates_sidecar_path = Path(staging_dir) / DATES_SIDECAR_NAME
        if dates_sidecar_path.exists():
            try: os.remove(dates_sidecar_path)
            except Exception: pass

        if converted_dir.exists():
            try: shutil.rmtree(converted_dir, ignore_errors=True)
            except Exception: pass

        # Update State
        latest_dt = stats["latest_dt"]
        if latest_dt > datetime(1970, 1, 1):
            state["last_synced_timestamp"] = latest_dt.isoformat()
        pushed_count = stats["pushed_count"]
        skipped_count = stats["skipped_count"]
        state["total_synced_files"] = state.get("total_synced_files", 0) + pushed_count
        state["status"] = "IDLE"
        state.setdefault("history", []).append({
            "timestamp": datetime.now().isoformat(),
            "mode": "COMPLETED",
            "newest_photo_exif": latest_dt.isoformat(),
            "count": pushed_count,
            "skipped": skipped_count,
            "errors": len(errors_list)
        })
        save_state(state)

        logger.log(f"Completed! Pushed: {pushed_count}, Skipped: {skipped_count}, Errors: {len(errors_list)}. Watermark updated to {latest_dt}.", level="SUCCESS")
        return pushed_count, skipped_count, errors_list

    except Exception as e:
        err_msg = traceback.format_exc()
        logger.log(f"Pipeline error: {e}\n{err_msg}", level="ERROR")
        return 0, 0, [str(e)]


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    start_time = time.time()

    logger.log("=" * 75)
    logger.log(" 🚀 MASTER AUTONOMOUS IPHONE -> SAMSUNG PHOTO SYNC PIPELINE (v3 — Optimized)", level="")
    logger.log("=" * 75)

    config = load_config()
    state = load_state()

    staging_dir = Path(config["input_dir"])
    staging_dir.mkdir(parents=True, exist_ok=True)

    cutoff_str = state.get("last_synced_timestamp", "2026-08-05T11:50:15")
    cutoff_dt = parse_iso_datetime(cutoff_str)

    logger.log(f"Run ID                 : {RUN_TIMESTAMP_STR}", level="INFO")
    logger.log(f"Cutoff Watermark Date : {cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')}", level="INFO")
    logger.log(f"Staging Directory     : {staging_dir}", level="INFO")
    logger.log(f"Run Log File          : {CURRENT_RUN_LOG}", level="INFO")
    logger.log(f"Master Log File       : {MASTER_LOG_PATH}", level="INFO")
    logger.log(f"History JSON Path     : {HISTORY_JSON_PATH}", level="INFO")
    logger.log("-" * 75)

    # Device pre-flight diagnostics
    adb_bin = config["adb_bin"]
    samsung_id, samsung_state, samsung_storage = check_samsung_connected(adb_bin)
    
    # Check iPhone presence early via usbmuxd
    iphone_ready = False
    iphone_desc = "None"
    try:
        import asyncio
        from pymobiledevice3.usbmux import list_devices
        devices = asyncio.run(list_devices())
        if devices:
            iphone_ready = True
            iphone_desc = f"{devices[0].serial} (Connection: {devices[0].connection_type})"
    except Exception as e:
        logger.log(f"usbmux list error: {e}", level="WARNING")

    logger.log(f"📱 iPhone Status       : {'✅ DETECTED (' + iphone_desc + ')' if iphone_ready else '❌ NOT CONNECTED'}", level="INFO")
    logger.log(f"🤖 Samsung Status      : {'✅ READY (' + samsung_id + ', ' + str(round(samsung_storage, 2)) + 'GB free)' if samsung_id and samsung_state == 'device' else '❌ NOT READY (State: ' + str(samsung_state) + ')'}", level="INFO")
    logger.log("-" * 75)

    # PRE-FLIGHT CHECK: Enforce BOTH devices must be connected before starting!
    missing_devices = []
    if not iphone_ready:
        missing_devices.append("iPhone (Please plug in via USB and unlock screen)")
    if not samsung_id or samsung_state != "device":
        missing_devices.append("Samsung (Please plug in via USB, unlock screen, and ensure USB debugging is active)")
    elif samsung_storage < 1.0:
        missing_devices.append(f"Samsung Storage Low ({samsung_storage:.2f} GB free). Minimum 1 GB required.")

    if missing_devices:
        logger.log("⛔ PRE-FLIGHT ABORT: Both devices must be connected and ready to run sync!", level="ERROR")
        for m in missing_devices:
            logger.log(f"   ❌ Missing: {m}", level="ERROR")
        logger.log("=" * 75)
        return

    # Step 1: Check existing files in staging
    staged_files = [f for f in os.listdir(staging_dir) if not f.startswith(".") and not f.endswith(".tmp") and f != DATES_SIDECAR_NAME]

    # Step 2: Run High-Speed Overlapped Pipeline
    pushed, skipped, errors = asyncio.run(
        run_sync_pipeline(cutoff_dt, staging_dir, config, state, staged_files)
    )

    if pushed == 0 and skipped == 0 and len(errors) == 0:
        logger.log("✅ No new photos found to sync. System is completely up to date!", level="SUCCESS")
        logger.log("=" * 75)
        append_history_json({
            "run_id": RUN_TIMESTAMP_STR,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 2),
            "status": "UP_TO_DATE",
            "files_pulled": 0,
            "files_pushed": 0,
            "errors": 0
        })
        return

    elapsed = time.time() - start_time
    logger.log("=" * 75)
    logger.log(" 📊 FINAL EXECUTION SUMMARY", level="")
    logger.log("=" * 75)
    logger.log(f"  ├── Total Elapsed Time     : {elapsed:.2f} seconds")
    logger.log(f"  ├── Files Pushed to Samsung: {pushed}")
    logger.log(f"  ├── Files Skipped          : {skipped}")
    logger.log(f"  ├── Errors Encountered     : {len(errors)}")
    logger.log(f"  ├── New Cutoff Watermark   : {state['last_synced_timestamp']}")
    logger.log(f"  ├── Mac Laptop Storage     : 0 Bytes 🧹 (All temp buffers purged)")
    logger.log(f"  └── Run Log Location       : {CURRENT_RUN_LOG}")
    logger.log("=" * 75)

    append_history_json({
        "run_id": RUN_TIMESTAMP_STR,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "status": "SUCCESS" if len(errors) == 0 else "COMPLETED_WITH_ERRORS",
        "files_staged": len(staged_files),
        "files_pushed": pushed,
        "files_skipped": skipped,
        "errors": len(errors),
        "error_details": errors,
        "watermark": state['last_synced_timestamp']
    })


if __name__ == "__main__":
    main()
