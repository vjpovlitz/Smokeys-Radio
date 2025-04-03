import requests
import json
import os
import time
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Error: No Discord token found in .env file")
    exit(1)

# Step 1: Get the bot's user info to find the application ID
headers = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

print("Getting bot information...")
response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)

if response.status_code != 200:
    print(f"Error getting bot information: {response.status_code}")
    print(response.text)
    exit(1)

bot_info = response.json()
bot_id = bot_info["id"]
bot_name = bot_info["username"]

print(f"Bot identified: {bot_name} (ID: {bot_id})")

# Step 2: Define the commands to register
commands = [
    {
        "name": "play",
        "description": "Play a song or add it to the queue.",
        "options": [
            {
                "name": "song_query",
                "description": "Search query or YouTube URL",
                "type": 3,
                "required": True
            }
        ]
    },
    {
        "name": "skip",
        "description": "Skips the current playing song"
    },
    {
        "name": "pause",
        "description": "Pause the currently playing song."
    },
    {
        "name": "resume",
        "description": "Resume the currently paused song."
    },
    {
        "name": "stop",
        "description": "Stop playback and clear the queue."
    },
    {
        "name": "queue",
        "description": "Show the current song queue"
    },
    {
        "name": "stats",
        "description": "Show bypass statistics and success rates"
    },
    {
        "name": "test",
        "description": "Test if the bot is responding to commands"
    }
]

# Step 3: Register each command
print(f"Registering commands for application ID: {bot_id}")
url = f"https://discord.com/api/v10/applications/{bot_id}/commands"

for command in commands:
    print(f"Registering {command['name']}...")
    response = requests.post(url, headers=headers, data=json.dumps(command))
    
    if response.status_code == 429:  # Rate limited
        retry_after = json.loads(response.text).get('retry_after', 1)
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after + 1)  # Wait the required time plus a buffer
        
        # Try again
        response = requests.post(url, headers=headers, data=json.dumps(command))
    
    if response.status_code in (200, 201):
        print(f"✅ {command['name']} registered successfully")
    else:
        print(f"❌ Error registering {command['name']}: {response.status_code}")
        print(response.text)

# Step 4: Generate invite link
permissions = 3149824  # Standard music bot permissions
invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions={permissions}&scope=bot%20applications.commands"

print("\n=== REGISTRATION COMPLETE ===")
print(f"Bot: {bot_name}")
print(f"Commands registered: {len(commands)}")
print("\nIMPORTANT: Use this link to add your bot to servers:")
print(invite_url)

# Save the invite link to a file
with open("bot_invite.txt", "w") as f:
    f.write(invite_url)
print("\nInvite link saved to bot_invite.txt")

print("\nAfter adding the bot with this link, wait 5-10 minutes for Discord to update the commands.")
print("Then try using the /test command to verify it's working.") 