#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Automated Setup Script for Direct iPhone -> Samsung Sync
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive

echo "=========================================================================="
echo " 🤖 Setting up Termux Photo Sync..."
echo "=========================================================================="

echo "📦 1. Requesting Storage Permissions..."
termux-setup-storage || true

echo "📦 2. Updating package repositories..."
pkg update -y -o Dpkg::Options::="--force-confold" || true

echo "📦 3. Installing dependencies (Python, FFmpeg, ExifTool, gPhoto2)..."
pkg install -y -o Dpkg::Options::="--force-confold" python ffmpeg exiftool libusb gphoto2 || true

echo "📦 4. Installing global 'photosync' and 'psync' commands into Termux bin..."
PREFIX_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin"
mkdir -p "$PREFIX_BIN"

cat << 'EOF' > "${PREFIX_BIN}/photosync"
#!/data/data/com.termux/files/usr/bin/bash
python3 /sdcard/TermuxSync/sync_from_iphone.py "$@"
EOF
chmod +x "${PREFIX_BIN}/photosync"

cat << 'EOF' > "${PREFIX_BIN}/psync"
#!/data/data/com.termux/files/usr/bin/bash
python3 /sdcard/TermuxSync/sync_from_iphone.py "$@"
EOF
chmod +x "${PREFIX_BIN}/psync"

echo "=========================================================================="
echo " ✅ Setup Complete!"
echo "=========================================================================="
echo " 🚀 You can now type either command from anywhere in Termux:"
echo "    photosync"
echo "    or"
echo "    psync"
echo "=========================================================================="
