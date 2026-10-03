# Autonomous Agent on Android — heartbeat, tools, memory (not just a chatbot)

**Goal (formalized):** a *persistent, self-hosted* AI agent with a **heartbeat** (wakes up on a
schedule and acts on its own), **tool use**, **persistent memory**, and **messaging gateways** —
running **on the Android phone itself** (the way Hermes normally runs on a VPS), with my own LLM
API attached. Is **Kai 9000** the only option?

**Answer: No — there are 3 real paths.** Ranked for "runs on my Android + heartbeat + tools":

---

## 🥇 Path 1 — Kai 9000 (best *app* fit, just works)

A real native Android app (Kotlin Multiplatform), open source (F-Droid), purpose-built for exactly
this. **This is the closest thing to "Hermes as an app."**

- **Heartbeat:** built-in — "doesn't sleep," self-checks **every 30 min during active hours
  (8am–10pm)**, reviewing pending tasks/emails/trends even when you're not chatting.
- **Scheduling:** recurring tasks via **cron expressions**.
- **40+ tools:** web search, email, **shell commands**, calendar, notifications, TTS, location/time,
  **MCP servers**.
- **Memory:** persistent across conversations.
- **Providers:** 11+ (DeepSeek, OpenAI, Claude, Gemini, Groq, OpenRouter, Ollama…) + free tier.
- **Why it beats Termux-Hermes on a phone:** it's a *real app* with proper Android lifecycle
  handling, so it survives Android's aggressive power management far better than a Termux process.
- **Setup:** install from F-Droid → add your API key → enable the tools + heartbeat you want. Done.

> Self-described as "an OpenClaw alternative in your pocket." If you want one thing that runs on the
> phone with a heartbeat and tools **without fighting the OS**, start here.

---

## 🥈 Path 2 — The *actual* Hermes Agent, on the phone via Termux

If you specifically want the **real Nous Research Hermes runtime** (its self-learning loop, skill
creation, the genuine article) living on the Samsung — it's officially supported.

- **Support level:** **Tier 2** (best-effort; `main` can break Termux at times).
- **Requirements:** Termux from **F-Droid** (not Play Store), Android 11+, ~5GB storage, 4GB+ RAM.

