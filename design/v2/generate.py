#!/usr/bin/env python3
"""Generate three Photo Relay UI directions as fully isolated HTML documents.

Isolation strategy: every variant has its own class prefix (a-/, b-/, c-/) and
its own keyframe prefix. No selector is shared between variants, so the three
can be merged into one comparison page without restyling each other. The shared
design tokens/components are emitted once per prefix. CSS templates use the
sentinel 'S-' (replaced per prefix); markup uses the explicit prefix.
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

PATH_SVG = {
    "phone":  '<rect x="7" y="2.5" width="10" height="19" rx="2.4"/><path d="M10.5 18.5h3"/>',
    "laptop": '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M2 20h20"/>',
    "drive":  '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 12h18"/><circle cx="7" cy="15" r="1"/><circle cx="10.5" cy="15" r="1"/>',
    "check":  '<path d="M20 6 9 17l-5-5"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "refresh":'<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4h-4"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6z"/><path d="M9.5 12l1.8 1.8L15 10"/>',
    "spark":  '<path d="M12 3l1.8 4.8L18.5 9.6l-4.7 1.8L12 16l-1.8-4.6L5.5 9.6l4.7-1.8z"/>',
    "clock":  '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "image":  '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="9.5" r="1.6"/><path d="M4 17l4.5-4.5 3 3L16 11l4 4"/>',
    "film":   '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M8 4.5v15M16 4.5v15M3.5 12h17"/>',
    "layers": '<path d="M12 3 3 8l9 5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "arrow":  '<path d="M4 12h15"/><path d="M13 6l6 6-6 6"/>',
    "x":      '<path d="M7 7l10 10M17 7 7 17"/>',
}

def ic(name, s=16, sw=1.7):
    return (f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{PATH_SVG[name]}</svg>')

# ---------------------------------------------------------------------------
# Shared tokens + components (emitted per prefix). Sentinel S -> prefix.
# ---------------------------------------------------------------------------
SHARED = r"""
.S-root{
  --bg:#0b0b0d; --surface:#141418; --surface-2:#191921; --sunken:#0e0e12;
  --line:rgba(255,255,255,.085); --line-2:rgba(255,255,255,.16);
  --ink:#f4f5f7; --dim:#a2a6b0; --faint:#6d7280;
  --accent:#7d6cff; --accent-soft:rgba(125,108,255,.15); --on-accent:#0c0a1e;
  --good:#43cf93; --warn:#f0b429; --bad:#f2696e; --live:#40c6dd;
  --r:9px; --r2:13px; --rl:18px;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  width:1180px; background:var(--bg); color:var(--ink);
  font-family:var(--sans); font-size:13px; line-height:1.5;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  border:1px solid var(--line); border-radius:var(--rl);
  overflow:hidden; position:relative;
}
.S-root *{box-sizing:border-box}
.S-mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.S-tnum{font-variant-numeric:tabular-nums}
.S-dim{color:var(--dim)}

.S-tb{display:flex;align-items:center;justify-content:space-between;gap:16px;height:48px;padding:0 16px;
  border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--bg) 82%,transparent)}
.S-id{display:flex;align-items:center;gap:10px;min-width:0}
.S-mark{display:grid;place-items:center;width:26px;height:26px;border-radius:8px;color:var(--on-accent);
  background:linear-gradient(140deg,var(--accent),color-mix(in oklab,var(--accent) 45%,var(--live)))}
.S-names{display:flex;flex-direction:column;line-height:1.15;min-width:0}
.S-name{font-size:13px;font-weight:600;letter-spacing:-.01em}
.S-sub{font-size:11px;color:var(--faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.S-tbactions{display:flex;align-items:center;gap:8px}

.S-pill{display:inline-flex;align-items:center;gap:7px;height:26px;padding:0 11px;border-radius:999px;
  background:var(--surface-2);border:1px solid var(--line);font-size:11.5px;font-weight:520;color:var(--dim)}
.S-dot{width:6px;height:6px;border-radius:50%;background:var(--faint)}
.S-pill[data-state="live"]{color:var(--ink)}
.S-pill[data-state="live"] .S-dot{background:var(--live);box-shadow:0 0 0 3px color-mix(in srgb,var(--live) 22%,transparent)}

.S-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;height:30px;padding:0 12px;border-radius:8px;
  border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;font-size:12.5px;font-weight:520;
  white-space:nowrap;cursor:pointer}
.S-btn:hover{background:var(--surface-2);border-color:var(--line-2)}
.S-btn-primary{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.S-btn-primary:hover{background:color-mix(in oklab,var(--accent) 88%,white)}
.S-btn-ghost{background:transparent;border-color:transparent;color:var(--dim)}
.S-btn-ghost:hover{color:var(--ink);background:var(--surface-2)}
.S-btn-danger{background:transparent;border-color:color-mix(in srgb,var(--bad) 42%,transparent);color:var(--bad)}
.S-btn-danger:hover{background:color-mix(in srgb,var(--bad) 12%,transparent)}
.S-iconbtn{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;color:var(--dim);cursor:pointer;border:0;background:none}
.S-iconbtn:hover{color:var(--ink);background:var(--surface-2)}

.S-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r2)}
.S-cardhead{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 15px;border-bottom:1px solid var(--line)}
.S-cardtitle{font-size:12.5px;font-weight:560;letter-spacing:-.005em}
.S-count{font-size:11.5px;color:var(--faint)}

