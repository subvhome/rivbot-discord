# Setup Guide for Discord Riven Bot

## Full Setup Steps

### 1. Clone the Repository
Clone the repo to your machine:
```sh
git clone https://github.com/subvhome/DiscordRivenBot.git
cd DiscordRivenBot
```

### 2. Install Dependencies
- **Optional**: Create a virtual environment to keep things tidy:
  ```sh
  python3 -m venv venv
  source venv/bin/activate  # Linux/macOS
  venv\Scripts\activate     # Windows
  ```
- Install the required Python packages:
  ```sh
  pip install discord.py requests
  ```

### 3. Configure the Bot
- Copy the example configuration file:
  ```sh
  cp config.example.json config.json
  ```
- Edit `config.json` with your specific details (see [Configuration](#configuration-configjson) section below).

### 4. Run the Bot
- Start the bot:
  ```sh
  python rivbot-discord.py
  ```
- Invite the bot to your Discord server using the token from `config.json` (instructions in [Configuration](#configuration-configjson)).

---

## Configuration (`config.json`)

Create `config.json` by copying `config.example.json` and filling in these fields:

```json
{
  "riven_api_url": "http://localhost:8080/api/v1",
  "riven_api_token": "your_riven_api_token_here",
  "discord_bot_token": "your_discord_bot_token_here",
  "whitelist": ["your_discord_username#1234"],
  "bot_prefix": "/",
  "tmdb_api_key": "your_tmdb_api_key_here"
}
```

- **`riven_api_url`**: The URL of your Riven server’s API endpoint.  
  - Default: `"http://localhost:8080/api/v1"` (for a local Riven instance).  
  - Replace with your server’s IP or domain if hosted remotely, e.g., `"http://yourserver:8080/api/v1"`.  

- **`riven_api_token`**: Your Riven API authentication token.  
  - Obtain this from your Riven server’s admin panel or configuration.  
  - Example: `"your_riven_api_key_here"`.  

- **`discord_bot_token`**: The token for your Discord bot.  
  - Get it from the Discord Developer Portal: [Discord Developer Portal](https://discord.com/developers/applications)  
  - Steps to obtain:
    1. Create a New Application, name it (e.g., `"RivenBot"`), and click **Create**.
    2. Go to the **Bot** tab, click **Add Bot**, then **Copy Token** (reset if needed).
    3. Enable **Presence Intent**, **Server Members Intent**, and **Message Content Intent** under Bot settings.
    4. Go to **OAuth2 > URL Generator**, select:
       - **Scopes**: `bot`
       - **Permissions**: `Send Messages`, `Read Messages/View Channels`, `Use Slash Commands`
       - Copy the generated URL and invite the bot to your server.
  - Example: `"NjYxMjM0NTY3ODkwMTIzNDU2.XgXxXw.abcdefg1234567890"`.  

- **`whitelist`**: A list of Discord usernames (in `username#discriminator` format) allowed to use the bot.  
  - Replace with your Discord username and any others you want to authorize.  
  - Example: `["subvhome#1234", "friend#5678"]`.  

- **`bot_prefix`**: The prefix for bot commands (e.g., `/health`).  
  - Default: `"/"`.  
  - Change to `"!"`, `"$"`, or any prefix you prefer.  
  - Example: `"!"`.  

- **`tmdb_api_key`**: Your TMDB API key for media searches.  
  - Obtain it from [The Movie Database](https://www.themoviedb.org/):  
    1. Sign up or log in, go to **Settings > API**, and request an API key (v3).
    2. Copy the `"API Key (v3 auth)"` (not v4 token).
  - Example: `"your_tmdb_api_key_here"`.  

---

## Troubleshooting

- **Bot not starting?**  
  - Double-check `config.json` for typos or missing values.  

- **No response in Discord?**  
  - Ensure your Riven server is running and reachable.  
  - Verify that Discord intents are enabled in the Developer Portal.  
