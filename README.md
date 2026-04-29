# Smokey's Radio

A Discord music bot that streams audio from YouTube using yt-dlp with multiple
extraction bypass methods, plus optional persistent stats backed by SQL Server.
Built on discord.py 2.x with slash commands, autocomplete search, and an
async event-driven architecture.

## Features

- Play music from YouTube search or direct URLs (slash command with autocomplete)
- Five-tier extraction bypass system: standard, mobile, embed, music, alternative
- Queue management with rich Discord embeds (now playing, queued, etc.)
- Bypass success/failure statistics per method
- Optional SQL Server stats: top songs, top listeners, personal play history
- Auto-disconnect after 5 minutes of inactivity
- Rotating log files (10 MB, 5 backups)
- Runs locally (Windows / Linux / macOS) or in Docker

## Project Structure

```
smokeys-radio/
  bot.py                 # Main bot (single-file)
  db.py                  # SQL Server persistence layer (fail-soft)
  requirements.txt       # Python dependencies
  Dockerfile             # Container build
  docker-compose.yml     # Container orchestration
  .env.example           # Template for .env (Discord token + DB env vars)
  scripts/
    schema.sql           # Idempotent SQL Server schema (creates SmokeysRadio DB)
    inspect_db.py        # Read-only CLI inspector for plays / commands / top lists
    setup_audio.py       # Dependency + FFmpeg installer (Windows)
    api_register.py      # Manual slash command registration via Discord API
    start.bat            # Windows launcher
  logs/                  # Rotating log files (gitignored)
```

## Prerequisites

