# Automated iPhone to Samsung Photo Sync Pipeline

A self-contained, local-only pipeline to sync photos and videos from iPhone 17 Pro to a Samsung Android device for unlimited Google Photos backup.

## Key Features

1. **Incremental Sync & State Tracking**: Maintains `sync_state.json` initialized to your latest photo baseline (`2026-08-05T11:50:15`). Automatically carries forward after every sync.
2. **Lossless Live Photo Conversion**: Converts Apple `.HEIC` + `.MOV` pairs into single-file **Google Motion Photos** (`GCamera:MotionPhoto="1"`) with exact Apple stabilization and EXIF dates.
3. **EXIF Date Preservation**: Keeps original capture timestamps so Google Photos displays images accurately on your timeline.
4. **Android MediaScanner Refresh**: Automatically triggers gallery index refresh via ADB intents.
5. **No Cloud Dependency**: Works 100% locally over USB-C / ADB Wi-Fi without iCloud or paid 3rd-party apps.

---

## Folder Structure

```
iphone_samsung_sync/
├── config.json           # Directory & dependency path configurations
├── sync_state.json        # Persistent watermark state & sync history log
├── sync_pipeline.py      # Master Python engine
├── run_sync.sh           # 1-Click launcher script
└── README.md             # Documentation
```

---

## How to Run

### 1. Place New Photos in Staging Folder
Copy new raw photos/videos from your iPhone 17 Pro to:
`~/Pictures/iphone_staging`

### 2. Connect Samsung Phone via USB / ADB
Ensure USB Debugging is active on your Samsung phone.

### 3. Run Sync Command
From the terminal, run:

```bash
./run_sync.sh
```

## Local Command Center

Run the local dashboard from this copied project:

```bash
./run_command_center.sh
```

Then open [http://127.0.0.1:8766](http://127.0.0.1:8766). It shows the sync
watermark, recent history, the live run log, and provides device preflight and
a confirmation-protected sync trigger. It intentionally binds only to localhost
by default.

### Safe preflight

Use the **Run device preflight** action in the local Command Center before a
real sync. The legacy `--dry-run` argument is not implemented by `sync.py`, so
it must not be used as a safety mechanism.

---

## Configuration (`config.json`)

To change input/output paths or binary locations, edit `config.json`:

```json
{
  "input_dir": "~/Pictures/iphone_staging",
  "converted_dir": "~/Pictures/iphone_converted",
  "phone_target_dir": "/sdcard/DCIM/Camera",
  "adb_bin": "adb",
  "ffmpeg_bin": "ffmpeg",
  "exiftool_bin": "exiftool",
  "state_file": "sync_state.json"
}
```
