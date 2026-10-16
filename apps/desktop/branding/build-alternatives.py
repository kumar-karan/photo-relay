#!/usr/bin/env python3
"""Generate Photo Relay icon alternatives.

For every concept this writes apps/desktop/branding/alternatives/<slug>/ with:
  mark.svg      24x24, stroke based, currentColor (in-app mark)
  icon.svg      1024x1024 squircle, #0b0b0d bg, indigo #7d6cff / cyan #40c6dd
  icon-1024.png 1024x1024 RGBA render (transparent squircle corners)

It also writes alternatives/comparison.html, a self contained page with the
mark and the full icon rendered at 16/24/48/128/256/512, using inline SVG.

Geometry is adapted from lucide (ISC), tabler (MIT) and phosphor style paths
where a suitable icon exists, then redrawn on a shared 24 unit grid so every
mark keeps a consistent optical weight.
"""
import json
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "alternatives")
BG = "#0b0b0d"
INDIGO = "#7d6cff"
INDIGO_SOFT = "#9d8cff"
CYAN = "#40c6dd"
WHITE = "#ffffff"

# ---------------------------------------------------------------------------
# Concept definitions. `body` is the inner markup on a 0 0 24 24 viewBox.
# mode: stroke | fill | duo.  color: grad | cyan | indigo | white | duo.
# ---------------------------------------------------------------------------
APERTURE_BODY = """<circle cx="12" cy="12" r="10"/>
<path d="m14.31 8 5.74 9.94"/>
<path d="M9.69 8h11.48"/>
<path d="m7.38 12 5.74-9.94"/>
<path d="M9.69 16 3.95 6.06"/>
<path d="M14.31 16H2.83"/>
<path d="m16.62 12-5.74 9.94"/>"""

