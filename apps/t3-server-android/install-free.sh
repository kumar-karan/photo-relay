#!/bin/bash
# Installs free-model config into Ubuntu opencode + restarts opencode serve.
cp /root/.config/opencode/opencode.json /root/.config/opencode/opencode.json.stub-bak
cp /data/data/com.termux/files/home/opencode-free.json /root/.config/opencode/opencode.json
node -e "JSON.parse(require('fs').readFileSync('/root/.config/opencode/opencode.json','utf8'));console.log('config valid JSON')"
pkill -f 'opencode serve'
echo "killed, supervisor restarts within ~20s"
