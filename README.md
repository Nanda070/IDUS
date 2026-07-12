<div align="center">

# IDUS

**A fully local voice assistant for the home — your own Jarvis, built from open-source pieces,
running on hardware you control.**

No cloud APIs. No subscriptions. Nothing leaves the house except web searches you ask it to make.

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Local-only](https://img.shields.io/badge/cloud%20dependencies-zero-3F7D5E)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%2F%20Qwen2.5-1a1a1a)
![Status](https://img.shields.io/badge/status-active%20development-0A84FF)

</div>

---

Talk to it out loud, or through Telegram from anywhere. It remembers what you tell it, sets
reminders and recurring routines on its own, and asks before doing anything that touches the
outside world.

## Contents

- [Why local?](#why-local)
- [What it can do today](#what-it-can-do-today)
- [What it can't do yet](#what-it-cant-do-yet)
- [Architecture](#architecture)
- [Stack](#stack)
- [Getting started](#getting-started)
- [Roadmap status](#roadmap-status)
- [A note on scope](#a-note-on-scope)

## Why local?

Because a home assistant that phones a cloud API for every sentence is a home assistant that
stops working when your internet does, and one whose "brain" belongs to someone else. Every
piece of IDUS — speech recognition, the language model, text-to-speech, web search — runs on
hardware you control.

## What it can do today

**Voice loop** — say "Hey Jarvis," wait for the pause, then talk. IDUS listens, transcribes,
thinks, and answers out loud, in Russian or English (it follows whichever language you use,
mid-sentence code-switching included).

**A real conversational brain** — backed by a local LLM (Ollama), with a personality that
doesn't lecture you and doesn't pretend to know things it doesn't. If it needs a fact, it
looks it up; if it mishears you, it says so instead of guessing.

**Tool use** — the model doesn't just talk, it acts:

| | |
|---|---|
| Time, date, calculator, timers | Web search — self-hosted, no API keys, no tracking |
| Shopping lists & voice notes | Reminders — survive a restart, reach you by voice *or* Telegram |
| Automation engine — recurring rules, not one-off answers | Cooking assistant — step-by-step, with per-step timers |
| On-the-fly translation | Jokes and trivia on request |

The bottom row needed zero new code — just a model doing what models do.

**Memory that grows on its own** — long-term facts persist across restarts, and once a day
IDUS quietly reviews the last day's conversations, writes itself a short summary, and picks
out anything worth remembering that you never explicitly asked it to save.

**Knows who's talking** — voice-based speaker identification, so it can recognize you (and
anyone else you enroll) by the sound of your voice.

**A second front door** — a Telegram bot wired into the exact same brain, text or voice
messages, so you can talk to your home from anywhere. Only responds to you.

**An agentic core with real guardrails** — before doing anything with consequences (sending a
message, building a shopping cart on a real account), it stops and asks "yes or no?" — and
your answer is understood by meaning, not by matching a fixed list of keywords. Some actions
(placing an actual order, for instance) aren't just gated behind confirmation — the code to
complete them simply doesn't exist. That's a design choice, not a missing feature.

## What it can't do yet

| Not yet | Why |
|---|---|
| Control smart home devices | No hardware purchased yet — next once it is |
| Media on the TV, presence awareness, reliable multi-step chains | Same hardware decision, or a bigger local model than a modest GPU can run |
| Place a real food order | Cart-building works end-to-end; the delivery platform's bot detection blocks automated login, and defeating that wasn't a line worth crossing — it stops at "cart's ready, go finish it" |
| Message your contacts as you | Sending *as you* to someone who's never messaged the bot needs your own Telegram account automated — a deliberate, not-yet-made call |

## Architecture

```
voice/     wake word · voice activity detection · speech-to-text · text-to-speech · speaker ID
brain/     the LLM loop, tool-calling, confirmation gate, nightly reflection
tools/     everything the model can actually do — one file per capability
memory/    SQLite-backed facts, reminders, automations, episodes, shopping list, notes
scripts/   entry points — the voice loop, the Telegram bot, and test/setup utilities
config/    downloaded models and voices, local service configuration
```

> The split between `voice/` (how you talk to it) and `brain/` (what it thinks) is deliberate —
> the Telegram bot is a second front door onto the *same* brain, not a separate assistant, and
> a future phone-companion channel can be added the same way without touching the core.

## Stack

| Piece | What it does | Why this one |
|---|---|---|
| [Ollama](https://ollama.com) + Qwen2.5 7B | The language model | Runs fully local, strong at Russian |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text | Fast, accurate enough, runs on CPU |
| [Silero TTS](https://github.com/snakers4/silero-models) | Text-to-speech | Natural-sounding, fully local |
| [Silero VAD](https://github.com/snakers4/silero-vad) | Voice activity detection | Small, fast, reliable |
| [openWakeWord](https://github.com/dscripka/openWakeWord) | Wake word detection | Trainable, no cloud account needed |
| [SpeechBrain](https://speechbrain.github.io) | Speaker identification | Pretrained ECAPA-TDNN embeddings |
| [SearXNG](https://docs.searxng.org) | Web search | Self-hosted, no API keys |
| [python-telegram-bot](https://docs.python-telegram-bot.org) | Remote access channel | Mature async Telegram API wrapper |
| SQLite | Everything persistent | One file, zero setup, plenty for one household |

## Getting started

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com), and
[Docker](https://www.docker.com/) (for the search backend).

```bash
uv sync
ollama pull qwen2.5:7b
docker compose up -d          # starts the SearXNG search backend
cp .env.example .env          # fill in your Telegram bot token, if you want that channel
```

Run the voice assistant:

```bash
uv run scripts/jarvis_loop.py
```

Run the Telegram bot (separately, same brain):

```bash
uv run scripts/telegram_loop.py
```

Individual `scripts/*_test.py` files exercise each component (VAD, STT, TTS, wake word,
memory, reminders, automations) in isolation — useful when something's not behaving and you
want to know which layer to blame.

## Roadmap status

<div align="center">

![Done](https://img.shields.io/badge/-9%20done-3F7D5E) ![Partial](https://img.shields.io/badge/-5%20partial-A8781F) ![Blocked](https://img.shields.io/badge/-2%20blocked%20on%20hardware-8B5E4A)

</div>

<details>
<summary><b>Full stage-by-stage breakdown</b></summary>
<br>

| # | Stage | Status |
|---|---|---|
| 0 | Environment & tooling | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 1 | Voice loop (wake word → STT → TTS) | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 2 | Local LLM connection | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 3 | Tool-calling | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 4 | Internet access (search) | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 5 | Long-term memory | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 6 | Smart home foundation | ![blocked](https://img.shields.io/badge/-blocked%20on%20hardware-8B5E4A) |
| 7 | Reminders, media, scenes | ![partial](https://img.shields.io/badge/-partial-A8781F) reminders done; media/scenes need devices |
| 8 | UX & reliability | ![partial](https://img.shields.io/badge/-partial-A8781F) latency + degradation done; barge-in needs a headset |
| 9 | Security & privacy | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 10 | Packaging & autostart | ![blocked](https://img.shields.io/badge/-blocked%20on%20hardware-8B5E4A) Ubuntu-specific |
| 11 | Remote access (Telegram) | ![done](https://img.shields.io/badge/-done-3F7D5E) |
| 12 | Agentic core | ![partial](https://img.shields.io/badge/-partial-A8781F) confirmation gate done; full planner needs a bigger model |
| 13 | Media stack | ![blocked](https://img.shields.io/badge/-blocked%20on%20hardware-8B5E4A) |
| 14 | External actions (ordering, messaging) | ![partial](https://img.shields.io/badge/-partial-A8781F) owner-messaging done; third-party & ordering blocked |
| 15 | Memory 2.0 & proactivity | ![partial](https://img.shields.io/badge/-partial-A8781F) episodes + reflection done; procedural memory needs devices |

Everything marked **done** has been verified against real hardware and a real voice, not just
tested in isolation.

</details>

## A note on scope

A few things were deliberately **not** built, on purpose, not by oversight:

- No feature here will ever complete a payment or place a real order — that boundary is
  structural in the code, not a setting you can flip
- No automation here defeats another service's bot protection — when that's the only path
  forward, the feature stops at "here's what I found, you finish it"

Local-first and user-controlled cuts both ways: it means no one else's cloud can pull the plug
on your assistant, and it means your assistant doesn't get to cut corners on your behalf
either.
