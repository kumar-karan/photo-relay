require('http').createServer((q, s) => s.end('probe-ok')).listen(4099, '0.0.0.0', () => console.log('PROBE_LISTENING'));
setTimeout(() => { console.log('PROBE_TIMEOUT'); process.exit(2); }, 60000);
