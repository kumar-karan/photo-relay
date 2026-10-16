#!/usr/bin/env python3
"""Photo Relay icon exploration generator.

For every concept it writes, into design/icon/concepts/<slug>/:
  mark.svg      24x24, monochrome, currentColor  -> in-app logo/menu glyph
  icon.svg      1024x1024 dark squircle #0b0b0d + accent -> macOS app icon source
  icon-1024.png 1024x1024 raster               -> what ships to the Dock

Then it assembles a single self-contained comparison.html (inline SVG for the
large tiles, tiny data-URI PNG chips for the 16/32/64px legibility test).
PNGs are rendered with macOS WebKit (qlmanage) then Lanczos-downscaled by
ImageMagick, the same pipeline scripts/make-icons.sh uses for the real app.
"""
import base64
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS_DIR = os.path.join(ROOT, "concepts")
GLYPH_SCALE = 26  # 24-grid * 26 = 624px glyph in a 1024 squircle (~61%)

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
PALETTES = [
    {
        "id": "ember",
        "name": "Ember Signal",
        "swatches": ["#ffc46b", "#ff8a1e", "#f0420b", "#7a3f15", "#0b0b0d"],
        "grad": [("#ffc46b", 0.0), ("#ff8a1e", 0.5), ("#f0420b", 1.0)],
        "glow": ("#ffc46b", 0.22),
        "tag": "Recommended",
        "short": "Warm light for a photo relay: amber source, orange core, burnt-ember depth.",
        "rationale": (
            "Photos are light, and a relay is light travelling between two devices. "
            "Ember is a warm, physical family: Arc's sunrise yellow, Pixelmator Pro's "
            "sunset orange, Bear's amber, Things' warmth all read as crafted light, never "
            "as default-AI. It keeps Raycast's discipline of one brand hue doing all the "
            "work on near-black. Contrast on #0b0b0d is strong (~11:1 at 16px) because "
            "amber carries luminance as well as hue, and it sits at the opposite end of "
            "the spectrum from the AI purple every icon explorer starts from."
        ),
    },
    {
        "id": "lime",
        "name": "Lime Instrument",
        "swatches": ["#eaf9a9", "#d2ec4b", "#18a881", "#335e3f", "#0b0b0d"],
        "grad": [("#eaf9a9", 0.0), ("#d2ec4b", 0.45), ("#18a881", 1.0)],
        "glow": ("#d2ec4b", 0.18),
        "tag": "Alternative",
        "short": "Chartreuse-to-teal, a precision instrument panel.",
        "rationale": (
            "Green family chosen for instrument energy, not nature: Camo's lime, "
            "Linear's green accents, GrapheneOS chartreuse. Reads precise, reliable, "
            "'transfer complete'. Problem: green is also the universal success state, "
            "so it can read as status rather than identity, and it edges toward the "
            "same saturated-futuristic register people already associate with AI."
        ),
    },
    {
        "id": "ivory",
        "name": "Studio Ivory",
        "swatches": ["#f1eae0", "#cfc5b6", "#f97316", "#51493f", "#0b0b0d"],
        "grad": [("#f1eae0", 0.0), ("#cfc5b6", 0.75), ("#a99c85", 1.0)],
        "glow": ("#f1eae0", 0.08),
        "tag": "Alternative",
        "short": "Warm monochrome, one chrome-orange punctuation point.",
        "rationale": (
            "Things / Notion minimalism: the mark is warm ivory on near-black at near-"
            "maximum luminance contrast, so it is the most legible of the three at 16px, "
            "and one strong orange point (the 'live' node) carries the brand. The most "
            "reserved and timeless of the three; the risk is that with no colour doing "
            "the job, the icon depends entirely on the geometry, and it can read plain "
            "rather than distinctive at Dock size."
        ),
    },
]
PALETTE = {p["id"]: p for p in PALETTES}
RECOMMENDED = "ember"


def eb(v):
    return v if v else None


