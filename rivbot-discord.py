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

# Load configuration
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

# Send response based on length
async def send_response(ctx, content):
    """Send a response to the channel, as text if under 2000 chars, or as a file if over."""
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
    print(f"Querying Riven API: {method} {url} with params {params}")
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
            print(f"Riven API response: {data}")
            return data
        except ValueError:
            return response.text
    except requests.RequestException as e:
        if hasattr(e.response, "text"):
            error = {"error": f"API error: {e.response.status_code} - {e.response.text}"}
        else:
            error = {"error": f"Request failed: {str(e)}"}
        print(f"Riven API error: {error}")
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

# Search TMDB extended with additional details for media card
def search_tmdb_extended(query, config, limit=50):
    tmdb_search_url = "https://api.themoviedb.org/3/search/multi"
    params = {"api_key": config["tmdb_api_key"], "query": query, "include_adult": False}
    try:
        response = requests.get(tmdb_search_url, params=params)
        response.raise_for_status()
        data = response.json()
        results = []
        for result in data.get("results", [])[:limit]:
            tmdb_id = result["id"]
            media_type = result["media_type"]
            details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
            details_response = requests.get(details_url, params={"api_key": config["tmdb_api_key"]})
            details_response.raise_for_status()
            details = details_response.json()
            name = result.get("title", result.get("name", "Unknown"))
            year = result.get("release_date", result.get("first_air_date", ""))[:4]
            rating = details.get("vote_average", "N/A")
            imdb_id = details.get("imdb_id", "N/A")
            tmdb_id = details.get("id", "N/A")
            poster = f"https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}" if details.get("poster_path") else "No poster"
            description = details.get("overview", "No description")[:150] + "..." if len(details.get("overview", "")) > 150 else details.get("overview", "No description")
            vote_count = details.get("vote_count", 0)
            results.append((name, year, rating, imdb_id, tmdb_id, poster, description, vote_count))
        return results
    except requests.RequestException as e:
        return {"error": f"TMDB search failed: {str(e)}"}

