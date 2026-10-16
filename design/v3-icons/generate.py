#!/usr/bin/env python3
"""Photo Relay — icon exploration generator (v3).

Produces, for every (palette x concept) pair:

    design/v3-icons/<palette>/<concept>/mark.svg        24px, currentColor, stroke
    design/v3-icons/<palette>/<concept>/icon.svg        1024px dark squircle + accent
    design/v3-icons/<palette>/<concept>/icon-1024.png   1024x1024 raster (Quick Look)

and the self-contained comparison page:

    design/v3-icons/comparison.html

Design language:
  * 24x24 geometry grid, round caps/joins, bold stroke (reads at 16-24px).
  * The icon keeps the same silhouette, adds a gradient stroke, a soft accent
    glow and a filled core, matching the current branding squircle (#0b0b0d).
  * Every colour is a token so the page can recolor all icons live via CSS vars.
"""
import os
import re
import subprocess
import tempfile

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Palettes. Each direction is a two-stop accent gradient plus a glow and a
# brighter "core" used for filled accents.
# ---------------------------------------------------------------------------
PALETTES = {
    "ember": {
        "name": "Ember",
        "tag": "warm · recommended",
        "i1": "#FFC24B",  # amber
        "i2": "#F4573E",  # coral-red
        "glow": "#FF8A3D",
        "core": "#FFD98A",
        "desc": "Amber into coral-red. The warm end of the spectrum — reads as "
                "memory, film and light rather than 'AI'. Raycast proved a single "
                "coral-red carries a whole near-black app; this is that move with "
                "a sunrise gradient instead of a flat fill.",
    },
    "verdant": {
        "name": "Verdant",
        "tag": "green · trust",
        "i1": "#93E9AC",  # mint
        "i2": "#12B981",  # emerald
        "glow": "#23C08A",
        "core": "#C4F6D2",
        "desc": "Mint into emerald. Green is the honest colour of 'verified, "
                "nothing lost, backup done', so it pairs with the product's "
                "integrity promise. Cool and grown-up, with none of the indigo "
                "sheen that reads as generic AI.",
    },
    "marine": {
        "name": "Marine",
        "tag": "blue · calm",
        "i1": "#8FC2FF",  # sky
        "i2": "#2E6BE6",  # royal blue
        "glow": "#5B9BFF",
        "core": "#CFE2FF",
        "desc": "Sky into royal blue. The safe, pro choice — but a true royal "
                "blue, not the cyan-teal of the old mark and not an electric "
                "indigo. Calm, tool-like, sits easily in a Dock of Apple icons.",
    },
    "citrine": {
        "name": "Citrine",
        "tag": "lime · bold",
        "i1": "#E8F87A",  # chartreuse
        "i2": "#7BD34E",  # leaf green
        "glow": "#A6E85A",
        "core": "#F2FBB8",
        "desc": "Chartreuse into leaf green. The most distinctive direction — "
                "the accent family Arc, Supabase and Vercel use to look crafted "
                "rather than corporate. High energy on near-black; unmistakably "
                "not an AI-gradient app.",
    },
}

PALETTE_ORDER = ["ember", "verdant", "marine", "citrine"]

# ---------------------------------------------------------------------------
# Concepts. Each is 24x24 geometry. `shapes` are SVG elements placed in a
# group that supplies fill="none" + the stroke; a shape may override fill with
# a token (A1/A2/CORE) to add a filled accent.
# ---------------------------------------------------------------------------
TOKENS = {
    "A1": {"file": "{i1}", "html": "var(--i1)"},
    "A2": {"file": "{i2}", "html": "var(--i2)"},
    "CORE": {"file": "{core}", "html": "var(--core)"},
    "GLOW": {"file": "{glow}", "html": "var(--glow)"},
}

