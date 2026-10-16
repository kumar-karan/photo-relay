#!/data/data/com.termux/files/usr/bin/bash
set -e
KEY="$1"
/data/data/com.termux/files/home/ubuntu-h.sh bash -c "node -e '
const fs = require(\"fs\");
const file = \"/root/.local/share/opencode/auth.json\";
fs.mkdirSync(\"/root/.local/share/opencode\", { recursive: true });
let data = {};
try { data = JSON.parse(fs.readFileSync(file, \"utf8\")); } catch (e) {}
const k = process.argv[1];
if (k && k !== \"clear\") {
  data.opencode = { type: \"api\", key: k };
} else {
  delete data.opencode;
}
fs.writeFileSync(file, JSON.stringify(data, null, 2));
console.log(\"Saved auth.json\");
' '$KEY'"
/data/data/com.termux/files/home/ubuntu-h.sh bash -c "pkill -f 'opencode serve' || true"
/data/data/com.termux/files/usr/bin/termux-toast "OpenCode key saved. Reloading..." 2>/dev/null || true
echo "OK"
