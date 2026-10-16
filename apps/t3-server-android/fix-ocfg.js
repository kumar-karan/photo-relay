const fs = require('fs');
const p = '/root/.config/opencode/opencode.json';
const raw = fs.readFileSync(p, 'utf8');
let key = '';
const m = raw.match(/apiKey\s*['\"]?\s*:\s*['\"]([^'\"]+)['\"]/);
if (m) key = m[1].trim();
if (!key) { console.log('NO_KEY_FOUND rawLen=' + raw.length); process.exit(1); }
const cfg = { $schema: 'https://opencode.ai/config.json', provider: { opencode: { options: { apiKey: key } } } };
fs.writeFileSync(p + '.bak', raw);
fs.writeFileSync(p, JSON.stringify(cfg, null, 2));
JSON.parse(fs.readFileSync(p, 'utf8'));
console.log('FIXED ok keyLen=' + key.length + ' backup=opencode.json.bak');