### Install (Termux-aware one-liner)
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```
It auto-detects Termux, uses a curated `.[termux]` extra, and links `hermes` onto your PATH.

### Setup for unattended/autonomous use
```bash
hermes setup --portal        # auto-refreshing OAuth — best for always-on
hermes gateway setup         # connect Telegram/Discord → talk to it from the iPhone
```
(Or point it at DeepSeek/OpenAI instead of the Nous portal.)

### The heartbeat = built-in cron scheduler + gateway daemon
The **gateway** drives the loop — it ticks the scheduler **every 60s** and runs due jobs in
isolated agent sessions.
```bash
hermes cron create "every 1h" "Heartbeat: read state, check services, do at most 1 safe action, report" --name heartbeat
# script-only watchdog (no LLM), only speaks up when something's wrong:
hermes cron create "every 5m" --no-agent --script watchdog.sh --deliver telegram --name watchdog
```
> "Agent-heartbeat" pattern (from the official Paperika example): every tick, wake the agent, give
> it context+tools, let it inspect state, take **at most 1–2 bounded actions**, verify, report.
> Note: cron sessions **can't create more cron jobs** (runaway-loop guard).

### ⚠️ The hard part: Android hates background processes
No systemd, aggressive power manager freezes locked-screen processes. Keep-alive recipe:
```bash
termux-wake-lock                          # ask Android to not freeze it
tmux new -s hermes 'hermes gateway run'   # survives shell close;  reattach: tmux attach -t hermes
```
Keep the phone **on a charger**, disable battery optimization for Termux. **Reboot = manual
restart** (no init system). This is why it's "best-effort" on a phone.

- Community one-liner installer: **`AbuZar-Ansarii/Hermes-Agent-On-Android`** (tracks fast-moving
  upstream — official installer is more reliable).

---

## 🥉 Path 3 — Hermes/Letta on a $5 VPS, phone as the remote (most reliable)

You said "Hermes runs on a VPS — I want it on my Android." Fair. But be aware of the tradeoff:
the VPS path is what Hermes is *designed* for, and it sidesteps every Android limitation.

- Run Hermes (or **Letta/MemGPT**) on a **$5 always-on VPS** → 24/7, survives reboots, real init.
- Connect the **Telegram/Discord gateway** → talk to it from the iPhone **and** the Samsung, anywhere.
- The phone becomes the *interface*, not the host. Nothing to keep alive on the phone.
- **Letta (MemGPT)** = the other big self-hosted agent: 3-tier OS-style memory, native heartbeat in
  the *legacy* architecture (⚠️ deprecated in Letta V1 — needs manual prompting there). Apache-2.0.

> If reliability ever matters more than "it's literally on my phone," this is the grown-up answer.
> Hybrid: **Kai 9000 on the phone for daily use + a VPS agent for the always-on 24/7 jobs.**

---

## Decision table

| What you want most | Pick |
|--------------------|------|
| A real **app** on Android, heartbeat + tools, minimal fuss | **Kai 9000** ⭐ |
| The **authentic Hermes** runtime physically on the Samsung | **Hermes in Termux** (wakelock+tmux+charger) |
| **Rock-solid 24/7**, reach it from any phone | **Hermes/Letta on a $5 VPS** + Telegram |
| Cloud, zero-setup, Google-hosted proactivity | Gemini Spark / Scheduled Actions |

## Honest caveats
- **Android is a hostile host** for 24/7 agents (no systemd, power-manager kills). An *app* (Kai)
  handles this better than a *Termux process* (Hermes).
- **Heartbeat = cron + gateway daemon**, not magic. Both Kai and Hermes implement it that way.
- **Shell-access agents = real risk.** These agents can run shell commands; keep API keys in a
  `.env`, don't give an autonomous loop destructive tools without guardrails.
- **No firsthand Reddit threads found** for the exact Hermes-on-Android-heartbeat combo — this is
  from official Nous docs, GitHub issues (#15400 requests first-class heartbeat jobs), and
  community guides. Treat Termux-Hermes as bleeding-edge.

## Recommended move
1. **Today:** install **Kai 9000** (F-Droid) → add DeepSeek key → turn on heartbeat + a couple of
   tools (web search, notifications, task scheduling). See if it does what you want.
2. **If you want the real Hermes on-device:** do the Termux install + wakelock/tmux keep-alive.
3. **If it needs to be bulletproof 24/7:** move the agent to a $5 VPS, keep the phone as the remote.

---

### Sources
- [NousResearch/hermes-agent (GitHub)](https://github.com/nousresearch/hermes-agent)
- [Hermes Agent — Android/Termux docs](https://hermes-agent.nousresearch.com/docs/getting-started/termux)
- [Hermes Agent — Scheduled Tasks (Cron)](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [Feature request: first-class agent heartbeat jobs (issue #15400)](https://github.com/NousResearch/hermes-agent/issues/15400)
- [Self-host Hermes Agent on a VPS](https://www.virtua.cloud/learn/en/tutorials/self-host-hermes-agent-vps)
- [Hermes-Agent-On-Android (AbuZar-Ansarii)](https://github.com/AbuZar-Ansarii/Hermes-Agent-On-Android)
- [Kai 9000 — F-Droid](https://f-droid.org/en/packages/com.inspiredandroid.kai/)
- [Kai 9000 — Docs](https://kai9000.com/docs/)
- [Letta (MemGPT) — GitHub](https://github.com/letta-ai/letta)
- [Agent memory 2026: Mem0/Letta/Zep/Hermes compared](https://www.innobu.com/en/articles/agent-memory-2026-mem0-letta-zep-hermes-openclaude-comparison.html)
