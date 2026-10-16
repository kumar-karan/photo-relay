#!/usr/bin/env python3
"""Build the self-contained Photo Relay icon comparison page (Postplan-ready).

Imports the palette + concept definitions from generate.py so the page and the
shipped SVG/PNG files can never drift apart.
"""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "generate.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

PALETTES = gen.PALETTES
ORDER = gen.PALETTE_ORDER
CONCEPTS = gen.CONCEPTS


def inline_shapes(concept):
    out = []
    for s in concept["shapes"]:
        s = s.replace('"A1"', '"var(--i1)"').replace('"A2"', '"var(--i2)"')
        s = s.replace('"CORE"', '"var(--core)"').replace('"GLOW"', '"var(--glow)"')
        out.append(s)
    return "\n      ".join(out)


def icon_svg(concept, ident):
    return f'''<svg class="ic" viewBox="0 0 1024 1024" role="img" aria-label="{concept['name']}">
      <defs>
        <linearGradient id="{ident}-s" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="var(--i1)"/><stop offset="1" stop-color="var(--i2)"/>
        </linearGradient>
        <radialGradient id="{ident}-glow" cx="0.5" cy="0.34" r="0.78">
          <stop offset="0" stop-color="var(--glow)" stop-opacity="0.30"/>
          <stop offset="0.55" stop-color="var(--glow)" stop-opacity="0.05"/>
          <stop offset="1" stop-color="var(--glow)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="1024" height="1024" rx="232" fill="#0b0b0d"/>
      <rect width="1024" height="1024" rx="232" fill="url(#{ident}-glow)"/>
      <rect x="6" y="6" width="1012" height="1012" rx="228" fill="none" stroke="#fff" stroke-opacity="0.07" stroke-width="12"/>
      <g transform="translate(196 196) scale(26.333)" fill="none" stroke="url(#{ident}-s)"
         stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
      {inline_shapes(concept)}
      </g>
    </svg>'''


def mark_svg(concept):
    body = "\n      ".join(
        re.sub(r'"(A1|A2|CORE|GLOW)"', '"currentColor"', s) for s in concept["shapes"])
    return f'''<svg class="mk" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      {body}
    </svg>'''


def palette_card(slug, active):
    p = PALETTES[slug]
    cls = "pcard active" if active else "pcard"
    return f'''<button class="{cls}" data-palette="{slug}" type="button">
        <span class="swatch" style="--s1:{p['i1']};--s2:{p['i2']}"></span>
        <span class="pname">{p['name']}<em>{p['tag']}</em></span>
        <code class="hexes">{p['i1']} · {p['i2']} · {p['glow']}</code>
      </button>'''


def four_up():
    cells = []
    for slug in ORDER:
        p = PALETTES[slug]
        concept = next(c for c in CONCEPTS if c["slug"] == "relay")
        cells.append(f'''<div class="four-cell" style="--i1:{p['i1']};--i2:{p['i2']};--glow:{p['glow']};--core:{p['core']}">
        <div class="ic-wrap">{icon_svg(concept, 'four-' + slug)}</div>
        <div class="four-name">{p['name']}</div>
        <code>{p['i1']} → {p['i2']}</code>
      </div>''')
    return "\n".join(cells)


def concept_tile(concept, i):
    marks = "".join(
        f'<span class="mk-box" style="color:var(--i1)">{mark_svg(concept)}</span>'
        f'<span class="mk-box" style="color:var(--i2)">{mark_svg(concept)}</span>'
        for _ in range(1))
    return f'''<article class="tile">
      <div class="tile-top">
        <span class="idx">{i:02d}</span>
        <div class="tile-meta"><h3>{concept['name']}</h3><p>{concept['note']}</p></div>
      </div>
      <div class="tile-body">
        <div class="ic-wrap">{icon_svg(concept, 't' + str(i))}</div>
        <div class="marks">{marks}</div>
      </div>
    </article>'''


JS_PALETTES = ",\n".join(
    f'"{s}":{{i1:"{PALETTES[s]["i1"]}",i2:"{PALETTES[s]["i2"]}",'
    f'glow:"{PALETTES[s]["glow"]}",core:"{PALETTES[s]["core"]}",'
    f'name:"{PALETTES[s]["name"]}"}}' for s in ORDER)