CONCEPTS = [
    dict(
        label="A", slug="aperture", name="Aperture",
        direction="Aperture / lens", mode="stroke", sw=2.0, color="grad",
        note="The current brand mark, kept as the baseline. Six aperture blades in a circle read as both a lens and a shutter.",
        best16="Strong: one circle, high contrast.",
        body=APERTURE_BODY,
    ),
    dict(
        label="B", slug="dual-phone-relay", name="Dual Phone Relay",
        direction="Two phones + transfer", mode="stroke", sw=2.0, color="grad",
        note="iPhone and Samsung side by side with opposed arrows between them. It states the job of the app literally.",
        best16="Good: two dark blocks and two arrows.",
        body="""<rect x="1.6" y="6" width="5.6" height="12.4" rx="1.5"/>
<path d="M4.4 15.6h.01"/>
<rect x="16.8" y="5.6" width="5.6" height="12.4" rx="1.5"/>
<path d="M19.6 15.2h.01"/>
<path d="M8.7 9.6h6.1"/>
<path d="M12.7 7.5l2.1 2.1-2.1 2.1"/>
<path d="M15.3 14.4H9.2"/>
<path d="M11.3 16.5l-2.1-2.1 2.1-2.1"/>""",
    ),
    dict(
        label="C", slug="photo-frame-arrow", name="Photo Frame Arrow",
        direction="Photo frame + arrow", mode="stroke", sw=2.0, color="cyan",
        note="A framed photo with a sun and mountain, and an arrow leaving the frame. Photo first, motion second.",
        best16="Fair: the arrow closes up a little at 16.",
        body="""<rect x="2.4" y="4.8" width="12.6" height="12.6" rx="2.2"/>
<circle cx="6.6" cy="8.9" r="1.4"/>
<path d="m3.6 16.4 2.7-2.7c.6-.55 1.4-.55 2 0l2.7 2.7"/>
<path d="M16.9 11.1h4.5"/>
<path d="M18.6 9.2l2.8 1.9-2.8 1.9"/>""",
    ),
    dict(
        label="D", slug="relay-loop", name="Relay Loop",
        direction="Relay / loop", mode="stroke", sw=2.0, color="grad",
        note="Two chasing arrows form a closed loop, the recurring relay cycle. Pure motion, no literal photos.",
        best16="Strong: bold ring with clear arrowheads.",
        body="""<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
<path d="M21 3v5h-5"/>
<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
<path d="M8 16H3v5"/>""",
    ),
    dict(
        label="E", slug="mountain-sun-relay", name="Mountain Sun Relay",
        direction="Landscape + arrow", mode="stroke", sw=2.0, color="grad",
        note="A mountain and sun scene with an arrow rising off the summit. Photo subject plus the transfer direction.",
        best16="Fair: busiest silhouette of the set.",
        body="""<circle cx="18.6" cy="5.6" r="2.2"/>
<path d="M2.4 19.6 8.4 9.4l3.4 5.1 2.3-2.6 6.3 7.7z"/>
<path d="M8.4 8.2V3.4"/>
<path d="M6.6 5.2 8.4 3.4l1.8 1.8"/>""",
    ),
    dict(
        label="F", slug="pr-monogram", name="PR Monogram",
        direction="Monogram", mode="duo", sw=2.2, color="duo",
        note="Geometric P and R built from stems and bowls, no typed glyphs. P takes indigo, R takes cyan in the icon.",
        best16="Good: two solid letterforms, reads at small sizes.",
        p='<path d="M5 20.5V4h4.5a3.4 3.4 0 0 1 0 6.8H5"/>',
        r='<path d="M14.3 20.5V4h4.3a3.1 3.1 0 0 1 0 6.2h-4.3"/><path d="M15.8 10.2l5 10.3"/>',
        dx=-0.9,
    ),
    dict(
        label="G", slug="node-relay", name="Node Relay",
        direction="Geometric relay chain", mode="stroke", sw=2.0, color="grad",
        note="Three nodes in a row joined by chevrons: iPhone to Mac to Samsung as one directed chain.",
        best16="Strong: three dots and two chevrons.",
        body="""<circle cx="3.8" cy="12" r="2"/>
<circle cx="12" cy="12" r="2"/>
<circle cx="20.2" cy="12" r="2"/>
<path d="M7.1 10 9 12l-1.9 2"/>
<path d="M15 10l1.9 2-1.9 2"/>""",
    ),
    dict(
        label="H", slug="minimal-aperture", name="Minimal Aperture",
        direction="Minimal line", mode="stroke", sw=1.35, color="indigo",
        note="The aperture taken to a hairline weight. Quiet, editorial, sits well at small UI sizes next to text.",
        best16="Fair: hairline weight disappears below 20px.",
        body=APERTURE_BODY,
    ),
    dict(
        label="I", slug="bold-camera", name="Bold Camera",
        direction="Filled bold", mode="fill", sw=0.0, color="grad",
        note="A solid camera silhouette with the lens knocked out and a floating center dot. The heaviest mark here.",
        best16="Strong: solid mass survives any size.",
        body='<path fill-rule="evenodd" d="M4 7.4h3.3l1.5-2.3h6.4l1.5 2.3H20a2.3 2.3 0 0 1 2.3 2.3v8.4a2.3 2.3 0 0 1-2.3 2.3H4a2.3 2.3 0 0 1-2.3-2.3V9.7A2.3 2.3 0 0 1 4 7.4Zm8 3.05a3.25 3.25 0 1 0 0 6.5 3.25 3.25 0 1 0 0-6.5Zm0 2.05a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 1 0 0-2.4Z"/>',
    ),
    dict(
        label="J", slug="gradient-orbit", name="Gradient Orbit",
        direction="Gradient / orbit", mode="stroke", sw=2.0, color="grad",
        note="Two wide orbits sweep around a central lens dot with two satellite nodes. Motion and depth.",
        best16="Good: distinct diagonal rhythm.",
        body="""<path d="M20.34 6.48A10 10 0 0 1 10.27 21.85"/>
<path d="M3.66 17.52A10 10 0 0 1 13.74 2.15"/>
<circle cx="12" cy="12" r="3"/>
<circle cx="19" cy="5" r="2"/>
<circle cx="5" cy="19" r="2"/>""",
    ),
    dict(
        label="K", slug="high-contrast-relay", name="High Contrast Relay",
        direction="High contrast mono", mode="stroke", sw=3.0, color="white",
        note="Two heavy exchange arrows in pure white on black, no glow. Maximum contrast, reads as transfer instantly.",
        best16="Strong: thickest strokes in the set.",
        glow=False,
        body="""<path d="M3.6 9.6h13.6"/>
<path d="M14.4 6.6l3 3-3 3"/>
<path d="M20.4 14.4H6.8"/>
<path d="M9.6 11.4l-3 3 3 3"/>""",
    ),
    dict(
        label="L", slug="frame-scan", name="Frame Scan",
        direction="Viewfinder + arrow", mode="stroke", sw=2.0, color="cyan",
        note="Camera viewfinder corners with a right arrow inside. Suggests grabbing and moving photos.",
        best16="Good: corners plus a centered arrow.",
        body="""<path d="M3.5 8.2V6.4A2.9 2.9 0 0 1 6.4 3.5h1.8"/>
<path d="M15.8 3.5h1.8a2.9 2.9 0 0 1 2.9 2.9v1.8"/>
<path d="M20.5 15.8v1.8a2.9 2.9 0 0 1-2.9 2.9h-1.8"/>
<path d="M8.2 20.5H6.4a2.9 2.9 0 0 1-2.9-2.9v-1.8"/>
<path d="M8.6 12h6.8"/>
<path d="M13.3 9.9l2.1 2.1-2.1 2.1"/>""",
    ),
    dict(
        label="M", slug="stacked-photos", name="Stacked Photos",
        direction="Photo stack", mode="stroke", sw=2.0, color="grad",
        note="Two overlapping photo frames, the back one peeking out. Says library and bulk in one shape.",
        best16="Good: overlapping squares stay distinct.",
        body="""<rect x="8.3" y="2.6" width="13.1" height="13.1" rx="2.3"/>
<circle cx="13.1" cy="6.7" r="1.05"/>
<path d="M21.4 10.4l-1.4-1.4a2.3 2.3 0 0 0-3.25 0L12.5 13.3"/>
<path d="M4.6 8.4a2.4 2.4 0 0 0-1.9 2.3v8.7a2.4 2.4 0 0 0 2.4 2.4h8.7a2.4 2.4 0 0 0 2.3-1.9"/>""",
    ),
    dict(
        label="N", slug="send-relay", name="Send Relay",
        direction="Relay / send", mode="stroke", sw=2.0, color="grad",
        note="A paper plane crossing a diagonal trail. Lightweight, fast, unmistakably about sending something onward.",
        best16="Good: simple triangle with a tail.",
        body="""<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/>
<path d="m21.854 2.147-10.94 10.939"/>""",
    ),
]


