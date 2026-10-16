#!/data/data/com.termux/files/usr/bin/bash
# Install an OpenCode Zen API key into Ubuntu's opencode.json and restart opencode.
# Usage: bash ~/set-zen-key.sh <ZEN_API_KEY>
# (Get the key from opencode.ai/zen -> sign in -> billing -> copy key.)
set -e
KEY="$1"
if [ -z "$KEY" ]; then
  echo "Usage: bash ~/set-zen-key.sh <ZEN_API_KEY>"
  exit 1
fi
U=/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs
printf '%s' "$KEY" > "$U/root/setup/zen-key.txt"
proot-distro login ubuntu -- node -e "const fs=require('fs');const k=fs.readFileSync('/root/setup/zen-key.txt','utf8').trim();const cfg={\$schema:'https://opencode.ai/config.json',provider:{opencode:{options:{apiKey:k}}}};fs.mkdirSync('/root/.config/opencode',{recursive:true});fs.writeFileSync('/root/.config/opencode/opencode.json',JSON.stringify(cfg,null,2));console.log('opencode.json written');"
rm -f "$U/root/setup/zen-key.txt"
proot-distro login ubuntu -- bash -c "pkill -f 'opencode serve' || true; echo opencode-restart-triggered"
echo "Done. Supervisor will restart opencode with the new key within ~20s."
