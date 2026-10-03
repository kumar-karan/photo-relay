#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 1-Click Termux Sync Launcher (Runs inside Termux on Samsung)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=========================================================================="
echo " 🤖 Direct iPhone -> Samsung Photo Sync Launcher (Termux)"
echo "=========================================================================="

python3 "${SCRIPT_DIR}/sync_from_iphone.py" "$@"
