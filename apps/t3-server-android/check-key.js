const fs = require('fs');
const c = JSON.parse(fs.readFileSync('/root/.config/opencode/opencode.json', 'utf8'));
const k = c && c.provider && c.provider.opencode && c.provider.opencode.options && c.provider.opencode.options.apiKey;
console.log('hasKey=' + !!k + ' keyLen=' + (k ? k.length : 0));
