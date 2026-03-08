#!/usr/bin/env python3
# Smokey's Radio - Advanced Discord Music Bot with yt-dlp
# This implementation uses the yt-dlp library which is regularly updated to bypass YouTube restrictions

import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import asyncio
import random
import logging
from logging.handlers import RotatingFileHandler
import json
import time
import sys

# Set up logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger('smokeys_radio')
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# File handler
file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, 'smokeys_radio.log'),
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Enable debug logging for discord voice to diagnose connection issues
discord_logger = logging.getLogger('discord.voice_state')
discord_logger.setLevel(logging.DEBUG)
discord_logger.addHandler(console_handler)
discord_logger.addHandler(file_handler)

discord_gw_logger = logging.getLogger('discord.gateway')
discord_gw_logger.setLevel(logging.DEBUG)
discord_gw_logger.addHandler(console_handler)
discord_gw_logger.addHandler(file_handler)

# Environment variables for tokens
logger.info("Starting Smokey's Radio...")
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.error("No Discord token found in environment variables. Please set DISCORD_TOKEN.")
    sys.exit(1)

# Create the structure for queueing songs - Dictionary of queues
SONG_QUEUES = {}

# YT-DLP User Agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/36.0 Mobile/15E148 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
]

# Initialize statistics for bypass methods
BYPASS_STATS = {
    "total_attempts": 0,
    "successful_attempts": 0,
    "failed_attempts": 0,
    "successful_videos": set(),
    "failed_videos": set(),
    "last_successful_method": None,
    "method_success_count": {
        "standard": 0,
        "mobile": 0,
        "embed": 0,
        "music": 0,
        "alternative": 0
    }
}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            BYPASS_STATS["successful_attempts"] += 1
            
            # Track statistics
            if "entries" in info:
                video_id = info["entries"][0].get("id", "unknown")
            else:
                video_id = info.get("id", "unknown")
                
            BYPASS_STATS["successful_videos"].add(video_id)
            
            # Record the method used
            if "method" in ydl_opts:
                BYPASS_STATS["last_successful_method"] = ydl_opts["method"]
                BYPASS_STATS["method_success_count"][ydl_opts["method"]] += 1
            
            return info
    except Exception as e:
        BYPASS_STATS["failed_attempts"] += 1
        
        if "entries" in locals().get("info", {}):
            video_id = info["entries"][0].get("id", "unknown")
        elif "ytsearch" in query:
            video_id = query.split("ytsearch")[1].strip()
        else:
            video_id = query
        
        BYPASS_STATS["failed_videos"].add(video_id)
        
        logger.error(f"Extraction failed: {str(e)}")
        raise e

# Advanced YT-DLP options with multiple bypass methods
def get_ytdlp_options(method="standard"):
    BYPASS_STATS["total_attempts"] += 1
    
    # Base options
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "method": method
    }
    
    # Method-specific configurations
    if method == "standard":
        options.update({
            "format": "bestaudio[abr<=128]/bestaudio/best",
            "user_agent": random.choice(USER_AGENTS),
            "referer": "https://www.youtube.com/",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"]
                }
            }
        })
    
    elif method == "mobile":
        options.update({
            "format": "bestaudio[abr<=128]/bestaudio/best",
            "user_agent": USER_AGENTS[-1],  # Mobile user agent
            "referer": "https://m.youtube.com/",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios"],
                    "skip": ["dash", "hls"]
                }
            }
        })
    
    elif method == "embed":
        options.update({
            "format": "bestaudio[abr<=128]/bestaudio/best",
            "user_agent": random.choice(USER_AGENTS),
            "referer": "https://www.example.com/",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded"],
                    "skip": ["dash", "hls"]
                }
            }
        })
    
    elif method == "music":
        options.update({
            "format": "bestaudio[abr<=128]/bestaudio/best",
            "user_agent": random.choice(USER_AGENTS),
            "referer": "https://music.youtube.com/",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_music", "web"],
                    "skip": ["dash", "hls"]
                }
            }
        })
    
    elif method == "alternative":
        options.update({
            "format": "bestaudio[abr<=128]/bestaudio/best",
            "user_agent": random.choice(USER_AGENTS),
            "referer": "https://www.google.com/",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"]
                }
            }
        })
    
    return options

