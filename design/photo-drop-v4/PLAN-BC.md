# Photo Drop — combined B+C implementation plan

`apps/photo-drop/android` · `dev.photodrop.app` · the "Handoff" direction.
Supersedes the *direction* in `PLAN.md`; **reuses its §3 tokens, §5 motion family, §7
wire format, §8 first-run, §9 accessibility verbatim.** Only the deltas are specified here.

---

## 1. The concept, in one paragraph

**One screen, two jobs at two moments: flip the switch, then become the card you hand over.**

Every other control lives inside those two. From **B** we take the *spine*: a thin status
band that answers "is it on?" without scrolling, a share/QR card that is the hero, and a QR
that is **permanently at arm's-length size** instead of hidden behind a toggle. From **C** we
take the *switch*: a single large orb is the primary control, the state change is **felt**
(a large colour field, not a pill), and the link arrives in a **panel that rises from the
bottom** once there is something worth showing. The two flaws the originals carried are
fixed here rather than inherited — see §4, which is the part of this plan that decides the
whole thing.

---

## 2. Layout anatomy

Four zones, top to bottom, in a single `LinearLayout` root. **No `ScrollView`** — the whole
point of B is that the card is the screen and nothing has to be scrolled to be seen. The band
and the panel are pinned; only the stage flexes.

```
┌──────────────────────────────────────────┐
│ [•] Online anywhere              [LIVE]  │  band   — pinned, 64dp min
│     Tunnel up · 3 sessions today         │
├──────────────────────────────────────────┤
│                                          │
│            ┌──────────────┐              │
│            │   ▓▓▒░ QR  ░▒▓│             │  stage  — flex:1, min 300dp
│            │   ▓▒░ (184dp)│              │           orb when off,
│            └──────────────┘              │           Handoff card when live
│         Hold this up to your friend      │
│                                          │
├──────────────────────────────────────────┤
│              ────────                    │  sheet  — pinned, rounded top
│  38.4 GB free   ▓▓▓▓▓▓░░░░░  ·  Copy     │           peek 72dp → 208dp
│  …/d/A7xKp2mQ…                    ⇅      │
│  Stop server                             │
└──────────────────────────────────────────┘
```

| Zone | id | Height | Pinned? | Role |
| --- | --- | --- | --- | --- |
| **Band** | `statusStrip` | 64dp min, `wrap` | yes | State dot + title + sub-line + state pill. Carries the state colour. |
| **Stage** | `stage` | `0dp`, `weight=1`, min 300dp | flexes | The switch when off; the Handoff card when live. |
| **Sheet** | `sheet` | peek 72dp → 208dp | yes | Storage always; URL + Copy + Stop once live. |
| **Nav** | `navRow` | 48dp | inside sheet | One "Owner dashboard" row (drop the duplicate — see §9). |

**The QR is the largest object on the screen and it is white.** That constraint drives §3.

---

## 3. State → screen matrix

Six semantic states, from the same source as `PLAN.md` §4, now mapped across three zones.
The colour decision that matters: **green fills the band and the page, never the space
behind the QR.** The Handoff card stays `#FFFFFF` so the QR keeps black-on-white contrast and
survives daylight. "The screen goes green" is delivered by the field *around* the card.

| State | Band | Stage | Sheet | Orb |
| --- | --- | --- | --- | --- |
| **Stopped** | `neutral_bg` · grey dot · "Server is offline" / "Nothing can upload right now" · pill `STOPPED` | **Orb**, neutral fill, "Tap to start" | peek · storage only | switch, primary |
| **Starting** | `warning_bg` · amber dot pulsing · "Starting" / "Bringing up Termux and the tunnel" · pill `WAIT` | Orb, amber fill, "Starting", caption "About four seconds" | peek · storage | switch, disabled |
| **Online, local only** | `#EAF5EC` tint · green dot · "On this Wi-Fi" / "Works here only" · pill `ON THIS WI-FI` | **Handoff card**: domain, mono URL, 184dp QR, "Hold this up to your friend" | full · URL + Copy + sessions + storage | docks to *Live badge*, tint green |
| **Online, via tunnel** | **solid `primary`** · mint dot `#7BE3A6` pulsing · "Online anywhere" / "Works for anyone with the link" · pill `LIVE` | Handoff card (as above) | full · URL + Copy + sessions + storage + **Stop server** | docks to white *Live badge* |
| **Storage low** | `danger_bg` · red dot · "Storage low" / "Uploads are paused at 1.6 GB free" | Card replaced by an **alert card**: "Free some space first" + a red storage readout | full · red storage | badge, hidden |
| **Termux unreachable** | **`#212529` inverted** · `#FF8A80` dot · "Can't reach Termux" / "Grant permission to run commands" | **Permission card** replaces orb & card | peek · storage | hidden |

