#!/bin/bash
# Stage 2 (runs INSIDE proot Ubuntu): Node + opencode + t3 + server scripts.
# Expects /root/setup/node-*.tar.xz and /root/setup/opencode-*.tar.gz present.
set -e
LOG=/root/setup/stage2.log
exec > >(tee -a "$LOG") 2>&1
echo "=== ubuntu stage2 start $(date) ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl ca-certificates openssh-client procps
echo "--- node ---"
tar -xJf /root/setup/node-v22.23.3-linux-arm64.tar.xz --strip-components=1 -C /usr/local
node -v
npm -v
echo "--- opencode ---"
tar -xzf /root/setup/opencode-linux-arm64.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/opencode
opencode --version
echo "--- t3 ---"
npm i -g t3@latest
t3 --version || npx -y t3@latest --version || echo "t3 version check skipped"
echo "--- server scripts ---"
mkdir -p /root/servers /root/.config/opencode
SERVER_PASS="t3phone-$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
echo "$SERVER_PASS" > /root/servers/.server-pass
chmod 600 /root/servers/.server-pass
cat > /root/servers/start-opencode.sh <<'EOF'
#!/bin/bash
export OPENCODE_SERVER_PASSWORD="$(cat /root/servers/.server-pass)"
mkdir -p /root/servers/logs
exec /usr/local/bin/opencode serve --hostname 0.0.0.0 --port 4096 >>/root/servers/logs/opencode.log 2>&1
EOF
cat > /root/servers/start-t3.sh <<'EOF'
#!/bin/bash
mkdir -p /root/servers/logs
exec /usr/local/bin/t3 serve --host 0.0.0.0 >>/root/servers/logs/t3.log 2>&1
EOF
cat > /root/servers/start-all.sh <<'EOF'
#!/bin/bash
mkdir -p /root/servers/logs
pkill -f 'opencode serve' 2>/dev/null || true
pkill -f 't3 serve' 2>/dev/null || true
sleep 1
nohup /root/servers/start-opencode.sh >/dev/null 2>&1 &
nohup /root/servers/start-t3.sh >/dev/null 2>&1 &
sleep 3
echo "--- listeners ---"
(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || cat /proc/net/tcp >/dev/null) || true
ps aux | grep -E 'opencode serve|t3 serve' | grep -v grep || true
echo "START_ALL_DONE"
EOF
cat > /root/servers/stop-all.sh <<'EOF'
#!/bin/bash
pkill -f 'opencode serve' || true
pkill -f 't3 serve' || true
echo "STOP_ALL_DONE"
EOF
chmod +x /root/servers/*.sh
# opencode.json with Zen placeholder (API key filled in later step)
cat > /root/.config/opencode/opencode.json <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "opencode": {
      "options": {
        "apiKey": "PASTE_ZEN_API_KEY_HERE"
      }
    }
  }
}
EOF
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
{
  echo "T3-Phone pairing info ($(date))"
  echo "Phone LAN IP: $IP"
  echo "OpenCode web: http://$IP:4096  (password in .server-pass)"
  echo "T3 serve: check t3 pair / logs for URL"
  echo "Server password: $SERVER_PASS"
} > /root/setup/PAIRING-INFO.txt
cat /root/setup/PAIRING-INFO.txt
echo "=== ubuntu stage2 DONE $(date) ==="