# Setup of intents for Discord API
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot ready-up code
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is now ready!")
    print(f"Smokey's Radio is online!")
    print(f"Logged in as: {bot.user}")
    print("------")
    
    # Generate and save invite link with proper scopes
    invite_link = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(
            send_messages=True,
            connect=True, 
            speak=True,
            use_voice_activation=True,
            read_messages=True,
            add_reactions=True,
            attach_files=True,
            embed_links=True,
            read_message_history=True
        ),
        scopes=["bot", "applications.commands"]  # This is what enables slash commands
    )
    with open("bot_invite.txt", "w") as f:
        f.write(invite_link)
    print(f"Invite link saved to bot_invite.txt")
    
    # Will sync commands on startup (global + per-guild for immediate effect)
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s) globally")
        print(f"Synced {len(synced)} slash commands globally")
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            guild_synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(guild_synced)} command(s) to guild: {guild.name}")
            print(f"Synced {len(guild_synced)} commands to {guild.name}")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Discord event error in {event}: {str(sys.exc_info())}")

@bot.command(name="sync")
async def sync_commands(ctx):
    """Manually sync slash commands"""
    await ctx.send("🔄 Syncing commands... This may take a moment.")
    
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Successfully synced {len(synced)} commands globally!")
    except Exception as e:
        await ctx.send(f"❌ Error syncing commands: {e}")


# Try all extraction methods until one works
async def try_extraction_methods(query):
    methods = ["standard", "mobile", "embed", "music", "alternative"]
    
    for method in methods:
        try:
            logger.info(f"Trying extraction method: {method} for query: {query}")
            ydl_options = get_ytdlp_options(method)
            return await search_ytdlp_async(query, ydl_options)
        except Exception as e:
            logger.warning(f"Method {method} failed: {str(e)}")
            continue
    
    # If all methods fail
    raise Exception("All extraction methods failed")

@bot.tree.command(name="skip", description="Skips the current playing song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped the current song.")
    else:
        await interaction.response.send_message("❌ Not playing anything to skip.")

@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("❌ I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        return await interaction.response.send_message("❌ Nothing is currently playing.")
    
    # Pause the track
    voice_client.pause()
    await interaction.response.send_message("⏸️ Playback paused!")

@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("❌ I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        return await interaction.response.send_message("❌ I'm not paused right now.")
    
    # Resume playback
    voice_client.resume()
    await interaction.response.send_message("▶️ Playback resumed!")

@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        return await interaction.response.send_message("❌ I'm not connected to any voice channel.")

    # Clear the guild's queue
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # Disconnect from the channel
    await voice_client.disconnect()

    await interaction.response.send_message("⏹️ Stopped playback and disconnected!")

@bot.tree.command(name="queue", description="Show the current song queue")
async def queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    
    if guild_id not in SONG_QUEUES or not SONG_QUEUES[guild_id]:
        return await interaction.response.send_message("📭 The queue is empty.")
    
    # Create an embed for the queue
    embed = discord.Embed(
        title="🎵 Current Queue",
        color=discord.Color.blue()
    )
    
    # Add current song if playing
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        embed.add_field(
            name="🎧 Now Playing",
            value=f"**{SONG_QUEUES[guild_id][0][1]}**",
            inline=False
        )
    
    # Add upcoming songs
    queue_display = []
    for i, (_, title) in enumerate(list(SONG_QUEUES[guild_id])[1:], 1):
        if i <= 10:  # Show only 10 songs to avoid overflow
            queue_display.append(f"{i}. **{title}**")
    
    if queue_display:
        embed.add_field(
            name="📋 Up Next",
            value="\n".join(queue_display),
            inline=False
        )
        
        # Add note if queue is longer
        if len(SONG_QUEUES[guild_id]) > 11:
            embed.set_footer(text=f"And {len(SONG_QUEUES[guild_id]) - 11} more songs...")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="Show bypass statistics and success rates")
async def stats(interaction: discord.Interaction):
    # Calculate success rate
    total = BYPASS_STATS["total_attempts"]
    success = BYPASS_STATS["successful_attempts"]
    success_rate = (success / total * 100) if total > 0 else 0
    
    # Create an embed for the stats
    embed = discord.Embed(
        title="🔍 YouTube Bypass Statistics",
        description=f"Success rate: {success_rate:.1f}%",
        color=discord.Color.green() if success_rate > 70 else discord.Color.orange()
    )
    
    # Overall stats
    embed.add_field(
        name="📊 Overall",
        value=f"Total attempts: {total}\nSuccessful: {success}\nFailed: {BYPASS_STATS['failed_attempts']}",
        inline=False
    )
    
    # Method success rates
    method_stats = []
    for method, count in BYPASS_STATS["method_success_count"].items():
        method_stats.append(f"{method}: {count}")
    
    embed.add_field(
        name="🧩 Method Success Counts",
        value="\n".join(method_stats) if method_stats else "No data yet",
        inline=False
    )
    
    # Last success info
    if BYPASS_STATS["last_successful_method"]:
        embed.add_field(
            name="🏆 Last Successful Method",
            value=BYPASS_STATS["last_successful_method"],
            inline=False
        )
    
    # Add totals
    embed.set_footer(text=f"Unique successful videos: {len(BYPASS_STATS['successful_videos'])} | Unique failed videos: {len(BYPASS_STATS['failed_videos'])}")
    
    await interaction.response.send_message(embed=embed)

async def song_query_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if len(current) < 2:
        return []
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "default_search": "ytsearch5",
            "noplaylist": True,
        }
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, lambda: _autocomplete_search(current, ydl_opts))
        return results[:25]  # Discord allows max 25 choices
    except Exception:
        return []

