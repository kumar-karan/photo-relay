# Photo Drop — UI/UX overhaul plan

`apps/photo-drop/android` · `dev.photodrop.app` · single `Activity`, no AndroidX, no Compose,
offline `aapt2` + `javac` + `d8` build, minSdk 26 / targetSdk 34, light theme only.

---

## 0. What this app actually is

Read the code before reading the plan, because almost every UI decision follows from one fact:
**this app is not the product.** The product is a Flask server running inside Termux on the owner's
Samsung. The app is a remote control for it.

Everything it does:

| Concern | Mechanism |
| --- | --- |
| Start / stop the server | `RUN_COMMAND` intent → `pd-control.sh start\|stop` |
| Push the two access tokens | `pd-control.sh bootstrap <drop> <owner>` on every `onResume` |
| Read status | `GET http://127.0.0.1:8080/healthz` with an `X-PD-Token` header, every 7s |
| Learn the public URL | read `public-url.txt` off shared storage, written by the server |
| Hand over the link | clipboard, or a ZXing-generated QR |

The owner's entire job is four actions, usually in about five seconds, one-handed:

1. **Start it.**
2. **Get the link.**
3. **Send it to one person.**
4. **Know there is room on the phone.**

That is the design target. Everything below is judged against it. The current design is a competent
settings form that loses on exactly this axis.

---

## 1. Diagnosis

Grounded in `MainActivity.java` and `activity_main.xml`.

1. **Nothing has presence.** The answer to "is it on?" lives in a header strip at the very top of a
   610-line `ScrollView`. On a 6.1" phone it is above the fold, but only just, and the scroll means
   every interaction drops the status off-screen.

2. **Two buttons, one alive.** `btnStart` is `setEnabled(false)` while running; `btnStop` is
   `setAlpha(0.45f)` while stopped. Both are always on screen. Half the primary surface is inert at
   any moment.

3. **Polling that shows nothing.** `refresh()` runs every 7s and calls `render()`, which assigns
   strings. There is no transition, no "updated 3s ago", no visible liveness. Tapping Start produces
   a Toast, then a hard jump from `STARTING` to `ONLINE` with no intermediate state.

4. **The good news is missing — the worst finding.** `tvUploads.setText("No uploads in this session
   yet")` is a **hardcoded literal**. It says that forever. Meanwhile the server *does* return
   `sessions` in `/healthz`. The single most reassuring fact for this app — *my friend's photos are
   actually landing* — is available and unused.

5. **The hero fights itself.** `cardLink` holds an overline, a domain, a monospace URL, a hint, a
   48dp button, a text toggle and a collapsible QR box, all in one 16dp box. Seven competing
   elements, one focal point.

6. **Inert exactly when it matters.** When stopped — which is every first open — the hero reads
   "Server not started" / `--`, and both copy and QR are disabled. The app's main surface is a greyed
   box on first launch. No onboarding, no explanation of the two one-time chores.

7. **Toast-only feedback.** Every single action is a `Toast`. Toasts cannot stack, cannot hold
   state, and vanish in two seconds. Copy confirmation is the one exception, and only on the button —
   tapping the hero card copies with *zero* feedback.

8. **The QR is the wrong shape.** `Show QR code` is a text link. But the natural real-world flow is
   *holding the phone up so the friend scans it*. That is a first-class use case buried behind a
   toggle in a collapsed box.

9. **Duplicated navigation.** `btnOwner` and `btnScan` are wired to the **identical URL**
   (`base() + "/owner/" + ownerToken`). Two rows, two different labels, one destination.

10. **Dead-end permission.** If `RUN_PERM` is not granted, `sendCmd` toasts a string and calls
    `openAppInfo()` — a system settings screen with no indication of what to toggle or why.

11. **Copy-paste beats the app.** The app *mints and owns* the token and pushes it into Termux on
    every resume — a deliberate, well-reasoned design (the commit message explains the drift bug it
    fixed). Yet the fastest real path is still "read the URL out of Termux". Nothing here is
    optimising for being the obvious place to get the link.

12. **No accessibility pass.** 11sp uppercase labels at `#64748B`, monospace URL at 11sp, and a
    10sp status pill. State is carried by colour *and* text, which is correct, but nothing was
    measured.

---

## 2. Three directions

Rendered at real device scale in `design/photo-drop-v4/mockups.html`.

### A — Live Header  *(recommended)*

