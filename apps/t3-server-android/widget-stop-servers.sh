#!/data/data/com.termux/files/usr/bin/bash
proot-distro login ubuntu -- bash -c 'touch /root/servers/STOP; pkill -f "opencode serve"; pkill -f "t3 serve"; pkill -f run-foreground; echo stopped'
termux-wake-unlock || true
termux-toast "Servers stopped"
