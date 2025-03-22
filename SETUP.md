# Setup Guide for Discord Riven Bot  

This guide provides step-by-step instructions to set up and run the Discord Riven Bot.  

## Prerequisites  

Before starting, make sure you have the following installed:  

- **Python 3.8 or higher**: [Download](https://www.python.org/downloads/)  
- **Git**: [Download](https://git-scm.com/downloads)  
- **Discord Account**: [Sign up](https://discord.com/register)  
- **Riven Server**: A running instance with API access. [Riven Docs](#)  
- **TMDB Account**: For API key. [Sign up](https://www.themoviedb.org/signup)  

## 1. Clone the Repository  

```sh
git clone https://github.com/subvhome/DiscordRivenBot.git
cd DiscordRivenBot
```

## 2. Install Dependencies  

### Optional: Create a Virtual Environment  

```sh
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# Windows: venv\Scripts\activate
```

### Install Required Packages  

```sh
pip install discord.py requests
```

## 3. Configure the Bot  

### Copy the Example Config  

```sh
cp config.example.json config.json  # Linux/macOS
# Windows: copy config.example.json config.json
```

### Edit `config.json`  

Open `config.json` in a text editor and update the fields (see below).  

## 4. Run the Bot  

Start the bot:  

```sh
python rivbot-discord.py
```

### Invite the Bot to Your Server  

Use the `discord_bot_token` to generate an invite URL (see instructions below).  

---

## Configuration Details  

Edit `config.json` with the following fields:  

```json
{
    "riven_api_url": "http://localhost:8080/api/v1",
    "riven_api_token": "your_riven_api_token_here",
    "discord_bot_token": "your_discord_bot_token_here",
    "whitelist": ["your_discord_username#1234"],
    "bot_prefix": "!",
    "tmdb_api_key": "your_tmdb_api_key_here",
    "log_to_file": true
}
```

### Field Explanations  

- **`riven_api_url`**  
  - URL of your Riven API.  
  - Default: `"http://localhost:8080/api/v1"`  
  - For remote servers: `"http://yourserver:8080/api/v1"`  

- **`riven_api_token`**  
  - Authentication token from your Riven server.  
  - Check Riven's admin panel or config files.  

- **`discord_bot_token`**  
  - Token for your Discord bot.  
  - **How to get it:**
    1. Go to [Discord Developer Portal](https://discord.com/developers/applications).  
    2. Create a new application (e.g., "RivenBot").  
    3. Go to the **Bot** tab, click **Add Bot**, then **Copy Token**.  
    4. Enable **Presence Intent**, **Server Members Intent**, and **Message Content Intent**.  
    5. Under **OAuth2 > URL Generator**:
       - Scopes: `bot`
       - Permissions: `Send Messages`, `Read Messages/View Channels`, `Embed Links`, `Attach Files`
       - Copy the URL and invite the bot to your server.  

- **`whitelist`**  
  - List of authorized Discord users (format: `username#1234`).  
  - Example: `["subvhome#1234", "friend#5678"]`  

- **`bot_prefix`**  
  - Command prefix (e.g., `!health`).  
  - Default: `"!"`  

- **`tmdb_api_key`**  
  - API key for TMDB.  
  - **How to get it:**
    1. Sign up at [TMDB](https://www.themoviedb.org/).  
    2. Go to **Settings > API**, request a **v3 key**, and copy it.  

- **`log_to_file`**  
  - Set to `true` to log output to `bot.log`.  

---

## Troubleshooting  

### Bot not starting?  
- Check `config.json` for missing or incorrect values.  
- Ensure **Python** and dependencies are installed.  

### No response in Discord?  
- Confirm the bot is **online** and **intents are enabled**.  
- Verify that the **Riven server is running** and URL is correct.  

### API errors?  
- Double-check **tokens and API keys**.  
- Test API URLs in a **browser** or with `curl`.  

### Commands not working?  
- Ensure your username is in **whitelist**.  
- Use the correct **command prefix** (e.g., `!health`).  
