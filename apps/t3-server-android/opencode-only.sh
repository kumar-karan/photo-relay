#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
exec proot-distro login ubuntu -- /root/servers/start-opencode.sh
