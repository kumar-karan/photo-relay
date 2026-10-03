# Run Google Antigravity locally on Android (via the `agy` CLI + Google Pro auth)

**Goal:** run Antigravity's agent **locally on the Android phone**, logged in with your **Google Pro
(Gemini subscription)** account — like a self-hosted Hermes agent. No remote desktop.

**Key realization:** don't try to run the *desktop app* (VS Code/Electron fork — not portable to
Android). Run the **Antigravity CLI (`agy`)** — the same agent harness, headless, with an
**aarch64 Linux binary** and **Google OAuth** login (= your subscription, no API key).

**Hard limit:** Gemini 3 and the code sandbox run in **Google's cloud**. "Local" = the *agent
process* runs on your phone under your Google Pro login and calls the cloud. (Same as Hermes:
local loop + cloud brain.) Fully offline is impossible for Antigravity.

---

## ✅ SOLVED by the community — no APK needed, use an auto-installer
There is **no Antigravity APK** and no official Termux support — but people run the **official
ARM64 `agy` binary on Android Termux** by **patching it**, and installers automate the whole thing.

**Why patching is needed (7 separate issues):** the Linux binary assumes glibc + a **48-bit** VA
space, Android uses Bionic + often **39-bit**; plus seccomp blocks `faccessat2`, DNS/TLS config
differs, and Termux's `LD_PRELOAD` leaks into the glibc process. The installers patch TCMalloc's
address bits **48→39**, bind Termux's `/etc/resolv.conf` for DNS, and shim glibc.

### The installers (pick by CPU)
- **`marshallrichards/ClawPhone`** ⭐ — native Termux, one command, with update/uninstall:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/marshallrichards/ClawPhone/main/scripts/install-antigravity-termux.sh | bash
  source ~/.bashrc && agy --version
  ```
  (Uses a tiny proot bind *only* for DNS — not a full VM.)
- **`wallentx/antigravity-cli-termux`** — auto-installer; a **GitHub Action re-patches every 6h**
  so `agy` updates don't break it.
- **`Brajesh2022` gist** — the original manual patching guide (the basis for the above).
- **`krecod/agy-termux-lse`** — **older-CPU route via proot** (e.g. Snapdragon 660 that Antigravity
  2.0's native binary won't run on).

> 🔑 **Which one:** modern Snapdragon/Exynos → **ClawPhone** (native). Older chip → **krecod** (proot).
> Check the Samsung's chip in Settings → About phone.

### The key insight for YOUR goal
Community note: *"if `agy` starts but complains about login/auth, the native binary is running — the
rest is just the account flow."* → once installed, you hit **Google OAuth**, and **that's where
your Google Pro account plugs in.** Local agent + Google Pro auth = exactly what you wanted.

---

## Step-by-step build (the real, community-tested path)

### 1. Termux (F-Droid, not Play Store)
```bash
pkg update && pkg upgrade -y
pkg install curl -y
```

### 2. Run the ClawPhone auto-installer (does all 7 patches)
```bash
curl -fsSL https://raw.githubusercontent.com/marshallrichards/ClawPhone/main/scripts/install-antigravity-termux.sh | bash
source ~/.bashrc
agy --version        # ✅ CHECKPOINT: version prints → patched binary runs
```
> Older CPU / `Illegal instruction` / segfault → use **krecod/agy-termux-lse** (proot) instead.
> Tip the community gives: paste the install guide into an on-device agent (opencode/Gemini) and
> let it fix your environment — there are many moving parts.

### 3. Log in with Google Pro (the headless loop)
```bash
agy
# choose: Google OAuth → it prints a URL + asks for a code
```
- Open the **URL** in the **phone's Chrome** → sign in with your **Google Pro** account.
- Paste the **authorization code** back into the `agy` terminal.
- ✅ **CHECKPOINT:** signed-in and it persists across a restart.
> If it logs in but **forgets on next launch** → token/keyring persistence issue. Look for an `agy`
> file-based token option, or re-auth per session as a stopgap.

### 4. Run it like an agent
```bash
agy                 # interactive TUI:  type ? for slash commands (/settings, /fork, /logout)
# or drive a task directly, e.g.:
agy "summarize the repo in ~/project and list TODOs"
```
Keep it alive on the phone (Hermes-style):
```bash
termux-wake-lock                          # in Termux (outside proot)
# run agy inside tmux so it survives:  apt install -y tmux ; tmux new -s agy
```

### 5. Multiple Google Pro accounts
- `/logout` clears the saved profile; log in with a different account to switch.
- Community tool **Antigravity Manager** (desktop) does account switching/backup — not on Android,
  but shows the pattern. On the phone you'll switch manually via `/logout` + re-auth.
- ⚠️ Keep rotation light — heavy multi-account automation risks Google flagging the accounts.

---

## Fallbacks if `agy`-on-Android fails
1. **Run `agy` on the Mac / a Linux box, reach it from the phone** — but you said no remote. Still,
   a $5 VPS running `agy` + an SSH app on the phone is the reliable version of "my agent, my Pro login."
2. **Use a BYOK agent CLI that's Android-friendly** — `opencode`, Factory **Droid**, `agent-loop`,
   or **Claude Code** in Termux. These *don't* use Google Pro, but they run cleanly on-device with
   your own key. (Different auth model, but actually supported.)
3. **Kai 9000 + Gemini** — if you just want Gemini's brain in a phone agent, add a Gemini API key
   (or Google AI Studio free key) to Kai. Not your Pro subscription, but zero hassle and it works.

---

## Verdict (updated)
- **Can you run Antigravity locally on Android with Google Pro?** **Yes — community-proven.** No APK,
  but the official ARM64 `agy` binary runs on Termux via patched auto-installers (ClawPhone /
  wallentx), and login uses **Google OAuth = your Google Pro**.
- **Confidence:** medium-high — real people have it working; it's a binary patch, not official, so
  updates can break it (wallentx's 6-hourly re-patch mitigates this).
- **Main variables:** your **CPU** (native vs proot) and **token persistence** after login.
- **Reminder:** the model + code sandbox still run in Google's cloud. The *agent* is local; the
  *brain* is Gemini via your subscription. That's the ceiling — and it's fine for a Hermes-style setup.

---

### Sources
- [ClawPhone — `agy` on Termux installer (marshallrichards)](https://github.com/marshallrichards/ClawPhone/blob/main/docs/antigravity-termux.md)
- [Brajesh gist — original Termux patching guide](https://gist.github.com/Brajesh2022/e42160d29b55417db6c18c52dd1d6d37)
- ["I got Antigravity CLI running natively on Android Termux" — Google AI forum](https://discuss.ai.google.dev/t/i-got-antigravity-cli-running-natively-on-android-termux-no-vms-no-cloud-shell-no-proot-distro-just-your-phone/147333)
- [Feature request: Android/Termux AArch64 support (issue #22)](https://github.com/google-antigravity/antigravity-cli/issues/22)
- [Antigravity CLI — install docs](https://antigravity.google/docs/cli/install)
- [Antigravity CLI install guide (Arm)](https://learn.arm.com/install-guides/antigravity/)
- [Antigravity BYOK feature request (forum)](https://discuss.ai.google.dev/t/antigravity-add-your-own-api-keys-models/137068)
