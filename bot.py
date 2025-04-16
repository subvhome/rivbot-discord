import discord
import requests
import io
import json
import logging
from discord.ext import commands
from discord import File, Intents
from config.config_loader import load_config
from core.logging_setup import logger
from core.riven_api import query_riven_api, handle_api_response, health_check
from embeds.media_embed import create_media_embed
from helpers.auth import check_authorization
from helpers.response import send_response
from helpers.poster_grid import create_poster_grid
from tmdb.search import search_tmdb_extended
from tmdb.details import fetch_tmdb_by_id
from tmdb.episodes import fetch_tmdb_episodes
from ui.dropdowns import SearchDropdown, LatestReleasesDropdown
from ui.views import SearchView, LatestReleasesView

config = load_config()

if config.get('log_to_file', False):
    file_handler = logging.FileHandler('bot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info("File logging enabled; logs will be written to bot.log")


intents = Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix=config["bot_prefix"], intents=intents)
bot.config = config
bot.active_recommended_messages = {}


@bot.event
async def on_ready():
    logger.info(f"Bot online as {bot.user}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.guild_id is None:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception as e:
            logger.error(f"Failed to fetch DM channel {payload.channel_id}: {e}")
            return
    else:
        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            logger.error(f"Could not resolve channel for ID {payload.channel_id}")
            return
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        logger.error(f"Failed to fetch message {payload.message_id}: {e}")
        return
    if message.id not in bot.active_recommended_messages:
        logger.debug(f"Reaction on untracked message {message.id}")
        return
    view = bot.active_recommended_messages[message.id]
    if payload.user_id != view.initiator_id:
        logger.info(f"Ignoring reaction from user {payload.user_id} (not initiator)")
        return
    reaction_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    emoji_str = payload.emoji.name
    if emoji_str in reaction_emojis[:len(view.recommended_ids)]:
        selected_index = reaction_emojis.index(emoji_str)
        new_tmdb_id = view.recommended_ids[selected_index]
        new_item = fetch_tmdb_by_id(new_tmdb_id, view.media_type, bot.config)
        if new_item:
            view.selected_item = new_item
            view.seasons = new_item[9] if view.media_type == "tv" else []
            view.riven_id = None
            view.riven_data = None
            name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, _, _ = new_item
            logger.info(f"Reaction selected {name} (TMDB: {tmdb_id})")
            riven_response = query_riven_api("items", bot.config, params={"search": name, "limit": 5})
            riven_state = "Not in Riven"
            if riven_response.get("success", False) and "items" in riven_response:
                for item in riven_response["items"]:
                    if item.get("tmdb_id") == str(tmdb_id) or item.get("imdb_id") == imdb_id:
                        view.riven_id = item.get("id")
                        riven_state = item.get("state", "Unknown")
                        break
            view.update_view()
            recommended_response = requests.get(
                f"https://api.themoviedb.org/3/{view.media_type}/{tmdb_id}/recommendations",
                params={"api_key": bot.config['tmdb_api_key']}
            )
            recommended_data = recommended_response.json().get("results", [])[:5]
            emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            recommended_titles = [
                f"{emoji_numbers[i]} {item['title' if view.media_type == 'movie' else 'name']} ({item.get('release_date', 'N/A')[:4] if view.media_type == 'movie' else item.get('first_air_date', 'N/A')[:4]}) - ★ {item['vote_average']}/10"
                for i, item in enumerate(recommended_data)
            ]
            view.recommended_ids = [item['id'] for item in recommended_data]
            embed = create_media_embed(view.query, name, year, rating, vote_count, description, imdb_id, tmdb_id, poster, riven_state, recommended_titles)
            await message.edit(embed=embed, view=view)
            if payload.guild_id is None:
                logger.info("Skipping clear_reactions in a DM channel.")
            else:
                await message.clear_reactions()
                for emoji in reaction_emojis[:len(view.recommended_ids)]:
                    await message.add_reaction(emoji)
                    logger.info(f"Re-added reaction {emoji} to message {message.id}")

@bot.command(name="latestreleases")
async def latest_releases(ctx):
    """Fetch the latest N releases from Trakt, create a full-width poster grid image, and send it as a file with an attached select menu.
    
    All required configuration keys must be present in config.json.
    The message will consist solely of the image attachment and the select menu.
    """
    await ctx.defer()

    # REQUIRED CONFIG KEYS – must exist in config.json (no defaults)
    required_keys = [
        "trakt_api_key",
        "tmdb_api_key",
        "latest_releases_count",
        "max_grid_width",
        "poster_image_width",
        "poster_image_height"
    ]
    for key in required_keys:
        if key not in config:
            await ctx.send(f"Error: Missing required config key: `{key}`")
            return

    # Load required config values.
    trakt_api_key = config["trakt_api_key"]
    tmdb_api_key = config["tmdb_api_key"]
    latest_count = config["latest_releases_count"]
    max_grid_width = config["max_grid_width"]
    poster_width = config["poster_image_width"]
    poster_height = config["poster_image_height"]

    trakt_url = "https://api.trakt.tv/users/garycrawfordgc/lists/latest-releases/items"
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": trakt_api_key
    }

    try:
        response = requests.get(trakt_url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json()

        results = []       # For the select menu: (title, year, rating, tmdb_id, media_type)
        poster_info = []   # For building the poster grid: dict with keys "title" and "poster_url"

        for item in items[:latest_count]:
            media_type = item.get("type")
            if media_type == "movie":
                media = item.get("movie", {})
            elif media_type == "show":
                media = item.get("show", {})
            else:
                continue

            title = media.get("title", "Unknown")
            year = media.get("year", "Unknown")
            tmdb_id = media.get("ids", {}).get("tmdb")
            rating = "N/A"   # Default rating
            poster_url = None

            if tmdb_id:
                tmdb_url = f"https://api.themoviedb.org/3/{'tv' if media_type=='show' else 'movie'}/{tmdb_id}"
                tmdb_params = {"api_key": tmdb_api_key}
                tmdb_response = requests.get(tmdb_url, params=tmdb_params, timeout=10)
                if tmdb_response.status_code == 200:
                    tmdb_data = tmdb_response.json()
                    rating = tmdb_data.get("vote_average", "N/A")
                    poster_path = tmdb_data.get("poster_path")
                    if poster_path:
                        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            
            logger.info(f"Fetched: {title} ({year}) with rating: {rating}")
            results.append((title, year, rating, tmdb_id, media_type))
            poster_info.append({"title": title, "poster_url": poster_url})

        if not results:
            await ctx.send(f"No new releases found in the latest {latest_count} entries.")
            return

        # Create the poster grid image.
        grid_image = await create_poster_grid(poster_info)
        image_buffer = io.BytesIO()
        grid_image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        view = SearchView(ctx, results, query=f"Latest {latest_count} Releases")
        await ctx.send(file=discord.File(fp=image_buffer, filename="poster_grid.png"), view=view)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching latest releases from Trakt: {e}")
        await ctx.send("Failed to retrieve latest releases. Please try again later.")

@bot.command()
async def health(ctx):
    logger.info(f"{ctx.author} ran health")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, "You’re not authorized!")
        return
    await send_response(ctx, await health_check(config))

