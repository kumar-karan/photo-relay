# iOS Shortcuts — Full Setup Guide (for a Samsung switcher)

Everything to go from zero → power user on iPhone 17 Pro. Three parts:
1. How the Shortcuts app actually works
2. Step-by-step builds for the 15 shortcuts
3. Smart community shortcuts worth installing

---

## PART 1 — How the Shortcuts app works

**Mental model (vs Samsung's Good Lock / Bixby Routines):**
A *Shortcut* = a mini-program made of **actions** (blocks) that run top-to-bottom.
Data flows down: each action can use the output of the one above ("**Shortcut Input**" /
"**Provided Input**" / a **Variable**).

### The 3 tabs
- **Shortcuts** — your library. Tap **+** (top-right) to build one.
- **Automation** — shortcuts that run *by themselves* on a trigger (time, WiFi, charger, NFC…).
- **Apps** (Gallery) — Apple's starter shortcuts + which app-actions exist.

### Building basics
- Tap **+** → name it (tap the name at top) → pick an icon/color.
- **Add Action** (search bar at bottom) → search the action name → tap to insert.
- Tap a **blue chip** inside an action to change its value or insert a **Variable**.
- **Magic Variable**: tap an action's output → "Select Variable" to feed it downstream.
- Test with the **▶︎ play** button while building.

### Key concepts you'll reuse
- **If / Otherwise** — branching (search "If").
- **Choose from Menu** — presents buttons; each becomes a branch.
- **Repeat / Repeat with Each** — loops over a list.
- **Ask for Input** — prompt the user for text/number.
- **Variables**: `Set Variable` / `Get Variable`, plus **Magic Variables**.
- **Shortcut Input** — data passed in from the Share Sheet or another shortcut.

### Ways to run a shortcut
- Tap it in the app • **Home Screen widget/icon** (Share → Add to Home Screen)
- **Action Button** (Settings → Action Button → Shortcut)
- **Back Tap** (Settings → Accessibility → Touch → Back Tap → double/triple)
- **Siri** ("Hey Siri, <shortcut name>") • **Share Sheet** (enable "Show in Share Sheet")
- **Automation** trigger

---

## PART 2 — Step-by-step builds

> Action names are searchable in the bottom search bar. "→" means "then add action".

### 1. Action Menu (mini launcher)
1. New shortcut → name "Action Menu".
2. Add **Choose from Menu** → set prompt "What do you need?" → add items:
   `Camera`, `Send Photos`, `Torch`, `Voice Memo`.
3. Under **Camera** branch → add **Open App → Camera**.
4. Under **Send Photos** → add **Run Shortcut → Monthly Backup** (build #3 first).
5. Under **Torch** → add **Set Flashlight → On**.
6. Under **Voice Memo** → **Open App → Voice Memos**.
7. Settings → **Action Button → Shortcut → Action Menu**.

### 2. Focus Down (battery saver combo)
1. New shortcut "Focus Down".
2. **Set Low Power Mode → On**.
3. **Set Appearance → Dark**.
4. (optional) **Set Brightness → 40%**.
→ Assign to a Home Screen icon or Back Tap.

### 3. Monthly Backup (iPhone → Samsung)
1. New shortcut "Monthly Backup".
2. **Find Photos** → tap **Add Filter**:
   - *Date Taken* → *is in the last* → `30` `Days`
   - *(add filter)* *Media Type* → *is* → `Image` (add a 2nd for Video if you want).
   - Turn **Sort by** Date Taken, and leave Limit off.
3. **Share** (search "Share") → run it → choose **LocalSend** in the sheet.
4. Settings → assign to **Back Tap (triple)** or the Action Menu.
> Tip: If LocalSend watches a folder, replace **Share** with **Save to Files → DCIM/LocalSend**.

### 4. Clean Screenshots
1. New shortcut "Clean Screenshots".
2. **Find Photos** → filters: *Is a Screenshot* = `On`; *Date Taken* *is not in the last* `7 Days`.
3. **Delete Photos** (uses the found photos). It confirms before deleting.
→ Optionally run monthly via Automation.

### 5. Last Photo → Share
1. New shortcut "Last Photo".
2. **Get Latest Photos** → Count `1`.
3. **Share**.
→ Great for Back Tap (double).

### 6. WiFi QR Code
1. New shortcut "WiFi QR".
2. **Get Network Details** → detail **Network** (SSID). Store via **Set Variable → ssid**.
3. **Ask for Input** (Text) → "WiFi password?" → **Set Variable → pass** *(iOS won't read the pass for you)*.
4. **Text** action → type: `WIFI:T:WPA;S:[ssid];P:[pass];;` (insert the variables).
5. **Show QR Code** (uses the Text). Scan with any phone to join.

### 7. What's My IP
1. New shortcut "My IP".
2. **Get Contents of URL** → `https://api.ipify.org`.
3. **Show Result**. (Add **Get Network Details → IP Address** to also show local IP.)

### 8. Base64 / URL encode clipboard
1. New shortcut "Encode Clipboard".
2. **Get Clipboard**.
3. **Choose from Menu**: `Base64`, `URL Encode`.
   - Base64 branch → **Base64 Encode**.
   - URL branch → **URL Encode**.
4. **Copy to Clipboard** (after the menu). Add **Show Notification** to confirm.

### 9. Automation — Arrive Home
Automation tab → **+** → **Wi-Fi** → Network = *home SSID* → *Is Joined*.
Actions: **Set Low Power Mode → Off**, **Open App → (Music/Spotify)**.
Set **Run Immediately** (no confirmation).

### 10. Automation — Charger at Night
Automation → **+** → **Charger** → *Is Connected*.
Add **If** → *Time is between 11pm–6am* → then: **Set Focus → Sleep On**, **Set Appearance → Dark**.

### 11. Automation — Battery < 20%
Automation → **+** → **Battery Level** → *falls below 20%* → **Set Low Power Mode → On**.
Run Immediately.

### 12. Automation — App-open nudge
Automation → **+** → **App** → pick a time-sink app → *Is Opened* →
**Show Notification** "Set a 15-min timer?" or **Start Timer**. (Will ask to confirm.)

### 13. Automation — CarPlay / Car Bluetooth
Automation → **+** → **CarPlay** (or **Bluetooth → your car**) → *Connects* →
**Get Directions** to a saved place + **Play** a playlist.

### 14. Automation — Monthly Backup reminder
Automation → **+** → **Time of Day** → `9:00 AM`, **Monthly**, day `1` →
**Run Shortcut → Monthly Backup**. Keep **Ask Before Running On**.

### 15. Good Morning
1. New shortcut "Good Morning".
2. **Get Current Weather** → **Get [Conditions]/[Temperature]**.
3. **Find Calendar Events** → *Today*.
4. **Text**: "Good morning! It's [temp], [conditions]. You have [count] events."
5. **Speak Text** (uses the Text).
6. **Play Playlist** → your morning playlist.
→ Trigger with the Action Button or a "Wake Up" alarm automation.

---

## PART 3 — Smart community shortcuts & where to get them

### Where the community lives
- **RoutineHub.co** — the biggest gallery of user-made shortcuts (search, ratings, auto-update).
- **MatthewCassinelli.com/shortcuts** — huge curated, explained library.
- **r/shortcuts** (Reddit) — requests, gems, troubleshooting.
- **ShareShortcuts.com**, **Sharecuts** — more galleries.
- In-app **Gallery** (Apps tab) — Apple's own starter set.

### Genuinely smart ones people love
- **Data Jar** *(app + actions)* — persistent database for shortcuts (remember state between runs). Free.
- **Toolbox Pro / Actions** *(apps)* — add hundreds of missing actions (device info, UI, files).
- **Pushcut** — notifications with buttons + server-triggered automations.
- **Charty** — turn shortcut data into charts (habit/health dashboards).
- **Speedtest shortcut** — run a network speed test hands-free.
- **YouTube → Picture-in-Picture / background audio** — classic RoutineHub favorite.
- **"Download video"** (yt-dlp-style via a web API) — grab clips.
- **Sleep Timer for anything** — stops audio after N minutes (works for any app).
- **ChatGPT / Claude via Siri** — pipe your voice → API → spoken answer (needs an API key).
- **Instant packing/travel list**, **Receipt scanner → Numbers**, **Calorie logger → Health**.

### ⚠️ Safety when installing community shortcuts
Shortcuts can read your data, hit URLs, and move files. Before running one:
1. **Open it and read the actions** (it shows every step before you add it).
2. Watch for **Get Contents of URL** that *uploads* your data somewhere.
3. Prefer ones from **known authors** with reviews.
4. iOS asks permission the first time it touches Photos/Contacts/Location — don't blanket-allow.

---

## Quick-win order (if starting today)
1. **Monthly Backup** (#3) — you'll use it every month.
2. **Action Menu** (#1) → put on the Action Button.
3. **Battery < 20% automation** (#11) — set-and-forget.
4. **Clean Screenshots** (#4).
5. Install **Data Jar** + browse **RoutineHub** once you're comfortable.
