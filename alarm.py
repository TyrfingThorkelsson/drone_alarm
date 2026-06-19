"""Cross-platform alarm sound playback.

Detects an available CLI audio player at startup and plays a sound file non-blockingly,
falling back to the terminal bell if no player or sound file is available.
"""

import os
import platform
import shutil
import subprocess
import sys


def pick_audio_player() -> list[str] | None:
    """Return the argv prefix for an available CLI audio player, or None."""
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
    def __init__(self, sound_path: str) -> None:
        self.sound_path = sound_path
        self.player = pick_audio_player()
        self._warned = False
        if self.player:
            print(f"Audio player: {' '.join(self.player)}")
        else:
            print("No audio player found; will use terminal bell as fallback.")
        if not os.path.exists(sound_path):
            print(f"Warning: alarm sound not found at {sound_path}; using terminal bell.")
            self.player = None

    def trigger(self) -> None:
        if self.player:
            try:
                subprocess.Popen(
                    self.player + [self.sound_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception as e:  # pragma: no cover - environment dependent
                if not self._warned:
                    print(f"Could not play sound ({e}); falling back to terminal bell.")
                    self._warned = True
        sys.stdout.write("\a")
        sys.stdout.flush()
