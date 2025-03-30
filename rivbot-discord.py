import json
import requests
import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
import asyncio
import io
from io import StringIO
from discord.ui import Select, View, Button
from discord.ui.button import ButtonStyle
from discord import SelectOption
import math
import re
from PIL import Image, ImageOps

# SECTION 1 - Setup logging with detailed output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# SECTION 2 - Load configuration with error handling
def load_config():
    try:
        with open("config.json", "r") as f:
            logger.info("Loading config.json")
            config = json.load(f)
            logger.info("Config loaded successfully")
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config.json: {e}")
        raise

config = load_config()

# SECTION 3 - Enable file logging if specified in config
if config.get('log_to_file', False):
    file_handler = logging.FileHandler('bot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info("File logging enabled; logs will be written to bot.log")

# SECTION 4 - **Helper function to handle API responses**
def handle_api_response(response):
    if "error" in response:
        return None, response["error"]
    return response, None

# SECTION 5 **Helper function to create media embed**
def create_media_embed(query, title, year, rating, vote_count, description, imdb_id, tmdb_id, poster, riven_state, recommended_titles=None):
    embed = discord.Embed(title=f"🔎 Results for '{query}'")

    # Create IMDb link if available, otherwise use plain title
    if imdb_id != 'N/A':
        title_display = f"[{title} ({year})](https://www.imdb.com/title/{imdb_id}/)"
    else:
        title_display = f"{title} ({year})"

    media_card = (
        f"**{title_display}**\n"
        f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
        f"📝 {description}\n"
        f"🔄 Riven: {riven_state}\n\n"
    )

    if recommended_titles:
        media_card += "Reaction at the bottom to select a title:\n"
        media_card += "**Recommended Titles:**\n"
        media_card += "\n".join(recommended_titles)

    embed.description = media_card.strip()
    embed.set_thumbnail(url=poster)
    embed.set_image(url=poster)
    return embed

# SECTION 6 - **Helper function to check authorization**
async def check_authorization(interaction, initiator_id):
    if interaction.user.id != initiator_id:
        await interaction.response.send_message("Not your button!", ephemeral=True)
        return False
    return True

# SECTION 7 - Send response based on content length
async def send_response(ctx, content):
    content_str = str(content)
    logger.info(f"Sending response to {ctx.author}: {content_str[:50]}...")
    if len(content_str) <= 2000:
        await ctx.send(content_str)
    else:
        file_content = StringIO(content_str)
        file = discord.File(file_content, filename="output.txt")
        await ctx.send("Output too long, here’s a file:", file=file)
        file_content.close()
    logger.info(f"Response sent to {ctx.author}")

# SECTION 8 - Query Riven API with logging
def query_riven_api(endpoint, config, method="GET", params=None, json_data=None):
    url = f"{config['riven_api_url']}/{endpoint}"
    headers = {"x-api-key": config["riven_api_token"]}
    logger.info(f"Querying Riven API: {method} {url} with params={params}, json={json_data}")
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, params=params, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Riven API response: {data}")
        return data
    except requests.RequestException as e:
        error_msg = f"API error: {e}"
        logger.error(f"Riven API failed for {endpoint}: {error_msg}")
        return {"error": error_msg}

# SECTION 9 - Health check function
async def health_check(config):
    health_url = f"{config['riven_api_url']}/health"
    headers = {"Authorization": f"Bearer {config['riven_api_token']}"}
    logger.info(f"Checking Riven health at {health_url}")
    try:
        response = requests.get(health_url, headers=headers)
        response.raise_for_status()
        logger.info("Riven API is healthy")
        return "Riven is up and running!"
    except requests.RequestException as e:
        logger.error(f"Health check failed: {e}")
        return f"Health check failed: {e}"

# SECTION 10 - Search TMDB with extended details
def search_tmdb_extended(query, config, max_pages=5):
    api_key = config["tmdb_api_key"]
    base_url = "https://api.themoviedb.org/3"
    results = []

    # Check if query ends with a 4-digit year
    match = re.search(r'\b(\d{4})\b$', query.strip())
    if match:
        year = int(match.group(1))
        query_without_year = re.sub(r'\s*\b\d{4}\b$', '', query).strip()
        logger.info(f"Query with year: '{query_without_year}' in {year}")
        # Search movies with year (up to 2 pages)
        for page in range(1, 3):
            url = f"{base_url}/search/movie?api_key={api_key}&query={query_without_year}&year={year}&page={page}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", []):
                    name = item.get("title", "Unknown")
                    release_date = item.get("release_date", "")
                    item_year = release_date[:4] if release_date else "N/A"
                    rating = item.get("vote_average", "N/A")
                    tmdb_id = item.get("id")
                    media_type = "movie"
                    results.append((name, item_year, rating, tmdb_id, media_type))
                if len(data.get("results", [])) < 20:  # Less than a full page
                    break
            else:
                logger.error(f"Movie search page {page} failed: {response.status_code}")
                break
        # Search TV shows with year (up to 2 pages)
        for page in range(1, 3):
            url = f"{base_url}/search/tv?api_key={api_key}&query={query_without_year}&first_air_date_year={year}&page={page}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", []):
                    name = item.get("name", "Unknown")
                    first_air_date = item.get("first_air_date", "")
                    item_year = first_air_date[:4] if first_air_date else "N/A"
                    rating = item.get("vote_average", "N/A")
                    tmdb_id = item.get("id")
                    media_type = "tv"
                    results.append((name, item_year, rating, tmdb_id, media_type))
                if len(data.get("results", [])) < 20:
                    break
            else:
                logger.error(f"TV search page {page} failed: {response.status_code}")
                break
    else:
        # General multi-search without year (up to max_pages, default 5)
        for page in range(1, max_pages + 1):
            url = f"{base_url}/search/multi?api_key={api_key}&query={query}&page={page}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", []):
                    if item["media_type"] in ["movie", "tv"]:
                        name = item.get("title" if item["media_type"] == "movie" else "name", "Unknown")
                        date_key = "release_date" if item["media_type"] == "movie" else "first_air_date"
                        item_year = item.get(date_key, "")[:4] if item.get(date_key) else "N/A"
                        rating = item.get("vote_average", "N/A")
                        tmdb_id = item.get("id")
                        media_type = item["media_type"]
                        results.append((name, item_year, rating, tmdb_id, media_type))
                if len(data.get("results", [])) < 20:
                    break
            else:
                logger.error(f"Multi-search page {page} failed: {response.status_code}")
                break

    logger.info(f"Found {len(results)} TMDB results for '{query}'")
    return results

