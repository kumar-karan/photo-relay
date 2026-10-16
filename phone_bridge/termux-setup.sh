#!/data/data/com.termux/files/usr/bin/bash
# termux-setup.sh — run this ON THE PHONE, inside Termux.
#
# It does not need the phone plugged into anything. Open Termux, paste the line
# from the README (or this file's contents), and the Mac can then reach the
# phone over SSH forever after, including from another network via Tailscale.
#
# Every step here is idempotent. Running it twice is harmless.

set -uo pipefail

# Termux normally exports these from its profile. Under `run-as com.termux` the
# profile is never sourced and HOME points at the app data dir rather than
# files/home, so `~` and $PREFIX mean the wrong place. Setting them here makes
# this script behave identically whether it is launched by a real Termux login,
# by ssh, or by run-as. That consistency is the whole point of the bridge.
export PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export HOME="${TERMUX_HOME:-/data/data/com.termux/files/home}"
export PATH="$PREFIX/bin:$PATH"

PORT=8023
MAC_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJof9pyGGTBqcntIF1Ny3Fgngb3GxVWmmK46kqA0fc8Z karan.8080dev@gmail.com'

echo "1/5  openssh"
pkg install -y openssh termux-services >/dev/null 2>&1 || { echo "   install failed"; exit 1; }
echo "   ok"

echo "2/5  authorising the Mac key"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
# Replace rather than append, so re-running does not stack duplicate lines.
grep -qF "$MAC_KEY" "$HOME/.ssh/authorized_keys" 2>/dev/null \
  || echo "$MAC_KEY" >> "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
echo "   ok"

echo "3/5  host keys and sshd config"
mkdir -p "$PREFIX/etc/ssh"
ssh-keygen -A >/dev/null 2>&1
# Keys only, no passwords. An SSH port open on a home network is a real
# exposure, and a password you have to remember is a weaker control than one
# you cannot brute force.
cat > "$PREFIX/etc/ssh/sshd_config" <<EOF
Port $PORT
PermitRootLogin no
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AllowUsers $(id -un)
Subsystem sftp $PREFIX/libexec/sftp-server
PrintMotd no
EOF
echo "   ok"

echo "4/5  starting sshd"
pkill -f "$PREFIX/bin/sshd" 2>/dev/null
sleep 1
"$PREFIX/bin/sshd" || { echo "   sshd failed to start"; exit 1; }
echo "   running on port $PORT"

echo "5/5  surviving a reboot"
mkdir -p "$PREFIX/var/service/sshd"
cat > "$PREFIX/var/service/sshd/run" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec $PREFIX/bin/sshd -D -e
EOF
chmod 700 "$PREFIX/var/service/sshd/run"
sv-enable sshd 2>/dev/null || true
echo "   ok (needs Termux:Boot installed, which you already have)"

IP="$(ip -4 addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}' | head -1)"
TS="$(ip -4 addr show tailscale0 2>/dev/null | grep -o 'inet [0-9.]*' | awk '{print $2}' | head -1)"

cat <<EOF

  READY

  ssh -p $PORT termux@${IP:-<no wifi>}

  ${TS:+Tailscale address: $TS}
  Tell the Mac one of those and it can connect from anywhere.
EOF
