#!/data/data/com.termux/files/usr/bin/bash
set -e
KEY="$1"
/data/data/com.termux/files/home/ubuntu-h.sh bash -c "node -e '
const fs = require(\"fs\");
const file = \"/root/.t3/userdata/settings.json\";
let data = {};
try { data = JSON.parse(fs.readFileSync(file, \"utf8\")); } catch (e) {}
if (!data.providerInstances) data.providerInstances = {};
if (!data.providerInstances.antigravity) data.providerInstances.antigravity = { driver: \"antigravity\", enabled: true };
if (!data.providerInstances.antigravity.config) data.providerInstances.antigravity.config = {};

const k = process.argv[1];
if (k && k !== \"oauth\" && k !== \"clear\") {
  data.providerInstances.antigravity.config.authMethod = \"gemini-api-key\";
  data.providerInstances.antigravity.config.apiKey = k;
} else {
  data.providerInstances.antigravity.config.authMethod = \"oauth-personal\";
  data.providerInstances.antigravity.config.apiKey = \"\";
}
fs.writeFileSync(file, JSON.stringify(data, null, 2));
console.log(\"Saved settings.json for Antigravity\");
' '$KEY'"
/data/data/com.termux/files/home/ubuntu-h.sh bash -c "pkill -f 't3 serve' || true"
/data/data/com.termux/files/usr/bin/termux-toast "Antigravity configuration saved. Reloading..." 2>/dev/null || true
echo "OK"
