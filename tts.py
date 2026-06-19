"""Cross-platform text-to-speech for spoken alerts.

Speaks the matched message after the alarm sound. Detects an available TTS engine at
startup (macOS `say`; Linux `espeak-ng`/`espeak`/`spd-say`) and no-ops if TTS is disabled
or no engine is available. `speak()` awaits completion so it doesn't stall the event loop.
"""

import asyncio
import platform
import shutil

# Cap spoken text so a very long message can't tie up the speaker.
MAX_CHARS = 1000


def pick_tts_engine() -> str | None:
    """Return the name of an available TTS CLI engine, or None."""
    if platform.system() == "Darwin":
        return "say" if shutil.which("say") else None
    for engine in ("espeak-ng", "espeak", "spd-say"):
        if shutil.which(engine):
            return engine
    return None


class Speaker:
    def __init__(
        self, enabled: bool = True, voice: str | None = None, rate: int | None = None
    ) -> None:
        self.engine = pick_tts_engine() if enabled else None
        self.voice = voice
        self.rate = rate
        if not enabled:
            print("TTS disabled.")
        elif self.engine:
            print(f"TTS engine: {self.engine}")
        else:
            print("No TTS engine found; messages will not be spoken.")

    def _command(self, text: str) -> list[str]:
        assert self.engine is not None
        cmd = [self.engine]
        if self.engine == "say":
            if self.voice:
                cmd += ["-v", self.voice]
            if self.rate:
                cmd += ["-r", str(self.rate)]
        elif self.engine in ("espeak-ng", "espeak"):
            if self.voice:
                cmd += ["-v", self.voice]
            if self.rate:
                cmd += ["-s", str(self.rate)]
        elif self.engine == "spd-say":
            cmd += ["-w"]  # block until speech finishes
            if self.voice:
                cmd += ["-l", self.voice]
            if self.rate:
                cmd += ["-r", str(self.rate)]
        cmd.append(text)
        return cmd

    async def speak(self, text: str) -> None:
        """Speak the given text and wait for it to finish."""
        if not self.engine or not text.strip():
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                *self._command(text[:MAX_CHARS]),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:  # pragma: no cover - environment dependent
            print(f"Could not speak message ({e}).")
