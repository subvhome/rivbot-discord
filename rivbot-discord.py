import json
import requests
import discord
from discord.ext import commands
import logging
import asyncio
from io import StringIO
from discord.ui import Select, View, button, Button
from discord.ui.button import ButtonStyle
from discord import SelectOption
import math

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load configuration with error handling
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config.json: {str(e)}")
        raise

config = load_config()

# Optional file logging based on config
if config.get('log_to_file', False):
    file_handler = logging.FileHandler('bot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

# Send response based on length
async def send_response(ctx, content):
    content_str = str(content)
    if len(content_str) <= 2000:
        await ctx.send(content_str)
    else:
        file_content = StringIO(content_str)
        file = discord.File(file_content, filename="output.txt")
        await ctx.send("Output exceeds 2000 characters, here’s a file:", file=file)
        file_content.close()

# Query Riven API with debugging
def query_riven_api(endpoint, config, method="GET", params=None, json_data=None):
    url = f"{config['riven_api_url']}/{endpoint}"
    headers = {"x-api-key": config["riven_api_token"]}
    logger.debug(f"Querying Riven API: {method} {url} with params {params}")
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, params=params, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()
        try:
            data = response.json()
            logger.debug(f"Riven API response: {data}")
            return data
        except ValueError:
            return response.text
    except requests.RequestException as e:
        error = {"error": f"API error: {e.response.status_code} - {e.response.text}" if hasattr(e.response, "text") else f"Request failed: {str(e)}"}
        logger.error(f"Riven API error: {error}")
        return error

# Health check
async def health_check(config):
    health_url = f"{config['riven_api_url']}/health"
    headers = {"Authorization": f"Bearer {config['riven_api_token']}"}
    logger.debug(f"Health check URL: {health_url}")
    try:
        response = requests.get(health_url, headers=headers)
        if response.status_code == 200:
            return "Riven is up and running!"
        elif response.status_code == 404:
            return "Health check endpoint not found."
        else:
            return f"Unexpected response: {response.status_code}"
    except requests.RequestException as e:
        logger.error(f"Error while checking health: {str(e)}")
        return f"Error while checking health: {str(e)}"

# Search TMDB with extended details
def search_tmdb_extended(query, config, limit=50):
    tmdb_search_url = "https://api.themoviedb.org/3/search/multi"
    params = {"api_key": config["tmdb_api_key"], "query": query, "include_adult": False}
    try:
        logger.debug(f"Searching TMDB: {tmdb_search_url} with params {params}")
        response = requests.get(tmdb_search_url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"TMDB search results: {len(data.get('results', []))} items found")
        results = []
        for result in data.get("results", [])[:limit]:
            tmdb_id = result["id"]
            media_type = result["media_type"]
            details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
            logger.debug(f"Fetching details from: {details_url}")
            details_response = requests.get(details_url, params={"api_key": config["tmdb_api_key"]})
            details_response.raise_for_status()
            details = details_response.json()
            name = result.get("title", result.get("name", "Unknown"))
            year = result.get("release_date", result.get("first_air_date", ""))[:4]
            rating = details.get("vote_average", "N/A")
            vote_count = details.get("vote_count", 0)
            poster = f"https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}" if details.get("poster_path") else "No poster"
            description = details.get("overview", "No description")[:150] + "..." if len(details.get("overview", "")) > 150 else details.get("overview", "No description")

            if media_type == "tv":
                external_ids_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids"
                logger.debug(f"Fetching external IDs for TV show: {external_ids_url}")
                external_ids_response = requests.get(external_ids_url, params={"api_key": config["tmdb_api_key"]})
                external_ids_response.raise_for_status()
                external_ids = external_ids_response.json()
                imdb_id = external_ids.get("imdb_id", "N/A")
            else:
                imdb_id = details.get("imdb_id", "N/A")

            if imdb_id == "N/A":
                logger.warning(f"No IMDb ID found for {name} (TMDB ID: {tmdb_id}, Type: {media_type})")
            else:
                logger.debug(f"Found IMDb ID {imdb_id} for {name} (TMDB ID: {tmdb_id})")

            seasons = [(s["season_number"], s["name"], s["episode_count"]) for s in details.get("seasons", [])] if media_type == "tv" else []
            results.append((name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons))
        return results
    except requests.RequestException as e:
        logger.error(f"TMDB search failed: {str(e)}")
        return {"error": f"TMDB search failed: {str(e)}"}

# Fetch TMDB episodes for a season
def fetch_tmdb_episodes(tmdb_id, season_number, config):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}"
    params = {"api_key": config["tmdb_api_key"]}
    try:
        logger.debug(f"Fetching episodes from: {url}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [(e["episode_number"], e["name"], e["overview"][:97] + "..." if len(e["overview"]) > 97 else e["overview"]) for e in data.get("episodes", [])]
    except requests.RequestException as e:
        logger.error(f"TMDB episode fetch failed: {str(e)}")
        return {"error": f"TMDB episode fetch failed: {str(e)}"}

# Dynamic Dropdown
class SearchDropdown(Select):
    def __init__(self, items, page, total_pages, dropdown_type="items", selected_value=None, show_data=None):
        self.items = items
        self.page = page
        self.total_pages = total_pages
        self.dropdown_type = dropdown_type
        self.show_data = show_data
        options = []
        if self.dropdown_type == "items":
            for idx, (name, year, rating, _, tmdb_id, _, _, _, _, _) in enumerate(items):
                max_name_length = 100 - len(f" ({year}) - Rating: {rating}/10")
                truncated_name = name[:max_name_length] if len(name) > max_name_length else name
                if len(name) > max_name_length:
                    logger.debug(f"Truncated '{name}' to '{truncated_name}' for TMDB ID: {tmdb_id}")
                label = f"{truncated_name} ({year}) - Rating: {rating}/10"
                options.append(
                    SelectOption(
                        label=label,
                        description=f"TMDB: {tmdb_id}",
                        value=str(idx + (page - 1) * 10),
                        default=(str(idx + (page - 1) * 10) == selected_value)
                    )
                )
        elif self.dropdown_type == "seasons":
            for idx, (season_num, season_name, episode_count) in enumerate(items):
                max_name_length = 100 - len(f"Season {season_num} - ")
                truncated_name = season_name[:max_name_length] if len(season_name) > max_name_length else season_name
                if len(season_name) > max_name_length:
                    logger.debug(f"Truncated season '{season_name}' to '{truncated_name}' for Season {season_num}")
                label = f"Season {season_num} - {truncated_name}"
                options.append(
                    SelectOption(
                        label=label,
                        description=f"Episodes: {episode_count}",
                        value=str(idx + (page - 1) * 10),
                        default=(str(idx + (page - 1) * 10) == selected_value)
                    )
                )
        elif self.dropdown_type == "episodes":
            for idx, (ep_num, ep_name, ep_desc) in enumerate(items):
                max_name_length = 100 - len(f"Episode {ep_num} - ")
                truncated_name = ep_name[:max_name_length] if len(ep_name) > max_name_length else ep_name
                if len(ep_name) > max_name_length:
                    logger.debug(f"Truncated episode '{ep_name}' to '{truncated_name}' for Episode {ep_num}")
                label = f"Episode {ep_num} - {truncated_name}"
                options.append(
                    SelectOption(
                        label=label,
                        description=ep_desc,
                        value=str(idx + (page - 1) * 10),
                        default=(str(idx + (page - 1) * 10) == selected_value)
                    )
                )
        super().__init__(placeholder=f"Select {self.dropdown_type.capitalize()} (Page {page}/{total_pages})", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this menu!", ephemeral=True)
            return
        selected_idx = int(self.values[0]) % 10
        if self.dropdown_type == "items":
            self.view.selected_item = self.items[selected_idx]
            name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = self.view.selected_item
            self.view.media_type = media_type
            logger.info(f"Selected item: {name} (TMDB: {tmdb_id}, IMDb: {imdb_id}, Type: {media_type})")
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
                        break
            self.view.riven_id = riven_id
            self.view.level = "show" if media_type == "tv" else "movie"
            self.view.seasons = seasons if media_type == "tv" else []
            self.view.update_view()
            id_display = f"IMDb: {imdb_id}" if imdb_id != "N/A" else f"TMDB: {tmdb_id}"
            media_card = (
                f"**{name} ({year})**\n"
                f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
                f"📝 {description}\n"
                f"🖼️ Poster: {poster}\n"
                f"{id_display}\n"
                f"🔄 Riven Status: {riven_state}"
            )
            query = self.view.query if hasattr(self.view, "query") else "Unknown query"
            content = f"🔎 TMDB results for '{query}':\n\n{media_card}"
        elif self.dropdown_type == "seasons":
            self.view.selected_season = self.items[selected_idx]
            season_num, season_name, _ = self.view.selected_season
            episodes = fetch_tmdb_episodes(self.view.selected_item[4], season_num, self.view.ctx.bot.config)
            if isinstance(episodes, dict) and "error" in episodes:
                await interaction.response.edit_message(content=f"Failed to fetch episodes: {episodes['error']}", view=self.view)
                return
            self.view.episodes = episodes
            self.view.level = "episode"
            self.view.update_view()
            name, year, _, imdb_id, tmdb_id, poster, description, vote_count, _, _ = self.view.selected_item
            riven_state = await self.view.get_riven_state()
            id_display = f"IMDb: {imdb_id}" if imdb_id != "N/A" else f"TMDB: {tmdb_id}"
            content = (
                f"**{name} ({year}) - Season {season_num}: {season_name}**\n"
                f"📝 {description}\n"
                f"🖼️ Poster: {poster}\n"
                f"{id_display}\n"
                f"🔄 Riven Status: {riven_state}"
            )
        elif self.dropdown_type == "episodes":
            self.view.selected_episode = self.items[selected_idx]
            ep_num, ep_name, ep_desc = self.view.selected_episode
            name, year, _, imdb_id, tmdb_id, poster, description, vote_count, _, _ = self.view.selected_item
            season_num, season_name, _ = self.view.selected_season
            riven_state = await self.view.get_riven_state()
            id_display = f"IMDb: {imdb_id}" if imdb_id != "N/A" else f"TMDB: {tmdb_id}"
            content = (
                f"**{name} ({year}) - Season {season_num}: {season_name} - Episode {ep_num}: {ep_name}**\n"
                f"📝 {ep_desc}\n"
                f"🖼️ Poster: {poster}\n"
                f"{id_display}\n"
                f"🔄 Riven Status: {riven_state}"
            )
            self.view.update_view()
        if len(content) > 1900:
            content = content[:1900] + "..."
        await interaction.response.edit_message(content=content, view=self.view)

# Dynamic View
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
        self.update_view()

    async def get_riven_state(self):
        if not self.riven_id:
            return "Not in Riven"
        if not self.riven_data:
            self.riven_data = query_riven_api(f"items/{self.riven_id}", self.ctx.bot.config)
        if "error" in self.riven_data:
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
            return "Season not found in Riven"
        return "Unknown"

    def update_view(self):
        self.clear_items()

        if self.level == "items":
            start = (self.page - 1) * 10
            end = start + 10
            page_results = self.all_results[start:end]
            dropdown = SearchDropdown(page_results, self.page, self.total_pages, "items")
            self.add_item(dropdown)
            self.add_item(self.prev_button)
            self.add_item(self.next_button)
            self.prev_button.disabled = self.page == 1
            self.next_button.disabled = self.page == self.total_pages

        elif self.level == "show":
            total_pages = math.ceil(len(self.seasons) / 10)
            start = (self.page - 1) * 10
            end = start + 10
            page_seasons = self.seasons[start:end]
            dropdown = SearchDropdown(page_seasons, self.page, total_pages, "seasons", show_data=self.selected_item)
            self.add_item(dropdown)
            self.add_item(self.prev_button)
            self.add_item(self.next_button)
            self.add_item(self.add_button)
            self.add_item(self.remove_button)
            self.add_item(self.retry_button)
            self.add_item(self.reset_button)
            self.add_item(self.refresh_button)
            exists_in_riven = self.riven_id is not None
            self.prev_button.disabled = self.page == 1
            self.next_button.disabled = self.page == total_pages
            self.add_button.disabled = exists_in_riven
            self.remove_button.disabled = not exists_in_riven
            self.retry_button.disabled = not exists_in_riven
            self.reset_button.disabled = not exists_in_riven
            self.refresh_button.disabled = False

        elif self.level == "episode":
            total_pages = math.ceil(len(self.episodes) / 10)
            start = (self.page - 1) * 10
            end = start + 10
            page_episodes = self.episodes[start:end]
            dropdown = SearchDropdown(page_episodes, self.page, total_pages, "episodes", show_data=self.selected_item)
            self.add_item(dropdown)
            self.add_item(self.prev_button)
            self.add_item(self.next_button)
            self.add_item(self.retry_button)
            self.add_item(self.reset_button)
            self.add_item(self.refresh_button)
            exists_in_riven = self.riven_id is not None
            self.prev_button.disabled = self.page == 1
            self.next_button.disabled = self.page == total_pages
            self.retry_button.disabled = not exists_in_riven
            self.reset_button.disabled = not exists_in_riven
            self.refresh_button.disabled = False

        elif self.level == "movie":
            self.add_item(self.add_button)
            self.add_item(self.remove_button)
            self.add_item(self.retry_button)
            self.add_item(self.reset_button)
            self.add_item(self.scrape_button)
            self.add_item(self.magnets_button)
            self.add_item(self.refresh_button)
            exists_in_riven = self.riven_id is not None
            self.add_button.disabled = exists_in_riven
            self.remove_button.disabled = not exists_in_riven
            self.retry_button.disabled = not exists_in_riven
            self.reset_button.disabled = not exists_in_riven
            self.scrape_button.disabled = not exists_in_riven
            self.magnets_button.disabled = not exists_in_riven
            self.refresh_button.disabled = False

    @button(label="Previous", style=ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if self.page > 1:
            self.page -= 1
            self.update_view()
            await interaction.response.edit_message(view=self)

    @button(label="Next", style=ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        total_pages = math.ceil(len(self.all_results if self.level == "items" else self.seasons if self.level == "show" else self.episodes) / 10)
        if self.page < total_pages:
            self.page += 1
            self.update_view()
            await interaction.response.edit_message(view=self)

    @button(label="Add", style=ButtonStyle.green)
    async def add_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.selected_item or self.level not in ["show", "movie"]:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        if imdb_id == "N/A":
            logger.error(f"Attempted to add {name} (TMDB: {tmdb_id}) but IMDb ID is N/A")
            await interaction.response.send_message("No IMDb ID available!", ephemeral=True)
            return
        logger.info(f"Adding {name} with IMDb ID {imdb_id} to Riven")
        response = query_riven_api("items/add", self.ctx.bot.config, "POST", params={"imdb_ids": imdb_id})
        if "error" in response:
            logger.error(f"Failed to add {name}: {response['error']}")
            await interaction.response.send_message(f"Failed to add {name}: {response['error']}", ephemeral=True)
        else:
            self.riven_id = response.get("ids", [None])[0]
            self.riven_data = None
            logger.info(f"Successfully added {name} (IMDb: {imdb_id})")
            await interaction.response.send_message(f"Added {name} (IMDb: {imdb_id})", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    @button(label="Remove", style=ButtonStyle.red)
    async def remove_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.selected_item or not self.riven_id or self.level not in ["show", "movie"]:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"Removing {name} with Riven ID {self.riven_id}")
        response = query_riven_api("items/remove", self.ctx.bot.config, "DELETE", params={"ids": self.riven_id})
        if "error" in response:
            logger.error(f"Failed to remove {name}: {response['error']}")
            await interaction.response.send_message(f"Failed to remove {name}: {response['error']}", ephemeral=True)
        else:
            logger.info(f"Successfully removed {name} (IMDb: {imdb_id})")
            self.riven_id = None
            self.riven_data = None
            await interaction.response.send_message(f"Removed {name} (IMDb: {imdb_id})", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    @button(label="Retry", style=ButtonStyle.green)
    async def retry_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"Retrying {name} with Riven ID {self.riven_id}")
        response = query_riven_api("items/retry", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            logger.error(f"Failed to retry {name}: {response['error']}")
            await interaction.response.send_message(f"Failed to retry {name}: {response['error']}", ephemeral=True)
        else:
            logger.info(f"Successfully retried {name} (IMDb: {imdb_id})")
            self.riven_data = None
            await interaction.response.send_message(f"Retrying {name} (IMDb: {imdb_id})", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    @button(label="Reset", style=ButtonStyle.blurple)
    async def reset_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, imdb_id, tmdb_id, _, _, _, _, _ = self.selected_item
        logger.info(f"Resetting {name} with Riven ID {self.riven_id}")
        response = query_riven_api("items/reset", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            logger.error(f"Failed to reset {name}: {response['error']}")
            await interaction.response.send_message(f"Failed to reset {name}: {response['error']}", ephemeral=True)
        else:
            logger.info(f"Successfully reset {name} (IMDb: {imdb_id})")
            self.riven_data = None
            await interaction.response.send_message(f"Reset {name} (IMDb: {imdb_id})", ephemeral=True)
        self.update_view()
        await interaction.message.edit(view=self)

    @button(label="Scrape", style=ButtonStyle.blurple)
    async def scrape_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.riven_id:
            await interaction.response.send_message("Item not in Riven!", ephemeral=True)
            return
        name, _, _, imdb_id, _, _, _, _, _, _ = self.selected_item
        logger.info(f"User {interaction.user} initiated scrape for {name} (Riven ID: {self.riven_id})")
        response = query_riven_api(f"items/{self.riven_id}/scrape", self.ctx.bot.config, method="POST")
        if "error" in response:
            logger.error(f"Scrape failed for {name}: {response['error']}")
            await interaction.response.send_message(f"Failed to scrape: {response['error']}", ephemeral=True)
        else:
            logger.info(f"Scrape initiated for {name} (IMDb: {imdb_id})")
            await interaction.response.send_message("Scraping initiated.", ephemeral=True)

    @button(label="Magnets", style=ButtonStyle.grey)
    async def magnets_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.riven_id:
            await interaction.response.send_message("Item not in Riven!", ephemeral=True)
            return
        name, _, _, imdb_id, _, _, _, _, _, _ = self.selected_item
        logger.info(f"User {interaction.user} requested magnets for {name} (Riven ID: {self.riven_id})")
        data = query_riven_api(f"items/{self.riven_id}/streams", self.ctx.bot.config)
        if "error" in data:
            logger.error(f"Failed to get magnets for {name}: {data['error']}")
            await interaction.response.send_message(f"Failed to get magnets: {data['error']}", ephemeral=True)
            return
        magnets = [stream.get("uri", "No URI") for stream in data] if isinstance(data, list) else []
        if not magnets:
            await interaction.response.send_message("No magnets found.", ephemeral=True)
            return
        magnet_list = "\n".join(magnets[:5])  # Limit to 5 for brevity
        await interaction.response.send_message(f"Magnets for {name}:\n{magnet_list}", ephemeral=True)

    @button(label="Refresh Info", style=ButtonStyle.grey)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.initiator_id:
            await interaction.response.send_message("You are not authorized to interact with this button!", ephemeral=True)
            return
        if not self.selected_item:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = self.selected_item
        riven_response = query_riven_api("items", self.ctx.bot.config, params={"search": name, "limit": 50})
        riven_state = "Not in Riven"
        if riven_response.get("success", False) and "items" in riven_response:
            for item in riven_response["items"]:
                if item.get("tmdb_id") == str(tmdb_id) or item.get("imdb_id") == imdb_id:
                    self.riven_id = item.get("id")
                    riven_state = item.get("state", "Unknown")
                    break
        id_display = f"IMDb: {imdb_id}" if imdb_id != "N/A" else f"TMDB: {tmdb_id}"
        if self.level == "show" or self.level == "movie":
            media_card = (
                f"**{name} ({year})**\n"
                f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
                f"📝 {description}\n"
                f"🖼️ Poster: {poster}\n"
                f"{id_display}\n"
                f"🔄 Riven Status: {riven_state}"
            )
        elif self.level == "episode":
            season_num, season_name, _ = self.selected_season
            ep_num, ep_name, ep_desc = self.selected_episode if self.selected_episode else (None, None, None)
            media_card = (
                f"**{name} ({year}) - Season {season_num}: {season_name}{' - Episode ' + str(ep_num) + ': ' + ep_name if ep_num else ''}**\n"
                f"📝 {ep_desc if ep_num else description}\n"
                f"🖼️ Poster: {poster}\n"
                f"{id_display}\n"
                f"🔄 Riven Status: {riven_state}"
            )
        content = f"🔎 TMDB results for '{self.query}':\n\n{media_card}"
        if len(content) > 1900:
            content = content[:1900] + "..."
        await interaction.response.edit_message(content=content, view=self)

# Get logs
def get_logs(config):
    data = query_riven_api("logs", config)
    if "error" in data:
        return f"Logs query failed: {data['error']}"
    logs = data if isinstance(data, str) else json.dumps(data, indent=2)
    return f"Recent Logs:\n```\n{logs[:1000]}\n```"

# Get services
def get_services(config):
    data = query_riven_api("services", config)
    if "error" in data:
        return f"Services query failed: {data['error']}"
    services = "\n".join([f"- {service}: {'Enabled' if status else 'Disabled'}" for service, status in data.items()])
    return f"Services:\n{services}"

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        help_text = (
            f"**{self.context.bot.command_prefix}health** - Check if Riven is up.\n"
            f"**{self.context.bot.command_prefix}search {{query}}** - Search TMDB and manage items.\n"
            f"**{self.context.bot.command_prefix}recentlyadded [n]** - Show last n items added (max 10).\n"
            f"**{self.context.bot.command_prefix}status** - Show Riven totals.\n"
            f"**{self.context.bot.command_prefix}logs** - View recent Riven logs.\n"
            f"**{self.context.bot.command_prefix}services** - List Riven services.\n"
            f"**{self.context.bot.command_prefix}help** - Show this message.\n"
            "Note: Whitelist required! Works in channels and DMs."
        )
        await send_response(self.context, help_text)

bot = commands.Bot(command_prefix=config["bot_prefix"], intents=intents, help_command=CustomHelpCommand())
bot.config = config

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

@bot.command()
async def health(ctx):
    logger.info(f"User {ctx.author} requested health check")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    health_status = await health_check(config)
    await send_response(ctx, health_status)

@bot.command()
async def search(ctx, *, query=None):
    logger.info(f"User {ctx.author} initiated search for '{query}'")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    if not query:
        await send_response(ctx, "Usage: {0}search {{query}}".format(ctx.prefix))
        return
    results = search_tmdb_extended(query, config)
    if isinstance(results, dict) and "error" in results:
        await send_response(ctx, results["error"])
        return
    if not results:
        await send_response(ctx, f"No results found for '{query}'.")
        return
    view = SearchView(ctx, results, query)
    await ctx.send(f"🔎 TMDB results for '{query}':", view=view)

@bot.command()
async def recentlyadded(ctx, n: int = 10):
    if str(ctx.author) not in config["whitelist"]:
        await ctx.send(f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    if n < 1 or n > 10:
        await ctx.send("Please provide a number between 1 and 10.")
        return
    logger.info(f"User {ctx.author} requested recently added items (n={n})")
    params = {
        "sort": "date_desc",
        "limit": n,
        "page": 1,
        "type": "movie,show"
    }
    data = query_riven_api("items", config, params=params)
    if "error" in data:
        await ctx.send(f"Failed to fetch recently added items: {data['error']}")
        return
    items = data.get("items", [])
    if not items:
        await ctx.send("No recently added movies or shows found.")
        return

    # Fetch posters and prepare embeds
    embeds = []
    for item in items:
        title = item.get("title", "Unknown")
        item_type = item.get("type", "Unknown").lower()
        state = item.get("state", "Unknown")
        tmdb_id = item.get("tmdb_id")

        # Fetch poster from TMDB
        poster_url = "https://image.tmdb.org/t/p/w500/null"  # Default if no poster
        if tmdb_id:
            tmdb_url = f"https://api.themoviedb.org/3/{'movie' if item_type == 'movie' else 'tv'}/{tmdb_id}"
            try:
                response = requests.get(tmdb_url, params={"api_key": config["tmdb_api_key"]})
                response.raise_for_status()
                tmdb_data = response.json()
                poster_path = tmdb_data.get("poster_path")
                if poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            except requests.RequestException as e:
                logger.error(f"Failed to fetch TMDB data for {title}: {str(e)}")

        # Create embed
        embed = discord.Embed(
            title=f"{item_type.capitalize()}: {title}",
            description=f"State: {state}",
            color=discord.Color.blue()
        )
        embed.set_image(url=poster_url)
        embeds.append(embed)

    # Send embeds with strict limit of 10 total, in batches of 5
    embeds = embeds[:10]  # Enforce Discord's 10-embed limit
    await ctx.send(f"**Recently Added Movies and Shows (Top {len(embeds)}):**")
    for i in range(0, len(embeds), 5):
        await ctx.send(embeds=embeds[i:i+5])

@bot.command()
async def status(ctx):
    if str(ctx.author) not in config["whitelist"]:
        await ctx.send(f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    logger.info(f"User {ctx.author} requested status")
    data = query_riven_api("stats", config)
    if "error" in data:
        await ctx.send(f"Failed to fetch status: {data['error']}")
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
    logger.info(f"User {ctx.author} requested logs")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    await send_response(ctx, get_logs(config))

@bot.command()
async def services(ctx):
    logger.info(f"User {ctx.author} requested services")
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    await send_response(ctx, get_services(config))

bot.run(config["discord_bot_token"])
