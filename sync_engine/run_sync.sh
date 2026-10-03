#!/usr/bin/env bash
# ==============================================================================
# Master Launcher Script for iPhone -> Samsung Autonomous Photo Sync
# Checks tool dependencies and launches sync.py with dual logging.
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Ensure dependencies exist
PYTHON_BIN="/usr/bin/python3"
if [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
fi

ADB_BIN="/opt/homebrew/bin/adb"
if [ ! -x "$ADB_BIN" ]; then
    ADB_BIN="$(which adb)"
fi

echo "=========================================================================="
echo " 📱➡️🤖 iPhone -> Samsung Autonomous Photo Sync"
echo "=========================================================================="
echo " Python Binary : $PYTHON_BIN"
echo " ADB Binary    : $ADB_BIN"
echo "=========================================================================="

"$PYTHON_BIN" "$SCRIPT_DIR/sync.py" "$@"