def _autocomplete_search(query, ydl_opts):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            if not info or "entries" not in info:
                return []
            choices = []
            for entry in info["entries"]:
                if entry and entry.get("title"):
                    title = entry["title"][:100]  # Discord choice max length
                    choices.append(app_commands.Choice(name=title, value=title))
            return choices
    except Exception:
        return []

@bot.tree.command(name="play", description="Play a song or add it to the queue.")
@app_commands.describe(song_query="Search query or YouTube URL")
@app_commands.autocomplete(song_query=song_query_autocomplete)
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()
    logger.info(f"Play command received: {song_query} from {interaction.user}")
    
    # Check if user is in a voice channel
    if not interaction.user.voice:
        logger.warning(f"User {interaction.user} not in a voice channel")
        await interaction.followup.send("❌ You must be in a voice channel.")
        return

    voice_channel = interaction.user.voice.channel
    logger.info(f"User in voice channel: {voice_channel.name}")

    # Get or create voice client
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        for attempt in range(2):
            try:
                logger.info(f"Attempting to connect to voice channel: {voice_channel.name} (attempt {attempt + 1})")
                voice_client = await voice_channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
                # Wait briefly for the connection to fully establish
                await asyncio.sleep(1)
                if not voice_client.is_connected():
                    logger.warning("Voice client connected but is_connected() returned False, retrying...")
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception:
                        pass
                    continue
                logger.info(f"Connected to voice channel: {voice_channel.name}")
                break
            except asyncio.TimeoutError:
                logger.error(f"Connection to voice channel timed out (attempt {attempt + 1})")
                if attempt == 0:
                    # Clean up any partial connection before retrying
                    if interaction.guild.voice_client:
                        try:
                            await interaction.guild.voice_client.disconnect(force=True)
                        except Exception:
                            pass
                    continue
                await interaction.followup.send("❌ Connection timed out. Try again or use a different voice channel.")
                return
            except Exception as e:
                logger.error(f"Failed to connect to voice channel: {str(e)}", exc_info=True)
                await interaction.followup.send(f"❌ Failed to connect to voice channel: {str(e)}")
                return
    elif voice_channel != voice_client.channel:
        logger.info(f"Moving from {voice_client.channel.name} to {voice_channel.name}")
        await voice_client.move_to(voice_channel)
        logger.info(f"Moved to voice channel: {voice_channel.name}")

    # Process the query
    try:
        # Check if it's a direct YouTube URL
        if "youtube.com/" in song_query or "youtu.be/" in song_query:
            logger.info(f"Processing direct YouTube URL: {song_query}")
            query = song_query
        else:
            # Use YouTube search
            logger.info(f"Searching YouTube for: {song_query}")
            query = "ytsearch1: " + song_query
        
        # Try extraction with all methods if needed
        logger.info("Starting extraction with all methods")
        for method in ["standard", "mobile", "embed", "music", "alternative"]:
            try:
                logger.info(f"Trying method: {method}")
                ydl_options = get_ytdlp_options(method)
                results = await search_ytdlp_async(query, ydl_options)
                logger.info(f"Method {method} succeeded!")
                break
            except Exception as e:
                logger.warning(f"Method {method} failed: {str(e)}")
                results = None
                continue
        
        if not results:
            logger.error("All extraction methods failed")
            await interaction.followup.send("❌ Could not extract video information after trying all methods.")
            return
        
        # Process the results
        if "entries" in results:
            # Search result
            tracks = results.get("entries", [])
            if not tracks:
                logger.warning("No tracks found in search results")
                await interaction.followup.send("❌ No results found.")
                return
            track = tracks[0]
            logger.info(f"Selected track from search: {track.get('title', 'Unknown')}")
        else:
            # Direct URL result
            track = results
            logger.info(f"Using direct URL result: {track.get('title', 'Unknown')}")
        
        audio_url = track["url"]
        title = track.get("title", "Untitled")
        thumbnail = track.get("thumbnail") if isinstance(track.get("thumbnail"), str) else None
        duration = track.get("duration") or 0
        duration_str = time.strftime("%M:%S", time.gmtime(duration))
        
        logger.info(f"Audio URL: {audio_url[:50]}... (truncated)")
        logger.info(f"Title: {title}")
        logger.info(f"Duration: {duration_str}")
        
        # Add to queue
        guild_id = str(interaction.guild_id)
        if guild_id not in SONG_QUEUES:
            SONG_QUEUES[guild_id] = deque()
        
        SONG_QUEUES[guild_id].append((audio_url, title, thumbnail, duration_str))
        logger.info(f"Added to queue. Queue length: {len(SONG_QUEUES[guild_id])}")
        
        # Create a more stylish embedded response
        if voice_client.is_playing() or voice_client.is_paused():
            # Added to queue message
            embed = discord.Embed(
                title="🎵 Added to Queue",
                description=f"**{title}**",
                color=discord.Color.blue()
            )
            
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            # Add more details
            embed.add_field(
                name="Duration",
                value=f"⏱️ {duration_str}",
                inline=True
            )
            
            embed.add_field(
                name="Position",
                value=f"📊 #{len(SONG_QUEUES[guild_id])}",
                inline=True
            )
            
            # Add a footer with the requester's name
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", 
                             icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)
            logger.info("Song added to queue notification sent")
        else:
            # Now playing message
            embed = discord.Embed(
                title="🎧 Now Playing",
                description=f"**{title}**",
                color=discord.Color.green()
            )
            
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            # Add duration and progress bar
            total_seconds = sum(x * int(t) for x, t in zip([60, 1], duration_str.split(":")))
            progress_bar = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            embed.add_field(
                name="Duration",
                value=f"⏱️ `{progress_bar}` {duration_str}",
                inline=False
            )
            
            # Add queue position
            queue_length = len(SONG_QUEUES[guild_id])
            if queue_length > 1:
                next_song = SONG_QUEUES[guild_id][1][1] if len(SONG_QUEUES[guild_id]) > 1 else "None"
                embed.add_field(
                    name="Queue",
                    value=f"📊 {queue_length} songs in queue | Next: **{next_song}**",
                    inline=False
                )
            
            # Add helpful tip
            embed.set_footer(text="Tip: Use /queue to see the full playlist")
            
            await interaction.followup.send(embed=embed)
            logger.info("Now playing notification sent")
            await play_next_song(voice_client, guild_id, interaction.channel)
    
    except Exception as e:
        logger.error(f"Error processing play command: {str(e)}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}")