A status strip that **owns the top of the screen** and takes a distinct colour for every state, so
"is it on?" is answered before a word is read. One primary control that **changes identity** with
state rather than two buttons where one is dead. Everything below is one scroll of progressively
less important detail.

- **For:** smallest diff from the current code, best legibility in direct sun (which is the stated
  reason for light-only), every state distinguishable at a glance, nothing moves that does not need to.
- **Against:** the link is not the only thing on screen, so it never gets the app to itself.

### B — Share Card

The app is treated as **one object you hand to someone**. The link card *is* the screen, the QR is
permanently visible at reading distance, and server state collapses into a thin top bar.

- **For:** the strongest possible answer to "what do I do with this app", and the best face-to-face
  scanning — the phone gets held up at arm's length, where a 148dp QR in a side panel is too small.
- **Against:** costs the most vertical space for anything that is not the link. Stop and Dashboard
  both end up in an overflow, which is a worse home for Stop than it is today.

### C — Tap to Toggle

The server *is* the interface. A large orb is the switch; the whole screen goes green when live; the
link and URL slide up from a bottom sheet only once there is something to show.

- **For:** the state change is felt rather than read. Delightful, and genuinely the fastest
  one-handed interaction of the three.
- **Against:** the most work by a distance — a real sheet transition, and a **hold-to-stop**
  affordance so a pocket tap does not kill an upload mid-flight. That guard is not optional.

### Recommendation

**Ship A.** It fixes every one of the twelve findings for roughly the diff size of the current app,
it is the only one that survives being read on a phone in a bright room, and it does not put
`Stop` — a genuinely destructive action — behind an overflow or a long-press that users will not
discover.

**Borrow from B:** make the QR permanent rather than toggled, even inside A. That single change is
worth more than everything else in B, because it matches how the app is actually used across a
table.

**Borrow from C:** one live indicator in the running state, so the 7-second poll has a visible
heartbeat. Nothing else from C.

### Material You — an option the research surfaced, and why to skip it

T3 Code's own Android app **defaults to Material You Layout**, per `docs/user/appearance.md`: *"It
changes shapes, spacing, and controls independently of the selected theme."* That is the single
strongest signal that "make it rhyme with T3 Code's mobile app" and "use Material You" are close to
the same request on Android.

It is also reachable here with **zero dependencies**, which is not obvious. There is no
`DynamicColors` without AndroidX, but at API 31 the framework publishes the wallpaper palette as
public colour resources:

```xml
<!-- res/values-v31/colors.xml -->
<color name="primary">@android:color/system_accent1_500</color>
```

with the brand green as the fallback in `res/values/colors.xml`. `values-v31` resource qualifiers
are a framework mechanism, not a support-library one, so they work in an `aapt2`-only build.

**Skip it anyway, deliberately.** Wallpaper-derived colour would hand the app's most important
decision — whether it is live, and whether there is room on the phone — to whatever picture the
user happens to have set. A user whose wallpaper is orange gets an amber "Storage low" strip. The
semantic mapping is not negotiable, so the palette stays fixed. The *shapes* are the part worth
copying, and those are in §3 already.

Worth revisiting only as an opt-in accent for the non-semantic chrome — buttons, chips — where a
wrong colour costs nothing.

---

## 3. Design tokens

Keep `#167A38` as the accent. It was chosen deliberately so that white text can sit on the fill, and
that constraint still holds.

### Surfaces

| Token | Hex | Role |
| --- | --- | --- |
| `page_bg` | `#F8F9FA` | Page. Tinted, so white cards read as raised. |
| `surface` | `#FFFFFF` | Cards. |
| `surface_low` | `#F1F3F5` | Insets, disabled fills, code chips. |
| `stroke` | `#E2E5E8` | Card borders. |
| `stroke_soft` | `#EDF0F2` | Inner dividers. |

**Elevation is available and deliberately unused.** `android:elevation` works framework-only and
`GradientDrawable.getOutline()` returns a rounded rect, so a real hardware shadow that follows the
corner radius costs one XML attribute. Cards still stay flat-on-tinted-page: the existing
`StorageBarView` rationale applies to the whole layout, and a shadow-heavy surface washes out in
daylight. Revisit this only if the status strip ever needs to read as floating chrome.