On transition, cross-fade the band background and text with an `ArgbEvaluator` over 200ms
(`PLAN.md` §5). The band is the thing that changes colour on every poll, so it must never
hard-cut.

---

## 4. Killing the two flaws — this is the deciding section

### 4.1 Stop is labelled and reachable, never an overflow

B buried Stop in an overflow, and the plan rejected that. Here **Stop server is a labelled
button inside the sheet**, in the bottom third of the screen where a thumb already is. It is
always present when live — not in a menu, not a long-press, not an icon a user has to decode.
It is the same action the foreground notification already exposes, so the app and the shade
agree.

### 4.2 A pocket tap cannot kill an upload

C's orb-as-switch means the *biggest* target on the phone is the destructive one, which is why
C needed a hold-to-stop — and a hold gesture is exactly what users never discover.

**This design splits the two meanings of "the orb":**

- **When live, tapping the orb copies the link.** Copying is idempotent and harmless. A stray
  pocket tap on a 200dp target does the safe thing and tells you so.
- **Stopping is a deliberate, labelled, small-target tap** in the sheet (§4.1), not the orb.

**And it confirms when it matters:**

```java
void onStopTapped() {
    if (last.sessions > 0) {
        showStopConfirm();   // inline strip, replaces nothing
    } else {
        stopServer();
    }
}
```

The confirm is an inline strip inside the sheet — *"A friend may be uploading right now."*
with `[ Stop anyway ]` `[ Keep running ]` — **not** an `AlertDialog` and **not** a `Snackbar`
(a transient that the user will miss because they already put the phone down). `/healthz`
reports `sessions` as a count of recently-touched batches, so it is the honest signal for
"something is likely in flight"; when it is zero there is nothing to protect and the tap is
immediate.

