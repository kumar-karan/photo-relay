#!/data/data/com.termux/files/usr/bin/bash
T=/data/data/com.termux/files/home
P=/data/data/com.termux/files/usr/bin
export PATH=$P:/system/bin
export HOME=/root USER=root LOGNAME=root
rm -f $T/auth-login.log
setsid $T/ubuntu-h.sh /usr/local/bin/opencode auth login >>$T/auth-login.log 2>&1 < /dev/null &
echo "auth pid $!"
sleep 12
cat $T/auth-login.log
