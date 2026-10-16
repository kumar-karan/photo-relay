#!/data/data/com.termux/files/usr/bin/bash
T=/data/data/com.termux/files/home
P=/data/data/com.termux/files/usr/bin
export PATH=$P:/system/bin
export HOME=$T
$P/termux-wake-lock 2>/dev/null || true
$P/sshd 2>/dev/null || true
echo "--- starting new session (samsung-s21fe) ---"
setsid $T/ubuntu-h.sh /root/servers/run-foreground.sh >>$T/servers-restart.log 2>&1 < /dev/null &
echo "launcher pid $!"
sleep 6
echo "--- proot cmdline check ---"
pgrep -af "proot.*run-foreground" | head -4