def mark_attrs(mode, sw):
    if mode == "fill":
        return 'fill="currentColor" fill-rule="evenodd"'
    return (
        f'fill="none" stroke="currentColor" stroke-width="{sw}" '
        'stroke-linecap="round" stroke-linejoin="round"'
    )


def mark_svg(c):
    body = c["body"] if "body" in c else c["p"] + c["r"]
    dx = c.get("dx", 0)
    inner = f'<g transform="translate({dx} 0)">{body}</g>' if dx else body
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" ' + mark_attrs(c["mode"], c["sw"]) + ' aria-hidden="true">\n'
        + inner + "\n</svg>\n"
    )


def stroke(color):
    return {
        "grad": f'stroke="url(#pg)"',
        "cyan": f'stroke="{CYAN}"',
        "indigo": f'stroke="{INDIGO_SOFT}"',
        "white": f'stroke="{WHITE}"',
    }[color]


def icon_group(c):
    """Return the <g> block that paints the mark on the 1024 canvas."""
    dx = c.get("dx", 0)
    xform = 'transform="translate(176 176) scale(28)' + (f' translate({dx} 0)"' if dx else '"')
    if c["mode"] == "fill":
        return f'<g {xform} fill="url(#pg)" fill-rule="evenodd">{c["body"]}</g>'
    if c["mode"] == "duo":
        common = f'fill="none" stroke-width="{c["sw"]}" stroke-linecap="round" stroke-linejoin="round"'
        return (
            f'<g {xform} {common} stroke="{INDIGO}">{c["p"]}</g>'
            f'<g {xform} {common} stroke="{CYAN}">{c["r"]}</g>'
        )
    return (
        f'<g {xform} fill="none" {stroke(c["color"])} stroke-width="{c["sw"]}" '
        f'stroke-linecap="round" stroke-linejoin="round">{c["body"]}</g>'
    )


def grad_defs():
    return (
        '<linearGradient id="pg" x1="200" y1="180" x2="824" y2="844" '
        'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{INDIGO_SOFT}"/>'
        f'<stop offset=".52" stop-color="{INDIGO}"/>'
        f'<stop offset="1" stop-color="{CYAN}"/></linearGradient>'
        '<radialGradient id="pglow" cx=".5" cy=".34" r=".72">'
        f'<stop offset="0" stop-color="{INDIGO}" stop-opacity=".34"/>'
        f'<stop offset=".6" stop-color="{INDIGO}" stop-opacity=".06"/>'
        f'<stop offset="1" stop-color="{INDIGO}" stop-opacity="0"/></radialGradient>'
    )


