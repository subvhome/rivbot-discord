# rivbot-discord

A Discord bot for managing and discovering media items in Riven with TMDB integration. It allows users to search for new content and manage existing media directly from Discord.

---

## 🚀 Docker Quick Start

You can run this bot with Docker in just a few steps:

### 1. Clone the Repository

```bash
git clone https://github.com/subvhome/rivbot-discord.git
cd rivbot-discord
```

### 2. Edit the Config

Create/Update the `data/config.json` file with your own tokens and preferences. You can copy and modify `data/config.example.json`and save it as `data/config.json`

### 3. Build & Run with Docker Compose

```bash
docker compose up -d --build
```

This builds the image and starts the bot in a container. Make sure Docker and Docker Compose are installed.

---

## 🧪 Manual Installation (No Docker)

### 1. Clone the Repository

```bash
git clone https://github.com/subvhome/rivbot-discord.git
cd rivbot-discord
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit the `./data/config.json` file with your API keys and settings. For example:

```json
{
    "riven_api_url": "http://localhost:8080/api/v1",
    "riven_api_token": "riven_api_token",
    "discord_bot_token": "discord_bot_token",
    "whitelist": ["you_discord_username", "username2"],
    "bot_prefix": "!",
    "tmdb_api_key": "tmdb_api_token",
    "log_to_file": true,
    "trakt_api_key": "keyplaceholder",
    "latest_releases_count": 4,
    "max_grid_width": 300,
    "poster_grid_columns": 2,
    "poster_image_width": 150,
    "poster_image_height": 220
}
```

### 4. Run the Bot

```bash
python rivbot-discord.py
```

---

## 🛠 Commands

- **!health** – Check if the Riven server is running.
- **!search <query>** – Search TMDB for movies/TV shows. Supports year-specific searches (e.g., `!search Pokemon 1997`). Fully supported film scraping. Series scraping is in the works.
- **!recentlyadded [n]** – Show the last n items added to Riven (max 10).
- **!status** – Display Riven stats (total shows, movies, completed, failed).
- **!logs** – View recent logs. [WIP]
- **!services** – List Riven services and their statuses.
- **!latestreleases** – Fetch the latest releases from Trakt, build a poster grid image of all titles, and display a select menu for managing them.
- **!help** – Show all available commands.

---

## ⚙️ Configuration

All configuration settings (API keys, release count, grid dimensions, etc.) are set in `config.json`. See the sample above for the required keys.

---

## 🤝 Contributing

- Fork the repository.
- Make your changes and submit a pull request.
- Report bugs or suggest features via GitHub issues.

---

## ⚠️ Notes

- Requires a running Riven instance with API access.
- The bot integrates with TMDB for media discovery and manages content on Riven.
- The `!latestreleases` command sends a full-width image (as a file attachment) of poster grids along with an interactive select menu.
- Keep `config.json` private (ensure it’s excluded via `.gitignore`).
- Logs are saved to `bot.log` if `log_to_file` is enabled.
- Scrape and Magnet buttons are not functional yet. Should be in a new release.
