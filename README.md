# Photo Relay

Move original photos, videos and Live Photos from an iPhone to a Samsung phone
through your Mac — locally, at full quality, with capture times preserved.

Photo Relay is a native macOS app that wraps a battle-tested Python transfer
engine. Photos go **iPhone → Mac → Samsung**, where Google Photos on the
Samsung does the backup. Nothing is uploaded anywhere.

```text
iPhone 17 Pro  ──USB──▶  Mac (staging + conversion)  ──ADB──▶  Samsung  ──▶  Google Photos
```

## Why

An old Samsung phone with a modded Google Photos app is the most generous
backup target available: original-quality uploads, effectively unlimited, and no
subscription. The catch is that getting photos onto it has always meant a chain
of cables, AirDrop, and manual cleanup. Photo Relay makes that one repeatable
action with verification at every step.

## What the app does

- **Live relay visualisation** — iPhone, Mac and Samsung with real connection
  state, animated while data moves.
- **Honest progress** — files completed, bytes moved, measured throughput and
  ETA, parsed from the engine's actual log output rather than guessed.
- **Live Photo conversion** — Apple Live Photos become Google Motion Photos
  (lossless video stream copy, exact Apple frame cropping).
- **Verified transfers** — every push is appended to
  `runtime/transfers.jsonl` with size, capture time and verification state.
- **Capture dates preserved** — files land on the Samsung with their original
  timestamps so the gallery sorts correctly.
- **Safe cleanup** — a staged file is only removed after the transfer is
  confirmed. Nothing is deleted on a failed push.
- **Media re-index** — triggers `MediaScanner` so new media appears in the
  Samsung gallery immediately.

## Requirements

- macOS 12 or later, Apple Silicon or Intel
- Node.js 20+ and Rust (for building from source)
- `adb` (Android platform tools), `ffmpeg` and `exiftool` on your `PATH`
- Python 3.10+ with `pymobiledevice3` for the engine
- An iPhone unlocked and trusted on this Mac, a Samsung with USB debugging on

## Project layout

```text
photo-relay/
├── apps/desktop/                Tauri 2 + React + TypeScript macOS app
│   ├── src/                     UI, design system, formatters, relay state
│   └── src-tauri/
│       ├── src/engine.rs        Log parser, event model, transfer journal
│       ├── src/engine_test.rs   Parser tests pinned to the real log format
│       ├── icons/               Vector mark plus generated macOS icon set
│       └── tauri.conf.json
├── sync_engine/                 Python transfer engine (the actual worker)
│   ├── sync.py                  Pipeline: pull, convert, push, verify, index
│   ├── detect_devices.py        Device preflight
│   ├── master_converter.py      Live Photo → Motion Photo
│   └── config.example.json      Copy to config.json and edit
├── runtime/                     Local, git-ignored session data
│   ├── events.jsonl             Structured activity events
│   └── transfers.jsonl          Verified per-file transfer journal
├── scripts/make-icons.sh        Regenerates the macOS icon bundle
├── docs/architecture.md         Design notes and the safety rule
└── .github/workflows/           CI: Rust tests, frontend typecheck, macOS build
```

## Getting started

```bash
# 1. Install engine dependencies
brew install android-platform-tools ffmpeg exiftool
pip3 install pymobiledevice3 tqdm

# 2. Configure the engine
cp sync_engine/config.example.json sync_engine/config.json
$EDITOR sync_engine/config.json

# 3. Install desktop dependencies
cd apps/desktop && npm install && cd ../..

# 4. Run the app in development
cd apps/desktop && npm run tauri dev
```

Build a distributable `.app`:

```bash
cd apps/desktop
npm run tauri build          # produces Photo Relay.app and a .dmg
```

The built app locates the project folder at runtime, so keep this repository
(and its `sync_engine/` and `runtime/` directories) together. Set
`PHOTO_RELAY_HOME` to override the location.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `⌘R` | Refresh engine state |
| `⌘↵` | Start a relay |
| `Esc` | Dismiss dialogs and messages |

## Local data

Everything stays on your Mac inside this repository:

| File | Contents |
| --- | --- |
| `runtime/events.jsonl` | Structured activity events for the UI |
| `runtime/transfers.jsonl` | Verified per-file transfer journal |
| `sync_engine/sync_state.json` | Watermark and sync counters |
| `sync_engine/logs/` | Full run logs |

These are git-ignored because they contain device identifiers and personal
paths. Small JSON documents hold current state; JSONL keeps append-only history
so an interrupted run can always be reconstructed without a database.

## Development

```bash
cd apps/desktop/src-tauri && cargo test    # parser tests
cd apps/desktop && npx tsc -b              # frontend typecheck
./scripts/make-icons.sh                    # regenerate icons from icon.svg
```

## License

MIT