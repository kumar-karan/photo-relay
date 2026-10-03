# Old Samsung → Always-On AI Node (local LLM + agent) — 2026 Guide

**Setup:** iPhone 17 Pro is the primary. Old Samsung = **secondary, no SIM**, lives on
office **WiFi / hotspot**. Goal: turn it into a always-on **AI / agent device** — run a model
locally and/or wire in a cheap API (DeepSeek), and see what else it can do.

> ⚠️ First: **check the Samsung's chip + RAM** (Settings → About phone). It decides everything.
> - **≥ 8GB RAM + Snapdragon 8-gen / recent Exynos** → runs 3B–4B models decently.
> - **6GB RAM** → stick to ≤2B models (Gemma 2B, Qwen 0.8–1.7B, Phi-3-mini).
> - **≤4GB RAM** → skip on-device inference; use the **API path** (Path C) instead.
> Tell me the model and I'll tailor the exact model picks.

---

## Three paths (pick one, or stack them)

| Path | What it is | Needs internet? | Effort |
|------|-----------|-----------------|--------|
| **A. On-device app** | Chat app runs an LLM fully offline | No (after download) | Easy |
| **B. Termux server** | Phone hosts Ollama + Open WebUI on WiFi | No | Medium |
| **C. Wire in an API** | App/agent calls DeepSeek (cloud) | Yes | Easy |

---

## PATH A — On-device LLM apps (easiest, fully private)

Install one, download a small model, chat offline. Best picks for 2026:

- **PocketPal AI** ⭐ best all-around. Free, open-source, any **GGUF** model straight from
  Hugging Face, "Pals" = per-role system prompts (coding Pal, writing Pal). Start here.
- **MLC Chat** — *fastest* if you have a Snapdragon flagship (uses the NPU, ~40 tok/s vs 8–12
  CPU). Downside: only its curated model list.
- **Google AI Edge Gallery** — Google's official app, runs **Gemma 3n** offline, multimodal
  (image/audio), zero config. Locked to Gemma.
- **ChatterUI** — clean, no signup, works offline **and** can point to an API (bridges to Path C).
- **Maid** — F-Droid, no Play Store, direct GGUF import (privacy purist).

**Model sizing rule of thumb:** ≤3B params for phones. Gemma 2B / Qwen 1.7B / Phi-3-mini are the
sweet spot. Bigger = slower + hot + battery drain. Inference is heavy — expect warmth and drain.

---

## PATH B — Termux server (the "AI node" — access it from the iPhone too)

Turn the Samsung into a tiny always-on AI server on your office WiFi. Then hit it from the
**iPhone's browser**, your Mac, anything on the same network.

### Steps (high level)
1. Install **Termux from F-Droid or GitHub** — *not* the Play Store version (it's outdated,
   compiles will fail).
2. In Termux:
   ```
   termux-setup-storage
   pkg update && pkg upgrade -y
   pkg install ollama
   ```
3. Start the server **exposed to the network** (default only listens on loopback):
   ```
   export OLLAMA_HOST=0.0.0.0 && ollama serve &
   ```
4. Pull a small model:
   ```
   ollama run qwen3.5:0.8b      # or gemma3:2b / llama3.2:3b
   ```
5. (Optional) Add **Open WebUI** for a ChatGPT-style UI — community script:
   `github.com/sw3nlab/Termux-Ollama-Openwebui`. Ports: Open WebUI `:8082`, Ollama `:11434`.
6. From the **iPhone / Mac** on the same WiFi, open `http://<samsung-ip>:8082` (or point any
   OpenAI-compatible client at `http://<samsung-ip>:11434`).