CONCEPTS = [
    {
        "slug": "relay",
        "name": "Relay",
        "note": "Two opposed arrows — the literal handoff between iPhone and Samsung.",
        "shapes": [
            '<path d="M3 8.5h13.6"/>',
            '<path d="M13.4 4.6 17.4 8.5 13.4 12.4"/>',
            '<path d="M21 15.5H7.4"/>',
            '<path d="M10.6 11.6 6.6 15.5 10.6 19.4"/>',
        ],
    },
    {
        "slug": "aperture",
        "name": "Aperture",
        "note": "The refined iris — keeps the brand's photo DNA, now with a lit core.",
        "shapes": [
            '<circle cx="12" cy="12" r="9.4"/>',
            '<path d="M14.31 8 20.05 17.94"/>',
            '<path d="M9.69 8 21.17 8"/>',
            '<path d="M7.38 12 13.12 2.06"/>',
            '<path d="M9.69 16 3.95 6.06"/>',
            '<path d="M14.31 16 2.83 16"/>',
            '<path d="M16.62 12 10.88 21.94"/>',
            '<circle cx="12" cy="12" r="1.7" fill="CORE"/>',
        ],
    },
    {
        "slug": "conduit",
        "name": "Conduit",
        "note": "Two device slabs with a straight transfer between them.",
        "shapes": [
            '<rect x="3.4" y="5" width="4.4" height="14" rx="1.7"/>',
            '<rect x="16.2" y="5" width="4.4" height="14" rx="1.7"/>',
            '<path d="M9.4 12h5.2"/>',
            '<path d="M12.7 10.2 14.6 12 12.7 13.8"/>',
        ],
    },
    {
        "slug": "frames",
        "name": "Frames",
        "note": "Two photo frames sliding past each other — a library on the move.",
        "shapes": [
            '<rect x="3.6" y="9.2" width="10.6" height="8.6" rx="2.1"/>',
            '<rect x="9.8" y="6.2" width="10.6" height="8.6" rx="2.1" fill="A2" fill-opacity="0.16"/>',
            '<path d="M4.6 20.4h3.2"/>',
            '<path d="M9.8 20.4h2.2"/>',
        ],
    },
    {
        "slug": "focus",
        "name": "Focus",
        "note": "A lens with a locked focus point — sharp, minimal, photographic.",
        "shapes": [
            '<circle cx="12" cy="12" r="9.4"/>',
            '<circle cx="12" cy="12" r="5.1"/>',
            '<circle cx="12" cy="12" r="1.8" fill="CORE"/>',
            '<path d="M12 2.6v2.2"/>',
            '<path d="M12 19.2v2.2"/>',
            '<path d="M2.6 12h2.2"/>',
            '<path d="M19.2 12h2.2"/>',
        ],
    },
    {
        "slug": "orbit",
        "name": "Orbit",
        "note": "A ring with a satellite catching it up — continuous sync.",
        "shapes": [
            '<path d="M12 3.1a8.9 8.9 0 1 0 8.9 8.9"/>',
            '<circle cx="20" cy="5.1" r="2.1" fill="CORE" stroke="none"/>',
            '<path d="M17.4 8.4 20 5.1"/>',
        ],
    },
    {
        "slug": "shutter",
        "name": "Shutter",
        "note": "Six-blade shutter as a pinwheel — motion and capture in one mark.",
        "shapes": [
            '<circle cx="12" cy="12" r="9.4"/>',
            '<path d="M12 2.6 16 9.6"/>',
            '<path d="M20.1 7.7 12.6 9.9"/>',
            '<path d="M20.1 16.3 14.9 10.6"/>',
            '<path d="M12 21.4 8 14.4"/>',
            '<path d="M3.9 16.3 11.4 14.1"/>',
            '<path d="M3.9 7.7 9.1 13.4"/>',
            '<circle cx="12" cy="12" r="1.5" fill="CORE"/>',
        ],
    },
    {
        "slug": "beam",
        "name": "Beam",
        "note": "Two ends with particles crossing the gap — a live, wireless transfer.",
        "shapes": [
            '<path d="M4.6 4.6v14.8"/>',
            '<path d="M19.4 4.6v14.8"/>',
            '<path d="M8 12h8.4" stroke-dasharray="0.1 3.1"/>',
            '<circle cx="9.1" cy="12" r="1.5" fill="CORE" stroke="none"/>',
            '<circle cx="12" cy="12" r="1.5" fill="A1" stroke="none"/>',
            '<circle cx="14.9" cy="12" r="1.5" fill="A2" stroke="none"/>',
        ],
    },
    {
        "slug": "prism",
        "name": "Prism",
        "note": "A beam entering and leaving a prism — the Mac routing every photo.",
        "shapes": [
            '<path d="M12 4.4 20.2 18.6 3.8 18.6Z"/>',
            '<path d="M2.4 12.6h6.4"/>',
            '<path d="M15.2 12.6h6.4"/>',
            '<path d="M9.6 11.5l2.2 1.1-2.2 1.1z" fill="CORE" stroke="none"/>',
        ],
    },
]

