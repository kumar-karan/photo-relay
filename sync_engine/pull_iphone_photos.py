#!/usr/bin/env python3
"""
Pull new photos from iPhone over USB using pymobiledevice3.
Only downloads photos taken after the watermark date in sync_state.json.
Zero manual selection. Zero old photos downloaded.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.afc import AfcService

SCRIPT_DIR = Path(__file__).parent.resolve()
STATE_PATH = SCRIPT_DIR / "sync_state.json"
CONFIG_PATH = SCRIPT_DIR / "config.json"

# Photo/video extensions we care about
MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.heif', '.png', '.mov', '.mp4', '.aae', '.dng'}


def load_cutoff():
    """Load the watermark timestamp from sync_state.json"""
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            data = json.load(f)
            ts_str = data.get("last_synced_timestamp", "2026-08-05T11:50:15")
            return datetime.fromisoformat(ts_str)
    return datetime(2026, 8, 5, 11, 50, 15)


def load_staging_dir():
    """Load staging directory from config.json"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
            return Path(cfg.get("input_dir", str(SCRIPT_DIR / "iphone_staging")))
    return SCRIPT_DIR / "iphone_staging"


def parse_afc_time(time_val):
    """Parse AFC stat time value which can be a datetime string or numeric."""
    if isinstance(time_val, datetime):
        return time_val
    if isinstance(time_val, str):
        # Try multiple formats
        for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(time_val, fmt)
            except ValueError:
                continue
    if isinstance(time_val, (int, float)):
        try:
            # Could be unix timestamp or nanoseconds
            if time_val > 1e15:
                return datetime.fromtimestamp(time_val / 1e9)
            elif time_val > 1e9:
                return datetime.fromtimestamp(time_val)
        except (ValueError, OSError):
            pass
    return None


async def scan_and_pull(dry_run=False):
    """Main function: connect to iPhone, find new photos, pull them."""
    cutoff = load_cutoff()
    staging_dir = load_staging_dir()
    staging_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  📱 iPhone Photo Puller (pymobiledevice3)")
    print("=" * 70)
    print(f"  Cutoff date : {cutoff}")
    print(f"  Staging dir : {staging_dir}")
    print(f"  Dry run     : {dry_run}")
    print("=" * 70)

    # Connect
    print("\n🔌 Connecting to iPhone over USB...")
    lockdown = await create_using_usbmux()
    print(f"✅ Connected: {lockdown.display_name}")

    afc = AfcService(lockdown)
    await afc.connect()

    # List all DCIM folders
    dcim_contents = sorted([
        d for d in await afc.listdir('/DCIM/')
        if d not in ('.', '..', '.MISC')
    ])
    print(f"\n📂 Found {len(dcim_contents)} DCIM folders")

    # Scan ALL folders for files after cutoff
    new_files = []
    total_scanned = 0

    for folder in dcim_contents:
        folder_path = f'/DCIM/{folder}'
        try:
            files = [f for f in await afc.listdir(folder_path) if f not in ('.', '..')]
        except Exception:
            continue

        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue

            total_scanned += 1
            fpath = f'{folder_path}/{fname}'

            try:
                stat = await afc.stat(fpath)
                # Use birthtime (creation) or mtime
                time_val = stat.get('st_birthtime') or stat.get('st_mtime')
                file_time = parse_afc_time(time_val)

                if file_time and file_time > cutoff:
                    size_bytes = int(stat.get('st_size', 0))
                    size_mb = size_bytes / (1024 * 1024)
                    new_files.append({
                        'path': fpath,
                        'name': fname,
                        'time': file_time,
                        'size': size_bytes,
                        'size_mb': size_mb
                    })
            except Exception:
                pass

        # Progress
        sys.stdout.write(f"\r  Scanned {folder} ({total_scanned} files checked, {len(new_files)} new found)")
        sys.stdout.flush()

    print(f"\n\n{'=' * 70}")
    print(f"  📊 SCAN RESULTS")
    print(f"  Total files scanned  : {total_scanned}")
    print(f"  New files after cutoff: {len(new_files)}")

    if not new_files:
        print("  ✅ No new photos to sync!")
        print(f"{'=' * 70}")
        return []

    # Sort by time
    new_files.sort(key=lambda x: x['time'])
    total_size_mb = sum(f['size_mb'] for f in new_files)
    print(f"  Total download size  : {total_size_mb:.1f} MB")
    print(f"{'=' * 70}")

    # Print file list
    print("\n📋 New files to download:")
    for i, f in enumerate(new_files, 1):
        print(f"  {i:3d}. {f['name']:30s} | {f['time']} | {f['size_mb']:.1f} MB")

    if dry_run:
        print("\n🔍 DRY RUN — No files downloaded.")
        return new_files

    # Download
    print(f"\n⬇️  Downloading {len(new_files)} files to {staging_dir}...")
    downloaded = []
    for i, f in enumerate(new_files, 1):
        dest = staging_dir / f['name']
        # Handle duplicate names
        if dest.exists():
            stem = dest.stem
            ext = dest.suffix
            counter = 1
            while dest.exists():
                dest = staging_dir / f"{stem}_{counter}{ext}"
                counter += 1

        try:
            data = await afc.get_file_contents(f['path'])
            with open(dest, 'wb') as out:
                out.write(data)
            downloaded.append(str(dest))
            pct = (i / len(new_files)) * 100
            sys.stdout.write(f"\r  [{pct:5.1f}%] Downloaded {i}/{len(new_files)}: {f['name']}")
            sys.stdout.flush()
        except Exception as e:
            print(f"\n  ❌ Failed: {f['name']}: {e}")

    print(f"\n\n✅ Downloaded {len(downloaded)}/{len(new_files)} files to {staging_dir}")
    
    # Update watermark to newest file time
    if new_files:
        newest_time = max(f['time'] for f in new_files)
        with open(STATE_PATH, 'r') as sf:
            state = json.load(sf)
        state['last_synced_timestamp'] = newest_time.isoformat()
        with open(STATE_PATH, 'w') as sf:
            json.dump(state, sf, indent=2)
        print(f"📌 Updated watermark to: {newest_time.isoformat()}")

    return downloaded


def main():
    dry_run = '--dry-run' in sys.argv
    downloaded = asyncio.run(scan_and_pull(dry_run=dry_run))
    
    if downloaded and not dry_run:
        print(f"\n🚀 {len(downloaded)} files staged. Ready for conversion & Samsung push!")
        print(f"   Run: python3 {SCRIPT_DIR}/sync_pipeline.py")

    return len(downloaded) if downloaded else 0


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