### Gotchas
- **Store models in Termux `~` home**, never `/sdcard` → avoids "Permission Denied".
- Models die if you **uninstall Termux or clear its data**.
- Only needs internet to *download*; after that runs in **Airplane Mode**.
- Keep the phone **plugged in** and disable battery optimization for Termux (it's a server now).
- On a Galaxy S24 Ultra testers had ~4.5GB free with Termux running — small models are "usable,
  not instant."

### Advanced: full Linux workstation
`Termux → Ubuntu (proot) → Node.js → Ollama` gives a real dev box (some tools only run under
Ubuntu). People even run coding agents this way. Overkill unless you want the phone as a dev node.

---

## PATH C — Wire in the DeepSeek API (cheap, powerful, needs WiFi) ⭐ your "deep seek" idea

DeepSeek is **OpenAI-compatible** — any app/agent that accepts a custom base URL + key works.
Perfect since the Samsung is on WiFi most of the time.

### Connection details
- **Base URL:** `https://api.deepseek.com`
- **Auth:** your DeepSeek API key
- **Free tier:** ~5M tokens, no credit card, to test.
- Migration from OpenAI = change **base URL + key + model name**, nothing else.

### ⚠️ Model name change (important — deadline soon)
- `deepseek-chat` (direct answers) and `deepseek-reasoner` (chain-of-thought) are **legacy
  aliases** for **`deepseek-v4-flash`**, and they **deprecate 2026-07-24**.
- Use **`deepseek-v4-flash`** going forward (toggle thinking in the request).
- Tiers & pricing (2026):
  - **deepseek-v4-flash** — $0.14 /1M input (cache miss), $0.0028 /1M (cache hit), $0.28 /1M output.
  - **deepseek-v4-pro** — $0.435 /1M in, $0.87 /1M out. Both **1M-token context**.
- **Caching is automatic** → keep static stuff (system prompt, docs) at the *start* of the
  message array, variable user input at the *end*, to hit the cheap cache rate.
- 🔒 **Privacy caveat:** DeepSeek servers are in China → don't send sensitive/health/gov data.
  For private stuff use Path A/B (local) instead.

### Where to plug the key in
- **ChatterUI** (Android app) → add a custom OpenAI-compatible endpoint → DeepSeek.
- **Open WebUI** (from Path B) → Settings → add OpenAI-compatible connection → DeepSeek.
- **Tasker / MacroDroid** agent (below) → `HTTP Request` action → DeepSeek endpoint.
- Any iPhone **Shortcut** → `Get Contents of URL` (POST) → DeepSeek (so even the iPhone can use it).

---

## Making it an *agent* (not just a chatbot)

An "agent" = LLM + triggers + the ability to *do things* on the device. On Android the glue is:

- **Tasker** (paid, the powerhouse) — 300+ triggers/actions. Recipe: trigger (time, notification,
  location, WiFi, spoken command) → **HTTP Request to DeepSeek** → parse reply → act
  (send message, toggle setting, TTS speak, log to a file). This is your "home-ish agent."
- **MacroDroid** — easier, friendlier Tasker alternative.
- **AutoInput / AutoNotification** (Tasker plugins) — let the agent read notifications & tap UI.
- **Home Assistant Companion app** — if you run Home Assistant anywhere, the Samsung becomes a
  wall-mounted **voice/agent dashboard + sensor** (presence, charging, etc.). HA's "Assist" can
  use a local LLM or DeepSeek as its conversation engine.

**Example agent flows**
- "Summarize my unread notifications every evening" → Tasker reads notifications → DeepSeek
  summarizes → TTS or push to iPhone.
- Voice memo → transcribe (on-device) → DeepSeek turns into a to-do → append to a shared note.
- WiFi = office → auto-start Ollama server so the node is ready when you arrive.

---

## What else the always-on Samsung can do (bonus uses)

- **Syncthing** — auto-sync photos/files between Samsung ↔ Mac ↔ iPhone folder (pairs with your
  Google Photos backup plan).
- **Home dashboard** — mount it, run a StandBy-style clock/calendar/weather/HA panel.
- **Security cam** — apps like *Alfred* / *IP Webcam* → view from the iPhone.
- **Pi-hole-style adblock** for the LAN (via Termux + a DNS tool) — ambitious but doable.
- **Telegram bot host** — run a bot in Termux that answers via DeepSeek; message it from anywhere.
- **Media/Jellyfin** or **Syncthing relay**, **file server (Termux + ssh/http)**.
- **Automation brain** — Tasker macros that watch WiFi/time/notifications and act.

---

## Recommended starting point
1. **Today:** install **PocketPal AI**, pull **Gemma 2B** → confirm local inference works + speed.
2. **This week:** grab a **DeepSeek** free key, plug into **ChatterUI** → compare local vs cloud.
3. **When ready:** **Termux + Ollama (+ Open WebUI)** so the iPhone/Mac can use the Samsung as a
   shared node on office WiFi.
4. **Agent phase:** **Tasker → HTTP → DeepSeek** for your first "do something" automation.

*(Tell me the exact Samsung model + RAM and I'll turn step 1–4 into precise commands & model picks.)*

---

## ⭐ Hermes Agent — there IS an official Android app (2026)

**This is the "app on Android + attach an API" answer.** Nous Research ships a real app.

### The official app
- **Hermes Agent – Android** on **Google Play** (`com.hermesagent.android`) — free, ~75MB,
  v1.1.6 (Jun 2026), 4.46★ / 1.4k ratings. Also a **F-Droid fork** (`com.mobilefork.hermesagent`).
- **What it does on-device:**
  - **Multi-provider** — plug in **OpenAI, Anthropic, Google, or local models** (LiteRT/GGUF).
    → DeepSeek works via its OpenAI-compatible base URL (`https://api.deepseek.com`).
  - Built-in **full Linux terminal** (bash / Python / git), code execution.
  - **Gateways** to **Telegram / Slack / Discord** (reach it from your iPhone!).
  - **Web search, image generation, text-to-speech, persistent memory**.
  - Local chat with **Gemma LiteRT** / **Qwen GGUF**, file attach, voice dictation.

**This is the ideal fit for you:** the *agent backend runs in the app on the Samsung*, the
*brains come from the API* you attach. No Termux required (though the terminal is there if you want it).

### Give Hermes its own phone (autonomous control)
- **`raulvidis/hermes-android`** (GitHub) — a **bridge APK**: install it, it connects out to your
  Hermes server via WebSocket (6-char pairing code, works behind any NAT — no port forwarding/VPN),
  then controls the phone via **AccessibilityService**: *"open Instagram", "take a screenshot",
  "what apps do I have?"*. Unsigned debug APK → Play Protect will warn. Prototype, but working.
- **`rusty4444/hermes-android`** — simpler: just a **chat client** for your Hermes sessions over
  WiFi / Tailscale. Use if you only want to talk to a Hermes server running elsewhere.

### Setup shape
1. Install **Hermes Agent** from Play Store (or F-Droid fork).
2. In settings → add provider → **OpenAI-compatible** → base URL `https://api.deepseek.com`,
   key = your DeepSeek key, model `deepseek-v4-flash`.
3. (Optional) Enable the **Telegram gateway** → message your agent from the iPhone anywhere.
4. (Optional) Add the **raulvidis bridge APK** if you want it to actually tap/swipe the phone.

---

## Other "agent as an app" options (if Hermes isn't your vibe)

- **agent-loop** (Termux) — autonomous **coding** agent, uses Cursor-style `mcp.json`, takes
  `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. Developer-oriented, on-device.
- **SwiftChat** / **Chatworm** — lightweight open-source chat clients; add a **custom base URL +
  key** → point at DeepSeek/OpenAI. Not autonomous, but clean bring-your-own-key apps.
- **DroidRun / AutoDroid / AppAgent** — open-source frameworks where an LLM **autonomously drives
  Android apps** (tap/scroll/type). Research-grade, powerful, more setup.
- **Google Gemini + AppFunctions** — OS-level agentic tool use (e.g. "show my cat pics from
  Samsung Gallery"), on newer Galaxy devices. Native but Google-model locked.

### ⚠️ Reality check on the Play Store "Hermes Agent" app
Rated 4.46★ but reviews flag real issues — and the worst ones hit *your* use case:
- **404 / model-loading errors with custom API endpoints** (the DeepSeek path is the buggy part).
- **Forced-rating paywall** to unlock tools before you can judge it.
- **Scroll bug** on long replies.
- **Murky branding** — listed dev is "Hen Works", not clearly Nous Research; **4 different apps**
  share the "Hermes Agent" name. Likely a third-party wrapper. Semi-closed-source.
- **Verdict:** usable but janky; don't build on it. Use an open-source app below instead.

### 🥇 Better: open-source agent apps with good UI

- **Kai 9000** ⭐ (F-Droid, fully open source) — the "Hermes done right." Genuinely agentic:
  **40+ tools** (web search, email, **shell, task scheduling, calendar, notifications, TTS,
  location/time**) + **MCP servers**. Attach **any** provider (DeepSeek, OpenAI, Claude, Gemini,
  Groq, OpenRouter, Ollama, any OpenAI-compatible) + a **built-in free tier**. **Best fit — start here.**
- **LobeChat** (PWA) — **best UI**, ChatGPT-like, installs to Android home screen as a PWA,
  agent/plugin marketplace, RAG, voice. Self-hosted (run on the Termux node or free cloud), then
  install the PWA pointing at it.
- **ChatterUI** (open source) — clean mobile chat client, on-device **or** any API. Less agentic.
- **LibreChat / Open WebUI** (PWA) — widest provider compatibility / dev-extensible; also PWA-installable.

### Quick pick
| You want… | Use |
|-----------|-----|
| Agent **app**, attach API, tools, open source, install & go | **Kai 9000** (F-Droid) ⭐ |
| **Best UI**, don't mind self-hosting | **LobeChat** (PWA) |
| Simple clean chat client with your key | **ChatterUI** |
| The agent to **physically control** the phone | **raulvidis/hermes-android** bridge APK |
| A **coding** agent on-device | **agent-loop** (Termux) |
| ~~Play Store "Hermes Agent"~~ | ⚠️ skip — buggy custom-API path, semi-closed |

---

### Sources
- [Best Local LLM Apps for Android 2026 — PromptQuorum](https://www.promptquorum.com/power-local-llm/best-local-llm-apps-android-2026)
- [Run an LLM on Your Phone 2026 — Local AI Master](https://localaimaster.com/blog/run-llm-on-phone)
- [DeepSeek API Pricing & Models Docs](https://api-docs.deepseek.com/quick_start/pricing)
- [DeepSeek API Pricing 2026 — lmmarketcap](https://lmmarketcap.com/deepseek-api-pricing)
- [Install Ollama in Termux (2026) — Nishchay Kaushik](https://nkaushik.in/writing/install-ollama-in-termux-android-2026-guide/)
- [Termux + Ollama + Open WebUI install script](https://github.com/sw3nlab/Termux-Ollama-Openwebui)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [Hermes Agent – Android (Google Play)](https://play.google.com/store/apps/details?id=com.hermesagent.android)
- [Hermes Agent Fork (F-Droid)](https://f-droid.org/en/packages/com.mobilefork.hermesagent/)
- [raulvidis/hermes-android — autonomous phone control bridge](https://github.com/raulvidis/hermes-android)
- [rusty4444/hermes-android — chat client](https://github.com/rusty4444/hermes-android)
- [Hermes Agent alternatives — AlternativeTo](https://alternativeto.net/software/hermes-agent/)
- [Kai 9000 — F-Droid (open-source agent app, 40+ tools + MCP)](https://f-droid.org/packages/com.inspiredandroid.kai/)
- [ChatterUI — GitHub](https://github.com/Vali-98/ChatterUI)
- [LobeChat vs Open WebUI vs LibreChat comparison](https://blog.elest.io/the-best-open-source-chatgpt-interfaces-lobechat-vs-open-webui-vs-librechat/)
- [F-Droid AI Chat category](https://f-droid.org/en/categories/ai-chat/)
