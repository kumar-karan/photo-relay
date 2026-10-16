#!/data/data/com.termux/files/usr/bin/bash
# Stage 3 (runs in Termux via run-as): Boot autostart + Widget 1-tap shortcuts.
set -e
LOG=/sdcard/Download/t3-stage3.log
exec > >(tee -a "$LOG") 2>&1
echo "=== stage3 start $(date) ==="
mkdir -p ~/.termux/boot ~/.shortcuts
cat > ~/.termux/boot/start-servers.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
proot-distro login ubuntu -- /root/servers/start-all.sh
EOF
cat > ~/.shortcuts/start-servers.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
proot-distro login ubuntu -- /root/servers/start-all.sh
termux-toast "Servers started"
EOF
cat > ~/.shortcuts/stop-servers.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login ubuntu -- /root/servers/stop-all.sh
termux-wake-unlock || true
termux-toast "Servers stopped"
EOF
cat > ~/.shortcuts/servers-status.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login ubuntu -- bash -c 'ps aux | grep -E "opencode serve|t3 serve" | grep -v grep; echo ---; tail -5 /root/servers/logs/opencode.log 2>/dev/null; tail -5 /root/servers/logs/t3.log 2>/dev/null'
EOF
chmod +x ~/.termux/boot/start-servers.sh ~/.shortcuts/*.sh
ls -la ~/.termux/boot/ ~/.shortcuts/
echo "=== stage3 DONE $(date) ==="
echo "NOTE: Open Termux:Boot app once and allow it to run at startup."
echo "NOTE: Add Termux:Widget to homescreen for 1-tap start/stop."