async def play_next_song(voice_client, guild_id, channel):
    if guild_id in SONG_QUEUES and SONG_QUEUES[guild_id]:
        audio_url, title, thumbnail, duration = SONG_QUEUES[guild_id][0]

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -af 'volume=0.5' -c:a libopus -b:a 128k",
        }

        try:
            # Verify voice connection is still alive, reconnect if needed
            guild = bot.get_guild(int(guild_id))
            if guild is None:
                logger.error(f"Could not find guild {guild_id}")
                return

            # Re-fetch voice_client from guild in case the reference is stale
            voice_client = guild.voice_client

            if voice_client is None or not voice_client.is_connected():
                logger.warning("Voice client disconnected before playback, attempting to reconnect...")
                # Try to find the channel to reconnect to
                if voice_client and voice_client.channel:
                    target_channel = voice_client.channel
                else:
                    # Fall back to checking members in voice channels
                    target_channel = None
                    for vc in guild.voice_channels:
                        if guild.me in vc.members:
                            target_channel = vc
                            break

                if target_channel:
                    try:
                        # Clean up old connection
                        if voice_client:
                            try:
                                await voice_client.disconnect(force=True)
                            except Exception:
                                pass
                        voice_client = await target_channel.connect(timeout=60.0, reconnect=True, self_deaf=True)
                        await asyncio.sleep(1)
                        logger.info(f"Reconnected to voice channel: {target_channel.name}")
                    except Exception as e:
                        logger.error(f"Failed to reconnect to voice: {e}")
                        await channel.send(f"❌ Lost voice connection and couldn't reconnect: {e}")
                        SONG_QUEUES[guild_id].clear()
                        return
                else:
                    logger.error("No voice channel to reconnect to")
                    await channel.send("❌ Lost voice connection.")
                    SONG_QUEUES[guild_id].clear()
                    return

            logger.info(f"Playing: {title}")
            
            # Check common ffmpeg locations, otherwise use system ffmpeg
            ffmpeg_path = None
            for path in [
                "bin\\ffmpeg\\ffmpeg.exe",
            ]:
                if os.path.exists(path):
                    ffmpeg_path = path
                    break

            # Search winget install location if not found
            if not ffmpeg_path:
                import glob
                winget_pattern = os.path.expandvars(
                    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe"
                )
                matches = glob.glob(winget_pattern)
                if matches:
                    ffmpeg_path = matches[0]

            if ffmpeg_path:
                source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable=ffmpeg_path)
            else:
                source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)
            
            def after_play(error):
                if error:
                    logger.error(f"Error playing {title}: {error}")
                
                # Remove the song we just played
                if guild_id in SONG_QUEUES and SONG_QUEUES[guild_id]:
                    SONG_QUEUES[guild_id].popleft()
                
                asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)
            
            voice_client.play(source, after=after_play)
            
            # Create embedded now playing message
            embed = discord.Embed(
                title="🎧 Now Playing",
                description=f"**{title}**",
                color=discord.Color.green()
            )
            
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
                
            # Add duration and progress bar
            total_seconds = sum(x * int(t) for x, t in zip([60, 1], duration.split(":")))
            progress_bar = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            embed.add_field(
                name="Duration",
                value=f"⏱️ `{progress_bar}` {duration}",
                inline=False
            )
            
            # Add queue position
            queue_length = len(SONG_QUEUES[guild_id])
            if queue_length > 1:
                next_song = SONG_QUEUES[guild_id][1][1] if len(SONG_QUEUES[guild_id]) > 1 else "None"
                embed.add_field(
                    name="Queue",
                    value=f"📊 {queue_length} songs in queue | Next: **{next_song}**",
                    inline=False
                )
            
            # Add helpful tip
            embed.set_footer(text="Tip: Use /queue to see the full playlist")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error starting playback: {str(e)}")
            await channel.send(f"❌ Error playing {title}: {str(e)}")
            
            # Try to play the next song
            if guild_id in SONG_QUEUES and SONG_QUEUES[guild_id]:
                SONG_QUEUES[guild_id].popleft()
                asyncio.create_task(play_next_song(voice_client, guild_id, channel))
    else:
        # Empty queue, disconnect after a delay
        await asyncio.sleep(300)  # 5 minutes
        guild = bot.get_guild(int(guild_id))
        vc = guild.voice_client if guild else None
        if vc and vc.is_connected() and not vc.is_playing():
            logger.info("Disconnecting due to inactivity")
            await vc.disconnect()

@bot.tree.command(name="test", description="Test if the bot is responding to commands")
async def test(interaction: discord.Interaction):
    logger.info(f"Test command received from {interaction.user}")
    await interaction.response.send_message("✅ Bot is working! Commands are registered correctly.")

@bot.command()
async def resync(ctx):
    """Manually resync all slash commands"""
    await ctx.send("Resyncing commands... This may take a moment.")
    
    try:
        # Clear existing commands first
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        
        # Then re-sync to each guild individually
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
            
        await ctx.send("✅ Commands have been resynced! Try using them now.")
    except Exception as e:
        await ctx.send(f"❌ Error while resyncing: {e}")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)  # Disable Discord.py's built-in logging as we have our own 