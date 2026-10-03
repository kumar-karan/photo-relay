# iPhone 17 Pro → Samsung → Google Photos (Unlimited Backup) Plan

**Goal:** Keep using the old Samsung's *modded Google Photos* (unlimited, original quality) as free
cloud backup, even though photos are now taken on the **iPhone 17 Pro**.

**Core idea:** The unlimited backup only works *from the Samsung* (the mod spoofs a Pixel).
So the whole job is: **get new iPhone photos onto the Samsung → let the Samsung back them up.**

---

## Recurring monthly routine (phone-to-phone, no PC)

1. **Transfer this month's photos** iPhone → Samsung using **LocalSend**
   (both phones on same WiFi, sends **original HEIC**, no recompression).
2. **Confirm** they appear in Google Photos as "backing up" on the Samsung.
3. Done. (Optional: once backup is confirmed, delete them off the Samsung to save space —
   they stay safe in Google Photos.)

⏱️ Selecting a month of photos on the iPhone takes ~10s (Photos groups by date).

---

## One-time setup

### A. Initial bulk move (everything already on the iPhone)
- Use **Samsung Smart Switch** *once*: iOS → Samsung over cable/WiFi.
- Preserves originals, drops straight into Gallery/DCIM → auto-backed-up. ✅

### B. Make LocalSend photos actually back up ⚠️ (the make-or-break step)
LocalSend saves to a `LocalSend`/`Downloads` folder by default, and Google Photos does **not**
back up arbitrary folders. Fix once:
- Google Photos (Samsung) → **Library → tap the folder → toggle "Back up"**, **or**
- Set LocalSend's save location to **`DCIM`**.

### C. iPhone camera format (keep it efficient)
- **Settings → Camera → Formats → High Efficiency (HEIC).**
  Google Photos accepts HEIC fine, files are ~half the size, quality identical. Keep this.
- **Settings → Apps → Photos → Transfer to Mac or PC → Keep Originals**
  (only matters if you ever route through the Mac — prevents auto HEIC→JPEG conversion).

---

## Alternative: Mac-as-hub (fully scriptable, for later)

If you ever want a **one-command** monthly run instead of tapping through apps:

```
iPhone → Mac (USB, read DCIM) → Samsung (adb push → /sdcard/DCIM) → media scan → mod backs up
```

- Samsung side (`adb push` + media scan) is rock-solid and scriptable.
- iPhone side needs `libimobiledevice` + `ifuse` (via macFUSE — a bit fiddly on Apple Silicon),
  or just drag from **Image Capture** manually.
- Big win: a state file remembers what's already sent → true "only new photos" each month.

**Status:** parked. Phone-to-phone (LocalSend) is the current chosen approach.

---

## Tools

| Tool | Role | Notes |
|------|------|-------|
| **LocalSend** | Monthly iPhone→Samsung | Free, open-source, original quality, same-WiFi |
| **Smart Switch** | One-time bulk migration | Official Samsung app |
| **Send Anywhere** | Backup option | Works off-WiFi via 6-digit code |
| Modded Google Photos | Unlimited cloud backup | Lives on Samsung only |

---

## Bonus: iOS Shortcut to speed up the monthly grab

You can build a **Shortcut** ("Find Photos" → last 30 days → **Share** → LocalSend) so the
whole monthly transfer is one tap. See `iphone-hacks.md` for how to set it up.

# photo-relay
