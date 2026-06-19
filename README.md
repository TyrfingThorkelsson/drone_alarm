# drone_alarm

A Telegram **user-bot** that monitors public channels for keywords. When a new message in a
watched channel matches one of your regex keywords, it **plays an alarm sound** and **prints
the message** to the console.

It uses the MTProto protocol via [Telethon](https://docs.telethon.dev) with your own Telegram
account — this is the only way to read arbitrary public channels programmatically (the regular
Bot API only sees channels where the bot is an admin). Runs on **macOS and Linux**.

## Setup

1. Get your API credentials from <https://my.telegram.org> → *API development tools*
   (you'll get an `api_id` and `api_hash`).

2. Install dependencies (Python 3.8+):

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create your config from the template and fill it in:

   ```bash
   cp config.example.yaml config.yaml
   ```

   Edit `config.yaml`: set `api_id`, `api_hash`, `phone`, the `channels` to watch, and the
   `keywords` (regex). `config.yaml` is gitignored so your credentials stay local.

## Run

```bash
python drone_alarm.py
```

On the first run Telegram sends a login code to your account — enter it at the prompt (and your
2FA password if you have one). The login is cached in a `.session` file, so subsequent runs start
without prompting. Leave the script running; it prints an alarm and plays a sound on each match.

## Linting & type checking

```bash
pip install -r requirements-dev.txt
./lint.sh             # runs ruff check, ruff format --check, and mypy
```

Or run the tools individually:

```bash
ruff check .          # lint
ruff format .         # auto-format (use --check in CI)
mypy drone_alarm.py alarm.py   # type-check
```

Config lives in `pyproject.toml`. All functions are type-annotated.

## Configuration reference

| Key             | Meaning                                                                 |
| --------------- | ----------------------------------------------------------------------- |
| `api_id`/`api_hash` | Telegram API credentials from my.telegram.org.                      |
| `phone`         | Your account phone number (one-time login).                             |
| `session`       | Name of the local `.session` file.                                      |
| `channels`      | List of public channels (`@username`, t.me link, or numeric id).        |
| `keywords`      | List of regex patterns matched against each message.                    |
| `case_sensitive`| `false` (default) makes keyword matching case-insensitive.              |
| `alarm_sound`   | Path to the alarm sound; defaults to the bundled `alarm.wav`.           |
| `auto_join`     | If `true`, join the listed channels on startup.                         |

## Audio

The bundled `alarm.wav` plays through whichever CLI player your OS has:
`afplay` on macOS; `paplay`, `aplay`, `ffplay`, or `play` (sox) on Linux. If none is found, it
falls back to the terminal bell. Sanity-check playback independently of Telegram:

```bash
afplay alarm.wav        # macOS
paplay alarm.wav        # Linux (PulseAudio)
```

## Note

Automating a personal account sits in a gray area of Telegram's Terms of Service. Use a dedicated
account and reasonable behavior. This tool only reads messages — it does not post.
