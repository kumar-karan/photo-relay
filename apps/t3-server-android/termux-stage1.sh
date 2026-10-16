#!/data/data/com.termux/files/usr/bin/bash
# Stage 1 (runs in Termux via run-as): base packages + Ubuntu proot.
# Requires: storage permission already granted via adb (pm grant).
set -e
LOG=/sdcard/Download/t3-stage1.log
exec > >(tee -a "$LOG") 2>&1
echo "=== stage1 start $(date) ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y -o Dpkg::Options::="--force-confold" || true
apt-get install -y -o Dpkg::Options::="--force-confold" proot-distro openssh git curl termux-api procps
termux-setup-storage || true
mkdir -p ~/.termux
if ! grep -q '^allow-external-apps=true' ~/.termux/termux.properties 2>/dev/null; then
  echo 'allow-external-apps=true' >> ~/.termux/termux.properties
fi
termux-reload-settings || true
echo "--- installing ubuntu (big download, be patient) ---"
proot-distro install ubuntu
proot-distro login ubuntu -- bash -c 'echo UBUNTU_OK; grep PRETTY /etc/os-release'
echo "=== stage1 DONE $(date) ==="
