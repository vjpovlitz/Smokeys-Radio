# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smokey's Radio is a Discord music bot built with Python that plays music from YouTube using yt-dlp with multiple extraction bypass methods. It uses discord.py 2.x with slash commands and an async event-driven architecture. Optional persistent stats are backed by SQL Server. Deployable via Docker or locally on Windows / Linux / macOS.

## Commands

```bash
# Install dependencies (automated, also downloads FFmpeg on Windows)
python scripts/setup_audio.py

# Install dependencies (manual)
pip install -r requirements.txt

# Run the bot
python bot.py

# Run with Docker
docker compose up -d

# Register slash commands via Discord API (rarely needed; bot auto-syncs on startup)
python scripts/api_register.py

# Inspect the stats database (read-only CLI)
python scripts/inspect_db.py
```

There are no tests, linting, or CI/CD configured.

## Architecture

**Single-file bot** (`bot.py`): not using discord.py cogs / extensions. The only other module is `db.py`, which is the SQL Server persistence layer.

### Project structure
```
bot.py               # Main bot entry point
db.py                # SQL Server persistence layer (fail-soft)
requirements.txt     # Python dependencies
Dockerfile           # Container build
docker-compose.yml   # Container orchestration
.env                 # Discord token + DB env vars (not committed)
.env.example         # Template for .env
scripts/
  schema.sql         # Idempotent SQL Server schema
  inspect_db.py      # Read-only CLI inspector for plays / commands / top lists
  setup_audio.py     # Dependency + FFmpeg installer (Windows)
  api_register.py    # Manual slash command registration via Discord API
  start.bat          # Windows launcher
logs/                # Rotating log files (not committed)
```

### Key data structures (module-level)
- `SONG_QUEUES`: dict mapping guild IDs to a `deque` of queued tracks. Each entry is a 15-tuple. Indices 0-3 (`audio_url, title, thumbnail, duration_str`) are the legacy fields; indices 4-14 carry the metadata needed by `db.log_play()` (youtube_id, duration_seconds, source, extraction_method, requester id / name / display / guild / guild_name, uploader, search_query).
- `BYPASS_STATS`: tracks extraction success / failure rates per method.
- `USER_AGENTS`: rotating user agent strings for request spoofing.

### Extraction system
Five tiered bypass methods tried in order: `standard`, `mobile`, `embed`, `music`, `alternative`. Each configures yt-dlp differently (different player clients, user agents, geo-bypass settings). `try_extraction_methods()` iterates through them; `_extract()` runs the actual yt-dlp call and updates `BYPASS_STATS`.

Blocking yt-dlp calls run in executor threads via `search_ytdlp_async()`.

### Audio playback
FFmpeg with Opus codec at 128 kbps, 50% volume. Auto-advances queue on song finish. 5-minute idle auto-disconnect. FFmpeg path resolution: checks `bin\ffmpeg\ffmpeg.exe`, then the winget install path, then system PATH.

When a song starts playing, `play_next_song` awaits `db.log_play()` to capture a `play_id`. The `after_play` callback computes the outcome (`completed` if listened >= 95% of duration, `skipped` otherwise, `error` if FFmpeg returned an error) and schedules `db.update_play_outcome()` via `asyncio.run_coroutine_threadsafe`.

### Slash commands
`/play` (with autocomplete), `/skip`, `/pause`, `/resume`, `/stop`, `/queue`, `/stats`, `/test`, `/topsongs`, `/topusers`, `/myhistory`. Prefix commands `!sync` and `!resync` exist for manual command syncing.

### Database (`db.py`, SQL Server)
Persistent stats live in a SQL Server database (`SmokeysRadio`). Schema in `scripts/schema.sql` (idempotent, safe to re-run).

- Connection is built from env vars (`SMOKEYS_DB_SERVER`, `SMOKEYS_DB_NAME`, `SMOKEYS_DB_DRIVER`, `SMOKEYS_DB_TRUSTED`, `SMOKEYS_DB_USER`, `SMOKEYS_DB_PASSWORD`), or supplied directly via `SMOKEYS_DB_CONN`. Defaults: `localhost` / `SmokeysRadio` with Windows authentication. `SMOKEYS_DB_DISABLED=true` is a kill switch.
- `db.init()` runs in `on_ready`. If the connection fails, the module sets `_enabled = False` and every helper becomes a no-op (or returns an empty list / `None`). DB outages must never break playback.
- pyodbc connection pooling is enabled (`pyodbc.pooling = True`).
- Writers dispatch blocking pyodbc calls via `loop.run_in_executor` to match the `search_ytdlp_async` pattern.
- Upserts use `MERGE`. The songs MERGE has `SET NOCOUNT ON` so the followup `SELECT song_id` works through pyodbc; the `plays` insert uses `OUTPUT inserted.play_id` to capture the new id in one round trip.
- Public writers: `log_command`, `log_play` (returns `play_id`), `update_play_outcome`. Public readers: `top_songs`, `top_users`, `user_history`, `totals`.
- Period filters in `_PERIOD_FILTERS` define `day` / `week` / `month` / `all` windows for the read functions.

## Environment

Requires a `.env` file with `DISCORD_TOKEN=<token>`. Optional DB env vars are documented in `.env.example`. The bot generates `bot_invite.txt` and logs to `logs/smokeys_radio.log` (rotating, 10 MB, 5 backups).

### Key dependencies
- `discord.py[voice]`: includes `davey`, required for Discord's Dave protocol (voice E2EE)
- `PyNaCl`: voice encryption
- `yt-dlp`: YouTube extraction
- `pyodbc`: SQL Server connectivity (required only if stats are enabled)
- `FFmpeg`: audio transcoding (installed via apt in Docker, `setup_audio.py` on Windows)

## Code Conventions

- PEP 8 style
- snake_case for functions / variables, UPPER_CASE for module-level constants
- Rich Discord Embeds for all user-facing responses (color-coded: green = playing, blue = queued, orange = warning, gold = top songs, purple = top users)
- Logging: INFO for operations, WARNING for non-fatal method failures, ERROR with `exc_info=True` for critical failures
- No em dashes in user-facing text or docs (project preference)