.S-bar{position:relative;height:8px;border-radius:999px;background:var(--sunken);overflow:hidden}
.S-barfill{height:100%;border-radius:inherit;position:relative;overflow:hidden;
  background:linear-gradient(90deg,var(--accent),color-mix(in oklab,var(--accent) 48%,var(--live)))}
.S-barfill::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(90deg,transparent 0 30px,rgba(255,255,255,.5) 42px,transparent 54px);
  animation:S-sheen 1.15s linear infinite}
@keyframes S-sheen{from{background-position:0 0}to{background-position:54px 0}}

.S-led{width:8px;height:8px;border-radius:50%;background:var(--faint);flex:none}
.S-led[data-on="1"]{background:var(--good);box-shadow:0 0 0 3px color-mix(in srgb,var(--good) 18%,transparent)}
.S-led[data-state="live"]{background:var(--live);box-shadow:0 0 0 3px color-mix(in srgb,var(--live) 22%,transparent);animation:S-pulse 1.7s ease-in-out infinite}
@keyframes S-pulse{0%,100%{box-shadow:0 0 0 3px color-mix(in srgb,var(--live) 22%,transparent)}50%{box-shadow:0 0 0 6px color-mix(in srgb,var(--live) 6%,transparent)}}

.S-tag{display:inline-flex;align-items:center;gap:5px;height:19px;padding:0 7px;border-radius:6px;font-size:10.5px;font-weight:540;
  background:var(--accent-soft);color:color-mix(in oklab,var(--accent) 60%,white)}
.S-tag[data-tone="live"]{background:color-mix(in srgb,var(--live) 16%,transparent);color:var(--live)}