ICON_STROKE = 2.4      # in 24-unit space -> ~63px at 1024
MARK_STROKE = 1.9
ICON_SCALE = 26.333    # 24 * 26.333 = 632, centred by a 196 margin


def apply_tokens(text, palette):
    for tok, val in TOKENS.items():
        text = text.replace(f'"{tok}"', f'"{val["file"].format(**palette)}"')
    return text


def grad_defs(palette, ident, html=False):
    if html:
        stops = (f'<stop offset="0" stop-color="var(--i1)"/>'
                 f'<stop offset="1" stop-color="var(--i2)"/>')
        glow = ('<stop offset="0" stop-color="var(--glow)" stop-opacity="0.30"/>'
                '<stop offset="0.55" stop-color="var(--glow)" stop-opacity="0.05"/>'
                '<stop offset="1" stop-color="var(--glow)" stop-opacity="0"/>')
    else:
        stops = (f'<stop offset="0" stop-color="{palette["i1"]}"/>'
                 f'<stop offset="1" stop-color="{palette["i2"]}"/>')
        glow = (f'<stop offset="0" stop-color="{palette["glow"]}" stop-opacity="0.30"/>'
                f'<stop offset="0.55" stop-color="{palette["glow"]}" stop-opacity="0.05"/>'
                f'<stop offset="1" stop-color="{palette["glow"]}" stop-opacity="0"/>')
    return (
        f'<linearGradient id="{ident}-s" x1="0" y1="0" x2="1" y2="1">'
        f'{stops}</linearGradient>'
        f'<radialGradient id="{ident}-glow" cx="0.5" cy="0.34" r="0.78">'
        f'{glow}</radialGradient>'
    )


def shapes_markup(concept, palette):
    return "\n    ".join(apply_tokens(s, palette) for s in concept["shapes"])


def build_mark(concept):
    body = re.sub(r'"(A1|A2|CORE|GLOW)"', '"currentColor"',
                  "\n    ".join(concept["shapes"]))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{MARK_STROKE}" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">\n    '
        f'{body}\n'
        '</svg>\n'
    )


def build_icon(concept, palette, ident):
    shapes = shapes_markup(concept, palette)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    {grad_defs(palette, ident)}
  </defs>
  <rect width="1024" height="1024" rx="232" fill="#0b0b0d"/>
  <rect width="1024" height="1024" rx="232" fill="url(#{ident}-glow)"/>
  <rect x="6" y="6" width="1012" height="1012" rx="228" fill="none" stroke="#ffffff" stroke-opacity="0.07" stroke-width="12"/>
  <g transform="translate(196 196) scale({ICON_SCALE})" fill="none"
     stroke="url(#{ident}-s)" stroke-width="{ICON_STROKE}"
     stroke-linecap="round" stroke-linejoin="round">
    {shapes}
  </g>
</svg>
'''


def render_png(svg_path, out_path):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["qlmanage", "-t", "-s", "1024", "-o", tmp, svg_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        produced = os.path.join(tmp, os.path.basename(svg_path) + ".png")
        subprocess.run(["magick", produced, "-depth", "8", "-strip", out_path], check=True)


def write_files():
    written = 0
    for pslug in PALETTE_ORDER:
        palette = PALETTES[pslug]
        for concept in CONCEPTS:
            cdir = os.path.join(OUT, pslug, concept["slug"])
            os.makedirs(cdir, exist_ok=True)
            with open(os.path.join(cdir, "mark.svg"), "w", encoding="utf-8") as fh:
                fh.write(build_mark(concept))
            ident = f'{pslug}-{concept["slug"]}'
            svg = build_icon(concept, palette, ident)
            svg_path = os.path.join(cdir, "icon.svg")
            with open(svg_path, "w", encoding="utf-8") as fh:
                fh.write(svg)
            render_png(svg_path, os.path.join(cdir, "icon-1024.png"))
            written += 1
    return written


if __name__ == "__main__":
    n = write_files()
    print(f"wrote {n} concept sets across {len(PALETTE_ORDER)} palettes")
