#!/usr/bin/env bash
# Build Photo Relay and install it into /Applications.
#
# The app needs two things at runtime:
#   1. A copy of itself in /Applications.
#   2. A pointer to this project folder, because the sync engine lives here and
#      is not bundled inside the app. The pointer is written to
#      ~/Library/Application Support/Photo Relay/project-home and re-read on
#      every launch, so moving or reinstalling the app never breaks it.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
app_name="Photo Relay.app"
bundle="$root/apps/desktop/src-tauri/target/release/bundle/macos/$app_name"
install_dir="${PHOTO_RELAY_INSTALL_DIR:-/Applications}"
pointer="$HOME/Library/Application Support/Photo Relay/project-home"

if [[ ! -d "$bundle" ]]; then
  echo "No built app found. Building it first…"
  (cd "$root/apps/desktop" && npm run tauri build -- --bundles app)
fi

if [[ ! -d "$bundle" ]]; then
  echo "error: build did not produce $bundle" >&2
  exit 1
fi

echo "Installing to $install_dir/$app_name"
# Quit any running copy so the bundle can be replaced cleanly.
osascript -e 'tell application "Photo Relay" to quit' >/dev/null 2>&1 || true
pkill -f "$app_name/Contents/MacOS/photo-relay" >/dev/null 2>&1 || true
sleep 1

rm -rf "$install_dir/$app_name"
cp -R "$bundle" "$install_dir/$app_name"

# Ad-hoc sign so Gatekeeper treats the local build as a stable local app.
codesign --force --deep --sign - "$install_dir/$app_name" >/dev/null 2>&1 || true

mkdir -p "$(dirname "$pointer")"
printf '%s\n' "$root" > "$pointer"

echo "Recorded project folder:"
echo "  $root"
echo "  -> $pointer"
echo
echo "Done. Launch it from Applications, or run:"
echo "  open \"$install_dir/$app_name\""