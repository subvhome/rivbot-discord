# 🛠 Setup Guide for rivbot-discord  

Follow these steps to install and configure the bot.  

## 📋 Prerequisites  

Before running the bot, ensure you have:  

- Python 3.8+ (https://www.python.org/downloads/)  
- Git (https://git-scm.com/downloads)  
- A Discord Bot Token (from the Discord Developer Portal: https://discord.com/developers/applications)  
- A Running Riven Server with API access  
- A TMDB API Key (https://www.themoviedb.org/signup)  
- A Trakt API Key (https://trakt.tv/oauth/applications)  

---

## 📥 1. Clone the Repository  

git clone https://github.com/subvhome/rivbot-discord.git  
cd rivbot-discord  

---

## 📦 2. Install Dependencies  

- Ensure Python 3.8+ is installed.  
- Install required dependencies:  

pip install -r requirements.txt  

- Verify installation:  

pip list  

---

## ⚙️ 3. Configure the Bot  

1. Copy the example config file:  
   cp config.example.json config.json  # Linux/macOS  
   # Windows: copy config.example.json config.json  

2. Edit config.json in a text editor and update the required fields:  

{
    "riven_api_url": "http://localhost:8080/api/v1",
    "riven_api_token": "riven_api_token",
    "discord_bot_token": "discord_bot_token",
    "whitelist": ["your_discord_username"],
    "bot_prefix": "!",
    "tmdb_api_key": "tmdb_api_token",
    "trakt_api_key": "trakt_api_key",
    "log_to_file": true,
    "latest_releases_count": 4,
    "max_grid_width": 300,
    "poster_grid_columns": 2,
    "poster_image_width": 150,
    "poster_image_height": 220
}

### Poster Grid Settings  
- latest_releases_count: Number of latest releases to fetch from Trakt.  
- max_grid_width: The maximum width for the poster grid image.  
- poster_grid_columns: Number of columns in the poster grid.  
- poster_image_width/poster_image_height: Dimensions for individual poster images.  

---

## 🛸 Discord Bot Setup Instructions  

To configure the bot on Discord:  

1. Create a New Application:  
   - Go to the Discord Developer Portal (https://discord.com/developers/applications).  
   - Click "New Application", name it (e.g., "RivenBot"), and save.  

2. Generate a Bot Token:  
   - Navigate to the "Bot" tab, click "Add Bot", then "Reset Token" to generate a token.  
   - Copy the token and keep it secure (paste it into config.json).  

3. Configure Intents:  
   - In the "Bot" tab, enable:  
     - Presence Intent  
     - Server Members Intent  
     - Message Content Intent  

4. Invite the Bot:  
   - Go to "OAuth2 > URL Generator".  
   - Select "Scopes": bot.  
   - Select "Permissions": Send Messages, Read Messages/View Channels, Embed Links, Attach Files, Add Reactions.  
   - Copy the URL, open it in a browser, and invite the bot to your server.  

5. Assign Roles:  
   - In your Discord server, go to "Server Settings > Roles".  
   - Create a role for the bot with the above permissions (or higher).  
   - Assign this role to your bot.  

---

## 🚀 4. Run the Bot  

python rivbot-discord.py  

---

## 🔧 Troubleshooting  

### ❌ Bot not starting?  
- Check config.json for missing values.  
- Ensure Python and dependencies are installed.  

### ❌ No response in Discord?  
- Confirm the bot is online and intents are enabled.  
- Verify that the Riven server URL is correct.  

### ❌ API errors?  
- Double-check tokens and API keys.  
- Test API URLs in a browser or with curl.  

### ❌ Commands not working?  
- Ensure your username is in the whitelist.  
- Use the correct command prefix (e.g., !health).  