# ---------------------------------------------------------------------------
# Concepts. Each element is ("stroke"|"solid", raw_geometry_string).
# Geometry lives on the 24x24 grid with 2px optical margins.
# ---------------------------------------------------------------------------
CONCEPTS = [
    {
        "slug": "aperture",
        "name": "Aperture",
        "family": "Control — the current mark",
        "note": "Baseline: today's mark, re-lit in Ember so the palette moves on its own.",
        "pro": "Proven identity, no disruption; aperture is a genuine photo signal and stays crisp at 16px.",
        "con": "Still a stroked line-drawing; at Dock size it reads 'camera utility' before it reads 'relay'.",
        "elements": [
            ("stroke", '<circle cx="12" cy="12" r="10"/>'),
            ("stroke", '<path d="M14.31 8 20.05 17.94"/>'),
            ("stroke", '<path d="M9.69 8 21.17 8"/>'),
            ("stroke", '<path d="M7.38 12 13.12 2.06"/>'),
            ("stroke", '<path d="M9.69 16 3.95 6.06"/>'),
            ("stroke", '<path d="M14.31 16 2.83 16"/>'),
            ("stroke", '<path d="M16.62 12 10.88 21.94"/>'),
        ],
    },
    {
        "slug": "cascade",
        "name": "Cascade",
        "family": "Abstract — forward progress",
        "note": "Three ascending solid bars. Every step up is one device in the chain; the last bar is the top of the job.",
        "pro": "Fully solid geometry: near-perfect 16px stop-shape. Reads progress and momentum without a clock.",
        "con": "Bars ascending rightward are the same grammar as volume/signal/battery meters.",
        "elements": [
            ("solid", '<rect x="3.6" y="14" width="3.3" height="6.5" rx="1.65"/>'),
            ("solid", '<rect x="10.35" y="10.5" width="3.3" height="10" rx="1.65"/>'),
            ("solid", '<rect x="17.1" y="7" width="3.3" height="13.5" rx="1.65"/>'),
        ],
    },
    {
        "slug": "chevrons",
        "name": "Chevrons",
        "family": "Abstract — send forward",
        "note": "A solid leading chevron with an outline chevron backing it: one relay hop after another.",
        "pro": "Immediate 'forward / hand off' semantics, bold solid-to-outline weight contrast at every size.",
        "con": "Shares the double-chevron shape of common 'next' glyphs; needs the weight contrast to hold.",
        "elements": [
            ("solid", '<path d="M8.75 5.5 19.75 12 8.75 18.5 11 12 Z"/>'),
            ("stroke", '<path d="M3 8.5 7 12 3 15.5"/>'),
        ],
    },
    {
        "slug": "nodepass",
        "name": "Node Pass",
        "family": "Literal — point-to-point",
        "note": "A filled source node, then an arrow leaving it. iPhone hands to Mac hands to Samsung.",
        "pro": "The relay concept stated plainly; the filled node guarantees a solid anchor at 16px.",
        "con": "Arrows are the most common icon language in existence; must lean on weight and geometry.",
        "elements": [
            ("solid", '<circle cx="4" cy="12" r="2.4"/>'),
            ("stroke", '<path d="M9 12 H15"/>'),
            ("stroke", '<path d="M15 8 20 12 15 16"/>'),
        ],
    },
    {
        "slug": "framepulse",
        "name": "Frame Pulse",
        "family": "Photo — a frame in motion",
        "note": "A photo frame with a transfer pulse crossing it; the packet has left the left edge.",
        "pro": "The only literal 'this is about photos' frame; pulse line + packet read as a live move.",
        "con": "A square outline plus a line needs a calm centre to stay legible downsampled.",
        "elements": [
            ("stroke", '<rect x="4.2" y="4.2" width="15.6" height="15.6" rx="3"/>'),
            ("stroke", '<path d="M4.2 12 H19.8"/>'),
            ("solid", '<rect x="13.4" y="10.4" width="3.6" height="3.2" rx="0.8"/>'),
        ],
    },
    {
        "slug": "trinode",
        "name": "Tri Node",
        "family": "Relay — the chain as a triangle",
        "note": "Three filled nodes, three equal edges: the three devices and the routes between them.",
        "pro": "Unmistakably a network; rounded geometry keeps it calm, and it survives 16px as three dots.",
        "con": "Node-triangles are used by messaging/social apps; the equilateral calm helps it stay neutral.",
        "elements": [
            ("stroke", '<path d="M6 7 H18"/>'),
            ("stroke", '<path d="M6 7 12 18.5"/>'),
            ("stroke", '<path d="M18 7 12 18.5"/>'),
            ("solid", '<circle cx="6" cy="7" r="2"/>'),
            ("solid", '<circle cx="18" cy="7" r="2"/>'),
            ("solid", '<circle cx="12" cy="18.5" r="2"/>'),
        ],
    },
    {
        "slug": "ringbuffer",
        "name": "Ring Buffer",
        "family": "Abstract — a packet on the loop",
        "note": "A thick open arc with a packet riding the top-right: data circulating, always in motion.",
        "pro": "Thick ring + one solid dot is the most reductive of the set; reads as a loop of work.",
        "con": "A thick ring risks reading as a generic 'orbit / network' default; the packet placement carries it.",
        "elements": [
            ("stroke", '<circle cx="12" cy="12" r="8.75" stroke-width="2.6"/>'),
            ("solid", '<circle cx="18.2" cy="5.8" r="2.1"/>'),
        ],
    },
    {
        "slug": "stacksend",
        "name": "Stack Send",
        "family": "Photo — take the stack and go",
        "note": "Two stacked photo cards on the left, a solid forward chevron on the right: move the photos.",
        "pro": "Combines the photo object with the send gesture; most honest about what the app does.",
        "con": "Most complex construction — the chevron and cards must hold a clear gap at 16px.",
        "elements": [
            ("stroke", '<rect x="3.5" y="4.5" width="9" height="7.5" rx="2"/>'),
            ("stroke", '<rect x="6" y="10" width="9" height="7.5" rx="2"/>'),
            ("solid", '<path d="M16 7.2 21.5 12 16 16.8 17.6 12 Z"/>'),
        ],
    },
    {
        "slug": "threshold",
        "name": "Threshold",
        "family": "Abstract — the checkpoint",
        "note": "A diamond crossed by a solid bar: every photo passes one gate on its way through.",
        "pro": "The most distinctive profile in the set — no other icon in the Dock looks like a diamond gate.",
        "con": "Unlike the others it has no motion axis; it reads as a state rather than a flow.",
        "elements": [
            ("stroke", '<path d="M12 3.5 20 12 12 20.5 4 12 Z"/>'),
            ("solid", '<rect x="4" y="10.9" width="16" height="2.2" rx="1.1"/>'),
        ],
    },
    {
        "slug": "pulse",
        "name": "Pulse",
        "family": "Relay — a live heartbeat",
        "note": "A flat line with one sharp signal spike: the relay is alive right now.",
        "pro": "The clearest 'data in motion' glyph in the set; thick rounded stroke keeps it soft and crafted.",
        "con": "Heartbeat lines are shared with health apps; the sharp single spike + flat baseline distances it.",
        "elements": [
            ("stroke", '<path d="M3 12 8.5 12 10.5 7 14 16 15.5 12 21 12" stroke-width="2.4"/>'),
        ],
    },
]


