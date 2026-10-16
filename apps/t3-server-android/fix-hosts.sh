#!/bin/bash
echo "samsung-s21fe" > /etc/hostname
if grep -q "localhost.localdomain" /etc/hosts; then
  sed -i 's/localhost\.localdomain/samsung-s21fe/g' /etc/hosts
  sed -i 's/127\.0\.0\.1.*/127.0.0.1 samsung-s21fe localhost/' /etc/hosts
  sed -i 's/::1.*/::1 samsung-s21fe localhost ip6-localhost ip6-loopback/' /etc/hosts
fi
echo "--- /etc/hostname ---"
cat /etc/hostname
echo "--- /etc/hosts head ---"
head -8 /etc/hosts
echo "--- uname ---"
uname -n
hostname
