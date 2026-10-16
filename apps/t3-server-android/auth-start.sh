#!/data/data/com.termux/files/usr/bin/bash
T=/data/data/com.termux/files/home
rm -f $T/auth-tty.log
setsid $T/ubuntu-h.sh bash $T/auth-guest.sh >>$T/auth-tty.log 2>&1 < /dev/null &
echo "started $!"
sleep 25
cat $T/auth-tty.log
