#!/usr/bin/env bash
# ==============================================================================
# Helper to push updated TermuxSync package to Samsung via ADB
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="${SCRIPT_DIR}/termux_package"
ADB_BIN="/opt/homebrew/bin/adb"

if [ ! -x "$ADB_BIN" ]; then
    ADB_BIN="$(which adb)"
fi

echo "=========================================================================="
echo " 🚀 Deploying Termux Direct Sync Package to Samsung Phone"
echo "=========================================================================="

"$ADB_BIN" shell "mkdir -p /sdcard/TermuxSync"
"$ADB_BIN" push "${PACKAGE_DIR}/." /sdcard/TermuxSync/
"$ADB_BIN" shell "chmod +x /sdcard/TermuxSync/*.sh"

echo "=========================================================================="
echo " ✅ Successfully deployed to /sdcard/TermuxSync on Samsung!"
echo "=========================================================================="