# SECTION 11 - Fetch TMDB episodes
def fetch_tmdb_episodes(tmdb_id, season_number, config):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}"
    params = {"api_key": config["tmdb_api_key"]}
    logger.info(f"Fetching episodes for TMDB ID {tmdb_id}, Season {season_number}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        episodes = [(e["episode_number"], e["name"], e["overview"][:97] + "..." if len(e["overview"]) > 97 else e["overview"]) for e in data.get("episodes", [])]
        logger.info(f"Fetched {len(episodes)} episodes")
        return episodes
    except requests.RequestException as e:
        logger.error(f"Episode fetch failed: {e}")
        return {"error": str(e)}

# SECTION 12 - Fetch TMDB details by ID
def fetch_tmdb_by_id(tmdb_id, media_type, config):
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
    params = {"api_key": config["tmdb_api_key"]}
    logger.info(f"Fetching TMDB details for {media_type} ID {tmdb_id}")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        details = response.json()
        name = details.get("title", details.get("name", "Unknown"))
        year = details.get("release_date", details.get("first_air_date", ""))[:4]
        rating = details.get("vote_average", "N/A")
        vote_count = details.get("vote_count", 0)
        poster = f"https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}" if details.get("poster_path") else "No poster"
        description = details.get("overview", "No description")[:150] + "..." if len(details.get("overview", "")) > 150 else details.get("overview", "No description")
        imdb_id = details.get("imdb_id", "N/A") if media_type == "movie" else "N/A"
        if media_type == "tv":
            external_ids_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids"
            external_ids_response = requests.get(external_ids_url, params={"api_key": config["tmdb_api_key"]})
            external_ids_response.raise_for_status()
            imdb_id = external_ids_response.json().get("imdb_id", "N/A")
        seasons = [(s["season_number"], s["name"], s["episode_count"]) for s in details.get("seasons", [])] if media_type == "tv" else []
        logger.info(f"Fetched details for {name} (TMDB ID: {tmdb_id})")
        return (name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch TMDB details: {e}")
        return None

# SECTION 13 - Dropdown for selecting items, seasons, or episodes
class SearchDropdown(Select):
    def __init__(self, items, page, total_pages, dropdown_type="items", selected_value=None):
        self.items = items
        self.page = page
        self.total_pages = total_pages
        self.dropdown_type = dropdown_type
        options = []
        max_label_length = 100  # Discord label limit

        if dropdown_type == "items":
            for idx, (name, year, rating, tmdb_id, media_type) in enumerate(items):
                # Ensure the label length is within the valid range (1 to 100 characters)
                label = f"{name[:80]} ({year}) - Rating: {rating}/10"
                if len(label) < 1:
                    label = "Invalid Label"  # Fallback if the label is too short
                elif len(label) > max_label_length:
                    label = label[:max_label_length]  # Truncate if the label is too long
                options.append(SelectOption(label=label, description=f"TMDB: {tmdb_id}", value=str(idx + (page - 1) * 10)))

        elif dropdown_type == "seasons":
            for idx, (season_num, season_name, episode_count) in enumerate(items):
                # Ensure the label length is within the valid range (1 to 100 characters)
                label = f"Season {season_num} - {season_name[:80]}"
                if len(label) < 1:
                    label = "Invalid Label"  # Fallback if the label is too short
                elif len(label) > max_label_length:
                    label = label[:max_label_length]  # Truncate if the label is too long
                options.append(SelectOption(label=label, description=f"Episodes: {episode_count}", value=str(idx + (page - 1) * 25)))

        elif dropdown_type == "episodes":
            for idx, (ep_num, ep_name, ep_desc) in enumerate(items):
                # Ensure the label length is within the valid range (1 to 100 characters)
                label = f"Episode {ep_num} - {ep_name[:80]}"
                if len(label) < 1:
                    label = "Invalid Label"  # Fallback if the label is too short
                elif len(label) > max_label_length:
                    label = label[:max_label_length]  # Truncate if the label is too long
                options.append(SelectOption(label=label, description=ep_desc, value=str(idx + (page - 1) * 25)))

        super().__init__(placeholder=f"Select {dropdown_type.capitalize()} (Page {page}/{total_pages})", options=options)
        logger.info(f"Created {dropdown_type} dropdown with {len(options)} options")

    async def callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.view.initiator_id):
            return
        selected_value = self.values[0]
        # Adjust index calculation based on dropdown type
        if self.dropdown_type == "items":
            selected_idx = int(selected_value) % 10
            selected_basic = self.items[selected_idx]
            tmdb_id = selected_basic[3]
            media_type = selected_basic[4]
            full_item = fetch_tmdb_by_id(tmdb_id, media_type, self.view.ctx.bot.config)
            if full_item:
                self.view.selected_item = full_item
                name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = full_item
                self.view.media_type = media_type
                self.view.seasons = seasons if media_type == "tv" else []
                self.view.level = "show" if media_type == "tv" else "movie"
                riven_response = query_riven_api("items", self.view.ctx.bot.config, params={"search": name, "limit": 50})
                exists_in_riven = False
                riven_id = None
                riven_state = "Not in Riven"
                if riven_response.get("success", False) and "items" in riven_response:
                    for item in riven_response["items"]:
                        if item.get("tmdb_id") == str(tmdb_id) or item.get("imdb_id") == imdb_id:
                            exists_in_riven = True
                            riven_id = item.get("id")
                            riven_state = item.get("state", "Unknown")
                            logger.info(f"Item {name} found in Riven: ID {riven_id}, State {riven_state}")
                            break
                self.view.riven_id = riven_id
                self.view.update_view()
                recommended_response = requests.get(f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/recommendations", params={"api_key": self.view.ctx.bot.config["tmdb_api_key"]})
                recommended_data = recommended_response.json().get("results", [])[:5]
                emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                recommended_titles = [
                    f"{emoji_numbers[i]} {item['title' if media_type == 'movie' else 'name']} ({item['release_date' if media_type == 'movie' else 'first_air_date'][:4]}) - ★ {item['vote_average']}/10"
                    for i, item in enumerate(recommended_data)
                ]
                self.view.recommended_ids = [item['id'] for item in recommended_data]
                embed = create_media_embed(self.view.query, name, year, rating, vote_count, description, imdb_id, tmdb_id, poster, riven_state, recommended_titles)
                await interaction.response.edit_message(embed=embed, view=self.view)
                message = await interaction.original_response()
                bot.active_recommended_messages[message.id] = self.view
                reaction_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                for emoji in reaction_emojis[:len(self.view.recommended_ids)]:
                    await message.add_reaction(emoji)
                    logger.info(f"Added reaction {emoji} to message {message.id}")
            else:
                await interaction.response.send_message("Failed to fetch item details.", ephemeral=True)
                return
        elif self.dropdown_type == "seasons":
            selected_idx = int(selected_value) - (self.page - 1) * 25
            self.view.selected_season = self.items[selected_idx]
            season_num, season_name, _ = self.view.selected_season
            self.view.episodes = fetch_tmdb_episodes(self.view.selected_item[4], season_num, self.view.ctx.bot.config)
            self.view.level = "episode"
            self.view.update_view()
            name, year, _, imdb_id, tmdb_id, poster, description, vote_count, _, _ = self.view.selected_item
            riven_state = await self.view.get_riven_state()
            if imdb_id != 'N/A':
                title_display = f"[{name} ({year})](https://www.imdb.com/title/{imdb_id}/)"
            else:
                title_display = f"{name} ({year})"
            media_card = (
                f"**{title_display} - Season {season_num}: {season_name}**\n"
                f"📝 {description}\n"
                f"🔄 Riven: {riven_state}\n"
            ).strip()
            embed = discord.Embed(title=f"🔎 Results for '{self.view.query}'", description=media_card)
            embed.set_thumbnail(url=poster)
            embed.set_image(url=poster)
            await interaction.response.edit_message(embed=embed, view=self.view)
        elif self.dropdown_type == "episodes":
            selected_idx = int(selected_value) - (self.page - 1) * 25
            self.view.selected_episode = self.items[selected_idx]
            ep_num, ep_name, ep_desc = self.view.selected_episode
            name, year, _, imdb_id, tmdb_id, poster, _, vote_count, _, _ = self.view.selected_item
            season_num, season_name, _ = self.view.selected_season
            riven_state = await self.view.get_riven_state()
            if imdb_id != 'N/A':
                title_display = f"[{name} ({year})](https://www.imdb.com/title/{imdb_id}/)"
            else:
                title_display = f"{name} ({year})"
            media_card = (
                f"**{title_display} - S{season_num}: {season_name} - E{ep_num}: {ep_name}**\n"
                f"📝 {ep_desc}\n"
                f"🔄 Riven: {riven_state}\n"
            ).strip()
            embed = discord.Embed(title=f"🔎 Results for '{self.view.query}'", description=media_card)
            embed.set_thumbnail(url=poster)
            embed.set_image(url=poster)
            await interaction.response.edit_message(embed=embed, view=self.view)

# SECTION 14 - View class with buttons and reaction handling
class SearchView(View):
    def __init__(self, ctx, all_results, query, page=1):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.all_results = all_results
        self.query = query
        self.initiator_id = ctx.author.id
        self.page = page
        self.total_pages = math.ceil(len(all_results) / 10)
        self.selected_item = None
        self.selected_season = None
        self.selected_episode = None
        self.riven_id = None
        self.media_type = None
        self.level = "items"
        self.seasons = []
        self.episodes = []
        self.riven_data = None
        self.recommended_ids = []

        # Pagination attributes
        self.items_per_page = 10
        self.options_per_page = 25
        self.seasons_page = 1
        self.episodes_page = 1

        self.prev_button = Button(label="Previous", style=ButtonStyle.grey)
        self.prev_button.callback = self.prev_button_callback
        self.next_button = Button(label="Next", style=ButtonStyle.grey)
        self.next_button.callback = self.next_button_callback
        self.add_button = Button(label="Add", style=ButtonStyle.green)
        self.add_button.callback = self.add_button_callback
        self.remove_button = Button(label="Remove", style=ButtonStyle.red)
        self.remove_button.callback = self.remove_button_callback
        self.retry_button = Button(label="Retry", style=ButtonStyle.green)
        self.retry_button.callback = self.retry_button_callback
        self.reset_button = Button(label="Reset", style=ButtonStyle.blurple)
        self.reset_button.callback = self.reset_button_callback
        self.scrape_button = Button(label="Scrape", style=ButtonStyle.blurple)
        self.scrape_button.callback = self.scrape_button_callback
        self.magnets_button = Button(label="Magnets", style=ButtonStyle.grey)
        self.magnets_button.callback = self.magnets_button_callback
        self.refresh_button = Button(label="Refresh", style=ButtonStyle.grey)
        self.refresh_button.callback = self.refresh_button_callback

        self.update_view()
        logger.info(f"SearchView initialized for '{query}' with {len(all_results)} results")

    async def get_riven_state(self):
        if not self.riven_id:
            return "Not in Riven"
        if not self.riven_data:
            self.riven_data = query_riven_api(f"items/{self.riven_id}", self.ctx.bot.config)
        if "error" in self.riven_data:
            logger.error(f"Riven state fetch error: {self.riven_data['error']}")
            return f"Error: {self.riven_data['error']}"
        if self.level in ["show", "movie"]:
            return self.riven_data.get("state", "Unknown")
        elif self.level == "episode" and self.selected_season:
            season_num = self.selected_season[0]
            for season in self.riven_data.get("seasons", []):
                if season.get("number") == season_num:
                    if self.selected_episode:
                        ep_num = self.selected_episode[0]
                        for episode in season.get("episodes", []):
                            if episode.get("number") == ep_num:
                                return episode.get("state", "Unknown")
                    return season.get("state", "Unknown")
            return "Season not in Riven"
        return "Unknown"

    def update_view(self):
        self.clear_items()
        logger.info(f"Updating view to level '{self.level}', page {self.page}")
        if self.level == "items":
            start = (self.page - 1) * self.items_per_page
            end = start + self.items_per_page
            page_results = self.all_results[start:end]
            total_items_pages = math.ceil(len(self.all_results) / self.items_per_page)
            self.add_item(SearchDropdown(page_results, self.page, total_items_pages, "items"))
            if total_items_pages > 1:
                self.add_item(self.prev_button)
                self.add_item(self.next_button)
                self.prev_button.disabled = self.page == 1
                self.next_button.disabled = self.page == total_items_pages

        elif self.level == "show":
            total_seasons_pages = math.ceil(len(self.seasons) / self.options_per_page)
            start = (self.seasons_page - 1) * self.options_per_page
            end = start + self.options_per_page
            page_seasons = self.seasons[start:end]
            self.add_item(SearchDropdown(page_seasons, self.seasons_page, total_seasons_pages, "seasons"))
            if total_seasons_pages > 1:
                self.add_item(self.prev_button)
                self.add_item(self.next_button)
                self.prev_button.disabled = self.seasons_page == 1
                self.next_button.disabled = self.seasons_page == total_seasons_pages
            self.add_action_buttons(include_add_remove=True)

        elif self.level == "episode":
            total_episodes_pages = math.ceil(len(self.episodes) / self.options_per_page)
            start = (self.episodes_page - 1) * self.options_per_page
            end = start + self.options_per_page
            page_episodes = self.episodes[start:end]
            self.add_item(SearchDropdown(page_episodes, self.episodes_page, total_episodes_pages, "episodes"))
            if total_episodes_pages > 1:
                self.add_item(self.prev_button)
                self.add_item(self.next_button)
                self.prev_button.disabled = self.episodes_page == 1
                self.next_button.disabled = self.episodes_page == total_episodes_pages
            self.add_action_buttons(include_add_remove=False)

        elif self.level == "movie":
            self.add_action_buttons(include_add_remove=True)

    def add_action_buttons(self, include_add_remove=True):
        exists_in_riven = self.riven_id is not None
        if include_add_remove:
            self.add_item(self.add_button)
            self.add_item(self.remove_button)
            self.add_button.disabled = exists_in_riven
            self.remove_button.disabled = not exists_in_riven
        self.add_item(self.retry_button)
        self.add_item(self.reset_button)
        self.add_item(self.refresh_button)
        self.retry_button.disabled = not exists_in_riven
        self.reset_button.disabled = not exists_in_riven
        if self.level == "movie":
            self.add_item(self.scrape_button)
            self.add_item(self.magnets_button)
            self.scrape_button.disabled = not exists_in_riven
            self.magnets_button.disabled = not exists_in_riven

    async def prev_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        logger.info(f"{interaction.user} pressed Previous")
        if self.level == "items" and self.page > 1:
            self.page -= 1
        elif self.level == "show" and self.seasons_page > 1:
            self.seasons_page -= 1
        elif self.level == "episode" and self.episodes_page > 1:
            self.episodes_page -= 1
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def next_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        logger.info(f"{interaction.user} pressed Next")
        if self.level == "items" and self.page < math.ceil(len(self.all_results) / self.items_per_page):
            self.page += 1
        elif self.level == "show" and self.seasons_page < math.ceil(len(self.seasons) / self.options_per_page):
            self.seasons_page += 1
        elif self.level == "episode" and self.episodes_page < math.ceil(len(self.episodes) / self.options_per_page):
            self.episodes_page += 1
        self.update_view()
        await interaction.response.edit_message(view=self)

    # The remaining button callbacks (add_button_callback, remove_button_callback, etc.) remain unchanged
    async def add_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} adding {name}")
        response, error = handle_api_response(query_riven_api("items/add", self.ctx.bot.config, "POST", params={"imdb_ids": imdb_id}))
        if error:
            await interaction.response.send_message(f"Add failed: {error}", ephemeral=True)
        else:
            self.riven_id = response.get("ids", [None])[0]
            self.riven_data = None
            await interaction.response.send_message(f"Added {name}", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    async def remove_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} removing {name}")
        response, error = handle_api_response(query_riven_api("items/remove", self.ctx.bot.config, "DELETE", params={"ids": self.riven_id}))
        if error:
            await interaction.response.send_message(f"Remove failed: {error}", ephemeral=True)
        else:
            self.riven_id = None
            self.riven_data = None
            await interaction.response.send_message(f"Removed {name}", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    async def retry_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} retrying {name}")
        response, error = handle_api_response(query_riven_api("items/retry", self.ctx.bot.config, "POST", params={"ids": self.riven_id}))
        if error:
            await interaction.response.send_message(f"Retry failed: {error}", ephemeral=True)
        else:
            self.riven_data = None
            await interaction.response.send_message(f"Retrying {name}", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    async def reset_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} resetting {name}")
        response, error = handle_api_response(query_riven_api("items/reset", self.ctx.bot.config, "POST", params={"ids": self.riven_id}))
        if error:
            await interaction.response.send_message(f"Reset failed: {error}", ephemeral=True)
        else:
            self.riven_data = None
            await interaction.response.send_message(f"Reset {name}", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    async def scrape_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} scraping {name}")
        response, error = handle_api_response(query_riven_api(f"items/{self.riven_id}/scrape", self.ctx.bot.config, "POST"))
        if error:
            await interaction.response.send_message(f"Scrape failed: {error}", ephemeral=True)
        else:
            await interaction.response.send_message("Scraping started", ephemeral=True)

    async def magnets_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"{interaction.user} requesting magnets for {name}")
        data, error = handle_api_response(query_riven_api(f"items/{self.riven_id}/streams", self.ctx.bot.config))
        if error:
            await interaction.response.send_message(f"Magnets failed: {error}", ephemeral=True)
        else:
            magnets = "\n".join([stream.get("uri", "No URI") for stream in data][:5])
            await interaction.response.send_message(f"Magnets for {name}:\n{magnets}", ephemeral=True)

    async def refresh_button_callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.initiator_id):
            return
        name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = self.selected_item
        logger.info(f"{interaction.user} refreshing {name}")
        riven_response = query_riven_api("items", self.ctx.bot.config, params={"search": name, "limit": 50})
        riven_state = "Not in Riven"
        if riven_response.get("success", False) and "items" in riven_response:
            for item in riven_response["items"]:
                if item.get("tmdb_id") == str(tmdb_id) or item.get("imdb_id") == imdb_id:
                    self.riven_id = item.get("id")
                    riven_state = item.get("state", "Unknown")
                    break
        recommended_response = requests.get(f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/recommendations", params={"api_key": self.ctx.bot.config["tmdb_api_key"]})
        recommended_data = recommended_response.json().get("results", [])[:5]
        emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        recommended_titles = [
            f"{emoji_numbers[i]} {item['title' if media_type == 'movie' else 'name']} ({item['release_date' if media_type == 'movie' else 'first_air_date'][:4]}) - ★ {item['vote_average']}/10"
            for i, item in enumerate(recommended_data)
        ]
        self.recommended_ids = [item['id'] for item in recommended_data]
        embed = create_media_embed(self.query, name, year, rating, vote_count, description, imdb_id, tmdb_id, poster, riven_state, recommended_titles)
        await interaction.response.edit_message(embed=embed, view=self)
        message = await interaction.original_response()
        bot.active_recommended_messages[message.id] = self
        reaction_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for emoji in reaction_emojis[:len(self.recommended_ids)]:
            await message.add_reaction(emoji)
            logger.info(f"Added reaction {emoji} to refreshed message {message.id}")

#SECTION 15 - Latest Release Dropdown Class
class LatestReleasesDropdown(Select):
    def __init__(self, items):
        options = []
        # items is a list of tuples: (title, year, tmdb_id, media_type, added_date)
        for idx, (title, year, tmdb_id, media_type, added_date) in enumerate(items):
            # Build a label with the title and year; include the added date in the description.
            label = f"{title[:80]} ({year})"
            description = f"Added: {added_date}"
            options.append(SelectOption(label=label, description=description, value=str(idx)))
        super().__init__(placeholder="Select a release", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Check if the interaction user is authorized (reusing your existing check_authorization function)
        if not await check_authorization(interaction, self.view.initiator_id):
            return

        selected_idx = int(self.values[0])
        selected_item = self.view.recent_items[selected_idx]  # Tuple: (title, year, tmdb_id, media_type, added_date)
        title, year, tmdb_id, media_type, added_date = selected_item

        # Fetch detailed info from TMDb using your existing helper function.
        details = fetch_tmdb_by_id(tmdb_id, media_type, self.view.ctx.bot.config)
        if details:
            # Unpack TMDb details: (name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons)
            name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = details
            imdb_link = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id != "N/A" else "N/A"
            # Here you may want to adjust how you construct the Trakt link if you store a slug; for now, we use tmdb_id
            trakt_link = f"https://trakt.tv/{media_type}s/{tmdb_id}"
            embed = discord.Embed(
                title=f"{name} ({year})",
                description=(
                    f"**Rating:** {rating}/10 ({vote_count} votes)\n"
                    f"**Added on Trakt:** {added_date}\n"
                    f"**Description:** {description}"
                ),
                color=discord.Color.green() if media_type == "movie" else discord.Color.purple()
            )
            # Use a large image (title card) instead of a thumbnail.
            if poster and poster != "No poster":
                embed.set_image(url=poster)
            embed.add_field(name="IMDb", value=f"[View on IMDb]({imdb_link})", inline=True)
            embed.add_field(name="Trakt", value=f"[View on Trakt]({trakt_link})", inline=True)

            # OPTIONAL: Add buttons based on Riven status by editing the view here.
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            await interaction.response.send_message("Failed to fetch details.", ephemeral=True)

class LatestReleasesView(View):
    def __init__(self, ctx, recent_items):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.recent_items = recent_items
        self.initiator_id = ctx.author.id
        # Add the select menu to the view.
        self.add_item(LatestReleasesDropdown(recent_items))
        # OPTIONAL: Here you can add additional buttons (e.g., Add/Remove) based on Riven availability.


# SECTION 16 - Bot setup
intents = discord.Intents.default()
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
    """Fetch the latest N releases from Trakt, stitch their posters into a grid, and display with an interactive select menu."""
    await ctx.defer()

    trakt_api_key = config.get("trakt_api_key")
    tmdb_api_key = config.get("tmdb_api_key")
    latest_count = config.get("latest_releases_count", 10)  # Adjustable count from config

    if not trakt_api_key or not tmdb_api_key:
        await ctx.send("API keys for Trakt or TMDb are missing from the config.")
        return

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

        results = []       # For the SearchView dropdown: (title, year, rating, tmdb_id, media_type)
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

        # Create the poster grid image with dynamic grid width.
        grid_image = await create_poster_grid(poster_info, max_grid_width=MAX_GRID_WIDTH, image_size=(200, 300))
        image_buffer = io.BytesIO()
        grid_image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        # Create an embed with the grid image attached.
        embed = discord.Embed(title=f"Latest {latest_count} Releases", color=discord.Color.blue())
        embed.set_image(url="attachment://poster_grid.png")

        # Create the interactive view using your existing SearchView.
        view = SearchView(ctx, results, query=f"Latest {latest_count} Releases")
        
        # Send the embed with the attached grid image and the view (select menu and buttons).
        await ctx.send(embed=embed, file=discord.File(fp=image_buffer, filename="poster_grid.png"), view=view)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching latest releases from Trakt: {e}")
        await ctx.send("Failed to retrieve latest releases. Please try again later.")

async def create_poster_grid(poster_info, max_grid_width=1024, image_size=(200,300)):
    """
    Given a list of dictionaries with 'title' and 'poster_url', create a grid image of poster images.
    The grid's width is set to max_grid_width, and the number of columns is computed based on image_size.
    The grid grows vertically as needed.
    """
    posters = []
    placeholder = Image.new("RGB", image_size, color=(50, 50, 50))  # Dark grey placeholder

    for info in poster_info:
        url = info.get("poster_url")
        if url:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    img = ImageOps.fit(img, image_size, Image.LANCZOS)
                    posters.append(img)
                else:
                    posters.append(placeholder)
            except Exception as e:
                logging.error(f"Error fetching poster from {url}: {e}")
                posters.append(placeholder)
        else:
            posters.append(placeholder)

    total = len(posters)
    # Calculate the number of columns so that the grid width is as wide as possible up to max_grid_width.
    columns = max(1, min(total, max_grid_width // image_size[0]))
    grid_rows = math.ceil(total / columns)
    grid_width = columns * image_size[0]
    grid_height = grid_rows * image_size[1]
    grid = Image.new("RGB", (grid_width, grid_height), color=(0, 0, 0))

    for index, poster in enumerate(posters):
        row = index // columns
        col = index % columns
        x = col * image_size[0]
        y = row * image_size[1]
        grid.paste(poster, (x, y))

    return grid

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
        poster_url = "https://image.tmdb.org/t/p/w500/null"
        if tmdb_id:
            tmdb_url = f"https://api.themoviedb.org/3/{'movie' if item_type == 'movie' else 'tv'}/{tmdb_id}"
            response = requests.get(tmdb_url, params={"api_key": config["tmdb_api_key"]})
            if response.status_code == 200:
                poster_path = response.json().get("poster_path")
                if poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
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