**Warm the neutrals — this is the single biggest lever for T3 resemblance.** T3 Code's own brand
theme does not use neutral grey. Its "dark foreground" is a desaturated plum (`#501854`), its muted
text is a saturated magenta (`#8d1255`), and its canvas is a warm off-white (`#fdf7fd`). The
character is in the *cast*, not the hue. Photo Drop keeps its green, but the greys should drift a
few degrees warm so they sit with the green rather than against it:

| Token | Neutral (current) | Warm (recommended) |
| --- | --- | --- |
| `page_bg` | `#F8F9FA` | `#FAFAF8` |
| `surface_low` | `#F1F3F5` | `#F2F3F0` |
| `stroke` | `#E2E5E8` | `#E3E4DF` |
| `text_faint` | `#6C737B` | `#6B6F68` |

Re-check contrast after any of these move; warm greys lose contrast slightly faster than cool ones.

### Text — four levels, all measured

| Token | Hex | vs `#FFFFFF` |
| --- | --- | --- |
| `text_main` | `#111315` | 17.0:1 |
| `text_muted` | `#494E54` | 8.4:1 |
| `text_faint` | `#6C737B` | 5.2:1 |
| `text_hair` | `#6C737B` | 5.2:1 |

**One correction to the current palette.** `text_faint` is `#6C737B` at 5.2:1 and is fine, but there
is a temptation to add a fourth, lighter tier for overlines and secondary labels. Do not. A tint
around `#9AA1A8` measures **2.5:1** and fails AA for body text; it is acceptable only for non-text
chrome (the reserve tick in `StorageBarView`, chevrons, dividers). Keep exactly two greys for text:

- **text:** `#6C737B` (5.2:1) as the floor, never lighter.
- **chrome:** `#B7BDC3` for ticks, chevrons, hairlines. Never for a glyph a user must read.

This was caught by scripting a WCAG sweep over the mockups, not by eye. Do the same on the real
layout before shipping.

### Accent and semantics

| Role | Hex |
| --- | --- |
| `primary` / `primary_dark` | `#167A38` / `#0E5224` |
| `on_primary` | `#FFFFFF` (5.2:1 on primary) |
| success bg / edge / fg | `#E6F4EA` / `#B7DFC4` / `#167A38` |
| warning bg / edge / fg | `#FDF2E3` / `#EFD3A6` / `#B26A00` |
| danger bg / edge / fg | `#FCEDEC` / `#F2C0BC` / `#B3261E` |
| neutral bg / edge / fg | `#EEF0F2` / `#DBDFE3` / `#3D4348` |

Sub-text on the solid green strip is `#DCF5E8` (4.7:1). `#C6EBD5` measures 4.2:1 and fails.

### Type, spacing, radius

- **Type:** adopt the T3 Code mobile scale verbatim — sizes/line-heights **11/14 · 12/16 · 13/17 ·
  14/19 · 16/23 · 18/23 · 21/28 · 26/32**. Then map it:

  | Role | sp / weight |
  | --- | --- |
  | App title | 21 / 700 |
  | Domain anchor | 18 / 700 |
  | Primary button | 16 / 700 |
  | Body | 16 / 400 |
  | Secondary | 14 / 400 |
  | Caption | 12 / 400 |
  | Overline | 11 / 700, `.08em` uppercase |
  | Monospace URL | 12 / 400 |

  **Drop the 10sp tier entirely.** T3 Code's smallest size is 11/14 and M3 Expressized moves every
  label *up* in weight while holding size constant. The current layout's 10sp overlines and 10sp
  status pills are below both. Bundling DM Sans Regular/Medium/Bold (three static weights, T3's own
  choice) is worth it — weight is carried by family name there, not a weight axis.

  Monospace is for machine-readable strings only — URLs, SSH, paths. Never for UI labels. T3 also
  deliberately falls back to the system mono on Android rather than bundling one, which matches the
  existing `android:typeface="monospace"`.
- **Spacing:** 4 / 8 / 12 / 16 / 20 / 24 / 32dp. 16dp screen gutters, 24dp section rhythm.
- **Radius:** 20dp hero · 16dp card · 12dp button · 9dp inset · pill `radius=999`.

---

## 4. Status surface — six states, all distinguishable

The current app gives `STOPPED` and `ON LOCALLY` the same neutral treatment. They must differ.

