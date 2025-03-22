# 🛠 Setup Guide for rivbot-discord  

Follow these steps to install and configure the bot.  

## 📋 Prerequisites  

Before running the bot, ensure you have:  

- **Python 3.8+** ([Download](https://www.python.org/downloads/))  
- **Git** ([Download](https://git-scm.com/downloads))  
- **A Discord Bot Token** (from the [Discord Developer Portal](https://discord.com/developers/applications))  
- **A Running Riven Server** with API access  
- **A TMDB API Key** ([Sign up here](https://www.themoviedb.org/signup))  

---

## 📥 1. Clone the Repository  

```sh
git clone https://github.com/subvhome/rivbot-discord.git
cd rivbot-discord
```

---

## 📦 2. Install Dependencies  

```sh
pip install -r requirements.txt
```

---

## ⚙️ 3. Configure the Bot  

1. **Copy the example config file:**  
   ```sh
   cp config.example.json config.json  # Linux/macOS
   # Windows: copy config.example.json config.json
   ```
2. **Edit `config.json`** in a text editor and update the required fields:  

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

### 🔹 How to Get Your Discord Bot Token  
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).  
2. Create a new **application** (e.g., "RivenBot").  
3. Navigate to the **Bot** tab → Click **Add Bot** → **Copy Token**.  
4. Enable:  
   - ✅ Presence Intent  
   - ✅ Server Members Intent  
   - ✅ Message Content Intent  
5. Under **OAuth2 > URL Generator**, select:  
   - **Scopes:** `bot`  
   - **Permissions:** `Send Messages`, `Read Messages/View Channels`, `Embed Links`, `Attach Files`  
6. Copy the generated URL and **invite the bot** to your server.  

---

## 🚀 4. Run the Bot  

```sh
python rivbot-discord.py
```

---

## 🔧 Troubleshooting  

### ❌ Bot not starting?  
- Check `config.json` for missing values.  
- Ensure **Python** and dependencies are installed.  

### ❌ No response in Discord?  
- Confirm the bot is **online** and **intents are enabled**.  
- Verify that the **Riven server URL is correct**.  

### ❌ API errors?  
- Double-check **tokens and API keys**.  
- Test API URLs in a **browser** or with `curl`.  

### ❌ Commands not working?  
- Ensure your username is in the **whitelist**.  
- Use the correct **command prefix** (e.g., `!health`).  