.S-row{display:grid;grid-template-columns:20px minmax(0,1fr) auto;align-items:center;gap:10px;padding:8px 15px;border-bottom:1px solid var(--line)}
.S-row:last-child{border-bottom:0}
.S-rowicon{display:grid;place-items:center;width:20px;height:20px;border-radius:6px;background:var(--surface-2);color:var(--dim)}
.S-rowname{font-size:12.5px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.S-rowmeta{display:flex;align-items:center;gap:7px;margin-top:1px;font-size:10.5px;color:var(--faint)}
.S-rowright{display:flex;align-items:center;gap:10px;color:var(--dim)}
.S-rowsize{font-size:11.5px}
.S-check{color:var(--good);display:grid;place-items:center}

.S-steps{position:relative;display:flex;padding:2px 0}
.S-steps::before{content:"";position:absolute;left:calc(100%/12);right:calc(100%/12);top:11px;height:2px;background:var(--line)}
.S-step{position:relative;flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;color:var(--faint)}
.S-step-dot{display:grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1.5px solid var(--line-2);
  background:var(--bg);color:transparent;z-index:1}
.S-step[data-state="done"] .S-step-dot{background:var(--good);border-color:var(--good);color:#06251a}
.S-step[data-state="done"]{color:var(--dim)}
.S-step[data-state="active"]{color:var(--ink)}
.S-step[data-state="active"] .S-step-dot{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.S-step-label{font-size:11.5px;white-space:nowrap}
"""

def tb(p):
    return f'''<header class="{p}-tb">
  <div class="{p}-id">
    <div class="{p}-mark">{ic('spark',14)}</div>
    <div class="{p}-names"><span class="{p}-name">Photo Relay</span><span class="{p}-sub">engine 1.4.2 · iphone-samsung-photo-backup</span></div>
  </div>
  <div class="{p}-tbactions">
    <span class="{p}-pill" data-state="live"><span class="{p}-dot"></span>Pulling</span>
    <button class="{p}-iconbtn">{ic('refresh',15)}</button>
  </div>
</header>'''

FILES = [
    ("IMG_4127.HEIC","4.2 MB",True,"layers"), ("IMG_4126.HEIC","3.9 MB",False,"layers"),
    ("IMG_4125.MOV","88 MB",False,"film"),    ("IMG_4124.HEIC","3.8 MB",True,"layers"),
    ("IMG_4123.HEIC","4.0 MB",False,"layers"),("IMG_4122.HEIC","3.6 MB",True,"layers"),
    ("IMG_4121.MOV","44 MB",False,"film"),    ("IMG_4120.HEIC","3.9 MB",False,"layers"),
    ("IMG_4119.HEIC","4.1 MB",True,"layers"),
]

def file_rows(p, n=8):
    out = []
    for name, size, live, kind in FILES[:n]:
        live_tag = f'<span class="{p}-tagmini">Live Photo</span>' if live else ''
        out.append(f'''<div class="{p}-row">
      <span class="{p}-rowicon">{ic(kind,13)}</span>
      <div><div class="{p}-rowname {p}-mono">{name}</div><div class="{p}-rowmeta">{live_tag}<span>Captured 10:15</span></div></div>
      <span class="{p}-rowright"><span class="{p}-rowsize {p}-mono">{size}</span><span class="{p}-check">{ic('check',13)}</span></span>
    </div>''')
    return "\n".join(out)

def run_rows(p, n=3):
    runs = [("Completed","10 Oct · 23m 24s · 6.4 GB","312 files"),
            ("Completed","9 Oct · 15m 05s · 1.7 GB","88 files"),
            ("Completed","8 Oct · 41m 12s · 9.8 GB","504 files")]
    out = []
    for title, meta, count in runs[:n]:
        out.append(f'''<div class="{p}-row">
      <span class="{p}-rowicon">{ic('check',13)}</span>
      <div><div class="{p}-rowname">{title}</div><div class="{p}-rowmeta"><span>{meta}</span></div></div>
      <span class="{p}-rowright"><span class="{p}-rowsize {p}-mono">{count}</span></span>
    </div>''')
    return "\n".join(out)

def steps(p):
    labels = [("Connect","done"),("Scan","done"),("Pull","active"),("Convert","todo"),("Push","todo"),("Index","todo")]
    out = []
    for name, state in labels:
        dot = ic('check',10,3) if state == "done" else ''
        out.append(f'<div class="{p}-step" data-state="{state}"><span class="{p}-step-dot">{dot}</span><span class="{p}-step-label">{name}</span></div>')
    return f'<div class="{p}-steps">{"".join(out)}</div>'

def ring(p):
    import math
    r = 26.0; c = 2*math.pi*r; off = c*(1-0.81)
    return (f'<svg width="66" height="66" viewBox="0 0 66 66">'
            f'<circle cx="33" cy="33" r="{r}" fill="none" stroke="var(--sunken)" stroke-width="7"/>'
            f'<circle cx="33" cy="33" r="{r}" fill="none" stroke="var(--accent)" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" transform="rotate(-90 33 33)"/>'
            f'<text x="33" y="37.5" text-anchor="middle" font-size="14.5" font-weight="640" fill="var(--ink)">81%</text></svg>')

# ===========================================================================
# A — Transfer window (Transmit-inspired: horizontal, big progress hero)
# ===========================================================================
def A_css(p):
    return r"""
.S-main{padding:14px 16px 16px;display:flex;flex-direction:column;gap:12px}
.S-hero{padding:16px;display:flex;flex-direction:column;gap:12px}
.S-herogrid{display:flex;align-items:flex-end;justify-content:space-between;gap:24px}
.S-pct{display:flex;align-items:baseline;line-height:.95}
.S-pctnum{font-size:52px;font-weight:640;letter-spacing:-.04em}
.S-pctsign{font-size:22px;font-weight:600;color:var(--dim);margin-left:3px}
.S-herosub{margin-top:7px;font-size:12px;color:var(--dim)}
.S-kvs{display:grid;grid-template-columns:auto auto;gap:8px 30px;text-align:right}
.S-kv{display:flex;flex-direction:column;gap:1px;align-items:flex-end}
.S-kvl{font-size:11px;color:var(--faint)}
.S-kvv{font-size:13.5px;font-weight:560}
.S-herofoot{display:flex;align-items:center;justify-content:space-between;gap:12px}
.S-cur{display:flex;align-items:center;gap:8px;min-width:0}
.S-curfile{font-size:12px}
.S-acts{display:flex;align-items:center;gap:8px}
.S-chain{padding:14px 16px}
.S-chainrow{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:10px}
.S-node{display:flex;align-items:center;gap:11px;padding:11px 12px;border-radius:var(--r);background:var(--surface-2);border:1px solid var(--line)}
.S-node[data-active="1"]{border-color:color-mix(in srgb,var(--accent) 45%,transparent);background:color-mix(in srgb,var(--accent) 9%,var(--surface-2))}
.S-nodeicon{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:var(--sunken);color:var(--dim);flex:none}
.S-node[data-active="1"] .S-nodeicon{background:var(--accent);color:var(--on-accent)}
.S-nodetext{min-width:0;flex:1}
.S-nodename{font-size:12.5px;font-weight:560}
.S-nodedetail{font-size:11px;color:var(--faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.S-link{display:flex;flex-direction:column;align-items:center;gap:5px;width:64px;color:var(--faint)}
.S-linktrack{position:relative;width:100%;height:3px;border-radius:999px;background:var(--sunken);overflow:hidden}
.S-linkflow{position:absolute;inset:0;opacity:0;
  background:repeating-linear-gradient(90deg,color-mix(in srgb,var(--accent) 92%,transparent) 0 6px,transparent 6px 16px)}
.S-link[data-active="1"] .S-linkflow{opacity:1;animation:S-flow .8s linear infinite}
@keyframes S-flow{from{background-position:0 0}to{background-position:16px 0}}
.S-linklabel{font-size:10px;letter-spacing:.04em}
.S-bottom{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:12px}
.S-stageswrap{padding:10px 16px}
"""

def A_body(p):
    return f'''<div class="{p}-root">
{tb(p)}
<div class="{p}-main">
  <section class="{p}-hero {p}-card">
    <div class="{p}-herogrid">
      <div>
        <div class="{p}-pct"><span class="{p}-pctnum {p}-tnum">81</span><span class="{p}-pctsign">%</span></div>
        <div class="{p}-herosub">complete · <b>112 of 138</b> files</div>
      </div>
      <div class="{p}-kvs">
        <div class="{p}-kv"><span class="{p}-kvl">Rate</span><span class="{p}-kvv {p}-mono">88 MB/s</span></div>
        <div class="{p}-kv"><span class="{p}-kvl">Time left</span><span class="{p}-kvv {p}-mono">10s</span></div>
        <div class="{p}-kv"><span class="{p}-kvl">Moved</span><span class="{p}-kvv {p}-mono">3.72 GB</span></div>
        <div class="{p}-kv"><span class="{p}-kvl">Total</span><span class="{p}-kvv {p}-mono">4.60 GB</span></div>
      </div>
    </div>
    <div class="{p}-bar"><div class="{p}-barfill" style="width:81%"></div></div>
    <div class="{p}-herofoot">
      <div class="{p}-cur"><span class="{p}-led" data-state="live"></span><span class="{p}-curfile {p}-mono">IMG_4127.HEIC</span><span class="{p}-tag" data-tone="live">Live Photo → Motion</span></div>
      <div class="{p}-acts">
        <button class="{p}-btn {p}-btn-ghost">{ic('shield',14)} Device check</button>
        <button class="{p}-btn {p}-btn-danger">{ic('x',13)} Stop relay</button>
        <button class="{p}-btn">{ic('folder',14)} Data</button>
      </div>
    </div>
  </section>

  <section class="{p}-chain {p}-card">
    <div class="{p}-chainrow">
      <div class="{p}-node" data-active="1"><span class="{p}-nodeicon">{ic('phone',18)}</span><div class="{p}-nodetext"><div class="{p}-nodename">iPhone</div><div class="{p}-nodedetail">iPhone 17 Pro · USB</div></div><span class="{p}-led" data-on="1"></span></div>
      <div class="{p}-link" data-active="1"><span class="{p}-linktrack"><span class="{p}-linkflow"></span></span><span class="{p}-linklabel">USB</span></div>
      <div class="{p}-node" data-active="1"><span class="{p}-nodeicon">{ic('laptop',18)}</span><div class="{p}-nodetext"><div class="{p}-nodename">This Mac</div><div class="{p}-nodedetail">Pulling · converting</div></div><span class="{p}-led" data-state="live"></span></div>
      <div class="{p}-link"><span class="{p}-linktrack"><span class="{p}-linkflow"></span></span><span class="{p}-linklabel">ADB</span></div>
      <div class="{p}-node"><span class="{p}-nodeicon">{ic('drive',18)}</span><div class="{p}-nodetext"><div class="{p}-nodename">Samsung</div><div class="{p}-nodedetail">Galaxy S23 · 118 GB free</div></div><span class="{p}-led" data-on="1"></span></div>
    </div>
  </section>

  <section class="{p}-stageswrap {p}-card">{steps(p)}</section>

  <section class="{p}-bottom">
    <div class="{p}-card">
      <div class="{p}-cardhead"><span class="{p}-cardtitle">Transfers</span><span class="{p}-count">112 of 138</span></div>
      {file_rows(p,8)}
    </div>
    <div class="{p}-card">
      <div class="{p}-cardhead"><span class="{p}-cardtitle">Recent runs</span><span class="{p}-count">last 3</span></div>
      {run_rows(p,3)}
    </div>
  </section>
</div>
</div>'''

# ===========================================================================
# B — Sidebar (Linear-style calm density; persistent rail, single column main)
# ===========================================================================
def B_css(p):
    return r"""
.S-layout{display:grid;grid-template-columns:308px minmax(0,1fr)}
.S-side{border-right:1px solid var(--line);padding:14px;display:flex;flex-direction:column;gap:14px;
  background:color-mix(in srgb,var(--bg) 55%,transparent);min-height:640px}
.S-run{display:flex;align-items:center;gap:14px;padding:13px;border-radius:var(--r2);background:var(--surface);border:1px solid var(--line)}
.S-runtitle{font-size:13px;font-weight:600}
.S-runsub{font-size:11.5px;color:var(--dim);margin-top:2px}
.S-grouplabel{font-size:10.5px;font-weight:560;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);margin-bottom:8px}
.S-dev{display:flex;align-items:center;gap:10px;padding:8px 0}
.S-devn{font-size:12.5px;font-weight:520}
.S-devd{font-size:11px;color:var(--faint)}
.S-actions{display:flex;flex-direction:column;gap:8px}
.S-wide{width:100%}
.S-actionrow{display:flex;gap:8px}
.S-actionrow .S-btn{flex:1}
.S-spacer{flex:1}
.S-foot{font-size:11.5px;color:var(--faint);border-top:1px solid var(--line);padding-top:12px}
.S-main{padding:20px 22px 22px;display:flex;flex-direction:column;gap:16px;min-width:0}
.S-eyebrow{font-size:11px;font-weight:560;letter-spacing:.05em;text-transform:uppercase;color:var(--accent)}
.S-h1{margin:6px 0 8px;font-size:30px;font-weight:640;letter-spacing:-.03em;line-height:1.05}
.S-h1 span{color:var(--faint);font-weight:600}
.S-statline{display:flex;flex-wrap:wrap;align-items:center;gap:9px;font-size:12.5px;color:var(--dim)}
.S-statline b{color:var(--ink);font-weight:560}
.S-statline .S-seps{color:var(--line-2)}
.S-seps{color:var(--faint)}
.S-tabs{display:inline-flex;gap:2px;padding:3px;border-radius:9px;background:var(--surface-2);border:1px solid var(--line);align-self:flex-start}
.S-tab{padding:5px 12px;border-radius:7px;border:0;background:none;color:var(--dim);font:inherit;font-size:12px;font-weight:520;cursor:pointer}
.S-tab[data-active="1"]{background:var(--surface);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.3)}
.S-list{flex:1;min-height:0}
"""

def B_body(p):
    return f'''<div class="{p}-root">
{tb(p)}
<div class="{p}-layout">
  <aside class="{p}-side">
    <div class="{p}-run">
      {ring(p)}
      <div>
        <div class="{p}-runtitle">Pulling</div>
        <div class="{p}-runsub">112 of 138 files</div>
        <div class="{p}-runsub">3.72 of 4.60 GB</div>
      </div>
    </div>
    <div>
      <div class="{p}-grouplabel">Devices</div>
      <div class="{p}-dev"><span class="{p}-led" data-on="1"></span><div><div class="{p}-devn">iPhone 17 Pro</div><div class="{p}-devd">USB · trusted</div></div></div>
      <div class="{p}-dev"><span class="{p}-led" data-on="1"></span><div><div class="{p}-devn">Galaxy S23</div><div class="{p}-devd">ADB · 118 GB free</div></div></div>
    </div>
    <div class="{p}-actions">
      <button class="{p}-btn {p}-btn-primary {p}-wide">{ic('spark',14)} Start relay</button>
      <div class="{p}-actionrow">
        <button class="{p}-btn {p}-btn-ghost">{ic('shield',14)} Device check</button>
        <button class="{p}-btn {p}-btn-ghost">{ic('folder',14)} Data</button>
      </div>
    </div>
    <div class="{p}-spacer"></div>
    <div class="{p}-foot">2,796 files secured in total</div>
  </aside>

  <main class="{p}-main">
    <div>
      <div class="{p}-eyebrow">Now relaying</div>
      <h1 class="{p}-h1">Pulling <span>from iPhone</span></h1>
      <div class="{p}-statline">
        <span><b class="{p}-mono">112</b> of 138 files</span><span class="{p}-seps">·</span>
        <span><b class="{p}-mono">3.72 GB</b> of 4.60 GB</span><span class="{p}-seps">·</span>
        <span><b class="{p}-mono">88 MB/s</b></span><span class="{p}-seps">·</span>
        <span><b class="{p}-mono">10s</b> left</span>
      </div>
    </div>
    <div class="{p}-bar"><div class="{p}-barfill" style="width:81%"></div></div>
    {steps(p)}
    <div class="{p}-tabs">
      <button class="{p}-tab" data-active="1">Files</button>
      <button class="{p}-tab">Stages</button>
      <button class="{p}-tab">Log</button>
    </div>
    <section class="{p}-card {p}-list">
      <div class="{p}-cardhead"><span class="{p}-cardtitle">Transferred files</span><span class="{p}-count">newest first</span></div>
      {file_rows(p,10)}
    </section>
  </main>
</div>
</div>'''

# ===========================================================================
# C — Stepper / timeline (sequential; vertical stage rail + sticky run panel)
# ===========================================================================
def C_css(p):
    return r"""
.S-layout2{display:grid;grid-template-columns:minmax(0,1fr) 380px}
.S-time{padding:20px 22px}
.S-h2{margin:0;font-size:15px;font-weight:600;letter-spacing:-.01em}
.S-timesub{margin:3px 0 20px;font-size:12px;color:var(--faint)}
.S-stage{display:grid;grid-template-columns:22px minmax(0,1fr);gap:13px;position:relative}
.S-rail{display:flex;flex-direction:column;align-items:center}
.S-dot{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;border:1.5px solid var(--line-2);background:var(--bg);color:transparent;flex:none}
.S-stage[data-state="done"] .S-dot{background:var(--good);border-color:var(--good);color:#06251a}
.S-stage[data-state="active"] .S-dot{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.S-line{flex:1;width:2px;background:var(--line);margin:4px 0}
.S-stage[data-state="done"] .S-line{background:color-mix(in srgb,var(--good) 55%,var(--line))}
.S-stagebody{padding-bottom:18px;min-width:0}
.S-stagetop{display:flex;align-items:center;gap:9px;margin-top:-1px}
.S-stagename{font-size:13.5px;font-weight:560}
.S-stage[data-state="todo"] .S-stagename{color:var(--faint);font-weight:520}
.S-stage[data-state="done"] .S-stagename{color:var(--dim)}
.S-badge{font-size:10.5px;font-weight:540;padding:2px 7px;border-radius:6px;background:var(--accent-soft);color:color-mix(in oklab,var(--accent) 60%,white)}
.S-sum{margin-top:4px;font-size:12px;color:var(--dim)}
.S-stage[data-state="todo"] .S-sum{color:var(--faint)}
.S-expand{margin-top:12px;padding:13px;border-radius:var(--r2);background:var(--surface);border:1px solid var(--line);display:flex;flex-direction:column;gap:11px}
.S-exphead{display:flex;align-items:center;gap:8px}
.S-expfile{font-size:12px}
.S-mini .S-row{padding:7px 0;border-bottom:1px solid var(--line)}
.S-mini .S-row:last-child{border-bottom:0}
.S-panel{border-left:1px solid var(--line);padding:20px;display:flex;flex-direction:column;gap:15px;background:color-mix(in srgb,var(--bg) 55%,transparent)}
.S-pct{display:flex;align-items:baseline;line-height:.95}
.S-pctnum{font-size:46px;font-weight:640;letter-spacing:-.04em}
.S-pctsign{font-size:19px;font-weight:600;color:var(--dim);margin-left:3px}
.S-pctsub{font-size:12px;color:var(--dim);margin-top:6px}
.S-kvs2{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px}
.S-kv2{display:flex;flex-direction:column;gap:2px}
.S-kvl2{font-size:10.5px;color:var(--faint)}
.S-kvv2{font-size:13px;font-weight:560}
.S-group{border-top:1px solid var(--line);padding-top:14px}
.S-grouplabel2{font-size:10.5px;font-weight:560;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);margin-bottom:10px}
.S-runs .S-row{padding:7px 0}
"""

def c_stage(p, state, name, summ, expand=False):
    dot = ic('check',11,3) if state == "done" else ''
    badge = f'<span class="{p}-badge">in progress</span>' if state == "active" else ''
    line = '' if state == "last" else f'<span class="{p}-line"></span>'
    expanded = ''
    if expand:
        mini = "".join(f'''<div class="{p}-row"><span class="{p}-rowicon">{ic('layers',12)}</span><div><div class="{p}-rowname {p}-mono">{n}</div></div><span class="{p}-rowright"><span class="{p}-rowsize {p}-mono">{s}</span><span class="{p}-check">{ic('check',12)}</span></span></div>'''
                        for n, s in [("IMG_4126.HEIC","3.9 MB"),("IMG_4125.MOV","88 MB"),("IMG_4124.HEIC","3.8 MB")])
        expanded = f'''<div class="{p}-expand">
      <div class="{p}-exphead"><span class="{p}-led" data-state="live"></span><span class="{p}-expfile {p}-mono">IMG_4127.HEIC</span><span class="{p}-tag" data-tone="live">Live Photo</span></div>
      <div class="{p}-bar"><div class="{p}-barfill" style="width:81%"></div></div>
      <div class="{p}-mini">{mini}</div>
    </div>'''
    return f'''<div class="{p}-stage" data-state="{state}">
  <div class="{p}-rail"><span class="{p}-dot">{dot}</span>{line}</div>
  <div class="{p}-stagebody">
    <div class="{p}-stagetop"><span class="{p}-stagename">{name}</span>{badge}</div>
    <div class="{p}-sum">{summ}</div>
    {expanded}
  </div>
</div>'''

def C_body(p):
    return f'''<div class="{p}-root">
{tb(p)}
<div class="{p}-layout2">
  <section class="{p}-time">
    <h2 class="{p}-h2">Run progress</h2>
    <p class="{p}-timesub">138 files queued · started 21:26</p>
    {c_stage(p,'done','Connect','iPhone 17 Pro recognized over USB')}
    {c_stage(p,'done','Scan','138 new items found since the last run')}
    {c_stage(p,'active','Pull','112 of 138 files copied off the iPhone', expand=True)}
    {c_stage(p,'todo','Convert','Apple Live Photos → Google Motion Photos')}
    {c_stage(p,'todo','Push','Write each file to the Samsung DCIM folder')}
    {c_stage(p,'last','Index','Trigger MediaScanner so the gallery updates')}
  </section>
  <aside class="{p}-panel">
    <div>
      <div class="{p}-pct"><span class="{p}-pctnum {p}-tnum">81</span><span class="{p}-pctsign">%</span></div>
      <div class="{p}-pctsub">112 of 138 files</div>
    </div>
    <div class="{p}-bar"><div class="{p}-barfill" style="width:81%"></div></div>
    <div class="{p}-kvs2">
      <div class="{p}-kv2"><span class="{p}-kvl2">Rate</span><span class="{p}-kvv2 {p}-mono">88 MB/s</span></div>
      <div class="{p}-kv2"><span class="{p}-kvl2">Time left</span><span class="{p}-kvv2 {p}-mono">10s</span></div>
      <div class="{p}-kv2"><span class="{p}-kvl2">Moved</span><span class="{p}-kvv2 {p}-mono">3.72 GB</span></div>
      <div class="{p}-kv2"><span class="{p}-kvl2">Total</span><span class="{p}-kvv2 {p}-mono">4.60 GB</span></div>
    </div>
    <div class="{p}-group">
      <div class="{p}-grouplabel2">Devices</div>
      <div class="{p}-dev"><span class="{p}-led" data-on="1"></span><div><div class="{p}-devn">iPhone 17 Pro</div><div class="{p}-devd">USB · trusted</div></div></div>
      <div class="{p}-dev"><span class="{p}-led" data-on="1"></span><div><div class="{p}-devn">Galaxy S23</div><div class="{p}-devd">ADB · 118 GB free</div></div></div>
    </div>
    <div class="{p}-group {p}-runs">
      <div class="{p}-grouplabel2">Recent runs</div>
      {run_rows(p,3)}
    </div>
  </aside>
</div>
</div>'''

# ---------------------------------------------------------------------------
VARIANTS = [
    ("a", A_body, A_css, "Transfer window", "Horizontal file-transfer window. One big progress hero on top, a source to destination device rail, then the file list and recent runs side by side."),
    ("b", B_body, B_css, "Sidebar workspace", "Persistent left rail holds the run summary, devices and actions; the main column is one calm, well-typeset column with a single north-star progress line."),
    ("c", C_body, C_css, "Stage timeline", "A vertical stepper down the left shows each stage, with the active Pull stage expanded to its live files; the run panel on the right holds progress and devices."),
]

STANDALONE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Relay — Direction {{L}}</title>
<style>
html,body{margin:0;background:#000;color:#fff}
body{display:grid;place-items:center;min-height:100vh;padding:28px;overflow:auto;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
@media (prefers-reduced-motion: reduce){*{animation-duration:.01ms !important;animation-iteration-count:1 !important}}
{{SHARED}}
{{VAR}}
</style>
</head>
<body>
{{BODY}}
</body>
</html>
"""

COMPARISON = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Relay — three UI directions</title>
<style>
:root{color-scheme:dark}
html,body{margin:0;background:#000;color:#fff}
.pg{max-width:1200px;margin:0 auto;padding:36px 24px 72px;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;font-size:15px;line-height:1.55}
.pg h1{font-size:25px;letter-spacing:-.02em;margin:0 0 8px}
.pg .lede{color:#9aa0aa;max-width:74ch;margin:0 0 24px}
.pg .lede b{color:#fff;font-weight:600}
.pg nav{position:sticky;top:0;z-index:9;display:flex;gap:8px;flex-wrap:wrap;padding:12px 0;margin-bottom:24px;
  background:rgba(0,0,0,.9);backdrop-filter:blur(8px);border-bottom:1px solid rgba(255,255,255,.12)}
.pg nav a{color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.14);border-radius:7px;padding:6px 12px;font-size:13px}
.pg nav a:hover{background:#141418}
.pg section{margin:0 0 56px;scroll-margin-top:64px}
.pg h2{font-size:19px;margin:0 0 4px;letter-spacing:-.01em}
.pg .tag{font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;color:#8b909a;margin-left:10px}
.pg .note{color:#8b909a;font-size:13.5px;margin:6px 0 14px;max-width:86ch}
.pg .wrap{overflow-x:auto;padding-bottom:6px}
.pg .shot{width:1180px;zoom:.95}
.pg .meta{color:#8b909a;font-size:13px;margin-top:12px;display:grid;gap:5px}
.pg .meta b{color:#fff;font-weight:600}
.pg footer{border-top:1px solid rgba(255,255,255,.12);padding-top:18px;color:#6d7280;font-size:13px}
.pg code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
@media(max-width:1260px){.pg .shot{zoom:.78}}
@media(max-width:1000px){.pg .shot{zoom:.6}}
@media(max-width:720px){.pg .shot{zoom:.44}}
@media (prefers-reduced-motion: reduce){.pg *{animation-duration:.01ms !important;animation-iteration-count:1 !important}}
{{ALLCSS}}
</style>
</head>
<body>
<div class="pg">
  <h1>Photo Relay — three UI directions</h1>
  <p class="lede">Each is the real app's state (<b>Pulling, 112 of 138 files, 3.72 of 4.60 GB, 88 MB/s, 10s left</b>) rebuilt three different ways. All fix the same problems: the redundant title, the status shown four times, the duplicated device panels, and the wall of small grey labels.</p>
  <nav>
    <a href="#d-a">A — Transfer window</a>
    <a href="#d-b">B — Sidebar workspace</a>
    <a href="#d-c">C — Stage timeline</a>
  </nav>
  <section id="d-a">
    <h2>A — Transfer window<span class="tag">horizontal</span></h2>
    <p class="note">{{NOTE_A}}</p>
    <div class="wrap"><div class="shot">{{BODY_A}}</div></div>
    <div class="meta"><span><b>North star</b> the 81% and the progress bar own the top band.</span><span><b>Structure</b> hero progress, source→destination rail, stage rail, files + runs.</span><span><b>Flow</b> seamless one-directional packets; no snap-back.</span></div>
  </section>
  <section id="d-b">
    <h2>B — Sidebar workspace<span class="tag">calm density</span></h2>
    <p class="note">{{NOTE_B}}</p>
    <div class="wrap"><div class="shot">{{BODY_B}}</div></div>
    <div class="meta"><span><b>North star</b> one progress line under a plain-language headline.</span><span><b>Structure</b> rail holds run + devices + actions; main is a single reading column.</span><span><b>Removes</b> the duplicate device panel and the giant redundant title.</span></div>
  </section>
  <section id="d-c">
    <h2>C — Stage timeline<span class="tag">sequential</span></h2>
    <p class="note">{{NOTE_C}}</p>
    <div class="wrap"><div class="shot">{{BODY_C}}</div></div>
    <div class="meta"><span><b>North star</b> where we are in the run, stage by stage.</span><span><b>Structure</b> vertical stepper with the active Pull stage expanded; run panel on the right.</span><span><b>Best when</b> the sequence matters more than the file list.</span></div>
  </section>
  <footer>Reply with a letter: <code>A</code>, <code>B</code>, or <code>C</code>. Mixes are fine, e.g. "B's layout with A's progress hero".</footer>
</div>
</body>
</html>
"""

def build():
    notes = {p: note for p, _, _, _, note in VARIANTS}
    bodies = {}
    allcss = []
    for p, body_fn, css_fn, label, _ in VARIANTS:
        shared = SHARED.replace("S-", p + "-")
        var = css_fn(p).replace("S-", p + "-")
        html = body_fn(p)
        bodies[p] = html
        allcss.append(shared + "\n" + var)
        page = (STANDALONE
                .replace("{{L}}", label)
                .replace("{{SHARED}}", shared)
                .replace("{{VAR}}", var)
                .replace("{{BODY}}", html))
        open(os.path.join(OUT, f"v2-{p}.html"), "w", encoding="utf-8").write(page)

    comp = (COMPARISON
            .replace("{{ALLCSS}}", "\n".join(allcss))
            .replace("{{BODY_A}}", bodies["a"])
            .replace("{{BODY_B}}", bodies["b"])
            .replace("{{BODY_C}}", bodies["c"])
            .replace("{{NOTE_A}}", notes["a"])
            .replace("{{NOTE_B}}", notes["b"])
            .replace("{{NOTE_C}}", notes["c"]))
    open(os.path.join(OUT, "v2-comparison.html"), "w", encoding="utf-8").write(comp)

    for p, *_ in VARIANTS:
        print(f"v2-{p}.html", os.path.getsize(os.path.join(OUT, f"v2-{p}.html")))
    print("v2-comparison.html", os.path.getsize(os.path.join(OUT, "v2-comparison.html")))

if __name__ == "__main__":
    build()