| State | Copy | Sub-line | Strip bg | Dot | Motion |
| --- | --- | --- | --- | --- | --- |
| Stopped | Server is offline | Nothing can upload right now | `#EEF0F2` | `#8B9199` 9dp | — |
| Starting | Starting | Bringing up Termux and the tunnel | `#FDF2E3` | `#B26A00` | opacity 1→.35→1, 1100ms loop |
| Online, local only | On this Wi-Fi | Works here only, not through the tunnel | `#EAF5EC` | `#167A38` | — |
| Online, via tunnel | Online anywhere | Works for anyone with the link | `#167A38` | `#7BE3A6` | alpha 1→.55→1, 2600ms loop |
| Storage low | Storage low | Uploads are paused at 1.6 GB free | `#FCEDEC` | `#B3261E` | — |
| Termux unreachable | Can't reach Termux | Grant permission to run commands | `#212529` | `#FF8A80` | — |

The last one is inverted on purpose. It is the only state where something is *wrong with the app's
environment* rather than with the server, and a dark strip is unmistakable next to five tinted ones.

**On transition:** cross-fade background and text colour with an `ArgbEvaluator` over 200ms, and
slide the copy 8dp up while fading in over 150ms. Never a hard cut — the 7s poll means a hard cut
would fire in the user's peripheral vision while they read something else.

---

## 5. Motion spec

**Principle:** everything answers a state change, nothing decorates. One easing family, 120–300ms.

**Why no overshoot.** `SpringAnimation` is AndroidX, so springs must be hand-integrated — but that
is not the reason to skip them. The reason is M3's own token split: **effects springs (colour,
opacity) are damping 1.0 in every scheme, so they never overshoot**, because those properties have
hard limits. All the character lives in *spatial* springs (0.8 expressive / 0.9 standard). This app
is almost entirely effects and one flat surface swap, so the correct token set is the effects family
— damping 1.0, stiffness 1600, ~200ms. Colour and opacity physically cannot wobble here, and
letting a status strip bounce would read as instability on a screen that re-polls every 7 seconds.

**A hard constraint that decides the curve.** `PathInterpolator` requires control points in `[0,1]`.
The M3 Expressive beziers violate that — expressive fast spatial is `cubic-bezier(0.42, 1.67, 0.21,
0.90)`, and `y1 = 1.67` is rejected outright. So every curve below is from the effects family
(`0.34, 0.80, 0.34, 1.00`) or the standard family (`0.2, 0, 0, 1`), both of which are legal. If
someone later wants overshoot, they need per-frame `Choreographer` integration, not a bezier.

**Running state is a shimmer sweep, not a spinner.** This is T3 Code's most distinctive motion and
it fits this app exactly: a 72dp-wide `LinearGradient` highlight sweeps across a 30dp icon+gap plus
the measured text width, then pauses, on loop. For this app it replaces both the opacity pulse and
the dot spinner — the same "something is happening, don't look away" signal, without a spinner that
implies a knowable duration.

| Trigger | View | Property | From → To | ms | Interpolator |
| --- | --- | --- | --- | --- | --- |
| Screen entry | root `LinearLayout` | `alpha`, `translationY` | `0→1`, `16dp→0` | 220 | standard `(.2,0,0,1)` |
| Status change | `tvStrip` | `backgroundColor`, `textColor` | old → new | 200 | effects `(.34,.8,.34,1)` |
| Status copy change | `tvStrip` children | `alpha`, `translationY` | `0→1`, `8dp→0` | 150 | standard |
| **Running shimmer** | `shimmerOverlay` | `translationX` | `-72dp→width+30dp` | **1350** | `LinearInterpolator` |
| **Shimmer pause** | — | — | — | **1450** | — |
| Primary press down | any button | `scaleX/Y` **+ cornerRadius** | `1→.97`, `12dp→8dp` | 120 | standard |
| Primary release | any button | `scaleX/Y` + corner radius | `.97→1`, `8dp→12dp` | 120 | standard |
| **Primary swap** | `btnPrimary` | `alpha` | `1→0→1` | 90 + 120 | standard |
| Copy confirm | `btnPrimary` | text, `textColor` | → "Copied", → `#167A38` | 140 | standard |
| Copy confirm reset | `btnPrimary` | text, `textColor` | → original | 160 | standard |
| Activity row insert | `rowActivity` | `alpha`, `translationY` | `0→1`, `12dp→0` | 220 | standard |
| Storage bar change | `StorageBarView` | fill fraction | old → new | 300 | effects |
| Permission error | `cardPermission` | `translationX` | `0, -8, 8, 0` | 260 | cycle |

