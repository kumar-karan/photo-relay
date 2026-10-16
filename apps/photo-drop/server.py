#!/data/data/com.termux/files/usr/bin/python
"""
Photo Drop — a single-file photo drop server for Android (Termux).

A friend opens a secret link in any phone browser, picks photos and videos,
watches them upload with real progress, and lands with a confirmation page.
The files land in DCIM on the owner's Samsung, which makes Google Photos
back them up to the owner's account automatically.

Everything the friend needs is a browser. Nothing is installed on their phone.

Design notes
------------
* MediaStore, not the filesystem, is the source of truth for Google Photos.
  Every completed file goes through media_scan.sh, which escalates through
  the known notification techniques and reports which one worked.
* Storage is checked *before* accepting a file and *during* the write, so a
  full disk degrades into a clean error instead of a half-written file.
* One file per request from the browser. That is what makes native XHR
  upload progress possible — the browser reports bytes-sent for free, which
  means no chunked protocol, no SSE, no websocket.
* Metadata lives in Termux home, never inside DCIM, so we never pollute the
  gallery with stray files.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from markupsafe import escape

from flask import (
    Flask,
    abort,
    jsonify,
    make_response,
    redirect,
    request,
    send_file,
)
from werkzeug.exceptions import ClientDisconnected
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

HOME = Path(os.environ.get("PHOTO_DROP_HOME", Path.home() / ".photo-drop"))

TOKEN = os.environ.get("PHOTO_DROP_TOKEN", "").strip()
OWNER_TOKEN = os.environ.get("PHOTO_DROP_OWNER_TOKEN", "").strip()

DEST = Path(os.environ.get("PHOTO_DROP_DIR", "/storage/emulated/0/DCIM/PhotoDrop"))

# One folder, deliberately.
#
# A dated layout such as DCIM/PhotoDrop/2026-10-16 reads better on the
# filesystem, but Google Photos lists nested folders separately. A parent that
# is switched on while its date subfolder is switched off backs up nothing at
# all, and it fails silently. One folder is one toggle with no way to half
# configure it, so there is no dated option to switch on by mistake.

HOST = os.environ.get("PHOTO_DROP_HOST", "127.0.0.1")
PORT = int(os.environ.get("PHOTO_DROP_PORT", "8080"))

# Free space we refuse to go below. Uploads stop cleanly rather than filling
# the device and wedging the phone.
RESERVE_BYTES = int(os.environ.get("PHOTO_DROP_RESERVE_BYTES", str(2 * 1024**3)))  # 2 GiB

MAX_FILE_BYTES = int(os.environ.get("PHOTO_DROP_MAX_FILE_BYTES", str(2 * 1024**3)))  # 2 GiB
MAX_FILES_PER_SESSION = int(os.environ.get("PHOTO_DROP_MAX_FILES", "500"))

# Concurrent uploads allowed at once. Flask's dev server spawns a thread per
# request, so without this a client could open hundreds of simultaneous
# multi-gigabyte writes and exhaust RAM, file descriptors or the disk write
# queue. Uploads are refused with 503 rather than queued, so a phone never
# silently builds a backlog it cannot drain.
MAX_CONCURRENT_UPLOADS = int(os.environ.get("PHOTO_DROP_MAX_CONCURRENT", "3"))
_UPLOAD_SLOTS = threading.BoundedSemaphore(max(1, MAX_CONCURRENT_UPLOADS))

# How long a session cookie stays valid.
SESSION_TTL = int(os.environ.get("PHOTO_DROP_SESSION_TTL", str(12 * 3600)))

COOKIE = "pd_session"
MEDIA_SCAN = str(Path(__file__).with_name("media_scan.sh"))

BATCHES = HOME / "batches"
LOGS = HOME / "logs"

app = Flask(__name__)


# --------------------------------------------------------------------------
# storage helpers
# --------------------------------------------------------------------------


def disk_free() -> int:
    """Free bytes on the volume holding DEST.

    On Termux this is a FUSE view of shared storage; statvfs works through it.
    If it ever fails we report a large number rather than blocking uploads,
    because a wrong "disk full" is worse than no check at all.
    """
    probe = DEST if DEST.exists() else DEST.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return RESERVE_BYTES * 100


def disk_total() -> int:
    """Total bytes on the volume holding DEST, for a used/free ratio."""
    probe = DEST if DEST.exists() else DEST.parent
    try:
        return shutil.disk_usage(probe).total
    except OSError:
        return 0


def disk_free_home() -> int:
    """Free bytes on the volume holding manifests, logs and the session store.

    Those live in Termux home, not in DEST, so a single check on DEST would
    miss a full home partition entirely.
    """
    try:
        return shutil.disk_usage(HOME).free
    except OSError:
        return RESERVE_BYTES * 100


def enough_space(needed: int) -> bool:
    return disk_free() - needed >= RESERVE_BYTES


def unique_name(raw: str, folder: Path) -> str:
    """Sanitise the uploaded filename and keep it recognisable.

    The name the friend saw on their own camera roll is what they will look
    for, and it is what shows up in Google Photos, so it is preserved. The
    random prefix this used to add made every file unreadable in a gallery for
    no gain: the folder is not browsable without the token anyway. Collisions
    get a numeric suffix instead.
    """
    base = secure_filename(raw or "photo")
    if not base or base in {".", ".."}:
        base = "photo"
    # secure_filename strips dots entirely, which costs us the extension.
    stem, dot, ext = raw.rpartition(".")
    if dot and len(ext) <= 5 and stem:
        base = f"{secure_filename(stem)}.{secure_filename(ext).lower()}"
    if len(base) > 120:
        stem, _, ext = base.rpartition(".")
        base = f"{stem[:100]}.{ext}" if ext else stem[:120]

    candidate = base
    n = 2
    while (folder / candidate).exists():
        stem, _, ext = base.rpartition(".")
        candidate = f"{stem}-{n}.{ext}" if ext else f"{base}-{n}"
        n += 1
    return candidate


def session_id() -> str:
    return request.cookies.get(COOKIE, "")


def new_session() -> str:
    return secrets.token_urlsafe(24)


def set_session_cookie(resp, sid: str):
    # Behind cloudflared the request reaching Flask is plain HTTP even though
    # the browser used HTTPS, so request.is_secure is False and Secure would
    # silently be dropped. Trust the proxy header instead.
    forwarded = request.headers.get("X-Forwarded-Proto", "")
    is_https = request.is_secure or forwarded.split(",")[0].strip() == "https"
    resp.set_cookie(
        COOKIE,
        sid,
        max_age=SESSION_TTL,
        httponly=True,
        samesite="Lax",
        secure=is_https,
        path="/",
    )


def log(line: str):
    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = LOGS / "photo-drop.log"
    # Same reasoning as the manifest cap: rotate rather than grow forever.
    if path.exists() and path.stat().st_size > 2_000_000:
        path.replace(LOGS / "photo-drop.log.1")
    with open(path, "a") as fh:
        fh.write(f"{stamp} {line}\n")


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

TOKEN_OK = bool(TOKEN) and len(TOKEN) >= 12
if not TOKEN_OK:
    print(
        "\n  PHOTO_DROP_TOKEN is missing or shorter than 12 characters.\n"
        "  Refusing to start. Generate one with:\n"
        "      python -c \"import secrets;print(secrets.token_urlsafe(16))\"\n",
        file=__import__("sys").stderr,
    )
    raise SystemExit(1)

OWNER_OK = bool(OWNER_TOKEN) and len(OWNER_TOKEN) >= 12


def check_token(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate or "", expected or "")


# --- session store ---------------------------------------------------------
# The session cookie has to be validated against something. Comparing it to
# the master token can never succeed, because the cookie holds a random id.
# So sessions are recorded server-side and looked up here.
#
# This also gives batches a real owner: a batch id is only accepted if it was
# created by the session presenting it, which is what makes MAX_FILES_PER_SESSION
# mean anything.

SESSIONS = HOME / "sessions.json"
SESSION_LOCK = threading.Lock()

# Upper bound on the store so a long-running phone can't grow it forever.
MAX_SESSIONS = 200


def _load_sessions() -> dict:
    try:
        return json.loads(SESSIONS.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sessions(data: dict):
    SESSIONS.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS.write_text(json.dumps(data))


def register_session(sid: str):
    with SESSION_LOCK:
        data = _load_sessions()
        now = time.time()
        # Drop anything expired, oldest-first, so the store cannot grow forever.
        data = {k: v for k, v in data.items() if v > now}
        while len(data) >= MAX_SESSIONS:
            data.pop(min(data, key=lambda k: data[k]), None)
        data[sid] = now + SESSION_TTL
        _save_sessions(data)


def valid_session(sid: str) -> bool:
    if not sid:
        return False
    with SESSION_LOCK:
        expiry = _load_sessions().get(sid)
    return bool(expiry) and expiry > time.time()


def require_drop_token() -> tuple[str, bool]:
    """Authorise a request to the drop endpoint.

    Returns (session_id, is_new). A new session is minted only when a valid
    token is presented — which is the first visit to a shared link.
    """
    sid = session_id()
    if valid_session(sid):
        return sid, False

    supplied = (
        request.view_args.get("token", "")
        or request.headers.get("X-PD-Token", "")
    )
    if check_token(supplied, TOKEN):
        sid = new_session()
        register_session(sid)
        return sid, True

    abort(404)


def batch_owned_by(bid: str, sid: str) -> bool:
    """True if this session created the batch, or has not claimed it yet.

    An unclaimed batch can be adopted by whoever reaches it first; a claimed
    one is off-limits. This is what stops the per-session file cap from being
    reset by simply inventing a new batch id.
    """
    marker = batch_dir(bid) / "owner"
    try:
        owner = marker.read_text().strip()
    except OSError:
        return True
    return owner == sid


def claim_batch(bid: str, sid: str):
    marker = batch_dir(bid) / "owner"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(sid)


# --------------------------------------------------------------------------
# batch journal
# --------------------------------------------------------------------------


def batch_dir(bid: str) -> Path:
    return BATCHES / bid


def record_upload(bid: str, name: str, original: str, size: int, scanned: str):
    d = batch_dir(bid)
    d.mkdir(parents=True, exist_ok=True)
    entry = {
        "name": name,
        "original": original,
        "size": size,
        "scanned": scanned,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest = d / "manifest.jsonl"
    # Cap the manifest. On a phone that is never going to be read, and an
    # unbounded append-only file in a small partition is a slow-motion failure.
    if manifest.exists() and manifest.stat().st_size > 1_000_000:
        manifest.unlink(missing_ok=True)
    with open(manifest, "a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def batch_files(bid: str) -> list[dict]:
    manifest = batch_dir(bid) / "manifest.jsonl"
    if not manifest.exists():
        return []
    out = []
    for line in manifest.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def batch_total(bid: str) -> int:
    return sum(f["size"] for f in batch_files(bid))


def batch_count(bid: str) -> int:
    return len(batch_files(bid))


def session_file_count(sid: str) -> int:
    """Total files this session has uploaded, across all of its batches.

    Counting a single batch would let the cap be reset just by sending a new
    ?batch= id, which makes MAX_FILES_PER_SESSION meaningless.
    """
    total = 0
    if not BATCHES.exists():
        return 0
    for d in BATCHES.iterdir():
        if not d.is_dir():
            continue
        try:
            if (d / "owner").read_text().strip() == sid:
                total += len(batch_files(d.name))
        except OSError:
            continue
    return total


# --------------------------------------------------------------------------
# media scan
# --------------------------------------------------------------------------


def scan_media(paths: list[str]) -> str:
    """Ask MediaProvider about these files. Returns the technique that stuck."""
    if not paths:
        return "none"
    try:
        proc = subprocess.run(
            ["bash", MEDIA_SCAN, *paths],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        log("media-scan timeout")
        return "timeout"
    except OSError as exc:
        log(f"media-scan failed: {exc}")
        return "unavailable"

    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    if detail:
        log("media-scan: " + " | ".join(detail[-6:]))
    return detail[-1].split(":")[0].removeprefix("scanned(") if detail else "unknown"


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------


@app.get("/")
def root():
    """Landing page.

    Deliberately accepts no token, in the path or the query string. An earlier
    version redirected on ?t=, which meant the token travelled through an
    access log on its way to becoming a path token. Useless convenience, real
    leak.
    """
    return PAGE_INDEX, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/healthz")
def healthz():
    """Liveness probe.

    start.sh polls this over loopback, but the same endpoint is reachable from
    the tunnel. Unauthenticated callers get a bare liveness answer — the
    filesystem path, exact free bytes and session counts are device
    fingerprinting and are only for someone who already holds a token.
    """
    drop = request.headers.get("X-PD-Token", "")
    owner = request.args.get("k", "") or request.args.get("owner", "")

    if check_token(drop, TOKEN) or (OWNER_OK and check_token(owner, OWNER_TOKEN)):
        free = disk_free()
        total = disk_total()
        return jsonify(
            ok=True,
            dest=str(DEST),
            free=free,
            dest_size=total,
            used=max(0, total - free),
            reserve=RESERVE_BYTES,
            sessions=len(batch_ids_recent()),
        )
    return jsonify(ok=True)


def batch_ids_recent() -> set[str]:
    if not BATCHES.exists():
        return set()
    cutoff = time.time() - SESSION_TTL
    return {p.name for p in BATCHES.iterdir() if p.is_dir() and p.stat().st_mtime > cutoff}


@app.get("/d/<token>/")
def drop_page(token: str):
    sid, is_new = require_drop_token()
    free = disk_free()
    if free - RESERVE_BYTES <= 0:
        return PAGE_FULL, 200, {"Content-Type": "text/html; charset=utf-8"}

    resp = make_response(
        PAGE_UPLOAD.format(
            base=f"/d/{TOKEN}",
            reserve=human(RESERVE_BYTES),
            max_mb=MAX_FILE_BYTES // (1024 * 1024),
            max_files=MAX_FILES_PER_SESSION,
        )
    )
    if is_new:
        set_session_cookie(resp, sid)
    return resp


@app.get("/d/<token>/status")
def drop_status(token: str):
    sid, _ = require_drop_token()
    bid = request.args.get("batch", "")
    free = disk_free()
    mine = bool(re.fullmatch(r"[a-f0-9]{6,32}", bid or "")) and batch_owned_by(bid, sid)
    return jsonify(
        free=free,
        free_human=human(free),
        usable=max(0, free - RESERVE_BYTES),
        uploaded=batch_count(bid) if mine else 0,
        reserve=RESERVE_BYTES,
        max_concurrent=MAX_CONCURRENT_UPLOADS,
    )


@app.post("/d/<token>/upload")
def upload(token: str):
    """Receive one file as the raw request body.

    The browser sends `xhr.send(file)` — no multipart envelope at all. That
    keeps the parser trivial, gives us Content-Length up front so we can reject
    a hopeless upload before a single byte lands, and preserves the native
    upload progress events the UI relies on.
    """
    sid, _ = require_drop_token()

    bid = request.args.get("batch") or uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[a-f0-9]{6,32}", bid):
        abort(400)
    if not batch_owned_by(bid, sid):
        abort(403)
    if session_file_count(sid) >= MAX_FILES_PER_SESSION:
        return jsonify(ok=False, error="session file limit reached"), 409
    claim_batch(bid, sid)

    original = request.args.get("name") or "photo"
    declared = request.content_length

    if declared is None:
        return jsonify(ok=False, error="missing content length"), 411
    if declared > MAX_FILE_BYTES:
        return jsonify(ok=False, error="file is larger than the per-file limit"), 413
    # Reject before reading anything — the common failure is a full phone, and
    # there is no reason to write 40 GB into it first.
    if not enough_space(declared):
        return jsonify(ok=False, error="phone storage is full"), 507
    if disk_free_home() - 5_000_000 < RESERVE_BYTES // 4:
        return jsonify(ok=False, error="phone storage is full"), 507

    # Everything above this line is cheap bookkeeping. Everything below writes
    # to disk and shells out, so that is what the concurrency bound protects.
    if not _UPLOAD_SLOTS.acquire(blocking=False):
        log(f"upload refused, {MAX_CONCURRENT_UPLOADS} uploads already in flight")
        busy = jsonify(ok=False, error="phone is busy with other uploads, try again")
        busy.headers["Retry-After"] = "5"
        return busy, 503

    try:
        dest_dir = DEST
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = unique_name(original, dest_dir)
        target = dest_dir / name
        tmp = dest_dir / f".{name}.part"

        written = 0
        try:
            with open(tmp, "wb") as out:
                while True:
                    chunk = request.stream.read(256 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_FILE_BYTES or not enough_space(written):
                        raise OSError("phone storage filled up mid-upload")
                    if written % (8 * 1024 * 1024) == 0 and disk_free_home() < RESERVE_BYTES // 4:
                        raise OSError("phone storage filled up mid-upload")
                    out.write(chunk)
            os.replace(tmp, target)
        except (OSError, ClientDisconnected) as exc:
            tmp.unlink(missing_ok=True)
            log(f"upload rejected ({original}): {exc}")
            return jsonify(ok=False, error=str(exc)), 507

        # Hand the file to MediaProvider so Google Photos sees it.
        scanned = scan_media([str(target)])
        entry = record_upload(bid, name, original, written, scanned)
        log(f"saved {original} -> {name} ({written}B, scan={scanned})")
    finally:
        # Released even when the write fails, so one bad upload cannot wedge
        # the server for the rest of the session.
        _UPLOAD_SLOTS.release()

    return jsonify(
        ok=True,
        batch=bid,
        scanned=scanned,
        free=disk_free(),
        files=[{"name": name, "size": written}],
    )


@app.get("/d/<token>/done/<batch>")
def done(token: str, batch: str):
    sid, is_new = require_drop_token()
    if not re.fullmatch(r"[a-f0-9]{6,32}", batch or ""):
        abort(400)
    if not batch_owned_by(batch, sid):
        abort(403)
    files = batch_files(batch)
    if not files:
        return redirect(f"/d/{TOKEN}/")

    unscanned = [f for f in files if f["scanned"] in {"scan-failed", "unavailable", "timeout", "none"}]
    rows = "\n".join(
        # `original` is the uploader's raw filename. It is NOT sanitised by
        # unique_name() — that only produces the on-disk name — so it must be
        # escaped here or it is a live XSS vector on this page.
        f'<li><span class="n">{escape(f["original"])}</span>'
        f'<span class="s">{human(f["size"])}</span></li>'
        for f in files
    )
    resp = make_response(PAGE_DONE.format(
        count=len(files),
        noun="file" if len(files) == 1 else "files",
        verb="is" if len(files) == 1 else "are",
        total=human(batch_total(batch)),
        rows=rows,
        thumbs=THUMBS.format(
            items="".join(
                f'<img loading="lazy" src="/d/{TOKEN}/file/{f["name"]}">'
                for f in files
                if f["name"].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"))
            )
        ),
        warning=(
            f"<p class=warn>{len(unscanned)} file(s) could not be handed to the phone's "
            "media library automatically. They are safely on the phone; open the Gallery "
            "app once and they will appear.</p>"
            if unscanned
            else ""
        ),
    ))
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    if is_new:
        set_session_cookie(resp, sid)
    return resp


@app.get("/d/<token>/file/<name>")
def serve_file(token: str, name: str):
    _, _ = require_drop_token()
    if "/" in name or name in {"", ".", ".."}:
        abort(404)
    path = DEST / name
    if not path.is_file():
        abort(404)
    resp = send_file(path, conditional=True)
    resp.headers["Cache-Control"] = "private, max-age=86400"
    return resp


@app.get("/owner")
@app.get("/owner/<token>")
def owner_dashboard(token: str = ""):
    """Owner dashboard.

    Prefers the path form /owner/<token>. A query string (?k=...) ends up in
    access logs and Referer headers, so start.sh prints the path form and this
    keeps working as a fallback for a bookmarked URL.
    """
    supplied = token or request.args.get("k", "")
    if not OWNER_OK or not check_token(supplied, OWNER_TOKEN):
        abort(404)

    free = disk_free()
    recent = []
    if BATCHES.exists():
        for d in sorted(BATCHES.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if time.time() - d.stat().st_mtime > SESSION_TTL:
                continue
            files = batch_files(d.name)
            recent.append(
                f"<tr><td>{d.name}</td><td>{len(files)}</td>"
                f"<td>{human(batch_total(d.name))}</td>"
                f"<td>{datetime.fromtimestamp(d.stat().st_mtime).strftime('%H:%M:%S')}</td></tr>"
            )

    selftest = subprocess.run(
        ["bash", MEDIA_SCAN, "--selftest"], capture_output=True, text=True
    ).stdout.strip()

    return f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Photo Drop — owner</title>
<style>
 body{{background:#0b0b0d;color:#e8e8ea;font:15px/1.5 -apple-system,system-ui,sans-serif;padding:20px;max-width:720px;margin:auto}}
 h1{{font-size:20px}} code{{background:#1a1a1e;padding:2px 6px;border-radius:4px;font-size:13px}}
 .box{{background:#151519;border:1px solid #26262c;border-radius:12px;padding:16px;margin:14px 0}}
 a{{color:#7cc4ff}} table{{width:100%;border-collapse:collapse;font-size:14px}}
 td{{padding:6px 8px;border-bottom:1px solid #26262c;text-align:left}}
 .bar{{height:8px;background:#26262c;border-radius:99px;overflow:hidden;margin-top:8px}}
 .fill{{background:{'#4ade80' if free-RESERVE_BYTES>RESERVE_BYTES else '#f87171'};height:100%}}
</style>
<h1>Photo Drop — owner</h1>
<div class=box>
  <b>Drop link</b><br><code>{request.host_url.rstrip('/')}/d/{TOKEN}</code><br>
  <span style="color:#888;font-size:13px">Send this to your friend. It is the credential — anyone with it can upload.</span>
</div>
<div class=box>
  <b>Destination</b> <code>{DEST}</code><br>
  <b>Free</b> {human(free)} · <b>reserve</b> {human(RESERVE_BYTES)}
  <div class=bar><div class=fill style="width:{min(100, free/disk_free()*100 if disk_free() else 0):.0f}%"></div></div>
</div>
<div class=box><b>Media scan capabilities</b><pre style="font-size:13px;color:#aaa">{selftest}</pre></div>
<div class=box><b>Recent uploads</b>
<table><tr><td>batch</td><td>files</td><td>size</td><td>at</td></tr>{''.join(recent) or '<tr><td colspan=4>none yet</td></tr>'}</table>
</div>"""


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

