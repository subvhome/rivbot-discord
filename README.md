# Discord Riven Bot
A Discord bot for managing media items in Riven using TMDB, featuring interactive dropdowns and buttons.

## Quick Start
1. **Clone**: `git clone https://github.com/subvhome/DiscordRivenBot.git`
2. **Install**: `pip install discord.py requests`
3. **Config**: Copy `config.example.json` to `config.json` and edit (see [SETUP.md](SETUP.md)).
4. **Run**: `python rivbot-discord.py`

## Prerequisites
- Python 3.8+
- Discord bot token
- Riven server with API token
- TMDB API key

## Commands
- `!health`: Check Riven status.
- `!search <query>`: Search and manage items.
- `!logs`: View logs.
- `!services`: List services.

## Contributing
Fork, submit pull requests, or open issues! See [SETUP.md](SETUP.md) for detailed setup.

## Notes
- Requires a running Riven instance.
- Keep `config.json` private (ignored by `.gitignore`).