**Pressed buttons become *more square*.** M3 Expressive shape-morphs buttons by state — round and
square converge on the same pressed shape — and T3 Code does the same thing to its composer
(27dp → 26dp on focus). `GradientDrawable.setCornerRadius` is animatable via `ObjectAnimator`, so
this is reachable framework-only and is the most T3-looking motion in the whole app for four lines
of code.

`pressFeedback(View)` already exists in `MainActivity` and is correct — keep it, extend it to drive
the radius as well as the scale, and apply it to every new control.

---

## 6. Custom views

| File | Why a `TextView` + drawable cannot do it |
| --- | --- |
| `StorageBarView.java` *(exists, keep)* | Fractional fill plus an absolute reserve tick. Already right. |
| `StatusStripView.java` *(new)* | Draws the state dot and owns the shimmer loop. The loop must cancel correctly on state change and stop when the app is backgrounded; `View.animate()` cannot hold that. |
| `ActivityRowView.java` *(new)* | Renders the session summary and animates row insert. Keeps `render()` out of layout arithmetic. |
| `ShimmerView.java` *(new)* | The sweep. A `LinearGradient` shader animated via `translate` across a measured text width. |
| `WorkLogRow.java` *(new)* | T3's transcript row: 24dp icon slot + text, `gap-px` hairline separation, no borders, 20dp radius, press tint. |

**The work-log row is the most T3-looking component in this app.** T3 Code renders its entire
transcript as flat, dividerless rows on Android with a fixed 24×24 icon slot and 1px gaps — a
"hairline plus centred chip" pattern that reads as hairlines rather than as a table. It is a much
better fit for this app's activity row and nav list than the current bordered card, and it costs one
custom view. (T3 also sets thread-row radius to **20 on Android specifically**, against 12 on iOS —
Android is deliberately the rounder platform.)

No XML attributes are needed on any of them; all are driven from Java, which suits a
programmatically-themed app. Each needs the standard three constructors so it inflates from XML.

---

## 7. Wire format

The real authenticated `/healthz` response, and the complete field list:

```json
{"ok":true,"dest":"/storage/emulated/0/DCIM/GuestUploads","free":41234567890,
 "dest_size":128884901888,"used":87650333998,"reserve":2147483648,"sessions":3}
```

**Parsing: keep the hand-rolled reader, but stop pretending it is a JSON parser.** `pick()` +
`parseLong()` are ~20 lines, work at minSdk 26, and adding Gson or `org.json` costs APK size for a
7-field flat object. Move them into a `Health` value class so `render()` stops juggling `-1`
sentinels:

```java
final class Health {
    boolean up; long free = -1, total = -1, reserve = -1; int sessions = 0;
    static Health parse(String body);   // null body -> up=false, everything -1
    float freeRatio();                 // 0f when total<=0
    float reserveRatio();               // 0f when total<=0
    boolean known();                   // free >= 0
}
```

Every accessor degrades to "unknown" rather than to zero, so a missing field can never render as
"0 bytes free".

| Field | Drives | Absent / failed |
| --- | --- | --- |
| `ok` | state machine: stopped vs online | → stopped; storage shows "Storage unknown" |
| `free` | "38.4 GB free", bar fill, danger state | bar empty, label greyed |
| `dest_size` | "of 128 GB", bar denominator | hide the denominator entirely |
| `reserve` | reserve tick, low-storage state | hide the tick, never claim "safe" |
| `sessions` | activity row | "No uploads yet" |
| `dest` | *nothing in the UI* | — |
| `used` | *nothing in the UI* | — |

**Be honest about `sessions`.** It is `len(batch_ids_recent())` — a count of batch directories
touched within `SESSION_TTL`. It does **not** carry names, file counts, or sizes. So the activity row
reads *"3 upload sessions today · most recent finished at 14:02"*, not *"Ravi is uploading, 14
files, 212 MB"*.

If a richer feed is wanted, it needs a new authenticated endpoint that iterates batches the way
`owner_dashboard()` already does. That is a `server.py` change and should be a **separate,
explicitly-scoped follow-up** — not smuggled into a UI task.

**Also fix:** `btnScan` and `btnOwner` point at the same URL. Delete `btnScan`; keep one
"Owner dashboard" row. If the media-scan report deserves its own entry, it needs its own route.

---

## 8. First run and the permission dead-end

