# Discord Riven Bot  

A Discord bot for managing media items in Riven using TMDB integration, featuring interactive dropdowns, buttons, and detailed media management commands.  

## Quick Start  

1. **Clone the Repository**  
   ```sh
   git clone https://github.com/subvhome/DiscordRivenBot.git
   ```
2. **Install Dependencies**  
   ```sh
   pip install discord.py requests
   ```
3. **Configure the Bot**  
   - Copy the example config file and edit it:  
     ```sh
     cp config.example.json config.json  # Linux/macOS
     # Windows: copy config.example.json config.json
     ```
4. **Run the Bot**  
   ```sh
   python rivbot-discord-v2.8.3.py
   ```

---

## Prerequisites  

Ensure you have the following before running the bot:  

- **Python 3.8+**  
- **Discord bot token**  
- **Riven server with API token**  
- **TMDB API key**  

---

## Commands  

- **`!health`** – Check if the Riven server is up and running.  
- **`!search <query>`** – Search TMDB for movies or TV shows and manage them with interactive dropdowns and buttons (`Add, Remove, Retry, Reset, Scrape, Magnets, Refresh`).  
- **`!recentlyadded [n]`** – Display the last `n` items (max 10) added to Riven, with posters and details in embeds.  
- **`!status`** – Show Riven stats (`total shows, movies, completed, incomplete, failed`).  
- **`!logs`** – View recent Riven logs.  
- **`!services`** – List Riven services and their statuses.  
- **`!help`** – Display a list of available commands.  

---

## Features  

✅ **Search and manage media** with **TMDB integration**  
✅ **Interactive UI** with **dropdowns** for selecting items, seasons, and episodes  
✅ **Buttons** for managing media: `Add, Remove, Retry, Reset, Scrape, Fetch Magnets`  
✅ **Embed support** for rich media displays (`!recentlyadded` shows posters)  
✅ **Whitelist-based access control** for bot commands  

---

## Contributing  

- **Fork** the repository  
- **Make changes** and submit a **pull request**  
- Report bugs or suggest features via **GitHub issues**  
- See [SETUP.md](SETUP.md) for setup details  

---

## Notes  

⚠️ **Requires a running Riven instance with API access**  
⚠️ **Keep `config.json` private** – it’s excluded via `.gitignore`  
⚠️ **Logs** can be saved to `bot.log` if `log_to_file` is enabled in `config.json`  
