#!/usr/bin/env python3
"""Merge the three Photo Relay design mockups into one comparison page.

The mockups share no class names, but they do share five @keyframes names and
each sets global html/body rules. So: rename keyframes per variant and scope the
global rules to a wrapper, then wrap every variant body in that wrapper.
"""
import re

VARIANTS = [
    ("mockup-a-control-room.html", "a"),
    ("mockup-b-focused-relay.html", "b"),
    ("mockup-c-split-deck.html", "c"),
]

DESIGN_DIR = "/Users/karankumar/Documents/antigravity/iphone-samsung-photo-backup/design"


def extract(path, tag):
    source = open(f"{DESIGN_DIR}/{path}", encoding="utf-8").read()
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", source, re.S)
    return match.group(1) if match else ""


def namespace(css, suffix, wrapper):
    """Rename @keyframes and rewrite global element selectors to be scoped."""
    # Every keyframe name gets a per-variant suffix so animations cannot collide.
    names = set(re.findall(r"@keyframes\s+([\w-]+)", css))
    for name in sorted(names, key=len, reverse=True):
        css = re.sub(rf"@keyframes\s+{re.escape(name)}\b", f"@keyframes {name}-{suffix}", css)
        css = re.sub(rf"animation(-name)?:\s*[^;{{}}]*?\b{re.escape(name)}\b",
                     lambda m: m.group(0).replace(name, f"{name}-{suffix}"), css)

    # The variant's global html/body rules must apply to the inner .vbody wrapper
    # (the mockup markup sits inside it), not the comparison section, or the
    # mockups' page-level flex/padding would wreck the comparison chrome. The
    # template neutralizes .vbody's layout props afterwards, keeping only the
    # inherited typography and color.
    css = re.sub(r"(?m)^(\s*)html\s*,\s*body\b", rf"\1{wrapper} .vbody", css)
    css = re.sub(r"(?m)^(\s*)body\s*\{", rf"\1{wrapper} .vbody {{", css)
    css = re.sub(r"(?m)^(\s*)html\s*\{", rf"\1{wrapper} .vbody {{", css)
    return css


def main():
    blocks = []
    for path, suffix in VARIANTS:
        css = namespace(extract(path, "style"), suffix, f".v{suffix}")
        body = extract(path, "body")
        # Keep the variant's own .frame wrapper intact (it is the real 1280x860
        # window), and put everything inside a .vbody that the scoped body rules
        # target. Stripping only the frame's opening tag would unbalance the HTML.
        blocks.append(
            f'<section class="variant v{suffix}" id="variant-{suffix}">'
            f'<div class="vbody">{body}</div>'
            f"</section>\n<style>\n{css}\n</style>"
        )

    open(f"{DESIGN_DIR}/_merged-parts.html", "w", encoding="utf-8").write("\n".join(blocks))
    print("parts written", sum(len(b) for b in blocks), "bytes")


main()