TILES = "\n".join(concept_tile(c, i + 1) for i, c in enumerate(CONCEPTS))
CARDS = "\n".join(palette_card(s, s == "ember") for s in ORDER)


def build():
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Relay — icon direction v3</title>
<style>
  :root{{
    --i1:#FFC24B; --i2:#F4573E; --glow:#FF8A3D; --core:#FFD98A;
    --bg:#0b0b0d; --surf:#141418; --surf2:#191921; --line:rgba(255,255,255,.09);
    --line2:rgba(255,255,255,.17); --ink:#f4f5f7; --dim:#a2a6b0; --faint:#6d7280;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  }}
  *{{box-sizing:border-box}}
  html{{background:var(--bg);color:var(--ink);font-family:var(--sans);
    -webkit-font-smoothing:antialiased}}
  body{{margin:0;padding:44px 40px 72px}}
  .wrap{{max-width:1120px;margin:0 auto}}
  h1{{font-size:30px;letter-spacing:-.02em;margin:0 0 8px}}
  .lede{{color:var(--dim);font-size:15px;line-height:1.55;max-width:74ch;margin:0 0 8px}}
  .lede b{{color:var(--ink)}}
  h2{{font-size:13px;font-weight:600;letter-spacing:.10em;text-transform:uppercase;
    color:var(--faint);margin:44px 0 16px}}
  code{{font-family:var(--mono);font-size:12px;color:var(--dim)}}

  /* palette switcher ---------------------------------------------------- */
  .pals{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
  .pcard{{display:flex;flex-direction:column;gap:10px;text-align:left;cursor:pointer;
    background:var(--surf);border:1px solid var(--line);border-radius:14px;padding:14px;
    color:var(--ink);font:inherit;transition:border-color .15s,background .15s}}
  .pcard:hover{{border-color:var(--line2)}}
  .pcard.active{{border-color:var(--i1);background:var(--surf2);
    box-shadow:0 0 0 1px var(--i1) inset}}
  .swatch{{height:44px;border-radius:9px;
    background:linear-gradient(135deg,var(--s1),var(--s2));
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.14)}}
  .pname{{font-size:14px;font-weight:600;display:flex;flex-direction:column;gap:2px}}
  .pname em{{font-style:normal;font-size:11px;font-weight:500;color:var(--faint)}}
  .hexes{{color:var(--dim);font-size:11px}}

  /* same mark, four palettes ------------------------------------------- */
  .four{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
  .four-cell{{display:flex;flex-direction:column;align-items:center;gap:10px;
    padding:18px 12px;background:var(--surf);border:1px solid var(--line);border-radius:16px}}
  .four-name{{font-size:13px;font-weight:600}}
  .four-cell code{{font-size:11px;color:var(--faint)}}

  /* concept grid -------------------------------------------------------- */
  .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
  .tile{{background:var(--surf);border:1px solid var(--line);border-radius:18px;
    padding:18px 18px 20px;display:flex;flex-direction:column;gap:16px}}
  .tile-top{{display:flex;gap:12px;align-items:baseline}}
  .idx{{font-family:var(--mono);font-size:12px;color:var(--faint)}}
  .tile-meta h3{{margin:0 0 4px;font-size:16px;letter-spacing:-.01em}}
  .tile-meta p{{margin:0;font-size:12.5px;line-height:1.5;color:var(--dim)}}
  .tile-body{{display:flex;align-items:flex-end;justify-content:space-between;gap:12px}}
  .ic-wrap{{flex:1;display:flex;align-items:center;justify-content:center}}
  .ic{{width:132px;height:132px;display:block;
    filter:drop-shadow(0 10px 22px rgba(0,0,0,.5))}}
  .four-cell .ic{{width:104px;height:104px}}
  .marks{{display:flex;flex-direction:column;gap:12px;padding-bottom:8px}}
  .mk-box{{display:grid;place-items:center;width:40px;height:40px;border-radius:10px;
    background:#0e0e12;border:1px solid var(--line)}}
  .mk{{width:24px;height:24px}}

  /* palette rationale --------------------------------------------------- */
  .rationale{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
  .rcard{{background:var(--surf);border:1px solid var(--line);border-radius:16px;padding:18px}}
  .rhead{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
  .rdot{{width:26px;height:26px;border-radius:8px;
    background:linear-gradient(135deg,var(--d1),var(--d2))}}
  .rhead b{{font-size:14px}}
  .rhead code{{margin-left:auto;font-size:11px;color:var(--faint)}}
  .rcard p{{margin:0;font-size:12.5px;line-height:1.55;color:var(--dim)}}

  .note{{font-size:12.5px;color:var(--faint);line-height:1.6;margin-top:28px;
    border-top:1px solid var(--line);padding-top:20px}}
  .note code{{color:var(--dim)}}
  footer{{margin-top:34px;font-size:12px;color:var(--faint)}}
  @media(max-width:900px){{
    body{{padding:28px 20px 56px}}
    .pals,.four{{grid-template-columns:repeat(2,1fr)}}
    .grid{{grid-template-columns:1fr}}
    .rationale{{grid-template-columns:1fr}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Photo Relay — icon direction v3</h1>
  <p class="lede">Out with the purple/indigo + cyan AI look. In: <b>four crafted
  palette directions</b> and <b>nine marks</b>, each shipped as a 24px
  <code>mark.svg</code>, a 1024px dark-squircle <code>icon.svg</code> and a
  <code>icon-1024.png</code>. Recolour every concept live with the palette
  buttons below; the file paths are listed at the end.</p>

  <h2>Palette directions</h2>
  <div class="pals" id="pals">
    {CARDS}
  </div>

  <h2>The same mark, four ways</h2>
  <div class="four">
    {four_up()}
  </div>

  <h2>Nine marks <span style="color:var(--faint);text-transform:none;letter-spacing:0">— shown in <span id="activeName">Ember</span></span></h2>
  <div class="grid">
    {TILES}
  </div>

  <h2>Why these colours</h2>
  <div class="rationale">
    <div class="rcard" style="--d1:#FFC24B;--d2:#F4573E"><div class="rhead">
      <span class="rdot"></span><b>Ember</b><code>#FFC24B → #F4573E</code></div>
      <p>{PALETTES['ember']['desc']}</p></div>
    <div class="rcard" style="--d1:#93E9AC;--d2:#12B981"><div class="rhead">
      <span class="rdot"></span><b>Verdant</b><code>#93E9AC → #12B981</code></div>
      <p>{PALETTES['verdant']['desc']}</p></div>
    <div class="rcard" style="--d1:#8FC2FF;--d2:#2E6BE6"><div class="rhead">
      <span class="rdot"></span><b>Marine</b><code>#8FC2FF → #2E6BE6</code></div>
      <p>{PALETTES['marine']['desc']}</p></div>
    <div class="rcard" style="--d1:#E8F87A;--d2:#7BD34E"><div class="rhead">
      <span class="rdot"></span><b>Citrine</b><code>#E8F87A → #7BD34E</code></div>
      <p>{PALETTES['citrine']['desc']}</p></div>
  </div>

  <p class="note">Apple's 2025 Liquid Glass guidance asks for <b>bold weights
  over hairline strokes</b> and <b>coloured backgrounds</b>, so every icon keeps
  the brand squircle at <code>#0b0b0d</code> and uses a ~63px gradient stroke
  with a soft accent glow and a lit core. Marks are drawn on the same 24-unit
  grid as the current icon, so any of them drops straight into
  <code>src-tauri/icons/</code>.</p>

  <footer>Files: <code>design/v3-icons/&lt;palette&gt;/&lt;concept&gt;/{{mark.svg, icon.svg, icon-1024.png}}</code></footer>
</div>
<script>
  const P = {{ {JS_PALETTES} }};
  const root = document.documentElement;
  const nameEl = document.getElementById('activeName');
  function apply(slug){{
    const p = P[slug]; if(!p) return;
    root.style.setProperty('--i1', p.i1);
    root.style.setProperty('--i2', p.i2);
    root.style.setProperty('--glow', p.glow);
    root.style.setProperty('--core', p.core);
    nameEl.textContent = p.name;
    document.querySelectorAll('.pcard').forEach(el =>
      el.classList.toggle('active', el.dataset.palette === slug));
  }}
  document.getElementById('pals').addEventListener('click', e => {{
    const card = e.target.closest('.pcard'); if(card) apply(card.dataset.palette);
  }});
</script>
</body>
</html>
'''


if __name__ == "__main__":
    path = os.path.join(HERE, "comparison.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build())
    print("wrote", path, os.path.getsize(path), "bytes")
