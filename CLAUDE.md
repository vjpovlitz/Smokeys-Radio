# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smokey's Radio is a Discord music bot built with Python that plays music from YouTube using yt-dlp with multiple extraction bypass methods. It uses discord.py 2.0+ with slash commands and an async event-driven architecture. Deployable via Docker or locally on Windows/Linux.

## Commands

```bash
# Install dependencies (automated - also downloads FFmpeg on Windows)
python scripts/setup_audio.py

# Install dependencies (manual)
pip install -r requirements.txt

# Run the bot
python bot.py

# Run with Docker
docker compose up -d

# Register slash commands via Discord API (rarely needed - bot auto-syncs on startup)
python scripts/api_register.py
```

There are no tests, linting, or CI/CD configured.

## Architecture

**Single-file bot** (`bot.py`, ~844 lines) — not using discord.py cogs/extensions.

### Project structure
```
bot.py              # Main bot entry point
requirements.txt    # Python dependencies
Dockerfile          # Container build
docker-compose.yml  # Container orchestration
.env                # Discord token (not committed)
.env.example        # Template for .env
scripts/
  setup_audio.py    # Dependency + FFmpeg installer (Windows)
  api_register.py   # Manual slash command registration via Discord API
  start.bat         # Windows launcher
logs/               # Rotating log files (not committed)
```

### Key data structures (module-level):
- `SONG_QUEUES` — dict mapping guild IDs to `deque` of `(url, title, thumbnail, duration)` tuples
- `BYPASS_STATS` — tracks extraction success/failure rates per method
- `USER_AGENTS` — rotating user agent strings for request spoofing

### Extraction system
Five tiered bypass methods tried in order: `standard` → `mobile` → `embed` → `music` → `alternative`. Each configures yt-dlp differently (different player clients, user agents, geo-bypass settings). The `try_extraction_methods()` function iterates through them; `_extract()` runs the actual yt-dlp call and updates `BYPASS_STATS`.

Blocking yt-dlp calls run in executor threads via `search_ytdlp_async()`.

### Audio playback
FFmpeg with Opus codec at 128kbps, 50% volume. Auto-advances queue on song finish. 5-minute idle auto-disconnect. FFmpeg path resolution: checks `bin\ffmpeg\ffmpeg.exe` → winget install path → system PATH.

### Slash commands
`/play` (with autocomplete), `/skip`, `/pause`, `/resume`, `/stop`, `/queue`, `/stats`, `/test`. Prefix commands `!sync` and `!resync` exist for manual command syncing.

## Environment

Requires a `.env` file with `DISCORD_TOKEN=<token>`. The bot generates `bot_invite.txt` and logs to `logs/smokeys_radio.log` (rotating, 10MB, 5 backups).

### Key dependencies
- `discord.py[voice]` — includes `davey` package required for Discord's Dave protocol (voice E2EE)
- `PyNaCl` — voice encryption
- `yt-dlp` — YouTube extraction
- `FFmpeg` — audio transcoding (installed via apt in Docker, setup_audio.py on Windows)

## Code Conventions

- PEP 8 style
- snake_case for functions/variables, UPPER_CASE for module-level constants
- Rich Discord Embeds for all user-facing responses (color-coded: green=playing, blue=queued, orange=warning)
- Logging: INFO for operations, WARNING for non-fatal method failures, ERROR with `exc_info=True` for critical failures
