# Smokey's Radio - Discord Music Bot

A Discord music bot built with Python that plays music from YouTube using yt-dlp with multiple extraction bypass methods. Uses discord.py 2.0+ slash commands with autocomplete search.

## Features

- Play music from YouTube search or direct URLs with autocomplete suggestions
- Five-tier extraction bypass system (standard, mobile, embed, music, alternative)
- Queue management with embedded displays
- Bypass statistics tracking
- Auto-disconnect after 5 minutes of inactivity
- Rotating log files

## Project Structure

```
smokeys-radio/
  bot.py              # Main bot (single-file)
  requirements.txt    # Python dependencies
  Dockerfile          # Container build
  docker-compose.yml  # Container orchestration
  .env                # Discord token (not committed)
  scripts/
    setup_audio.py    # Dependency installer (Windows)
    api_register.py   # Manual slash command registration
    start.bat         # Windows launcher
  logs/               # Rotating log files (not committed)
```

## Prerequisites

- Python 3.10+ (for local) or Docker
- FFmpeg
- A Discord bot token — [create one here](https://discord.com/developers/applications)

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**, give it a name
3. Go to **Bot** > click **Reset Token** > copy the token
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**
5. Save changes

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

The Docker image includes FFmpeg and all dependencies. Logs are mounted to `./logs/` on the host.

### Option 2: Local (Windows)

1. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/yourusername/smokeys-radio.git
   cd smokeys-radio
   pip install -r requirements.txt
   ```
   Or use the automated setup (also downloads FFmpeg):
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

### Option 3: Local (Linux/macOS)

```bash
git clone https://github.com/yourusername/smokeys-radio.git
cd smokeys-radio

# Install FFmpeg
sudo apt install ffmpeg          # Debian/Ubuntu
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
| `/stats` | Show extraction bypass statistics |
| `/test` | Check if the bot is responding |
| `!sync` | Manually sync slash commands |
| `!resync` | Clear and re-register slash commands |

## Extraction System

The bot tries five extraction methods in order until one works:

1. **Standard** — default yt-dlp with geo-bypass
2. **Mobile** — Android/iOS player clients
3. **Embed** — embedded player parameters
4. **Music** — YouTube Music player client
5. **Alternative** — US geo-bypass with Google referer

Use `/stats` to see success rates per method.

## Troubleshooting

### Bot can't join voice channels
- Ensure the bot has **Connect** and **Speak** permissions in the voice channel
- Update dependencies: `pip install -U "discord.py[voice]"` — the `davey` package is required for Discord's voice encryption (Dave protocol)
- Check `logs/smokeys_radio.log` for WebSocket close codes

### Slash commands not appearing
1. Try `!sync` or `!resync` in your server
2. Run `python scripts/api_register.py` to register commands via the API
3. Re-invite the bot using the link in `bot_invite.txt`
4. Wait up to 10 minutes for Discord to propagate

### No audio playing
- Verify FFmpeg is installed: `ffmpeg -version`
- On Windows, run `python scripts/setup_audio.py` to install FFmpeg automatically
- Check logs for extraction errors — yt-dlp may need updating: `pip install -U yt-dlp`

## License

MIT License — see [LICENSE](LICENSE) for details.
