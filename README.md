# Photo Relay & Photo Drop

Move original photos, videos and Live Photos from an iPhone to a Samsung phone
through your Mac — locally, at full quality, with capture times preserved.
Or share a link with a friend to drop photos straight onto your Samsung —
in the browser, with no app installed on their phone.

```text
iPhone 17 Pro  ──USB──▶  Mac (staging + conversion)  ──ADB──▶  Samsung  ──▶  Google Photos

friend's browser ──HTTPS──▶ Cloudflare Tunnel ──▶ Termux on Samsung ──▶ DCIM/PhotoDrop ──▶ Google Photos
```

> **Friends who want to replicate the setup:** start at
> [`apps/photo-drop/README.md`](apps/photo-drop/README.md) — full install,
> security model, troubleshooting, and improvement roadmap. Repo:
> https://github.com/kumar-karan/photo-relay

Photo Relay is a native macOS app that wraps a battle-tested Python transfer
engine. Photos go **iPhone → Mac → Samsung**, where Google Photos on the
Samsung does the backup. Nothing is uploaded anywhere. Photo Drop is the
same Samsung + `DCIM` + Google Photos idea, but the upload happens from a
friend's browser to a Termux-hosted server behind a Cloudflare tunnel.

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

## Photo Drop (guest uploads)

Photo Drop is the other half of this repo: a small Flask server that runs in
Termux on the Samsung and gives friends a secret browser link. They upload from
any phone with nothing installed, files land in `DCIM/PhotoDrop`, and Google
Photos on the Samsung backs them up.

- **Live owner console** — tap **Open live dashboard** in the Android launcher
  app, or open `/owner/<owner-token>` in a browser. It shows every guest
  session with device label, IP, short id, file count and bytes, plus per-file
  progress bars and measured speed while a file is still uploading.
- **Live guest feedback** — the uploader page shows their session id, the
  phone's free space and how many files the phone has received, and warns
  before the tab is closed mid-transfer.
- **Restart-safe state** — live sessions are rebuilt from the on-disk batch
  manifests, so a restart does not erase the history.
- **No inbound ports** — a Cloudflare quick tunnel fronts the loopback-only
  server; the link is the password.

Full install, security model and troubleshooting:
[`apps/photo-drop/README.md`](apps/photo-drop/README.md).

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
├── apps/photo-drop/             Guest upload server + Android launcher
│   ├── server.py                Flask server, owner console and live state
│   ├── android/                 Launcher app, in-app dashboard, APK build
│   └── tests/                   Auth, upload, space guard and owner API tests
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