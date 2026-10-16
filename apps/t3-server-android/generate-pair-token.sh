#!/data/data/com.termux/files/usr/bin/bash
set -e
PAIR_OUT=$(/data/data/com.termux/files/home/ubuntu-h.sh /usr/local/bin/t3 pair --ttl 30d 2>&1)
TOKEN=$(echo "$PAIR_OUT" | grep -oE 'token=[A-Z0-9]+' | cut -d= -f2 | head -n 1)
if [ -n "$TOKEN" ]; then
  echo "$TOKEN" > /sdcard/Download/t3-pair-token.txt
  chmod 666 /sdcard/Download/t3-pair-token.txt 2>/dev/null || true
  /data/data/com.termux/files/usr/bin/termux-toast "Minted new 30-day pairing token: $TOKEN" 2>/dev/null || true
  echo "TOKEN: $TOKEN"
else
  /data/data/com.termux/files/usr/bin/termux-toast "Failed to generate pairing token" 2>/dev/null || true
  echo "ERROR"
fi