def _strip_sw(raw):
    """Remove any embedded stroke-width so we can re-emit a single one."""
    import re as _re

    m = _re.search(r'stroke-width="([0-9.]+)"', raw)
    width = m.group(1) if m else None
    cleaned = _re.sub(r'\s+stroke-width="[0-9.]+"', "", raw)
    return cleaned, width


def glyph_mark_body(concept):
    """Inner <g> markup for the 24px currentColor mark."""
    parts = []
    for kind, raw in concept["elements"]:
        cleaned, width = _strip_sw(raw)
        if kind == "stroke":
            parts.append(
                cleaned.replace(
                    "/>",
                    f' fill="none" stroke="currentColor" stroke-width="{width or 2}"/>',
                )
            )
        else:
            parts.append(cleaned.replace("/>", ' fill="currentColor" stroke="none"/>'))
    return "".join(parts)


def glyph_icon_body(concept):
    """Inner <g> markup for the 1024 icon, ink-gradient stroke/fill."""
    parts = []
    for kind, raw in concept["elements"]:
        cleaned, width = _strip_sw(raw)
        if kind == "stroke":
            parts.append(
                cleaned.replace(
                    "/>",
                    f' fill="none" stroke="url(#ink)" stroke-width="{width or 2}"/>',
                )
            )
        else:
            parts.append(cleaned.replace("/>", ' fill="url(#ink)" stroke="none"/>'))
    return "".join(parts)