@bot.command()
async def search(ctx, *, query=None):
    logger.info(f"{ctx.author} searching '{query}'")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, "You’re not authorized!")
        return
    if not query:
        await send_response(ctx, "Usage: {0}search <query>".format(ctx.prefix))
        return
    results = search_tmdb_extended(query, config)
    if isinstance(results, dict) and "error" in results:
        await send_response(ctx, results["error"])
        return
    if not results:
        await send_response(ctx, f"No results for '{query}'")
        return
    view = SearchView(ctx, results, query)
    # Create initial embed for the first page of results
    start = (view.page - 1) * 10
    end = start + 10
    page_results = view.all_results[start:end]
    embed = discord.Embed(title=f"🔎 Results for '{query}'", description="Select an item below to view details.")
    await ctx.send(embed=embed, view=view)

@bot.command()
async def recentlyadded(ctx, n: int = 10):
    logger.info(f"{ctx.author} ran recentlyadded with n={n}")
    if str(ctx.author) not in config["whitelist"]:
        await ctx.send("You’re not authorized!")
        return
    if n < 1 or n > 10:
        await ctx.send("Number must be between 1 and 10.")
        return
    data = query_riven_api("items", config, params={"sort": "date_desc", "limit": n, "type": "movie,show"})
    if "error" in data:
        await ctx.send(f"Error: {data['error']}")
        return
    items = data.get("items", [])
    if not items:
        await ctx.send("No recent items.")
        return
    embeds = []
    for item in items[:10]:
        title = item.get("title", "Unknown")
        item_type = item.get("type", "Unknown").lower()
        state = item.get("state", "Unknown")
        tmdb_id = item.get("tmdb_id")
        poster_url = "https://image.tmdb.org/t/p/original/null"
        if tmdb_id:
            tmdb_url = f"https://api.themoviedb.org/3/{'movie' if item_type == 'movie' else 'tv'}/{tmdb_id}"
            response = requests.get(tmdb_url, params={"api_key": config["tmdb_api_key"]})
            if response.status_code == 200:
                poster_path = response.json().get("poster_path")
                if poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
        embed = discord.Embed(title=f"{item_type.capitalize()}: {title}", description=f"State: {state}")
        embed.set_image(url=poster_url)
        embeds.append(embed)
    await ctx.send(f"**Recently Added (Top {len(embeds)}):**")
    for i in range(0, len(embeds), 5):
        await ctx.send(embeds=embeds[i:i+5])

@bot.command()
async def status(ctx):
    logger.info(f"{ctx.author} ran status")
    if str(ctx.author) not in config["whitelist"]:
        await ctx.send("You’re not authorized!")
        return
    data = query_riven_api("stats", config)
    if "error" in data:
        await ctx.send(f"Error: {data['error']}")
        return
    status_text = (
        f"**Riven Status:**\n"
        f"Shows: {data.get('total_shows', 0)}\n"
        f"Movies: {data.get('total_movies', 0)}\n"
        f"Completed: {data.get('states', {}).get('Completed', 0)}\n"
        f"Incomplete: {data.get('incomplete_items', 0)}\n"
        f"Failed: {data.get('states', {}).get('Failed', 0)}"
    )
    await ctx.send(status_text)

@bot.command()
async def logs(ctx):
    logger.info(f"{ctx.author} ran logs")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, "You’re not authorized!")
        return
    data = query_riven_api("logs", config)
    if "error" in data:
        await send_response(ctx, f"Error: {data['error']}")
    else:
        logs = json.dumps(data, indent=2)[:1000]
        await send_response(ctx, f"Recent Logs:\n```\n{logs}\n```")

@bot.command()
async def services(ctx):
    logger.info(f"{ctx.author} ran services")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, "You’re not authorized!")
        return
    data = query_riven_api("services", config)
    if "error" in data:
        await send_response(ctx, f"Error: {data['error']}")
    else:
        services = "\n".join([f"- {s}: {'Enabled' if v else 'Disabled'}" for s, v in data.items()])
        await send_response(ctx, f"Services:\n{services}")

bot.run(config["discord_bot_token"])
