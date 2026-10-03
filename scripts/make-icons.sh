#!/usr/bin/env bash
# Regenerate the macOS icon bundle from the vector mark in
# apps/desktop/src-tauri/icons/icon.svg.
#
# The mark is rendered by macOS Quick Look (WebKit), which keeps the SVG
# gradients and blur filters intact, then downscaled with Lanczos resampling.
# Result: icon.icns, icon.png and the PNG sizes Tauri expects for packaging.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
icons="$root/apps/desktop/src-tauri/icons"
svg="$icons/icon.svg"

for tool in qlmanage magick iconutil; do
  command -v "$tool" >/dev/null || { echo "$tool is required (macOS plus ImageMagick)" >&2; exit 1; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

qlmanage -t -s 2048 -o "$work" "$svg" >/dev/null 2>&1
master="$work/icon.svg.png"
magick identify "$master" >/dev/null

set_size() { magick "$master" -filter Lanczos -resize "${2}x${2}" -depth 8 -strip "$1"; }

set_size "$icons/32x32.png" 32
set_size "$icons/128x128.png" 128
set_size "$icons/128x128@2x.png" 256
set_size "$icons/icon.png" 1024

iconset="$work/icon.iconset"
mkdir -p "$iconset"
set_size "$iconset/icon_16x16.png" 16
set_size "$iconset/icon_16x16@2x.png" 32
set_size "$iconset/icon_32x32.png" 32
set_size "$iconset/icon_32x32@2x.png" 64
set_size "$iconset/icon_128x128.png" 128
set_size "$iconset/icon_128x128@2x.png" 256
set_size "$iconset/icon_256x256.png" 256
set_size "$iconset/icon_256x256@2x.png" 512
set_size "$iconset/icon_512x512.png" 512
set_size "$iconset/icon_512x512@2x.png" 1024

iconutil -c icns "$iconset" -o "$icons/icon.icns"

echo "Wrote:"
ls -1 "$icons"