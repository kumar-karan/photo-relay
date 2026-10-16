#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
termux-toast "Servers starting (persistent)"
sshd
exec $HOME/ubuntu-h.sh /root/servers/run-foreground.sh