PAGE_INDEX = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Photo Drop</title><style>
body{background:#0b0b0d;color:#e8e8ea;font:16px/1.6 -apple-system,system-ui,sans-serif;
display:grid;place-items:center;min-height:100vh;margin:0;padding:24px;text-align:center}
h1{font-size:22px;font-weight:600} p{color:#8a8a92;max-width:34ch}</style>
<h1>Photo Drop</h1><p>Open the link your friend sent you to send photos.</p>"""

PAGE_FULL = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Photo Drop</title><style>
body{background:#0b0b0d;color:#e8e8ea;font:16px/1.6 -apple-system,system-ui,sans-serif;
display:grid;place-items:center;min-height:100vh;margin:0;padding:24px;text-align:center}
h1{font-size:20px}p{color:#8a8a92;max-width:36ch}</style>
<h1>Phone storage is full</h1>
<p>The phone has run out of room, so uploads are paused. Nothing was lost. Try again shortly.</p>"""

THUMBS = '<div class=grid>{items}</div>'

PAGE_UPLOAD = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Send photos</title>
<style>
 :root{{--bg:#0b0b0d;--card:#151519;--line:#26262c;--fg:#e8e8ea;--dim:#8a8a92;--ok:#4ade80}}
 *{{box-sizing:border-box}}
 body{{background:var(--bg);color:var(--fg);margin:0;padding:20px 16px 90px;
   font:16px/1.5 -apple-system,system-ui,sans-serif}}
 h1{{font-size:19px;margin:0 0 4px}} .sub{{color:var(--dim);font-size:13px;margin:0 0 20px}}
 .space{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:16px}}
 .space b{{font-size:14px}} .bar{{height:6px;background:var(--line);border-radius:99px;overflow:hidden;margin-top:8px}}
 .fill{{background:var(--ok);height:100%;width:100%}}
 .drop{{border:1.5px dashed var(--line);border-radius:16px;padding:34px 18px;text-align:center;cursor:pointer}}
 .drop:active{{background:var(--card)}}
 .drop svg{{opacity:.4}} .drop p{{margin:10px 0 0;color:var(--dim);font-size:14px}}
 .items{{margin-top:18px;display:flex;flex-direction:column;gap:8px}}
 .item{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px}}
 .item .nm{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
 .item .track{{height:4px;background:var(--line);border-radius:99px;overflow:hidden;margin-top:7px}}
 .item .fill{{width:0;transition:width .12s linear}}
 .item.done .fill{{background:var(--ok)}} .item.err{{border-color:#7f1d1d}}
 .st{{float:right;color:var(--dim);font-variant-numeric:tabular-nums}}
 .go{{position:fixed;left:0;right:0;bottom:0;padding:14px;background:rgba(11,11,13,.92);
   backdrop-filter:blur(10px);border-top:1px solid var(--line)}}
 button{{width:100%;padding:15px;border:0;border-radius:12px;background:var(--fg);color:#0b0b0d;
   font:600 16px/1 -apple-system,system-ui,sans-serif}}
 button:disabled{{opacity:.35}}
 .quiet{{text-align:center;color:var(--dim);font-size:12px;margin-top:14px}}
</style>
<h1>Send photos</h1>
<p class=sub>They go straight to the phone and get backed up. Nothing is stored anywhere else.</p>

<div class=space><b>Phone has <span id=free>--</span> free</b>
  <div class=bar><div class=fill id=spacebar></div></div>
  <div style="color:var(--dim);font-size:11px;margin-top:6px">
    Uploads pause at {reserve} free to keep the phone healthy. Up to {max_mb} MB per file.</div></div>

<div class=drop id=drop>
 <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#e8e8ea" stroke-width="1.6">
  <path d="M12 16V4m0 0L8 8m4-4 4 4"/><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>
 <p><b>Tap to choose photos and videos</b><br>You can pick as many as you like</p>
 <input type=file id=pick multiple accept="image/*,video/*" hidden>
</div>

<div class=items id=items></div>

<div class=go><button id=go disabled>Send</button></div>
<p class=quiet id=status></p>

<script>
const BATCH = Math.random().toString(16).slice(2,14);
const BASE = "{base}";
let queue = [], free = 0;

async function poll(){{
  try{{
    const r = await fetch(BASE + "/status?batch=" + BATCH, {{credentials:"same-origin"}});
    const d = await r.json();
    free = d.usable;
    document.getElementById("free").textContent = d.free_human;
    // Reserve comes from the server so the bar stays honest if it is retuned.
    const pct = d.reserve ? (d.usable / (d.usable + d.reserve)) * 100 : 100;
    document.getElementById("spacebar").style.width =
      Math.max(2, Math.min(100, pct)) + "%";
  }}catch(e){{}}
}}
poll(); setInterval(poll, 5000);

const drop = document.getElementById("drop"), pick = document.getElementById("pick");
drop.onclick = () => pick.click();
pick.onchange = () => {{ add([...pick.files]); pick.value = ""; }};
drop.ondragover = e => e.preventDefault();
drop.ondrop = e => {{ e.preventDefault(); add([...e.dataTransfer.files]); }};

function add(files){{
  for (const f of files) queue.push({{file:f, el:null, done:false, err:false}});
  render();
}}

function render(){{
  const box = document.getElementById("items"); box.innerHTML = "";
  queue.forEach((it, i) => {{
    const d = document.createElement("div");
    d.className = "item" + (it.done?" done":"") + (it.err?" err":"");
    d.innerHTML = '<span class=st></span><div class=nm"></div><div class=track"><div class=fill"></div></div>';
    d.querySelector(".nm").textContent = it.file.name;
    it.el = d;
    box.appendChild(d);
  }});
  const left = queue.filter(i=>!i.done&&!i.err).length;
  document.getElementById("go").disabled = left === 0;
  document.getElementById("go").textContent = left ? `Send ${{left}} file${{left>1?"s":""}}` : "Send";
}}

document.getElementById("go").onclick = async () => {{
  const btn = document.getElementById("go"); btn.disabled = true;
  const pending = queue.filter(i=>!i.done&&!i.err);
  for (const it of pending) {{
    if (free <= 0) {{ setStatus("Phone storage is full. Upload paused."); render(); return; }}
    try {{
      const url = BASE + "/upload?batch=" + BATCH + "&name=" + encodeURIComponent(it.file.name);
      const xhr = new XMLHttpRequest();
      const p = xhr.upload;
      p.onprogress = e => {{
        if (!e.lengthComputable) return;
        const pct = e.loaded / e.total * 100;
        it.el.querySelector(".fill").style.width = pct + "%";
        it.el.querySelector(".st").textContent = Math.round(pct) + "%";
      }};
      await new Promise((res, rej) => {{
        p.onerror = () => rej(new Error("network dropped"));
        xhr.onload = () => {{
          if (xhr.status >= 200 && xhr.status < 300) res();
          else {{
            let m = "upload failed";
            try {{ m = JSON.parse(xhr.responseText || "{{}}").error || m; }} catch (_) {{}}
            rej(new Error(m));
          }}
        }};
        xhr.open("POST", url);
        // Raw body, not multipart — this is what makes progress exact and
        // lets the server know the size before it writes anything.
        xhr.send(it.file);
      }});
      it.done = true;
      it.el.querySelector(".st").textContent = "safe";
      it.el.querySelector(".fill").style.width = "100%";
      setStatus("Saved: " + it.file.name);
    }} catch (err) {{
      it.err = true;
      it.el.querySelector(".st").textContent = "failed";
      setStatus(String(err.message || err));
    }}
    poll(); render();
  }}
  if (queue.some(i=>i.done)) location.href = BASE + "/done/" + BATCH;
}};

function setStatus(s){{ document.getElementById("status").textContent = s; }}
</script>"""

PAGE_DONE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Photos received</title>
<style>
 body{{background:#0b0b0d;color:#e8e8ea;margin:0;padding:28px 18px 60px;
  font:16px/1.6 -apple-system,system-ui,sans-serif}}
 .tick{{width:56px;height:56px;border-radius:50%;background:#4ade80;color:#0b0b0d;
  display:grid;place-items:center;font-size:30px;margin:0 auto 18px}}
 h1{{font-size:21px;text-align:center;margin:0 0 6px}}
 .sub{{text-align:center;color:#8a8a92;margin:0 0 26px;font-size:15px}}
 .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:26px;border-radius:12px;overflow:hidden}}
 .grid img{{width:100%;aspect-ratio:1;object-fit:cover;background:#151519;display:block}}
 ul{{list-style:none;padding:0;margin:0}} li{{display:flex;justify-content:space-between;gap:12px;
  padding:11px 2px;border-bottom:1px solid #26262c;font-size:14px}}
 li .n{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} li .s{{color:#8a8a92;flex:none;font-size:13px}}
 .warn{{background:#3a2a10;border:1px solid #7c5a1a;color:#f0d9a8;padding:12px;border-radius:10px;
  font-size:13px;margin-top:20px}}
 h2{{font-size:13px;color:#8a8a92;text-transform:uppercase;letter-spacing:.06em;margin:26px 0 10px}}
</style>
<div class=tick>&#10003;</div>
<h1>Your {count} {noun} {verb} safe</h1>
<p class=sub>{total} landed on the phone and is now being backed up to Google Photos.
You can close this page.</p>
{thumbs}
<h2>Received</h2><ul>{rows}</ul>
{warning}"""


# --------------------------------------------------------------------------
# boot
# --------------------------------------------------------------------------


def main():
    BATCHES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    # A run killed mid-upload leaves .part files behind. They are invisible to
    # the gallery but they eat storage, so clear them out on boot.
    if DEST.exists():
        stale = [p for p in DEST.glob(".*.part") if p.is_file()]
        for p in stale:
            p.unlink(missing_ok=True)
        if stale:
            log(f"cleared {len(stale)} stale partial upload(s)")

    if not DEST.exists():
        print(f"\n  Destination {DEST} does not exist.")
        print("  Run:  termux-setup-storage   and pick the phone storage.\n")
        raise SystemExit(1)

    print(f"  photo-drop  ->  http://{HOST}:{PORT}/d/{TOKEN}")
    print(f"  destination ->  {DEST}")
    print(f"  free        ->  {human(disk_free())} (reserve {human(RESERVE_BYTES)})")
    app.run(host=HOST, port=PORT, threaded=True, debug=False)


if __name__ == "__main__":
    main()