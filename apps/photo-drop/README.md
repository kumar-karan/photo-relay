# Photo Drop

A photo drop server that runs on the owner's Samsung phone. A friend opens a
secret link in any phone browser, picks photos and videos, watches them upload
with real progress, and lands on a confirmation page. The files land in `DCIM`
on the phone, so Google Photos backs them up to the owner's account on its own.

Nothing is installed on the friend's phone. Nothing is stored on anyone else's
server.

```
friend's browser  ──HTTPS──▶  Cloudflare Tunnel  ──▶  Termux  ──▶  DCIM/PhotoDrop
  (nothing installed)         (public link)         (this repo)       │
                                                              Google Photos
                                                              backs it up
```

## Why this exists instead of an app

The hard part is not the upload. It is that **Google Photos queries MediaStore,
not the filesystem**. A file written into `DCIM` is invisible to Google Photos
until MediaProvider is told it exists. Most off-the-shelf solutions write files
and leave them invisible — [Syncthing's own maintainer admits](https://forum.syncthing.net/t/images-are-not-indexed-at-android-os-level/20812)
its notification "has bugs/rotted with android apis changing".

So this server does the upload *and* owns the media-library handshake, and
`media_scan.sh` escalates through every known technique and reports which one
actually worked on the device it ran on.

## Requirements

- Termux + Termux:API on the Samsung
- Shared storage granted (`termux-setup-storage`)
- Google Photos backed up and configured to cover `DCIM`
- A friend with a phone browser

## Install

Copy this directory into Termux (`~/photo-drop`), then:

```bash
cd ~/photo-drop
bash install.sh
```

`install.sh` installs Python packages, grants storage, fetches `cloudflared`,
generates the two access tokens into `~/.photo-drop/env`, and prints which
media-scan techniques this device supports.

## Run

```bash
bash start.sh --tunnel
```

It prints a `trycloudflare.com` link. That link, plus the token in the path,
is the whole credential:

```
https://<something>.trycloudflare.com/d/<token>
```

Send that to your friend. On the owner's own Wi-Fi you can skip the tunnel and
use `bash start.sh`, then read the local URL it prints.

While it runs, the phone must stay awake — `start.sh` takes a Termux wake lock
automatically. For several hours plugged in that is enough. If the phone still
sleeps, set **Settings → Apps → Termux → Battery → Unrestricted**.

To shut down:

```bash
bash stop.sh
```

## What the friend sees

1. Taps the drop zone, picks any number of photos and videos from their camera
   roll. Nothing is installed.
2. Each file uploads one at a time with a real percentage — driven by the
   browser's native `XMLHttpRequest` progress events, so the number is bytes
   actually sent, not a fake animation.
3. They see the phone's free space before and during the session.
4. They land on a confirmation page with a thumbnail grid and a file list, and
   can close the tab.

## Configuration

Everything lives in `~/.photo-drop/env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PHOTO_DROP_TOKEN` | generated | The drop link credential |
| `PHOTO_DROP_OWNER_TOKEN` | generated | Owner dashboard credential |
| `PHOTO_DROP_DIR` | `/storage/emulated/0/DCIM/PhotoDrop` | Where files land |
| `PHOTO_DROP_PORT` | `8080` | Local port |
| `PHOTO_DROP_HOST` | `127.0.0.1` | Bind address — keep it local, the tunnel fronts it |
| `PHOTO_DROP_RESERVE_BYTES` | `2147483648` (2 GiB) | Uploads stop below this much free |
| `PHOTO_DROP_MAX_FILE_BYTES` | `2147483648` (2 GiB) | Per-file cap |
| `PHOTO_DROP_MAX_FILES` | `500` | Per-session cap, counted across all of the session's batches |
| `PHOTO_DROP_MAX_CONCURRENT` | `3` | Uploads in flight at once; extras get HTTP 503 |

## Safety behaviour

- **Space is checked twice** — once from `Content-Length` before a byte is
  written, and again continuously during the write, so a large video cannot
  quietly eat the reserve. A third check covers the Termux home partition,
  which holds the manifests and logs and is a different volume from `DEST`.
- **A rejected upload writes nothing.** The body streams to a `.part` file that
  is deleted on failure; only a complete file is renamed into place. Stale
  `.part` files are swept on boot.
- **Concurrent uploads are bounded.** Flask's dev server spawns a thread per
  request, so `PHOTO_DROP_MAX_CONCURRENT` uploads run at once and the rest get
  HTTP 503 with `Retry-After` rather than being queued. Slots are released in a
  `finally`, so a failed upload cannot leak one.
- **Filenames are sanitised.** `../../etc/passwd` becomes `etc_passwd` inside
  the destination directory. The *original* filename is displayed back to the
  uploader on the confirmation page and is HTML-escaped there.
- **Batches belong to a session.** Another session cannot append to or read a
  batch it did not create, and the per-session file cap cannot be reset by
  inventing a new `?batch=` id.
- **The link is the credential.** Random 24-char token, compared in constant
  time, exchanged for an `HttpOnly`, `SameSite=Lax` cookie on first visit. The
  cookie is looked up server-side, not compared against the master token.
- **The token never travels in a query string.** It lives in the URL path or the
  `X-PD-Token` header only, because query strings land in access logs and
  `Referer` headers. The landing page accepts no token at all.
- **`/healthz` reveals nothing without a token.** Bare `{"ok": true}` for
  anyone; the device path, free bytes and session counts are token-holders only.
- **Append-only files are capped.** Manifest at 1 MB, log rotates at 2 MB.
- **Exposed only through the tunnel.** The server binds `127.0.0.1` and
  `cloudflared` terminates TLS in front of it.

## If Google Photos doesn't pick the photos up

Check the owner dashboard — it shows which scan technique succeeded. If they
all failed, open the Samsung Gallery app once, which triggers a rescan, and
reboot if needed. Every version of this problem traces back to MediaStore, so
the dashboard's technique report is the first thing to look at.

## Owner dashboard

```
<base-url>/owner?k=<PHOTO_DROP_OWNER_TOKEN>
```

Shows the drop link, destination, live free space, which media-scan techniques
this device supports, and recent upload batches with file counts and sizes.

## Why not croc / Swap / Syncthing?

- **croc** — excellent and one command, but no free-space pre-check and no
  MediaStore notification. It is also a fine *complement*: you could point a
  friend at `croc` and have a watcher script move files into `DCIM`.
- **Swap** — best LAN drag-and-drop UI, but LAN-only, plain HTTP, and no space
  check.
- **Syncthing-Fork** — the only off-the-shelf option with proven MediaStore
  handling, but a much heavier setup and a project lineage that has already
  lost its maintainer once.

## Tests

`server.py` has been exercised end to end for auth, upload, filename
sanitisation, the space guard, the size guard and the confirmation page.