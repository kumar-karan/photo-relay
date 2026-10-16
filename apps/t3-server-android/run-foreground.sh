#!/bin/bash
# Persistent foreground supervisor for T3-Phone servers.
# MUST stay running: proot-distro uses --kill-on-exit, so if this login
# session ends, the servers are reaped. Respects /root/servers/STOP flag
# (created by Stop) and exits cleanly so Stop actually stops.
mkdir -p /root/servers/logs
rm -f /root/servers/STOP
export OPENCODE_SERVER_PASSWORD="$(cat /root/servers/.server-pass)"
echo "=== supervisor start $(date) ==="
while true; do
  if [ -f /root/servers/STOP ]; then
    echo "$(date) STOP flag set, supervisor exiting"
    exit 0
  fi
  pgrep -f 'opencode serve' >/dev/null || {
    echo "$(date) starting opencode"
    nohup /usr/local/bin/opencode serve --hostname 0.0.0.0 --port 4096 >>/root/servers/logs/opencode.log 2>&1 &
  }
  pgrep -f 't3 serve' >/dev/null || {
    echo "$(date) starting t3"
    nohup /usr/local/bin/t3 serve --mode web --host 0.0.0.0 >>/root/servers/logs/t3.log 2>&1 &
  }
  sleep 20
done