def build_mark_svg(concept):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" aria-hidden="true">\n'
        f'  {glyph_mark_body(concept)}\n'
        "</svg>\n"
    )


def build_icon_svg(concept, palette):
    p = PALETTE[palette]
    grad_stops = "\n".join(
        f'      <stop offset="{o}" stop-color="{c}"/>' for c, o in p["grad"]
    )
    g0, galpha = p["glow"]
    glyph = glyph_icon_body(concept)
    t = (1024 - 24 * GLYPH_SCALE) / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="shell" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#141417"/>
      <stop offset="0.6" stop-color="#0d0d10"/>
      <stop offset="1" stop-color="#0b0b0d"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.3" r="0.74">
      <stop offset="0" stop-color="{g0}" stop-opacity="{galpha}"/>
      <stop offset="0.55" stop-color="{g0}" stop-opacity="0.05"/>
      <stop offset="1" stop-color="{g0}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.10"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.035"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0.025"/>
    </linearGradient>
    <linearGradient id="ink" x1="196" y1="176" x2="828" y2="848" gradientUnits="userSpaceOnUse">
{grad_stops}
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="230" fill="url(#shell)"/>
  <rect width="1024" height="1024" rx="230" fill="url(#glow)"/>
  <rect x="7" y="7" width="1010" height="1010" rx="224" fill="none" stroke="url(#rim)" stroke-width="2"/>
  <g transform="translate({t} {t}) scale({GLYPH_SCALE})" stroke-linecap="round" stroke-linejoin="round">
  {glyph}
  </g>