**Two chores, once.** Detect Termux presence with `getPackageManager().getPackageInfo("com.termux", 0)`
and permission with the existing `checkSelfPermission(RUN_PERM)`.

| Step | Title | Body | Done when |
| --- | --- | --- | --- |
| 1 | Termux is installed | Found on this phone. | package resolves |
| 2 | Copy the server into Termux | Run `bash ~/photo-drop/install.sh` once. | `sendCmd` returns true **and** `/healthz` answers |
| 3 | Allow Photo Drop to run commands | Settings → Apps → Photo Drop → Permissions. | `checkSelfPermission == GRANTED` |

Step 3 is the one that currently dead-ends, so it gets its own inline card with a real button rather
than a system settings hop:

> **Photo Drop needs permission to run commands in Termux.**
> Grant it in Settings → Apps → Photo Drop → Permissions.
> `[ Grant permission ]`

A `Snackbar` with an action is wrong here — this is a blocker, not a transient message, and the user
will dismiss it and forget. It must persist until resolved. When the permission is granted, update
the step in place rather than dismissing the whole sheet, so the user sees their action land.

---

## 9. Accessibility

- 48dp minimum on every interactive target. The current 40dp nav rows and the `btnQrToggle` text link
  are both under it.
- `contentDescription` on `imgQr`, `vStatusDot`, and any icon-only control. The dot must announce the
  state in words — it is colour and shape, nothing else.
- State is **never** colour alone: every strip carries a text label as well as a distinct colour, and
  the low-storage state additionally changes the bar fill and the copy.
- Run the AA sweep. The specific failure mode to watch for is introducing a fourth, lighter grey for
  overlines; it measures 2.5:1 and looks fine on a calibrated monitor in a dark room.
- Respect the system animator scale, but **do not assume you can read it**. `ValueAnimator`'s
  `setDurationScale` is `@hide @TestApi` and absent from the public SDK, and `areAnimatorsEnabled()`
  only landed at API 33. Below that the setting still *applies* globally — every framework animator
  is scaled by the system — so `Settings → Accessibility → Remove animations` works for free. To
  know it, read `Settings.Global.ANIMATOR_DURATION_SCALE` (a plain global-settings string read, not
  the hidden API), or call `areAnimatorsEnabled()` behind an API-33 guard.

  **The shimmer needs an explicit guard.** A 1350ms sweep on a loop is the one animation that gets
  *worse* at a reduced scale rather than merely instant — at scale 0 it can spin rather than settle.
  Gate it on the same reduced-motion check T3 Code threads through its own shimmer, and on
  `AppState == active`, so it stops when the app is backgrounded.

---

## 10. Change plan

Ordered. Each step is independently buildable.

**`res/values/colors.xml`** — add `text_hair`/chrome grey, `strip_*` backgrounds, `on_strip`
sub-text. Remove nothing that is referenced; `surface_press`, `row_press` and `track_bg` are
currently unused by any layout and can go.

**`res/drawable/`** — add `strip_*.xml` per state, `btn_primary_off.xml` (needs an explicit
`state_enabled=false` item — the current `btn_primary.xml` already has one, keep that pattern), and
`card_alert.xml` for the permission card.

**`res/layout/activity_main.xml`** — restructure, do not patch. Pin the status strip above the
scroll so it never leaves the screen. Inside the `ScrollView`: link hero → primary → storage card →
two nav rows (not three). Move `btnStart`/`btnStop` out; one `btnPrimary` plus an overflow `btnMore`.

**`StatusStripView.java`** — new.

**`ActivityRowView.java`** — new.

**`MainActivity.java`**:

| Replace | With |
| --- | --- |
| `pill(String,int,int)` | `applyState(State)` — one switch driving the whole screen |
| `render(String)` | `render(Health)` |
| `pick`, `parseLong` | moved into `Health` |
| `start`, `up`, `stop` flags | a single `enum State` field |
| `btnStart`/`btnStop` listeners | one `btnPrimary` listener that dispatches on `State` |
| `copyLink()` | same, plus a real `copied` confirmation with revert |
| `toggleQr()` | `showQr()` — the toggle goes away, the QR is always there |
| `onResume` polling | unchanged, but `State` diffing means no redraw when nothing changed |

---

## 11. Verification

```bash
bash apps/photo-drop/android/build.sh      # must print BUILD_OK
bash apps/photo-drop/deploy.sh             # adb install to the Samsung
```

