# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telegram **user-bot** (single-file, [drone_alarm.py](drone_alarm.py)) that listens to public
channels and raises an alarm on regex keyword matches: it plays a sound and prints the matched
message to the console. Built for monitoring Russian-language channels but language-agnostic.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # then fill in api_id/api_hash/phone, channels, keywords

# Run (first run prompts for the Telegram login code interactively)
python drone_alarm.py

# Regenerate the bundled alarm sound (stdlib only, no deps)
# see the wave-based generator pattern; ~1s 880Hz beep, 16-bit mono PCM

# Sanity-check audio without Telegram
afplay alarm.wav     # macOS
paplay alarm.wav     # Linux

# Linting & type checking (config in pyproject.toml)
pip install -r requirements-dev.txt
./lint.sh                        # ruff check + ruff format --check + mypy
pre-commit install               # run the same checks automatically on git commit
```

There is no test suite or build step. All functions are type-annotated; keep new code typed so
`mypy` stays clean (`disallow_untyped_defs` is on). To smoke-test helpers without a live Telegram
connection, import the module and call `pick_audio_player()` / `compile_patterns()` /
`format_alert()` directly — `main()` is the only part that needs credentials.

## Architecture & key constraints

- **Must use MTProto (Telethon), not the Bot API.** Reading arbitrary public channels is impossible
  with the Bot API (bots only see channels they administer). The script logs in as a real user
  account via `TelegramClient`, caching auth in a `<session>.session` file after the one-time code
  prompt. Do not propose switching to `python-telegram-bot` or the Bot API — it cannot satisfy the
  core requirement.
- **Event-driven loop.** `@client.on(events.NewMessage(chats=channels))` fires per message;
  the handler matches `event.raw_text` against precompiled regex patterns, then `await`s
  `Alarm.play()` followed by `Speaker.speak()` so the message is spoken *after* the beep.
  `auto_join` (config) subscribes the account to channels on startup so updates are received.
- **Audio/TTS are split into modules** ([alarm.py](alarm.py), [tts.py](tts.py)), each detecting a
  CLI tool via `shutil.which` and degrading gracefully. `Alarm` (`pick_audio_player`): `afplay` on
  macOS; `paplay`/`aplay`/`ffplay`/`play` on Linux, falling back to the terminal bell (`\a`).
  `Speaker` (`pick_tts_engine`): `say` on macOS; `espeak-ng`/`espeak`/`spd-say` on Linux, no-op if
  disabled or absent. Both use `asyncio.create_subprocess_exec` + `await proc.wait()` — they run on
  the event loop but the handler awaits them so playback is ordered (beep → speech).
- **Config-driven, fail-fast.** `load_config()` requires `config.yaml` (gitignored) and validates
  required keys; `compile_patterns()` exits with the offending index on an invalid regex. Keyword
  matching is case-insensitive unless `case_sensitive: true`.

## Conventions

- Secrets live only in `config.yaml` (gitignored); `config.example.yaml` is the committed template.
  Never commit `config.yaml` or `*.session`.
- Keep it dependency-light: audio uses system CLI players rather than a Python audio package, and
  `alarm.wav` is generated with the stdlib `wave` module rather than shipping a binary asset.
