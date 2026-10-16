#!/data/data/com.termux/files/usr/bin/bash
# Direct proot launcher for Ubuntu with custom hostname (samsung-s21fe).
# Bypasses `proot-distro login` (which offers no hostname flag) using the
# exact flags proot-distro v5 uses, plus a faked nodename so T3 advertises
# a proper device label instead of "localhost".
# Usage: ubuntu-h.sh <guest-command> [args...]
P=/data/data/com.termux/files/usr
U=$P/var/lib/proot-distro/containers/ubuntu
export HOME=/root USER=root LOGNAME=root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
unset LD_PRELOAD LD_LIBRARY_PATH
exec $P/bin/proot --kill-on-exit --link2symlink --sysvipc \
  '--kernel-release=\Linux\samsung-s21fe\6.17.0-PRoot-Distro\#1 SMP PREEMPT_DYNAMIC Fri, 10 Oct 2025 00:00:00 +0000\aarch64\localdomain\-1\' \
  -L --change-id=0:0 \
  --rootfs=$U/rootfs --cwd=/root \
  --bind=/dev --bind=/proc --bind=/sys --bind=/dev/urandom:/dev/random \
  --bind=$U/sysdata/sys_empty:/sys/fs/selinux \
  --bind=$U/sysdata/loadavg:/proc/loadavg \
  --bind=$U/sysdata/stat:/proc/stat \
  --bind=$U/sysdata/uptime:/proc/uptime \
  --bind=$U/sysdata/version:/proc/version \
  --bind=$U/sysdata/vmstat:/proc/vmstat \
  --bind=$U/sysdata/sysctl_entry_cap_last_cap:/proc/sys/kernel/cap_last_cap \
  --bind=$U/sysdata/sysctl_inotify_max_user_watches:/proc/sys/fs/inotify/max_user_watches \
  --bind=$U/sysdata/sysctl_kernel_overflowuid:/proc/sys/kernel/overflowuid \
  --bind=$U/sysdata/sysctl_kernel_overflowgid:/proc/sys/kernel/overflowgid \
  --bind=$U/sysdata/shm:/dev/shm \
  --bind=/data/app --bind=/data/dalvik-cache --bind=/data/misc/apexdata/com.android.art/dalvik-cache \
  --bind=/storage/self/primary:/mnt/sdcard \
  --bind=/storage/self/primary:/sdcard \
  --bind=/storage/self/primary:/storage/emulated/0 \
  --bind=/storage/self/primary:/storage/self/primary \
  --bind=/data/data/com.termux/cache \
  --bind=/data/data/com.termux/files/home \
  --bind=/apex --bind=/odm --bind=/product --bind=/system --bind=/system/system_ext --bind=/vendor \
  --bind=/linkerconfig/ld.config.txt \
  --bind=/linkerconfig/com.android.art/ld.config.txt \
  --bind=$P \
  "$@"