Then check, in order:

1. Cold start with the server stopped — status strip reads *Server is offline*, the link hero is
   honest rather than dashed, one primary button.
2. Tap Start — strip goes amber and pulses, copy says *Starting*, button swaps to a disabled
   *Starting…*, **no Toast**.
3. When `/healthz` answers — strip turns solid green, link appears, button becomes *Copy link*.
4. Copy — button reads *Copied* in green, reverts after 2s. **Tapping the hero card gives the same
   feedback**, which it does not today.
5. Friend uploads — activity row leaves its empty state and animates in, driven by `sessions`.
6. Fill the phone below the reserve — strip goes red, bar goes red, copy says uploads are paused.
7. Revoke the Termux permission — the inline card appears and persists. It does not dump you into
   App Info.
8. First run on a clean install — the three-step checklist, which disappears once step 3 passes and
   never returns.
9. `adb shell settings put global animator_duration_scale 0` — the setting applies globally to
   framework animators, so nothing should still be moving. Then confirm the shimmer is *stopped*,
   not spinning. Reset with `= 1` afterwards.
10. Run the AA contrast sweep over the built layout. Anything under 4.5:1 for body text is a bug.

---

## 12. Non-goals

- **Dark mode.** Light-only is deliberate, for daylight. `values-night/` does not get created.
- **Compose, AndroidX, Material Components, dynamic color.** The build is `aapt2` + `javac` + `d8`
  with one jar. Adding a dependency toolchain to modernise the visuals would cost more than it buys.
- **A bottom navigation bar.** One screen. There is nothing to navigate between.
- **Rewriting the upload page or the owner dashboard.** Both are server-rendered HTML in `server.py`
  and out of scope.
- **Per-uploader names, file counts, sizes in the app.** Requires a new server endpoint. Separate task.
- **Push notifications or a foreground service.** The app is a launcher, not a daemon; the server
  owns the wake lock.

---

## Appendix — how this plan was produced

Designed by `gemini-4-argon` through the Gemini Web UI planner, per the `gemini-ui-planner` skill:
the code was gathered and inlined by hand, the planner returned prose, and this document is the
edited result. The first pass returned a plan that mostly restated the existing palette and invented
a Gradle build path, so it went back with a critique and a corrected field list — that second pass
supplied the status-state table, the `Health` value class and the activity-row framing.

T3 Code specifics in §2, §3, §5 and §6 come from a separate research pass that read the mobile app's
**source** (`apps/mobile/`) rather than inferring from screenshots — type scale from
`lib/typography.ts`, radii and thread-row geometry from `thread-list-v2-row-appearance.android.ts`,
shimmer constants from `thread-work-log.tsx`, composer radii from `ThreadComposer.tsx`, and the
Material You default from `docs/user/appearance.md`. Framework API availability was checked against
AOSP `frameworks/base/core/api/current.txt` rather than recalled.

Corrections made during editing, worth knowing about if these numbers are reused:

- The planner invented `active_uploads`, which the server does not return. The real field list is the
  seven in §7.
- The planner proposed file paths under `app/src/main/java/…`. The real layout is
  `apps/photo-drop/android/src/dev/photodrop/app/`.
- The planner proposed removing `surface_press`, `row_press` and `track_bg` as part of a palette
  change. They are unreferenced, but that is a cleanup, not a design decision — separate commit.
- **An error of mine.** An earlier draft of §9 said only that reduced motion "works for free" because
  the animations are framework animators. That is true about the *setting applying*, but it implied
  the app can read it. It cannot below API 33 — `ValueAnimator.setDurationScale` is `@hide`. Corrected
  above, along with the shimmer case that actually breaks at scale 0.

## Open questions for you

1. **Direction A, or do you want to see B and C fleshed out too?** The mockups show all three; the
   plan only specs A.
2. **Keep the green, or move toward T3's plum?** The research argues the character is in the *cast*
   of the neutrals, not the accent hue — §3 warms the greys to capture that without abandoning the
   brand. But if you would rather the app actually read as T3, `primary #db2777` with `fg #501854` is
   the literal brand palette and costs nothing to swap.
3. **Bundle DM Sans?** Three static weights, ~200KB, and it is what T3 uses. The app currently uses
   the system font.
4. **The `sessions` endpoint question in §7** — worth a separate `server.py` task, or is
   "3 upload sessions today" enough?