def icon_svg(c):
    use_grad = c["mode"] == "fill" or (c["mode"] == "stroke" and c["color"] == "grad")
    glow = c.get("glow", True)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" '
             'viewBox="0 0 1024 1024">']
    defs = []
    if use_grad:
        defs.append(
            '<linearGradient id="pg" x1="200" y1="180" x2="824" y2="844" '
            'gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{INDIGO_SOFT}"/>'
            f'<stop offset=".52" stop-color="{INDIGO}"/>'
            f'<stop offset="1" stop-color="{CYAN}"/></linearGradient>'
        )
    if glow:
        defs.append(
            '<radialGradient id="pglow" cx=".5" cy=".34" r=".72">'
            f'<stop offset="0" stop-color="{INDIGO}" stop-opacity=".34"/>'
            f'<stop offset=".6" stop-color="{INDIGO}" stop-opacity=".06"/>'
            f'<stop offset="1" stop-color="{INDIGO}" stop-opacity="0"/></radialGradient>'
        )
    if defs:
        parts.append("<defs>" + "".join(defs) + "</defs>")
    parts.append(f'<rect width="1024" height="1024" rx="232" fill="{BG}"/>')
    if glow:
        parts.append('<rect width="1024" height="1024" rx="232" fill="url(#pglow)"/>')
    parts.append('<rect x="6" y="6" width="1012" height="1012" rx="228" fill="none" '
                 'stroke="#ffffff" stroke-opacity=".06" stroke-width="12"/>')
    parts.append(icon_group(c))
    parts.append("</svg>\n")
    return "\n".join(parts)


