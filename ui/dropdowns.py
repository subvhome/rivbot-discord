import discord
import requests
import logging
from discord.ui import Select
from discord import SelectOption
from core.logging_setup import logger
from embeds.media_embed import create_media_embed
from helpers.auth import check_authorization
from tmdb.details import fetch_tmdb_by_id
from core.riven_api import query_riven_api
from tmdb.episodes import fetch_tmdb_episodes

class SearchDropdown(Select):
    def __init__(self, items, page, total_pages, dropdown_type="items", selected_value=None):
        self.items = items
        self.page = page
        self.total_pages = total_pages
        self.dropdown_type = dropdown_type
        options = []
        max_label_length = 100  

        if dropdown_type == "items":
            for idx, (name, year, rating, tmdb_id, media_type) in enumerate(items):
                label = f"{name[:80]} ({year}) - Rating: {rating}/10"
                if len(label) < 1:
                    label = "Invalid Label"  
                elif len(label) > max_label_length:
                    label = label[:max_label_length]  
                options.append(SelectOption(label=label, description=f"TMDB: {tmdb_id}", value=str(idx + (page - 1) * 10)))

        elif dropdown_type == "seasons":
            for idx, (season_num, season_name, episode_count) in enumerate(items):
                label = f"Season {season_num} - {season_name[:80]}"
                if len(label) < 1:
                    label = "Invalid Label" 
                elif len(label) > max_label_length:
                    label = label[:max_label_length]  
                options.append(SelectOption(label=label, description=f"Episodes: {episode_count}", value=str(idx + (page - 1) * 25)))

        elif dropdown_type == "episodes":
            for idx, (ep_num, ep_name, ep_desc) in enumerate(items):
                label = f"Episode {ep_num} - {ep_name[:80]}"
                if len(label) < 1:
                    label = "Invalid Label"
                elif len(label) > max_label_length:
                    label = label[:max_label_length]
                options.append(SelectOption(label=label, description=ep_desc, value=str(idx + (page - 1) * 25)))

        super().__init__(placeholder=f"Select {dropdown_type.capitalize()} (Page {page}/{total_pages})", options=options)
        logger.info(f"Created {dropdown_type} dropdown with {len(options)} options")

    async def callback(self, interaction: discord.Interaction):
        if not await check_authorization(interaction, self.view.initiator_id):
            return
        selected_value = self.values[0]
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
                        logger.info(f"Comparing TMDB: {item.get('tmdb_id')} vs {str(tmdb_id)}, IMDb: {item.get('imdb_id')} vs {imdb_id}")
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
                self.view.ctx.bot.active_recommended_messages[message.id] = self.view
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
        if not await check_authorization(interaction, self.view.initiator_id):
            return

        selected_idx = int(self.values[0])
        selected_item = self.view.recent_items[selected_idx]  # Tuple: (title, year, tmdb_id, media_type, added_date)
        title, year, tmdb_id, media_type, added_date = selected_item

        details = fetch_tmdb_by_id(tmdb_id, media_type, self.view.ctx.bot.config)
        if details:
            # Unpack TMDb details: (name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons)
            name, year, rating, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = details
            imdb_link = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id != "N/A" else "N/A"
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
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            await interaction.response.send_message("Failed to fetch details.", ephemeral=True)
