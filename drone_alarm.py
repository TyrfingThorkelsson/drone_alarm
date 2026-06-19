#!/usr/bin/env python3
"""Telegram user-bot that watches public channels for keywords and raises an alarm.

Reads new messages from a configured list of public channels, matches each against
regex keywords, and on a match plays an alarm sound and prints the message to the
console. Uses the MTProto protocol (Telethon) with a real user account, which is the
only way to read arbitrary public channels programmatically.
"""

import asyncio
import os
import re
import sys
from datetime import datetime
from typing import Any

import yaml
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

from alarm import Alarm

Config = dict[str, Any]
Pattern = tuple[str, re.Pattern[str]]

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.yaml")
EXAMPLE_PATH = os.path.join(HERE, "config.example.yaml")


def load_config() -> Config:
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"Config not found at {CONFIG_PATH}.\n"
            f"Copy the template first:  cp {EXAMPLE_PATH} {CONFIG_PATH}\n"
            "then fill in your api_id / api_hash / phone."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = ["api_id", "api_hash", "phone", "channels", "keywords"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        sys.exit(f"config.yaml is missing required key(s): {', '.join(missing)}")
    return cfg


def compile_patterns(keywords: list[str], case_sensitive: bool) -> list[Pattern]:
    flags = 0 if case_sensitive else re.IGNORECASE
    patterns: list[Pattern] = []
    for i, kw in enumerate(keywords):
        try:
            patterns.append((kw, re.compile(kw, flags)))
        except re.error as e:
            sys.exit(f"Invalid regex in keywords[{i}] {kw!r}: {e}")
    return patterns


def format_alert(chat: Any, matched: list[str], text: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat)
    bar = "=" * 60
    return (
        f"\n{bar}\n"
        f"[{ts}] ALARM  channel: {name}\n"
        f"matched: {', '.join(matched)}\n"
        f"{bar}\n"
        f"{text}\n"
        f"{bar}"
    )


async def auto_join(client: TelegramClient, channels: list[Any]) -> None:
    for ch in channels:
        try:
            entity = await client.get_entity(ch)
            await client(JoinChannelRequest(entity))
        except Exception as e:
            print(f"Could not join {ch}: {e} (continuing)")


async def main() -> None:
    cfg = load_config()
    patterns = compile_patterns(cfg["keywords"], cfg.get("case_sensitive", False))

    sound_path = cfg.get("alarm_sound", "alarm.wav")
    if not os.path.isabs(sound_path):
        sound_path = os.path.join(HERE, sound_path)
    alarm = Alarm(sound_path)

    channels = cfg["channels"]
    client = TelegramClient(cfg["session"], int(cfg["api_id"]), cfg["api_hash"])
    await client.start(phone=cfg["phone"])

    if cfg.get("auto_join", False):
        print("Joining channels...")
        await auto_join(client, channels)

    @client.on(events.NewMessage(chats=channels))
    async def handler(event: events.NewMessage.Event) -> None:
        text = event.raw_text or ""
        matched = [kw for kw, pat in patterns if pat.search(text)]
        if matched:
            alarm.trigger()
            chat = await event.get_chat()
            print(format_alert(chat, matched, text))

    print(f"Listening on {len(channels)} channel(s) for {len(patterns)} keyword(s).")
    print("Press Ctrl+C to stop.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
