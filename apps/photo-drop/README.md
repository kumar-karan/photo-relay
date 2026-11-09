# Photo Drop

A photo drop server that runs on your Samsung phone and turns it into a
private, shareable upload inbox. A friend opens a secret link in any phone
browser, picks photos and videos, watches them upload with real progress, and
lands on a confirmation page. Files land in `DCIM/PhotoDrop` on your phone, so
Google Photos backs them up to your account automatically.

Nothing is installed on the friend's phone. Nothing is stored on anyone else's
server. No app store, no account, no subscription.

```
friend's browser  ──HTTPS──▶  Cloudflare Tunnel  ──▶  Termux  ──▶  DCIM/PhotoDrop
  (nothing installed)         (public link)         (this repo)       │
                                                              Google Photos
                                                              backs it up
```

> **Repo:** https://github.com/kumar-karan/photo-relay
> Share this page with anyone who wants to replicate the setup. Everything below
> is what a friend needs — no prior context required.

## Requirements

- An Android phone (Samsung or any device that can run Termux)
- [Termux](https://f-droid.org/packages/com.termux/) **and** [Termux:API](https://f-droid.org/packages/com.termux.api/) installed **from the same source** (both F-Droid, or both Play Store) — a signature mismatch makes `termux-media-scan` hang
- Shared storage permission (`termux-setup-storage`)
- Google Photos signed in and set to back up `DCIM` (see [One-time Google Photos setup](#one-time-google-photos-setup))
- A computer with `adb` for the APK path, **or** just a browser for the shell path
- A friend with any phone browser

## Two ways to run it

### Option A — Android app (recommended for daily use)

The `android/` folder builds a small launcher app (`dev.photodrop.app`) that
starts and stops the Termux server and tunnel for you, and always shows the
live link. This is what the phone runs day-to-day.

1. Build the APK on your Mac/Linux (Android SDK must be present under
   `apps/t3-server-android/android-sdk/` — see `android/build.sh`):
   ```bash
   bash apps/photo-drop/android/build.sh   # must print BUILD_OK
   ```
2. Push it + the server scripts to the phone over USB:
   ```bash
   bash apps/photo-drop/deploy.sh
   ```
3. On the phone, open Termux and run the printed install command once, then
   install `photodrop.apk` (adb install or tap to install).
4. Open the **Photo Drop** app → **Start**. It shows the live link + QR code.
   Send that link to your friend. **Stop** shuts everything down cleanly.

### Option B — Termux shell only (quickest to try)

Copy this directory into Termux (`~/photo-drop`), then:

```bash
cd ~/photo-drop
bash install.sh
bash start.sh --tunnel
```

It prints a `trycloudflare.com` link. That link, plus the token in the path,
is the whole credential:

```
https://<something>.trycloudflare.com/d/<token>
```

On your own Wi-Fi skip the tunnel: `bash start.sh` and use the local URL it
prints. Shut down with `bash stop.sh`.

## One-time Google Photos setup (you only do this once)

1. Open Google Photos on the Samsung → your profile → **Google Photos settings**
   → **Backup** → ON, and set **Backup folders → DCIM → PhotoDrop** to ON.
2. If uploads don't appear, open the Samsung Gallery app once and reboot.
   Every version of this problem traces back to MediaStore; the owner
   dashboard (`<base-url>/owner/<owner-token>`) reports which scan technique
   actually worked on your device.

## What the friend sees

1. Opens your link. Nothing to install, no login.
2. Taps the drop zone, picks any number of photos/videos from their camera
   roll (HEIC, JPEG, MP4, MOV, Live Photos).
3. Each file uploads with a real percentage — driven by the browser's native
   `XMLHttpRequest` progress events, so the number is bytes actually sent.
4. They see the phone's free space before and during the session. Uploads pause
   if free space drops below the safety reserve (2 GiB by default).
5. They land on a confirmation page with a thumbnail grid and file list.

## Security model — please read

- **The link is the password.** Anyone who has it can upload while you are
  running. Share it directly (text, not a public post), and hit **Stop** when
  you are done. Quick-tunnel links (`*.trycloudflare.com`) die on reboot or
  Stop and are re-minted on the next Start — an old link you already sent will
  not come back.
- **Tokens never travel in query strings.** They live in the URL path and are
  exchanged for an `HttpOnly` cookie. Query strings leak into logs and
  `Referer` headers; paths are safer.
- **`/healthz` reveals nothing** without a token. Free space and batch counts
  are token-holders only.
- **The server binds `127.0.0.1`** and `cloudflared` terminates TLS in front of
  it. Never change `PHOTO_DROP_HOST` to `0.0.0.0` unless you understand it
  exposes the server to your LAN.
- **Space is checked twice** — from `Content-Length` before a byte is written,
  and continuously during the write. A rejected upload writes nothing; the
  body streams to a `.part` file deleted on failure.

## Configuration

Everything lives in `~/.photo-drop/env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PHOTO_DROP_TOKEN` | generated | The drop link credential |
| `PHOTO_DROP_OWNER_TOKEN` | generated | Owner dashboard credential |
| `PHOTO_DROP_DIR` | `/storage/emulated/0/DCIM/PhotoDrop` | Where files land (keep it flat — nested folders confuse Google Photos backup) |
| `PHOTO_DROP_PORT` | `8080` | Local port |
| `PHOTO_DROP_HOST` | `127.0.0.1` | Bind address — keep it local, the tunnel fronts it |
| `PHOTO_DROP_RESERVE_BYTES` | `2147483648` (2 GiB) | Uploads stop below this much free |
| `PHOTO_DROP_MAX_FILE_BYTES` | `2147483648` (2 GiB) | Per-file cap |
| `PHOTO_DROP_MAX_FILES` | `500` | Per-session cap |
| `PHOTO_DROP_MAX_CONCURRENT` | `3` | Uploads in flight at once; extras get HTTP 503 |

## Keeping the phone awake

While it runs, the phone must stay awake — `start.sh` / the app takes a Termux
wake lock. Keep it plugged in, and set **Settings → Apps → Termux → Battery →
Unrestricted**, or Android will doze the tunnel mid-upload.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Link returns HTTP 530 | Tunnel has no origin — server is stopped. Hit Start again; you will get a *new* link. |
| `termux-media-scan` hangs | Termux and Termux:API are from different sources. Reinstall both from the same source. |
| Photos don't appear in Google Photos | Enable the `PhotoDrop` backup folder (above), open Gallery once, reboot. Check the owner dashboard's scan report. |
| Upload stalls at 0% | Phone dozed. Plug in, set Termux battery to Unrestricted, retry. |

## Planned improvements (roadmap)

These are deliberately not built yet — they are the honest next steps if you
want to contribute:

1. **Stable tunnel URL** — a named Cloudflare tunnel (`yourname.trycloudflare.com`
   via a free Cloudflare account + custom hostname) so the link survives reboots
   instead of being re-minted. Today's quick tunnel is zero-setup but ephemeral.
2. **Resumable chunked uploads** — today one file = one request, so a dropped
   connection restarts that file. Chunked resumption would save multi-GB video
   uploads on flaky networks.
3. **Token rotation + expiry** — one-tap "rotate link" in the owner dashboard
   and auto-expiry after N hours, for when you send the link to someone you
   don't fully trust.
4. **EXIF / Live Photo handling** — preserve capture time + location through
   to MediaStore (HEIC and Motion Photos are preserved today; verify on your
   Android version).
5. **LAN-only mode** — skip the tunnel entirely on trusted Wi-Fi with a
   `http://<phone-ip>:8080` link and a PIN, for parties.

## Why not croc / Swap / Syncthing?

- **croc** — excellent and one command, but no free-space pre-check and no
  MediaStore notification. A fine *complement*: point a friend at `croc` and
  have a watcher move files into `DCIM`.
- **Swap** — best LAN drag-and-drop UI, but LAN-only, plain HTTP, no space check.
- **Syncthing-Fork** — the only off-the-shelf option with proven MediaStore
  handling, but a much heavier setup and a lineage that lost its maintainer once.
- Related projects worth reading if you want to extend this:
  [croc](https://github.com/schollz/croc) (P2P transfer), [LocalSend](https://github.com/localsend/localsend) (LAN sharing), [Magic Wormhole](https://github.com/warner/magic-wormhole) (code-phrase transfers).

## Tests

```bash
python3 -m pip install flask pytest
python3 -m pytest apps/photo-drop/tests/ -q
```

Covers auth, upload, filename sanitisation, space guard, size guard, and the
confirmation page.
