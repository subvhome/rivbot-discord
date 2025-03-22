# rivbot-discord  

A **Discord bot** for managing media items in **Riven** using **TMDB integration**.  
Features **interactive dropdowns, buttons, and detailed media management commands**.  

## 📌 Features  

✅ **Search & manage media** with **TMDB integration**  
✅ **Interactive UI** with **dropdowns** for selecting items, seasons, and episodes  
✅ **Buttons** for managing media (`Add, Remove, Retry, Reset, Scrape, Magnets, Refresh`)  
✅ **Embed support** (`!recentlyadded` shows posters)  
✅ **Whitelist-based access control**  

## 🚀 Quick Start  

For installation and setup, see **[SETUP.md](SETUP.md)**.  

1. Clone the repository:  
   ```sh
   git clone https://github.com/subvhome/rivbot-discord.git
   cd rivbot-discord
   ```
2. Install dependencies:  
   ```sh
   pip install -r requirements.txt
   ```
3. Run the bot:  
   ```sh
   python rivbot-discord.py
   ```

## 🛠 Commands  

- **`!health`** – Check if the Riven server is running.  
- **`!search <query>`** – Search TMDB for movies/TV shows & manage them.  
- **`!recentlyadded [n]`** – Show the last `n` items added to Riven (max 10).  
- **`!status`** – Display Riven stats (`total shows, movies, completed, failed`).  
- **`!logs`** – View recent logs.  
- **`!services`** – List Riven services & their statuses.  
- **`!help`** – Show all available commands.  

## ⚙️ Configuration  

Edit `config.json` (see **[SETUP.md](SETUP.md)** for details).  

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

## 🤝 Contributing  

- **Fork** the repository  
- **Make changes** and submit a **pull request**  
- Report bugs or suggest features via **GitHub issues**  

## ⚠️ Notes  

- Requires a **running Riven instance** with API access  
- Keep **`config.json` private** (excluded via `.gitignore`)  
- Logs are saved to `bot.log` if `log_to_file` is enabled  
