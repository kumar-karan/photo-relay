#!/bin/bash
sed -i 's/^ff02::1.*/ff02::1     ip6-allnodes/' /etc/hosts
cat /etc/hosts
