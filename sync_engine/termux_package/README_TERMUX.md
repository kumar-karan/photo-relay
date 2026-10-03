# Direct iPhone -> Samsung Photo Sync Package (Termux Native)

Runs 100% locally on your Samsung phone inside Termux without requiring a Mac or laptop!

## Quick Setup Guide

### 1. Open Termux on Samsung
Launch **Termux** on your Samsung phone.

### 2. Run Automated Setup
Execute:
```bash
bash /sdcard/TermuxSync/setup_termux.sh
```

### 3. Connect iPhone 17 Pro via USB-C Cable
1. Connect USB-C to USB-C cable between iPhone 17 Pro and Samsung.
2. Unlock iPhone screen and tap **Trust This Computer**.

### 4. Run Photo Sync
Inside Termux, execute:
```bash
cd /sdcard/TermuxSync && ./run_termux_sync.sh
```

## How It Works
1. `gphoto2` reads new photos directly over the USB-C cable.
2. Python filters photos taken after `last_synced_timestamp` (`2026-08-05T11:50:15`).
3. Converts Live Photos to single-file Google Motion Photos natively inside Termux using `ffmpeg` + `exiftool`.
4. Saves files straight into `/sdcard/DCIM/Camera/`.
5. Refreshes Android MediaScanner so Google Photos uploads them to Cloud under your unlimited plan!
6. Updates `sync_state.json` and purges temp files.