</svg>
'''


def svg_to_pngs(icon_svg, out_dir):
    """WebKit render at 2048 then Lanczos downscale — same pipeline as make-icons.sh."""
    work = os.path.join(out_dir, ".render")
    os.makedirs(work, exist_ok=True)
    svg_path = os.path.join(work, "icon.svg")
    with open(svg_path, "w") as f:
        f.write(icon_svg)
    subprocess.run(
        ["qlmanage", "-t", "-s", "2048", "-o", work, svg_path],
        capture_output=True,
    )
    master = os.path.join(work, "icon.svg.png")
    out = {}
    for size in (16, 32, 64, 128, 256, 1024):
        path = os.path.join(out_dir, f"icon-{size}.png")
        subprocess.run(
            [
                "magick", master, "-filter", "Lanczos", "-resize",
                f"{size}x{size}", "-depth", "8", "-strip", path,
            ],
            check=True,
        )
        out[size] = path
    return out


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def inline_svg(path):
    with open(path) as f:
        return f.read().strip()


def build_html(concepts_data):
    """Assemble the self-contained comparison page."""
    tiles = []
    for c in concepts_data:
        tiles.append(f"""
      <div class="tile" id="{c['slug']}">
        <div class="tk">
          <div class="big">{c['icon']}</div>
          <div class="mark">{c['mark']}</div>
        </div>
        <div class="tc">
          <h3>{c['name']}</h3>
          <p class="fam">{c['family']}</p>
          <p class="note">{c['note']}</p>
          <ul>
            <li><b>For</b> {c['pro']}</li>
            <li><b>Against</b> {c['con']}</li>
          </ul>
        </div>
        <div class="chips">
          <div class="chip"><img src="{c['p16']}" alt="" width="16" height="16"><span>16</span></div>
          <div class="chip"><img src="{c['p32']}" alt="" width="32" height="32"><span>32</span></div>
          <div class="chip"><img src="{c['p64']}" alt="" width="64" height="64"><span>64</span></div>
        </div>
      </div>""")
    tiles_html = "\n".join(tiles)

    pal_cards = []
    for p in PALETTES:
        sw = "".join(
            f'<span class="sw" style="--c:{hexa}"></span>' for hexa in p["swatches"]
        )
        tag = f'<span class="ptag {p["id"]}">{p["tag"]}</span>'
        pal_cards.append(f"""
      <div class="pal {p['id']}">
        <div class="phead">{tag}<h3>{p['name']}</h3></div>
        <div class="sws">{sw}</div>
        <div class="hexes">{", ".join(p['swatches'])}</div>
        <p class="short">{p['short']}</p>
        <p class="why">{p['rationale']}</p>
      </div>""")
    pals_html = "\n".join(pal_cards)

    css = """
    :root { color-scheme: dark; --page:#08080a; --ink:#f4f1ec; --dim:#9d978c; --faint:#6b665c; --edge:rgba(255,255,255,.10); --ember:#ff8a1e; }
    * { box-sizing:border-box; }
    html,body { margin:0; background:var(--page); color:var(--ink); }
    body { font:15px/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing:antialiased; }
    .wrap { max-width:1160px; margin:0 auto; padding:40px 22px 80px; }
    h1 { font-size:25px; letter-spacing:-.02em; margin:0 0 8px; }
    .lede { color:var(--dim); max-width:74ch; margin:0 0 30px; }
    .lede strong { color:var(--ink); }
    section { margin:0 0 44px; }
    section h2 { font:600 15px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); margin:0 0 16px; }
    .research { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }
    .r { border:1px solid var(--edge); border-radius:12px; padding:14px 16px; background:#0d0d10; }
    .r b { display:block; margin-bottom:6px; color:var(--ink); }
    .r span { color:var(--dim); font-size:13.5px; }
    .pals { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px; }
    .pal { border:1px solid var(--edge); border-radius:14px; padding:18px; background:#0d0d10; }
    .pal.ember { border-color:rgba(255,138,30,.55); box-shadow:0 0 0 1px rgba(255,138,30,.18), 0 0 44px -18px rgba(255,138,30,.4); }
    .phead { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
    .phead h3 { margin:0; font-size:16px; }
    .ptag { font:600 10px/1 ui-monospace, Menlo, monospace; letter-spacing:.08em; text-transform:uppercase; padding:4px 8px; border-radius:6px; background:#222; color:var(--dim); }
    .ptag.ember { background:rgba(255,138,30,.16); color:#ffb35c; }
    .sws { display:flex; gap:6px; margin-bottom:8px; }
    .sw { width:26px; height:26px; border-radius:7px; background:var(--c); border:1px solid rgba(255,255,255,.12); }
    .hexes { font:500 11px/1.6 ui-monospace, Menlo, monospace; color:var(--dim); margin-bottom:10px; }
    .short { margin:0 0 10px; color:var(--ink); }
    .why { margin:0; color:var(--dim); font-size:13.5px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
    .tile { display:grid; grid-template-columns:150px 1fr; gap:14px; border:1px solid var(--edge); border-radius:16px; padding:16px; background:#0d0d10; }
    .tk { display:flex; flex-direction:column; align-items:center; gap:12px; }
    .big { width:132px; height:132px; background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="%2308080a"/></svg>'); }
    .big svg { width:132px; height:132px; display:block; border-radius:16px; }
    .mark { margin-top:2px; }
    .mark svg { width:34px; height:34px; display:block; color:var(--ink); }
    .mark::after { content:"mark · currentColor"; display:block; font:500 9px ui-monospace,Menlo,monospace; color:var(--faint); text-align:center; margin-top:4px; letter-spacing:.04em; }
    .tc h3 { margin:0 0 3px; font-size:16px; }
    .fam { margin:0 0 8px; font:600 10.5px/1 ui-monospace,Menlo,monospace; letter-spacing:.08em; text-transform:uppercase; color:var(--ember); }
    .note { margin:0 0 10px; color:var(--dim); font-size:13.5px; }
    .tc ul { margin:0; padding-left:16px; font-size:13px; color:var(--dim); }
    .tc b { color:var(--ink); font-weight:600; }
    .chips { grid-column:1 / -1; display:flex; gap:16px; align-items:flex-end; padding-top:10px; border-top:1px solid var(--edge); }
    .chip { display:flex; flex-direction:column; align-items:center; gap:6px; }
    .chip img { image-rendering:pixelated; border-radius:7px; box-shadow:0 1px 0 rgba(255,255,255,.08); }
    .chip span { font:500 10px ui-monospace,Menlo,monospace; color:var(--faint); }
    footer { border-top:1px solid var(--edge); padding-top:18px; color:var(--faint); font-size:13px; }
    code { font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12.5px; }
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Relay — icon exploration</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>Photo Relay — icon exploration</h1>
  <p class="lede">
    Moving Photo Relay away from the default-AI look (purple/indigo aperture, glow).
    Ten geometric marks for the same product thought — <strong>photos relayed
    iPhone → Mac → Samsung</strong> — drawn in one recommended palette and tested
    for real at 16/32/64px.
  </p>

  <section>
    <h2>What reads crafted vs default-AI</h2>
    <div class="research">
      <div class="r"><b>The AI tell</b><span>Indigo and violet (#6366f1, #8b5cf6, #7c3aed) and purple→cyan gradients. The current mark (#7d6cff → #40c6dd) is a textbook sample. The 2025–26 anti-slop consensus names indigo the #1 fingerprint.</span></div>
      <div class="r"><b>One hue, done well</b><span>Raycast: near-black #07080a + one brand red #ff6363, everything else greyscale. Crafted icons ration colour; they don't gradient it.</span></div>
      <div class="r"><b>Warm = physical</b><span>Arc sunrise yellow, Pixelmator Pro sunset orange, Bear amber, Camo lime, Things' flat reds. Warm/light temperatures read as physical objects; violet reads as software default.</span></div>
      <div class="r"><b>Geometry over glow</b><span>Distinctive profiles at 16px come from solid stops and weight contrast, not halos. Align glyphs to a 24-grid, keep strokes ≥2 units, let one solid shape anchor each mark.</span></div>
    </div>
  </section>

  <section>
    <h2>Three palettes</h2>
    <div class="pals">{pals_html}</div>
  </section>

  <section>
    <h2>Ten concepts — Ember Signal</h2>
    <div class="grid">{tiles_html}</div>
  </section>

  <footer>
    <strong>Recommended:</strong> Ember Signal, concept <strong>Pulse</strong> — reservation:
    verify Aperture / Frame Pulse / Stack Send in the real Dock before the buildbot lands on a favourite.
    Each concept ships <code>mark.svg</code> (24&thinsp;px currentColor), <code>icon.svg</code> (1024 dark squircle)
    and <code>icon-1024.png</code>.
  </footer>
</div>
</body>
</html>
"""


def main():
    os.makedirs(CONCEPTS_DIR, exist_ok=True)
    concepts_data = []

    for concept in CONCEPTS:
        out = os.path.join(CONCEPTS_DIR, concept["slug"])
        os.makedirs(out, exist_ok=True)

        mark_svg = build_mark_svg(concept)
        with open(os.path.join(out, "mark.svg"), "w") as f:
            f.write(mark_svg)

        icon_svg = build_icon_svg(concept, RECOMMENDED)
        with open(os.path.join(out, "icon.svg"), "w") as f:
            f.write(icon_svg)

        pngs = svg_to_pngs(icon_svg, out)

        concepts_data.append(
            {
                **concept,
                "icon": inline_svg(os.path.join(out, "icon.svg")),
                "mark": inline_svg(os.path.join(out, "mark.svg")),
                "p16": data_uri(pngs[16]),
                "p32": data_uri(pngs[32]),
                "p64": data_uri(pngs[64]),
            }
        )
        print(f"  {concept['slug']}: mark.svg icon.svg icon-1024.png (+16/32/64/128/256)")

    html = build_html(concepts_data)
    page = os.path.join(ROOT, "comparison.html")
    with open(page, "w") as f:
        f.write(html)
    print(f"\nWrote {page} ({len(html)//1024} KB), concepts: {len(concepts_data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())