def render_png(svg_path, png_path):
    """qlmanage renders the SVG through WebKit, which keeps gradients intact but
    paints a white page behind the squircle. Key that white out from the four
    corners so the squircle corners are transparent (what Tauri/macOS expect),
    then downsample to exactly 1024 RGBA."""
    work = tempfile.mkdtemp(prefix="pr-icon-")
    try:
        subprocess.run(
            ["qlmanage", "-t", "-s", "2048", "-o", work, svg_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        master = os.path.join(work, os.path.basename(svg_path) + ".png")
        if not os.path.exists(master):
            raise RuntimeError(f"qlmanage produced no output for {svg_path}")
        # Clip to the squircle with an antialiased mask. qlmanage paints white
        # behind the SVG, and a per-pixel floodfill at 2048^2 is far too slow,
        # so a matching round-rectangle mask is both faster and exact.
        subprocess.run(
            ["magick", master, "-filter", "Lanczos", "-resize", "1024x1024",
             "(", "-size", "1024x1024", "xc:none", "-fill", "white",
             "-draw", "roundrectangle 0,0 1023,1023 232,232", ")",
             "-alpha", "set", "-compose", "DstIn", "-composite",
             "-define", "png:compression-level=9",
             "-depth", "8", "-strip", "PNG32:" + png_path],
            check=True,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def build_html(concepts):
    def mark_sym(c):
        body = c["body"] if "body" in c else c["p"] + c["r"]
        dx = c.get("dx", 0)
        if dx:
            body = f'<g transform="translate({dx} 0)">{body}</g>'
        if c["mode"] == "fill":
            g = f'<g fill="currentColor" fill-rule="evenodd">{body}</g>'
        else:
            g = (f'<g fill="none" stroke="currentColor" stroke-width="{c["sw"]}" '
                 f'stroke-linecap="round" stroke-linejoin="round">{body}</g>')
        return f'<symbol id="m-{c["slug"]}" viewBox="0 0 24 24">{g}</symbol>'

    def icon_sym(c):
        use_grad = c["mode"] == "fill" or (c["mode"] == "stroke" and c["color"] == "grad")
        glow = c.get("glow", True)
        block = [f'<rect width="1024" height="1024" rx="232" fill="{BG}"/>']
        if glow:
            block.append('<rect width="1024" height="1024" rx="232" fill="url(#pglow)"/>')
        block.append('<rect x="6" y="6" width="1012" height="1012" rx="228" fill="none" '
                     'stroke="#ffffff" stroke-opacity=".06" stroke-width="12"/>')
        block.append(icon_group(c))
        return f'<symbol id="i-{c["slug"]}" viewBox="0 0 1024 1024">{"".join(block)}</symbol>'

    symbols = "".join(mark_sym(c) + icon_sym(c) for c in concepts)

    SIZES = [16, 24, 48, 128, 256, 512]

    def strip(c, kind):
        cells = []
        for s in SIZES:
            ref = f'#{"m" if kind == "mark" else "i"}-{c["slug"]}'
            vb = "0 0 24 24" if kind == "mark" else "0 0 1024 1024"
            cls = "mark" if kind == "mark" else "icon"
            cells.append(
                f'<figure class="cell"><div class="stage"><svg class="{cls}" '
                f'viewBox="{vb}" style="width:{s}px;height:{s}px"><use href="{ref}"/></svg>'
                f'</div><figcaption>{s}</figcaption></figure>'
            )
        return '<div class="strip">' + "".join(cells) + "</div>"

    cards = []
    for c in concepts:
        style = {"stroke": f'{c["sw"]}u stroke', "fill": "solid fill", "duo": "two-tone"}[c["mode"]]
        cards.append(f"""
<article class="card" id="c-{c['slug']}">
  <header class="card-head">
    <span class="badge">{c['label']}</span>
    <div class="titles"><h3>{c['name']}</h3><span class="slug">{c['slug']}</span></div>
    <span class="tag">{c['direction']}</span>
  </header>
  <div class="meta"><span>mark.svg · 24px · currentColor · {style}</span><span>icon.svg · 1024 · {c['color']}</span></div>
  <section class="block">
    <h4>Mark <em>in-app, currentColor</em></h4>
    {strip(c, 'mark')}
  </section>
  <section class="block">
    <h4>App icon <em>1024 squircle</em></h4>
    {strip(c, 'icon')}
  </section>
  <p class="note">{c['note']} <strong>At 16px:</strong> {c['best16']}</p>
</article>""")

    style_name = {"stroke": "line", "fill": "filled", "duo": "monogram"}
    rows = "".join(
        f'<tr><td><span class="badge sm">{c["label"]}</span></td><td>{c["name"]}</td>'
        f'<td>{c["direction"]}</td><td>{style_name[c["mode"]]}</td>'
        f'<td>{c["best16"].split(":")[0]}</td></tr>'
        for c in concepts
    )

    return (TEMPLATE
            .replace("<!--SYMBOLS-->", symbols)
            .replace("<!--SUMMARY-->", rows)
            .replace("<!--CARDS-->", "".join(cards)))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photo Relay - Icon Alternatives</title>
<style>
:root{--bg:#000;--panel:#0b0b0d;--panel2:#111114;--fg:#f5f5f7;--muted:#8b8b93;--line:#232329;--indigo:#7d6cff;--cyan:#40c6dd}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--cyan)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.page{padding:48px 0 24px;border-bottom:1px solid var(--line)}
h1{font-size:26px;margin:0 0 8px;letter-spacing:-.01em}
.page p{margin:6px 0;color:var(--muted);max-width:80ch}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.chip{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:4px 11px}
.dot{width:12px;height:12px;border-radius:50%}
.summary{margin:28px 0;border:1px solid var(--line);border-radius:12px;overflow-x:auto}
table.sum{border-collapse:collapse;width:100%;min-width:620px;font-size:13px}
table.sum th,table.sum td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
table.sum th{color:var(--muted);font-weight:600;background:var(--panel2)}
table.sum tr:last-child td{border-bottom:0}
.badge{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;background:linear-gradient(160deg,#9d8cff,#40c6dd);color:#0b0b0d;font-weight:800;font-size:13px}
.badge.sm{width:22px;height:22px;font-size:12px;border-radius:6px}
.grid{display:grid;grid-template-columns:1fr;gap:22px;padding:8px 0 40px}
@media(min-width:900px){.grid{grid-template-columns:1fr 1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.card-head{display:flex;align-items:center;gap:12px}
.titles{flex:1;min-width:0}
.titles h3{margin:0;font-size:16px}
.slug{color:var(--muted);font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.tag{font-size:11px;color:var(--cyan);border:1px solid var(--line);border-radius:999px;padding:3px 9px}
.meta{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:11px;margin:10px 0 4px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.block{margin-top:10px}
.block h4{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.block h4 em{text-transform:none;letter-spacing:0;font-style:normal;color:#5a5a63;margin-left:6px}
.strip{display:flex;align-items:flex-end;gap:12px;overflow-x:auto;padding:12px;background:var(--panel2);border:1px solid var(--line);border-radius:10px}
.cell{margin:0;flex:0 0 auto;text-align:center}
.stage{display:flex;align-items:center;justify-content:center;min-width:28px;min-height:28px}
.mark{color:#c9c4ff}
.icon{border-radius:0}
figcaption{color:#5a5a63;font-size:10px;margin-top:6px;font-family:ui-monospace,Menlo,monospace}
.note{font-size:12.5px;color:var(--muted);margin:14px 0 0}
.note strong{color:#c9c4ff;font-weight:600}
footer{padding:24px 0 60px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line)}
.hide{position:absolute;width:0;height:0;overflow:hidden}
</style>
</head>
<body>
<div class="hide" aria-hidden="true">
<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"><defs>
<linearGradient id="pg" x1="200" y1="180" x2="824" y2="844" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#9d8cff"/><stop offset=".52" stop-color="#7d6cff"/><stop offset="1" stop-color="#40c6dd"/>
</linearGradient>
<radialGradient id="pglow" cx=".5" cy=".34" r=".72">
<stop offset="0" stop-color="#7d6cff" stop-opacity=".34"/><stop offset=".6" stop-color="#7d6cff" stop-opacity=".06"/><stop offset="1" stop-color="#7d6cff" stop-opacity="0"/>
</radialGradient>
<!--SYMBOLS-->
</defs></svg>
</div>
<div class="wrap">
<header class="page">
  <h1>Photo Relay - Icon Alternatives</h1>
  <p>14 concepts for the macOS app mark and dock icon. Each ships a 24px <code>mark.svg</code> (stroke based, currentColor) for in-app use and a 1024px <code>icon.svg</code> plus rendered <code>icon-1024.png</code> (RGBA, transparent squircle corners) for the Tauri icon flow.</p>
  <p>Each mark is shown at 16, 24, 48, 128, 256 and 512 where it runs, so small-size legibility is visible directly. Geometry is adapted from lucide, tabler and phosphor where a suitable icon existed, then redrawn on one 24 unit grid.</p>
  <div class="chips">
    <span class="chip"><span class="dot" style="background:#0b0b0d;border:1px solid #333"></span>squircle bg #0b0b0d</span>
    <span class="chip"><span class="dot" style="background:#7d6cff"></span>indigo #7d6cff</span>
    <span class="chip"><span class="dot" style="background:#40c6dd"></span>cyan #40c6dd</span>
    <span class="chip">mark = currentColor</span>
    <span class="chip">icon-1024.png = RGBA</span>
  </div>
</header>
<div class="summary">
<table class="sum">
<thead><tr><th>#</th><th>Concept</th><th>Direction</th><th>Style</th><th>Legible at 16px</th></tr></thead>
<tbody>
<!--SUMMARY-->
</tbody>
</table>
</div>
<p class="note" style="margin-top:-8px">Files live in <code>apps/desktop/branding/alternatives/&lt;slug&gt;/</code>. Rendered PNGs are 1024x1024 RGBA at <code>icon-1024.png</code>.</p>
<div class="grid">
<!--CARDS-->
</div>
<footer>
Generated by <code>apps/desktop/branding/build-alternatives.py</code>. Icon geometry adapted from lucide (ISC), tabler (MIT) and phosphor (MIT) on a shared 24 unit grid.
</footer>
</div>
</body>
</html>
"""


def main():
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            p = os.path.join(OUT, name)
            if os.path.isdir(p) and name not in ("fonts",):
                shutil.rmtree(p)
    os.makedirs(OUT, exist_ok=True)

    manifest = []
    for c in CONCEPTS:
        d = os.path.join(OUT, c["slug"])
        os.makedirs(d, exist_ok=True)
        mark_path = os.path.join(d, "mark.svg")
        icon_path = os.path.join(d, "icon.svg")
        png_path = os.path.join(d, "icon-1024.png")
        with open(mark_path, "w", encoding="utf-8") as f:
            f.write(mark_svg(c))
        with open(icon_path, "w", encoding="utf-8") as f:
            f.write(icon_svg(c))
        render_png(icon_path, png_path)
        manifest.append(dict(
            label=c["label"], slug=c["slug"], name=c["name"],
            direction=c["direction"], mode=c["mode"], color=c["color"],
            sw=c["sw"], note=c["note"], best16=c["best16"],
            files=dict(mark=f"{c['slug']}/mark.svg", icon=f"{c['slug']}/icon.svg",
                       png=f"{c['slug']}/icon-1024.png"),
        ))
        print(f"  {c['label']}  {c['name']:<20} -> {c['slug']}/")

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    html = build_html(CONCEPTS)

    html_path = os.path.join(OUT, "comparison.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\ncomparison.html {len(html.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