# Dropdown for selecting search results
class SearchDropdown(Select):
    def __init__(self, results, page, total_pages, selected_value=None):
        self.results = results
        self.page = page
        self.total_pages = total_pages
        options = [
            SelectOption(
                label=f"{name} ({year}) - Rating: {rating}/10",
                description=f"TMDB: {tmdb_id}",
                value=str(idx + (page - 1) * 10),
                default=(str(idx + (page - 1) * 10) == selected_value)
            ) for idx, (name, year, rating, imdb_id, tmdb_id, _, _, _) in enumerate(results)
        ]
        super().__init__(placeholder=f"Select an item (Page {page}/{total_pages})", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_idx = int(self.values[0]) % 10
        self.view.selected_item = self.results[selected_idx]
        selected_value = self.values[0]
        name, year, rating, imdb_id, tmdb_id, poster, description, vote_count = self.view.selected_item
        print(f"Selected item: {name} (TMDB: {tmdb_id}, IMDb: {imdb_id})")

        # Update dropdown
        self.view.clear_items()
        start = (self.page - 1) * 10
        end = start + 10
        page_results = self.view.all_results[start:end]
        self.view.add_item(SearchDropdown(page_results, self.page, self.total_pages, selected_value))
        self.view.add_item(self.view.prev_button)
        self.view.add_item(self.view.next_button)
        self.view.add_item(self.view.add_button)
        self.view.add_item(self.view.remove_button)
        self.view.add_item(self.view.retry_button)
        self.view.add_item(self.view.reset_button)
        self.view.add_item(self.view.pause_button)
        self.view.add_item(self.view.unpause_button)
        self.view.add_item(self.view.refresh_button)  # Add refresh button

        # Check Riven for item existence, get internal ID and state
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
        print(f"Checked in Riven: exists={exists_in_riven}, Riven ID={riven_id}, State={riven_state}")

        # Update button states
        self.view.update_button_states(exists_in_riven)

        # Build media card with Riven status
        media_card = (
            f"**{name} ({year})**\n"
            f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
            f"📝 {description}\n"
            f"🖼️ Poster: {poster}\n"
            f"TMDB: {tmdb_id}\n"
            f"🔄 Riven Status: {riven_state}"
        )
        content = f"🔎 TMDB results for '{self.view.ctx.message.content.split(' ', 1)[1]}':\n\n{media_card}"
        if len(content) > 1900:  # Leave buffer for Discord
            truncated_desc = description[:100] + "..."
            media_card = (
                f"**{name} ({year})**\n"
                f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
                f"📝 {truncated_desc}\n"
                f"🖼️ Poster: {poster}\n"
                f"TMDB: {tmdb_id}\n"
                f"🔄 Riven Status: {riven_state}"
            )
            content = f"🔎 TMDB results for '{self.view.ctx.message.content.split(' ', 1)[1]}':\n\n{media_card}"
        await interaction.response.edit_message(content=content, view=self.view)

# View with dropdown and buttons for /search
class SearchView(View):
    def __init__(self, ctx, all_results, page=1):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.all_results = all_results
        self.page = page
        self.total_pages = math.ceil(len(all_results) / 10)
        self.selected_item = None
        self.riven_id = None
        self.update_dropdown()

    def update_dropdown(self):
        self.clear_items()
        start = (self.page - 1) * 10
        end = start + 10
        page_results = self.all_results[start:end]
        self.add_item(SearchDropdown(page_results, self.page, self.total_pages))
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.add_button)
        self.add_item(self.remove_button)
        self.add_item(self.retry_button)
        self.add_item(self.reset_button)
        self.add_item(self.pause_button)
        self.add_item(self.unpause_button)
        self.add_item(self.refresh_button)  # Add refresh button
        self.children[1].disabled = self.page == 1  # Previous
        self.children[2].disabled = self.page == self.total_pages  # Next
        self.update_button_states(False)  # Initially disable all action buttons

    def update_button_states(self, exists_in_riven):
        self.children[3].disabled = exists_in_riven  # Add
        self.children[4].disabled = not exists_in_riven  # Remove
        self.children[5].disabled = not exists_in_riven  # Retry
        self.children[6].disabled = not exists_in_riven  # Reset
        self.children[7].disabled = not exists_in_riven  # Pause
        self.children[8].disabled = not exists_in_riven  # Unpause
        self.children[9].disabled = False  # Refresh always enabled
        print(f"Button states: Add={not exists_in_riven}, Remove={exists_in_riven}, Retry={exists_in_riven}, Reset={exists_in_riven}, Pause={exists_in_riven}, Unpause={exists_in_riven}, Refresh=True")

    @button(label="Previous", style=ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            self.page -= 1
            self.update_dropdown()
            await interaction.response.edit_message(view=self)

    @button(label="Next", style=ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            self.page += 1
            self.update_dropdown()
            await interaction.response.edit_message(view=self)

    @button(label="Add", style=ButtonStyle.green)
    async def add_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        # Unpack all fields, including imdb_id
        name, year, rating, imdb_id, tmdb_id, poster, description, vote_count = self.selected_item
        # Check if imdb_id is valid
        if imdb_id == "N/A":
            await interaction.response.send_message("No IMDb ID available for this item!", ephemeral=True)
            return
        # Use imdb_ids instead of tmdb_ids
        response = query_riven_api("items/add", self.ctx.bot.config, "POST", params={"imdb_ids": imdb_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to add {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Added {name} (IMDb: {imdb_id})", ephemeral=True)
            # Update riven_id if the API returns it
            self.riven_id = response.get("ids", [None])[0]
        await self.refresh_state(interaction)

    @button(label="Remove", style=ButtonStyle.red)
    async def remove_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, _, tmdb_id, _, _, _ = self.selected_item
        response = query_riven_api("items/remove", self.ctx.bot.config, "DELETE", params={"ids": self.riven_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to remove {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Removed {name} (TMDB: {tmdb_id})", ephemeral=True)
            self.riven_id = None
        await self.refresh_state(interaction)

    @button(label="Retry", style=ButtonStyle.green)
    async def retry_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, _, tmdb_id, _, _, _ = self.selected_item
        response = query_riven_api("items/retry", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to retry {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Retrying {name} (TMDB: {tmdb_id})", ephemeral=True)
        await self.refresh_state(interaction)

    @button(label="Reset", style=ButtonStyle.blurple)
    async def reset_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, _, tmdb_id, _, _, _ = self.selected_item
        response = query_riven_api("items/reset", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to reset {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Reset {name} (TMDB: {tmdb_id})", ephemeral=True)
        await self.refresh_state(interaction)

    @button(label="Pause", style=ButtonStyle.grey)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, _, tmdb_id, _, _, _ = self.selected_item
        response = query_riven_api("items/pause", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to pause {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Paused {name} (TMDB: {tmdb_id})", ephemeral=True)
        await self.refresh_state(interaction)

    @button(label="Unpause", style=ButtonStyle.grey)
    async def unpause_button(self, interaction: discord.Interaction, button: Button):
        if not self.selected_item or not self.riven_id:
            await interaction.response.send_message("Select an item first!", ephemeral=True)
            return
        name, _, _, _, tmdb_id, _, _, _ = self.selected_item
        response = query_riven_api("items/unpause", self.ctx.bot.config, "POST", params={"ids": self.riven_id})
        if "error" in response:
            await interaction.response.send_message(f"Failed to unpause {name}: {response['error']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Unpaused {name} (TMDB: {tmdb_id})", ephemeral=True)
        await self.refresh_state(interaction)

    @button(label="Refresh Results", style=ButtonStyle.blurple)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await self.refresh_state(interaction)

    async def refresh_state(self, interaction):
        if self.selected_item:
            name, year, rating, imdb_id, tmdb_id, poster, description, vote_count = self.selected_item
            riven_response = query_riven_api("items", self.ctx.bot.config, params={"search": name, "limit": 50})
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
            self.riven_id = riven_id
            self.update_button_states(exists_in_riven)
            media_card = (
                f"**{name} ({year})**\n"
                f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
                f"📝 {description}\n"
                f"🖼️ Poster: {poster}\n"
                f"TMDB: {tmdb_id}\n"
                f"🔄 Riven Status: {riven_state}"
            )
            content = f"🔎 TMDB results for '{self.ctx.message.content.split(' ', 1)[1]}':\n\n{media_card}"
            if len(content) > 1900:  # Leave buffer
                truncated_desc = description[:100] + "..."
                media_card = (
                    f"**{name} ({year})**\n"
                    f"⭐ Rating: {rating}/10 ({vote_count} votes)\n"
                    f"📝 {truncated_desc}\n"
                    f"🖼️ Poster: {poster}\n"
                    f"TMDB: {tmdb_id}\n"
                    f"🔄 Riven Status: {riven_state}"
                )
                content = f"🔎 TMDB results for '{self.ctx.message.content.split(' ', 1)[1]}':\n\n{media_card}"
            # Check if the interaction has been responded to
            if not interaction.response.is_done():
                await interaction.response.edit_message(content=content, view=self)
            else:
                await interaction.message.edit(content=content, view=self)


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

# Bot setup with custom help command
config = load_config()
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        help_text = (
            "Here’s what I can do for you:\n\n"
            f"**{self.context.bot.command_prefix}health** - Check if Riven is up and running.\n"
            f"**{self.context.bot.command_prefix}search {{query}}** - Search TMDB and manage items (add, remove, retry, reset, pause, unpause).\n"
            f"**{self.context.bot.command_prefix}logs** - View recent Riven logs (up to 1000 characters).\n"
            f"**{self.context.bot.command_prefix}services** - List Riven’s enabled and disabled services.\n"
            f"**{self.context.bot.command_prefix}help** - Show this help message.\n\n"
            "Note: You need to be whitelisted to use these commands!"
        )
        await send_response(self.context, help_text)

bot = commands.Bot(command_prefix=config["bot_prefix"], intents=intents, help_command=CustomHelpCommand())
bot.config = config

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

@bot.command()
async def health(ctx):
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    health_status = await health_check(config)
    await send_response(ctx, health_status)

@bot.command()
async def search(ctx, *, query=None):
    """Search TMDB and manage Riven items with interactive buttons."""
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    if not query:
        await send_response(ctx, "Usage: /search {query}")
        return
    results = search_tmdb_extended(query, config)
    if isinstance(results, dict) and "error" in results:
        await send_response(ctx, results["error"])
        return
    if not results:
        await send_response(ctx, f"No results found for '{query}'.")
        return
    view = SearchView(ctx, results)
    await ctx.send(f"🔎 TMDB results for '{query}':", view=view)

@bot.command()
async def logs(ctx):
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    await send_response(ctx, get_logs(config))

@bot.command()
async def services(ctx):
    if str(ctx.author) not in config["whitelist"]:
        await send_response(ctx, f"Sorry {ctx.author.mention}, you're not authorized.")
        return
    await send_response(ctx, get_services(config))

bot.run(config["discord_bot_token"])
