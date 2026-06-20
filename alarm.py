"""Cross-platform alarm sound playback.

Detects an available CLI audio player at startup and plays a sound file, falling back to
the terminal bell if no player or sound file is available. `play()` awaits completion so
callers can sequence follow-up audio (e.g. text-to-speech) after the alarm.
"""

import asyncio
import os
import platform
import shutil
import sys


def pick_audio_player(override: str | None = None) -> list[str] | None:
    """Return the argv prefix for an available CLI audio player, or None.

    `override` (e.g. "aplay -q" to force ALSA on a headless box) takes precedence when its
    command is on PATH; otherwise auto-detect by platform.
    """
    if override:
        cmd = override.split()
        if cmd and shutil.which(cmd[0]):
            return cmd
        print(f"Configured audio_player {override!r} not found; auto-detecting instead.")
    system = platform.system()
    if system == "Darwin":
        candidates = [["afplay"]]
    else:  # Linux and other POSIX
        candidates = [
            ["paplay"],
            ["aplay", "-q"],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
            ["play", "-q"],  # sox
        ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            return cmd
    return None


class Alarm:
    def __init__(self, sound_path: str, player: str | None = None) -> None:
        self.sound_path = sound_path
        self.player = pick_audio_player(player)
        self._warned = False
        if self.player:
            print(f"Audio player: {' '.join(self.player)}")
        else:
            print("No audio player found; will use terminal bell as fallback.")
        if not os.path.exists(sound_path):
            print(f"Warning: alarm sound not found at {sound_path}; using terminal bell.")
            self.player = None

    async def play(self) -> None:
        """Play the alarm sound and wait for it to finish, or ring the terminal bell."""
        if self.player:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *self.player,
                    self.sound_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
                return
            except Exception as e:  # pragma: no cover - environment dependent
                if not self._warned:
                    print(f"Could not play sound ({e}); falling back to terminal bell.")
                    self._warned = True
        sys.stdout.write("\a")
        sys.stdout.flush()
