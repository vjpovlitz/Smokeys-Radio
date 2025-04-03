# 🎵 Smokey's Radio - Advanced Discord Music Bot

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue)

Smokey's Radio is an advanced Discord music bot that uses multiple extraction methods to play music from YouTube and other sources, even when the content has restrictions. The bot provides high-quality audio playback, reliable connections, and a variety of commands for controlling your music experience.

## ✨ Features

- 🎧 Play music from YouTube search queries or direct URLs
- 🔄 Multiple extraction methods that bypass common restrictions
- 📊 Statistics tracking for bypass success rates
- 🎮 Easy-to-use slash commands
- 📋 Queue management with visual display
- 🏃‍♂️ Reliable streaming with automatic reconnection
- 📝 Detailed logging for troubleshooting

## 🔧 Installation

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed on your system or in the bot's directory
- A Discord bot token ([Create a bot here](https://discord.com/developers/applications))

### Setup

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/smokeys-radio.git
   cd smokeys-radio
   ```

2. **Install dependencies**
   ```
   python setup_audio.py
   ```
   Or manually install with:
   ```
   pip install -r requirements.txt
   ```

3. **Create a `.env` file with your Discord token**
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**
   ```
   python bot.py
   ```

5. **Register commands with Discord API** (if needed)
   ```
   python api_register.py
   ```

6. **Invite the bot to your server**
   - Use the link generated in `bot_invite.txt` after running the bot

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/play [song_query]` | Play a song or add it to the queue |
| `/skip` | Skip to the next song in the queue |
| `/pause` | Pause the currently playing song |
| `/resume` | Resume a paused song |
| `/stop` | Stop playback and clear the queue |
| `/queue` | Display the current song queue |
| `/stats` | Show bypass statistics and success rates |
| `/test` | Check if the bot is responding to commands |
| `!sync` | Sync commands with Discord (admin only) |
| `!resync` | Force a resync of commands (admin only) |

## 🔍 Extraction Methods

Smokey's Radio uses multiple extraction methods to bypass restrictions:

- **Standard**: Default yt-dlp extraction
- **Mobile**: Mimics a mobile device to access restricted content
- **Embed**: Uses embedded player parameters
- **Music**: Attempts to extract through YouTube Music
- **Alternative**: Falls back to alternative sources when available

## 🛠️ Troubleshooting

### Commands Not Appearing
1. Use `!sync` or `!resync` in your server
2. Run `python api_register.py` to register commands directly with Discord
3. Reinvite the bot using the link in `bot_invite.txt`
4. Wait 5-10 minutes for Discord to update

### Audio Not Playing
1. Make sure FFmpeg is installed correctly
2. Run `python setup_audio.py` to install all audio dependencies
3. Check the logs in the `logs` directory for specific errors
4. Ensure the bot has proper permissions in your Discord server

### Connection Issues
1. Check your internet connection
2. Try different voice channels
3. Restart the bot
4. Check if Discord's voice servers are experiencing issues

## 📈 Advanced Usage

### Self-Hosting
- For 24/7 operation, consider using a service like PM2 or running on a VPS
- Update regularly with `git pull` to get the latest bypass methods

### Custom FFmpeg Path
If you have FFmpeg installed in a non-standard location, modify the path in `bot.py`:
```python
ffmpeg_path = "path/to/your/ffmpeg"
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - The Discord API wrapper
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader with bypass capabilities
- All contributors who have helped with testing and development 