- Python 3.10+ (for local installs) or Docker
- FFmpeg
- A Discord bot token. Create one at the
  [Discord Developer Portal](https://discord.com/developers/applications).
- (Optional) SQL Server with the ODBC Driver 17 (or 18) for stats logging

### Creating a Discord Bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and give it a name.
3. Go to **Bot**, click **Reset Token**, and copy the token.
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
5. Save changes.

## Setup

### Option 1: Docker (recommended for servers)

```bash
git clone https://github.com/yourusername/smokeys-radio.git
cd smokeys-radio

# Configure your token
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN

# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The Docker image installs FFmpeg and all Python dependencies. Logs are mounted
to `./logs/` on the host.

### Option 2: Local (Windows)

1. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/yourusername/smokeys-radio.git
   cd smokeys-radio
   pip install -r requirements.txt
   ```
   Or use the automated setup, which also downloads FFmpeg:
   ```bash
   python scripts/setup_audio.py
   ```

2. Configure your token:
   ```bash
   cp .env.example .env
   # Edit .env and add your DISCORD_TOKEN
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```
   Or double-click `scripts/start.bat`.

4. Invite the bot using the link saved to `bot_invite.txt` after first run.

### Option 3: Local (Linux / macOS)

```bash
git clone https://github.com/yourusername/smokeys-radio.git
cd smokeys-radio

# Install FFmpeg
sudo apt install ffmpeg          # Debian / Ubuntu
brew install ffmpeg              # macOS

pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN

python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/play <query>` | Play a song or add it to the queue (supports autocomplete) |
| `/skip` | Skip the current song |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/stop` | Stop playback, clear queue, and disconnect |
| `/queue` | Show the current queue |
| `/stats` | Show extraction bypass statistics (and DB totals if enabled) |
| `/topsongs [period] [scope]` | Most-played songs (all-time / day / week / month, this server or global) |
| `/topusers [period] [scope]` | Users who play the most music |
| `/myhistory` | Your 10 most recent plays (ephemeral) |
| `/test` | Check if the bot is responding |
| `!sync` | Manually sync slash commands |
| `!resync` | Clear and re-register slash commands |

## Stats Database (optional)

If a SQL Server instance is reachable, the bot logs every command and song
play. This powers `/topsongs`, `/topusers`, `/myhistory`, and the totals
shown by `/stats`. The DB layer is fail-soft: if the connection fails at
startup, the bot logs a warning and disables stats; playback is unaffected.

### Enable

1. Run `scripts/schema.sql` against your SQL Server instance. It creates the
   `SmokeysRadio` database, all tables, indexes, and FKs. The script is
   idempotent so it is safe to re-run.
2. Set the DB environment variables in `.env` (see `.env.example`). Defaults
   are `localhost` / `SmokeysRadio` with Windows authentication, which works
   for a local SQL Server install on Windows out of the box.
3. Start the bot. The startup log line `Database connection OK` confirms the
   connection is live. A failure logs `Database connection failed: ...` and
   disables stats for that session.

### Schema overview

| Table | Purpose |
|-------|---------|
| `dbo.users` | One row per Discord user (PK = `discord_user_id`). Tracks `first_seen` / `last_seen`. |
| `dbo.guilds` | One row per server. |
| `dbo.songs` | One row per unique YouTube ID. Stores title, uploader, duration, thumbnail. |
| `dbo.plays` | One row per play. Stores requester, source (`url` or `search`), the bypass method that won, the raw search query, outcome (`started` / `completed` / `skipped` / `error`), and how many seconds were actually listened. |
| `dbo.commands` | One row per slash command invocation. Stores success / failure, args, and any error message. |

A play starts as `outcome = 'started'`. When playback ends, the bot updates
the row to `completed`, `skipped`, or `error`, and writes `listened_seconds`.
The completion heuristic is `listened_seconds >= duration_seconds * 0.95`.

### Inspecting the DB

A small read-only CLI is included for ad-hoc inspection without needing
a SQL client:

```bash
python scripts/inspect_db.py              # row counts + last 20 plays + last 20 commands
python scripts/inspect_db.py plays 50     # last 50 plays
python scripts/inspect_db.py commands 50  # last 50 commands
python scripts/inspect_db.py top          # top songs / users / most-skipped
python scripts/inspect_db.py raw          # row counts only
```

It uses the same `SMOKEYS_DB_CONN` env var (or the default localhost /
Windows-auth connection) as the bot.

## Extraction System

The bot tries five extraction methods in order until one works:

1. **Standard**: default yt-dlp with geo-bypass
2. **Mobile**: Android / iOS player clients
3. **Embed**: embedded player parameters
4. **Music**: YouTube Music player client
5. **Alternative**: US geo-bypass with Google referer

Use `/stats` to see success rates per method.

## Troubleshooting

### Bot can't join voice channels

- Ensure the bot has **Connect** and **Speak** permissions in the voice channel.
- Update voice deps: `pip install -U "discord.py[voice]"`. The `davey` package
  is required for Discord's voice encryption (Dave protocol).
- Check `logs/smokeys_radio.log` for WebSocket close codes.

### Slash commands not appearing

1. Try `!sync` or `!resync` in your server.
2. Run `python scripts/api_register.py` to register commands via the API.
3. Re-invite the bot using the link in `bot_invite.txt`.
4. Wait up to 10 minutes for Discord to propagate global commands.

### No audio playing

- Verify FFmpeg is installed: `ffmpeg -version`.
- On Windows, run `python scripts/setup_audio.py` to install FFmpeg automatically.
- Check logs for extraction errors. yt-dlp may need updating: `pip install -U yt-dlp`.

### Database connection failed

- Confirm SQL Server is reachable from the host running the bot.
- Confirm the ODBC driver name in `SMOKEYS_DB_DRIVER` matches a driver
  installed on the host (`ODBC Driver 17 for SQL Server` is the default).
- For SQL auth, set `SMOKEYS_DB_TRUSTED=no` and provide `SMOKEYS_DB_USER`
  and `SMOKEYS_DB_PASSWORD`.
- To turn the DB off entirely, set `SMOKEYS_DB_DISABLED=true`.

## License

MIT License. See [LICENSE](LICENSE) for details.
