# Setup Guide for Discord Riven Bot

## Full Setup Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/subvhome/DiscordRivenBot.git
   cd DiscordRivenBot
Install Dependencies:
Optional: Create a virtual environment:
bash

Collapse

Wrap

Copy
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
Install packages:
bash

Collapse

Wrap

Copy
pip install discord.py requests
Configure the Bot:
Copy the example config:
bash

Collapse

Wrap

Copy
cp config.example.json config.json
Edit config.json (details below).
Run the Bot:
bash

Collapse

Wrap

Copy
python rivbot-discord.py
Invite the bot to your Discord server using its token.
Configuration (config.json)
Create config.json by copying config.example.json and filling in these fields:

json

Collapse

Wrap

Copy
{
    "riven_api_url": "http://localhost:8080/api/v1",
    "riven_api_token": "your_riven_api_token_here",
    "discord_bot_token": "your_discord_bot_token_here",
    "whitelist": ["your_discord_username#1234"],
    "bot_prefix": "/",
    "tmdb_api_key": "your_tmdb_api_key_here"
}
riven_api_url:
URL of your Riven server’s API.
Default: "http://localhost:8080/api/v1" (local).
Use your server’s IP/domain if remote (e.g., "http://yourserver:8080/api/v1").
riven_api_token:
Authentication token from your Riven server (check admin panel or config).
Example: "your_riven_api_key_here".
discord_bot_token:
Token for your Discord bot.
Get it from Discord Developer Portal:
New Application > Name (e.g., "RivenBot") > Create.
Bot tab > Add Bot > Copy Token (reset if needed).
Enable "Presence Intent," "Server Members Intent," "Message Content Intent."
OAuth2 > URL Generator > Scopes: bot, Permissions: Send Messages, Read Messages/View Channels, Use Slash Commands > Invite bot.
Example: "NjYxMjM0NTY3ODkwMTIzNDU2.XgXxXw.abcdefg1234567890".
whitelist:
Discord usernames (username#discriminator) allowed to use the bot.
Example: ["subvhome#1234", "friend#5678"].
bot_prefix:
Command prefix (e.g., /health).
Default: "/". Change to "!", "$", etc.
Example: "!".
tmdb_api_key:
API key for TMDB media searches.
Get it from The Movie Database:
Sign up/login > Settings > API > Request API key (v3).
Copy "API Key (v3 auth)".
Example: "your_tmdb_api_key_here".
Troubleshooting
Bot not starting? Check config.json for typos or missing keys.
No response? Ensure Riven server is running and intents are enabled in Discord.