Net effect: the destructive action is **discoverable** (unlike C's long-press) and
**guarded** (unlike a bare tap). That is the combination neither original had.

---

## 5. Component inventory

Lean. No AndroidX, so `BottomSheetBehavior`, `ViewDragHelper` and `SpringAnimation` are all
unavailable and none is used.

| File | New? | Why it is a `View` and not a `LinearLayout` |
| --- | --- | --- |
| `Health.java` | new | Value class from `PLAN.md` §7. Kills the `-1` sentinels in `render()`. |
| `StatusStripView.java` | new | Owns the state dot and the **shimmer loop**, which must cancel on state change and on background. `View.animate()` cannot hold that. |
| `OrbView.java` | new | Draws circle + halo + dot and owns the pulse loop, the press morph, and its **two modes** (switch / docked Live badge). |
| `StorageBarView.java` | **reuse as-is** | Already correct. |
| Sheet | **layout only** | A `LinearLayout` with a rounded-top background, animated height. No custom view. |
| Nav row | **layout only** | Keep the existing `btn_text_only` row. `WorkLogRow` is optional polish, deferred. |

### The sheet is content-driven, not draggable

**v1: no drag.** The sheet has exactly two heights, and which one applies is a function of
state, not of user intent:

- **peek (72dp):** handle + storage row. Shown when stopped/starting/error.
- **full (208dp):** handle + URL row + `Copy` + `⇅` flip + sessions row + `Stop server`.
  Shown when live.

Transition between them with an `ObjectAnimator` on the sheet's height plus a translationY on
the content, ~220ms, standard easing. This keeps C's "it rises from the bottom when there is
something to show" and drops the entire drag-gesture problem — the single biggest cost in C.
A drag handle is listed as an explicit **v2**, not a v1 requirement.

### The orb morphs, it does not disappear

`OrbView` has two modes:

- `MODE_SWITCH` — 200dp circle, centered in the stage. Stopped / starting / error.
- `MODE_BADGE` — 40dp pill, docked to the top of the Handoff card, reading "Live".

The transition is a **single `ViewPropertyAnimator` pass**: scale `1 → 0.2`, translationY to the
docked position, alpha on the mode-specific children, 260ms standard easing. No layout swap,
no second view. This is what makes the state change *felt*: the switch visibly becomes the
thing you hand over.

---

## 6. State wiring in `MainActivity`

`render(String)` becomes `render(Health)`. `pill(String,int,int)` becomes
`applyState(AppState)`. The six flags collapse to one enum.

```java
enum AppState { STOPPED, STARTING, ONLINE_LOCAL, ONLINE_TUNNEL, STORAGE_LOW, TERMUX_ERROR }

/** Single tap dispatcher. Replaces the btnStart / btnStop / btnQrToggle listeners. */
void onOrbTapped() {
    switch (state) {
        case STOPPED:                 startServer(); break;
        case STARTING:                break;                 // inert, not a dead button
        case ONLINE_LOCAL:
        case ONLINE_TUNNEL:
        case STORAGE_LOW:             copyLink(); break;     // safe for pocket taps
        case TERMUX_ERROR:            openPermissionCard(); break;
    }
}

AppState classify(Health h, boolean permitted) {
    if (!permitted)                       return AppState.TERMUX_ERROR;
    if (!h.up)      return starting ? AppState.STARTING : AppState.STOPPED;
    starting = false;
    if (h.known() && h.reserve > 0 && h.free <= h.reserve) return AppState.STORAGE_LOW;
    return publicUrl.isEmpty() ? AppState.ONLINE_LOCAL : AppState.ONLINE_TUNNEL;
}

void render(Health h) {
    AppState next = classify(h, Termux.permitted(this));
    if (next == state && !somethingChanged(h)) return;   // no redraw on a no-op poll
    state = next;
    applyState(next);          // band colour/text, orb mode, sheet height, QR
    last = h;
}
```

| Remove | Replace with |
| --- | --- |
| `pill(String,int,int)` | `applyState(AppState)` |
| `render(String)` | `render(Health)` |
| `pick`, `parseLong` fields | moved into `Health` |
| `starting`, `up`, `stop` flags | `enum AppState state` |
| `btnStart`/`btnStop` listeners | `onOrbTapped()` + `btnStop` in the sheet |
| `toggleQr()` | gone — the QR is always in the card when live |
| `qrVisible`, `qrForUrl` | `qrForUrl` stays as a cache key only; no visibility state |

**Keep unchanged:** `mintToken`, `loadTokens`, `bootstrap`, the 7s poll in `onResume`/`onPause`,
`pressFeedback` (extend it to drive corner radius), `domainOf`, `copy`, `human`, `httpGet`,
`readPublicUrl`, `sendCmd`, and the `PhotoDropService` sync in `render()` (start when up, stop
when down — the notification must keep tracking reality).

---

## 7. Motion deltas (only what §5 of `PLAN.md` does not already cover)

| Trigger | Property | From → To | ms |
| --- | --- | --- | --- |
| Orb → badge (enter live) | `OrbView` scale/translationY | `1 → 0.2`, to dock | 260 |
| Badge → orb (leave live) | reverse | dock → centered | 240 |
| Sheet peek → full | sheet `height` + content `translationY` | 72dp → 208dp | 220 |
| Sheet full → peek | reverse | — | 180 |
| QR arrives | `imgQr` alpha/scale | `0→1`, `.94→1` | 220 |
| Stop confirm strip in | `translationY`, alpha | `12dp→0`, `0→1` | 160 |

Everything else — state colour cross-fade, press morph, running shimmer, storage bar — is
`PLAN.md` §5 and is unchanged.

---

## 8. Ordered, independently-buildable change plan

Each step builds and runs on its own.

1. **`Health.java`** — add the value class. Build. Nothing consumes it yet.
2. **`MainActivity.java`** — swap `render(String)` for `render(Health)` and introduce
   `enum AppState` + `classify()`. Keep the *old* layout; drive the existing `tvStatus` pill
   from `applyState(AppState)`. Build, deploy, confirm no behaviour regression.
3. **`StatusStripView.java` + `res/layout/activity_main.xml`** — replace the header row with
   the band; collapse the `ScrollView` to the pinned four-zone `LinearLayout`. Stage still holds
   the old link card; sheet is a stub. Build, deploy, walk the six states.
4. **`OrbView.java`** — implement both modes and the morph. Wire `onOrbTapped()`. Remove
   `btnStart`/`btnStop`. Build, deploy, confirm start-from-orb and copy-when-live.
5. **Handoff card in the stage** — domain + mono URL + permanent QR + flip. Delete
   `btnQrToggle`/`qrBox`. Build, deploy, **scan the QR with a real phone at arm's length.**
6. **Sheet content** — storage row (reuse `StorageBarView`), URL row + `Copy`, sessions row,
   `Stop server`, inline confirm strip. Build, deploy, confirm the session guard.
7. **First-run checklist + permission card** (`PLAN.md` §8) inside the stage. Build, deploy.
8. **Accessibility & contrast sweep** (`PLAN.md` §9) over the built layout.
9. **Cleanup** — delete `btnUpload`/`btnScan`/`tvScan` dead wiring; drop the unreferenced
   `surface_press`, `row_press`, `track_bg` colours.

---

## 9. Things this plan deliberately deletes

- **`btnScan`.** It points at the identical URL as `btnOwner` (`base() + "/owner/" + token`).
  One "Owner dashboard" row. The media-scan report needs its own route before it earns its own row.
- **`tvUploads`'s hardcoded literal.** Replace with the real `sessions` count from `Health`.
- **The QR toggle.** The QR is permanent when live; that was B's whole argument.
- **`ScrollView`.** Nothing should need scrolling to be seen.

---

## 10. Verification

```bash
bash apps/photo-drop/android/build.sh      # must print BUILD_OK
bash apps/photo-drop/deploy.sh             # adb install + push to the Samsung
```

Then, in order:

1. **Cold start, server stopped** — band grey "Server is offline", the orb is the only big
   object, sheet is a bare storage peek. Nothing is a greyed-out box.
2. **Tap the orb** — band goes amber, orb goes amber "Starting", sheet unchanged. **No Toast.**
3. **`/healthz` answers** — band turns solid green, the orb **shrinks and docks** to the Live
   badge, the Handoff card fades in with the QR. Sheet grows to full.
4. **Stand back and scan** — a second phone scans the QR from ~40cm, in daylight. It must open
   the upload page. This is the test B exists for; do it on real hardware, not a screenshot.
5. **Pocket-tap safety** — with the phone live, tap the orb repeatedly. It copies. The server
   does **not** stop. `sessions` on the sheet ticks up as a friend uploads.
6. **Stop** — tap `Stop server` in the sheet while `sessions > 0`: the confirm strip appears,
   not a dialog. `Keep running` dismisses it; `Stop anyway` stops. With `sessions == 0` the
   first tap stops immediately.
7. **Storage low** — fill below the reserve: band red, card replaced by the alert card, no QR.
8. **Revoke the Termux permission** — the permission card replaces the orb and persists. It
   does not dump you into App Info.
9. **Reduced motion** — `adb shell settings put global animator_duration_scale 0`, then confirm
   the shimmer is **stopped**, not spinning (`PLAN.md` §9), and the orb/sheet changes are
   instant rather than animated. Reset to `1`.
10. **Contrast sweep** over the built layout: body text ≥ 4.5:1, the QR stays black-on-white.

---

## 11. Risks, and what to cut first

This is **more work than direction A**, and the plan should say so plainly. The orb morph and
the sheet both need real animation code, and step 4 of verification depends on hardware.

Cut in this order if it runs long:

1. **Sheet transition** → show/hide instead of animating the height. Keeps the two contents.
2. **Orb morph** → swap `VISIBLE`/`GONE` between the orb and the badge (no scale pass). Loses
   the "felt" state change, keeps the layout.
3. **Pull the sheet's `Stop server` up next to the card** as a labelled button and drop the
   sheet entirely — this degrades toward B with a permanent QR, which is still a good app.

**Do not cut** the §4.2 guard. A big tap target that kills an in-flight upload is worse than
any visual compromise here, and it is the reason the combination exists.

---

## 12. Open questions

1. **Orb size and colour in the live state** — dock it as a small green pill in the card header,
   or fade it out entirely and let the band's `LIVE` pill carry it? The mock docks it.
2. **Does `sessions > 0` justify a confirm?** It is a proxy for "an upload is in flight", not a
   guarantee. Alternative: only confirm below the reserve, and stop immediately otherwise.
3. **Drag-to-expand the sheet** — worth a v2, or is the content-driven two-position sheet
   enough forever?
4. **The `⇅` flip** — is a URL-large/QR-large flip wanted, or is the QR always large with the
   URL as the second line (as drawn)?
