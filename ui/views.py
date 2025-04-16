import discord
import math
import requests
import logging
from discord.ui import View, Button
from discord.ui.button import ButtonStyle
from core.logging_setup import logger
from ui.dropdowns import SearchDropdown
from core.riven_api import query_riven_api, handle_api_response
from tmdb.episodes import fetch_tmdb_episodes
from embeds.media_embed import create_media_embed
from helpers.auth import check_authorization

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
        if self.level in ["movie", "show"]:  
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
        try:
            # Step 0: Verify authorization and defer response
            if not await check_authorization(interaction, self.initiator_id):
                return
            await interaction.response.defer(ephemeral=True)

            if not self.riven_id:
                await interaction.followup.send("Scrape unavailable: Title not in Riven.", ephemeral=True)
                return
            name, _, _, imdb_id, tmdb_id, poster, description, vote_count, media_type, seasons = self.selected_item
            logger.info(f"{interaction.user} initiating scrape for {name}")

            # Show an animated status message
            progress_msg = await interaction.followup.send("⏳ Scraping in progress...", ephemeral=True)

            # Get API configuration values
            riven_url = self.ctx.bot.config.get("riven_api_url")
            riven_api_token = self.ctx.bot.config.get("riven_api_token")
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {riven_api_token}'
            }

            # --- Step 1: Fetch Streams ---
            streams_url = f"{riven_url}/scrape/scrape/{self.riven_id}"
            logger.debug(f"[Fetch Streams] URL: {streams_url}")
            streams_response = requests.get(streams_url, headers=headers, verify=False)
            logger.debug(f"[Fetch Streams] Status: {streams_response.status_code}")
            logger.debug(f"[Fetch Streams] Body: {streams_response.text}")
            if streams_response.status_code != 200:
                await interaction.followup.send("Failed to fetch streams.", ephemeral=True)
                return

            data = streams_response.json()
            if "streams" not in data or not data["streams"]:
                await interaction.followup.send("No streams found for this item.", ephemeral=True)
                return

            self.streams = []
            for infohash, stream in data["streams"].items():
                stream["riven_id"] = self.riven_id
                stream["infohash"] = infohash
                self.streams.append(stream)
            logger.info(f"[Fetch Streams] Found {len(self.streams)} streams for {name}")

            # --- Step 2: Build and Send Stream Select Menu ---
            options = []
            for s in self.streams:
                title = s.get("parsed_title") or s.get("raw_title") or "Unknown"
                title = title[:40] 
                parsed = s.get("parsed_data", {})
                year_val = parsed.get("year", "N/A")
                resolution = parsed.get("resolution", "N/A")
                codec = parsed.get("codec", "N/A")
                audio = "/".join(parsed.get("audio", [])) if parsed.get("audio") else "N/A"
                channels = "/".join(parsed.get("channels", [])) if parsed.get("channels") else "N/A"
                languages = " ".join(parsed.get("languages", [])) if parsed.get("languages") else "N/A"
                label = f"{title} {year_val} {resolution} {codec} {audio} {channels} {languages}"
                options.append(discord.SelectOption(label=label[:100], value=s["infohash"]))
            logger.info(f"[Stream Menu] Created {len(options)} stream options.")

            stream_menu = discord.ui.Select(placeholder="Select a stream", options=options)

            async def on_stream_select(select_int: discord.Interaction):
                await select_int.response.defer(ephemeral=True)
                selected_hash = stream_menu.values[0]
                logger.info(f"[Stream Select] {select_int.user} selected stream with infohash: {selected_hash}")

                # --- Step 3: Start Session ---
                start_url = f"{riven_url}/scrape/scrape/start_session?item_id={self.riven_id}&magnet={selected_hash}"
                logger.debug(f"[Start Session] URL: {start_url}")
                try:
                    start_resp = requests.post(start_url, headers=headers, verify=False)
                    logger.debug(f"[Start Session] Status: {start_resp.status_code}")
                    logger.debug(f"[Start Session] Body: {start_resp.text}")
                except Exception as e:
                    logger.error(f"[Start Session] Exception: {e}")
                    await select_int.followup.send(f"Error starting session: {e}", ephemeral=True)
                    return

                if start_resp.status_code != 200:
                    try:
                        detail = start_resp.json().get("detail", "No detail provided")
                    except Exception:
                        detail = "Failed to parse response"
                    logger.error(f"[Start Session] Failed: {detail}")
                    await select_int.followup.send(f"Start session failed: {detail}", ephemeral=True)
                    return

                session_data = start_resp.json()
                session_id = session_data.get("session_id")
                if not session_id:
                    await select_int.followup.send("Failed to start session: No session ID returned.", ephemeral=True)
                    return
                logger.info(f"[Start Session] Started session with session_id: {session_id}")

                torrent_info = session_data.get("torrent_info", {})
                logger.debug(f"[Start Session] Torrent info: {torrent_info}")
                files_dict = torrent_info.get("files", {})
                logger.info(f"[Start Session] Torrent returned {len(files_dict)} file(s).")

                # --- Step 4: Filter Files ---
                valid_files = []
                min_size = 200 * 1024 * 1024 if media_type.lower() == "movie" else 80 * 1024 * 1024
                valid_exts = (".mkv", ".avi", ".mp4")
                for fid, file_data in files_dict.items():
                    fname = file_data.get("filename", "").lower()
                    fsize = file_data.get("bytes") or file_data.get("filesize") or 0
                    if fname.endswith(valid_exts) and fsize >= min_size:
                        valid_files.append({
                            "session_id": session_id,
                            "file_id": fid,
                            "filename": file_data.get("filename"),
                            "filesize": fsize
                        })
                logger.info(f"[File Filter] Found {len(valid_files)} valid file(s) for session {session_id}.")
                if not valid_files:
                    await select_int.followup.send("No valid files found for this stream.", ephemeral=True)
                    return

                # --- Step 5: Handle File Selection Based on Media Type ---
                if media_type.lower() == "movie":
                    # For movies, present a select menu (limit to 25 options)
                    if len(valid_files) > 25:
                        file_list_str = "\n".join(
                            f"{i+1}. {file['filename']} ({file['filesize']} bytes)" for i, file in enumerate(valid_files)
                        )
                        buffer = io.StringIO(file_list_str)
                        await select_int.followup.send("Too many file options. See attached file for the full list. Only the first 25 options will be shown.",
                                                       file=discord.File(fp=buffer, filename="file_options.txt"), ephemeral=True)
                        valid_files = valid_files[:25]

                    file_options = []
                    for idx, file in enumerate(valid_files):
                        file_options.append(discord.SelectOption(
                            label=file["filename"][:100],
                            value=str(idx)
                        ))
                    logger.info(f"[File Menu] Created {len(file_options)} file options for session {session_id}.")

                    file_menu = discord.ui.Select(placeholder="Select a file", options=file_options)

                    class FileView(discord.ui.View):
                        def __init__(self, valid_files):
                            super().__init__(timeout=180.0)
                            self.valid_files = valid_files

                    file_view = FileView(valid_files)

                    async def on_file_select(file_int: discord.Interaction):
                        logger.info("[File Select] Callback triggered.")
                        await file_int.response.defer(ephemeral=True)
                        selected_idx = int(file_menu.values[0])
                        selected_file = file_view.valid_files[selected_idx]
                        session_id_sel = selected_file["session_id"]
                        file_id_sel = selected_file["file_id"]
                        filename_sel = selected_file["filename"]
                        filesize_sel = selected_file["filesize"]

                        payload = {
                            file_id_sel: {
                                "file_id": file_id_sel,
                                "filename": filename_sel,
                                "filesize": int(filesize_sel)
                            }
                        }
                        logger.info(f"[Select Files] Payload (Movie): {payload}")

                        select_files_url = f"{riven_url}/scrape/scrape/select_files/{session_id_sel}"
                        logger.info(f"[Select Files] URL: {select_files_url}")
                        try:
                            sf_resp = requests.post(
                                select_files_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}',
                                    'Content-Type': 'application/json'
                                },
                                json=payload,
                                verify=False
                            )
                            logger.info(f"[Select Files] Status: {sf_resp.status_code}")
                            logger.info(f"[Select Files] Body: {sf_resp.text}")
                        except Exception as e:
                            logger.error(f"[Select Files] Exception: {e}")
                            await file_int.followup.send(f"Error selecting file: {e}", ephemeral=True)
                            return

                        if sf_resp.status_code != 200:
                            await file_int.followup.send("Failed to select file.", ephemeral=True)
                            return

                        # For movies, update attributes immediately using the same payload structure.
                        update_url = f"{riven_url}/scrape/scrape/update_attributes/{session_id_sel}"
                        logger.info(f"[Update Attributes] URL: {update_url}")
                        logger.info(f"[Update Attributes] Payload (Movie): {payload}")
                        try:
                            up_resp = requests.post(
                                update_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}',
                                    'Content-Type': 'application/json'
                                },
                                json=payload,
                                verify=False
                            )
                            logger.info(f"[Update Attributes] Status: {up_resp.status_code}")
                            logger.info(f"[Update Attributes] Body: {up_resp.text}")
                        except Exception as e:
                            logger.error(f"[Update Attributes] Exception: {e}")
                            await file_int.followup.send(f"Error updating attributes: {e}", ephemeral=True)
                            return

                        if up_resp.status_code != 200:
                            await file_int.followup.send("Failed to update attributes.", ephemeral=True)
                            return

                        complete_url = f"{riven_url}/scrape/scrape/complete_session/{session_id_sel}"
                        logger.info(f"[Complete Session] URL: {complete_url}")
                        try:
                            comp_resp = requests.post(
                                complete_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}'
                                },
                                verify=False
                            )
                            logger.info(f"[Complete Session] Status: {comp_resp.status_code}")
                            logger.info(f"[Complete Session] Body: {comp_resp.text}")
                        except Exception as e:
                            logger.error(f"[Complete Session] Exception: {e}")
                            await file_int.followup.send(f"Error completing session: {e}", ephemeral=True)
                            return

                        if comp_resp.status_code != 200:
                            await file_int.followup.send("Failed to complete session.", ephemeral=True)
                            return

                        await file_int.followup.send(f"Scraping session completed for file: {filename_sel}", ephemeral=True)

                    file_menu.callback = on_file_select
                    file_view = FileView(valid_files)
                    file_view.add_item(file_menu)
                    await select_int.followup.send("Step 3: Select a file:", ephemeral=True, view=file_view)

                else:
                    # --- TV Branch ---
                    # For TV shows, build a text file listing all valid file options.
                    file_list_lines = []
                    for i, f in enumerate(valid_files):
                        line = f"{i+1}. {f['filename']} - {f['filesize']} bytes"
                        file_list_lines.append(line)
                    file_list_str = "\n".join(file_list_lines)
                    buffer = io.StringIO(file_list_str)

                    # Create a confirmation button.
                    confirm_button = Button(label="Confirm File Selection", style=ButtonStyle.green)

                    async def on_confirm(confirm_int: discord.Interaction):
                        await confirm_int.response.defer(ephemeral=True)
                        select_files_payload = {}
                        for idx, f in enumerate(valid_files, start=1):
                            select_files_payload[str(idx)] = {
                                "file_id": f["file_id"],
                                "filename": f["filename"],
                                "filesize": f["filesize"]
                            }
                        logger.info(f"[TV Select Files] Payload: {select_files_payload}")
                        select_files_url = f"{riven_url}/scrape/scrape/select_files/{session_id}"
                        logger.info(f"[TV Select Files] URL: {select_files_url}")
                        try:
                            sf_resp = requests.post(
                                select_files_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}',
                                    'Content-Type': 'application/json'
                                },
                                json=select_files_payload,
                                verify=False
                            )
                            logger.info(f"[TV Select Files] Status: {sf_resp.status_code}")
                            logger.info(f"[TV Select Files] Body: {sf_resp.text}")
                        except Exception as e:
                            logger.error(f"[TV Select Files] Exception: {e}")
                            await confirm_int.followup.send(f"Error selecting files: {e}", ephemeral=True)
                            return

                        if sf_resp.status_code != 200:
                            await confirm_int.followup.send("Failed to select files.", ephemeral=True)
                            return

                        # --- Continue: Call Parse Endpoint ---
                        filenames = [f["filename"] for f in valid_files]
                        parse_url = f"{riven_url}/scrape/parse"
                        logger.info(f"[Parse] URL: {parse_url}")
                        logger.info(f"[Parse] Payload: {filenames}")
                        try:
                            parse_resp = requests.post(
                                parse_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}',
                                    'Content-Type': 'application/json'
                                },
                                json=filenames,
                                verify=False
                            )
                            logger.info(f"[Parse] Status: {parse_resp.status_code}")
                            logger.info(f"[Parse] Body: {parse_resp.text}")
                        except Exception as e:
                            logger.error(f"[Parse] Exception: {e}")
                            await confirm_int.followup.send(f"Error parsing files: {e}", ephemeral=True)
                            return
                        if parse_resp.status_code != 200:
                            await confirm_int.followup.send("Failed to parse file data.", ephemeral=True)
                            return

                        parsed_data = parse_resp.json().get("data", [])
                        if not parsed_data or len(parsed_data) != len(valid_files):
                            await confirm_int.followup.send("Parsed file data is incomplete.", ephemeral=True)
                            return

                        # --- Build Update Attributes Payload ---
                        update_payload = {}
                        # Assume order between valid_files and parsed_data matches.
                        for f, p_item in zip(valid_files, parsed_data):
                            for season in p_item.get("seasons", []):
                                season_key = str(season)
                                if season_key not in update_payload:
                                    update_payload[season_key] = {}
                                for episode in p_item.get("episodes", []):
                                    episode_key = str(episode)
                                    update_payload[season_key][episode_key] = {
                                        "filename": f["filename"],
                                        "filesize": f["filesize"]
                                    }
                        logger.info(f"[TV Update Attributes] Payload: {update_payload}")

                        update_url = f"{riven_url}/scrape/scrape/update_attributes/{session_id}"
                        logger.info(f"[TV Update Attributes] URL: {update_url}")
                        try:
                            up_resp = requests.post(
                                update_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}',
                                    'Content-Type': 'application/json'
                                },
                                json=update_payload,
                                verify=False
                            )
                            logger.info(f"[TV Update Attributes] Status: {up_resp.status_code}")
                            logger.info(f"[TV Update Attributes] Body: {up_resp.text}")
                        except Exception as e:
                            logger.error(f"[TV Update Attributes] Exception: {e}")
                            await confirm_int.followup.send(f"Error updating attributes: {e}", ephemeral=True)
                            return
                        if up_resp.status_code != 200:
                            await confirm_int.followup.send("Failed to update attributes.", ephemeral=True)
                            return

                        # --- Step 6: Complete Session ---
                        complete_url = f"{riven_url}/scrape/scrape/complete_session/{session_id}"
                        logger.info(f"[Complete Session] URL: {complete_url}")
                        try:
                            comp_resp = requests.post(
                                complete_url,
                                headers={
                                    'Accept': 'application/json',
                                    'Authorization': f'Bearer {riven_api_token}'
                                },
                                verify=False
                            )
                            logger.info(f"[Complete Session] Status: {comp_resp.status_code}")
                            logger.info(f"[Complete Session] Body: {comp_resp.text}")
                        except Exception as e:
                            logger.error(f"[Complete Session] Exception: {e}")
                            await confirm_int.followup.send(f"Error completing session: {e}", ephemeral=True)
                            return
                        if comp_resp.status_code != 200:
                            await confirm_int.followup.send("Failed to complete session.", ephemeral=True)
                            return

                        await confirm_int.followup.send("TV scraping session completed.", ephemeral=True)

                    confirm_button.callback = on_confirm
                    confirm_view = discord.ui.View(timeout=180.0)
                    confirm_view.add_item(confirm_button)
                    await select_int.followup.send(
                        "Too many file options. Attached is the full list. Please review and click Confirm to proceed.",
                        ephemeral=True,
                        file=discord.File(fp=buffer, filename="file_options.txt"),
                        view=confirm_view
                    )

                # End TV branch

            stream_menu.callback = on_stream_select
            stream_view = discord.ui.View(timeout=180.0)
            stream_view.add_item(stream_menu)
            await interaction.followup.send("Step 2: Select a stream:", ephemeral=True, view=stream_view)

        except Exception as e:
            logger.error(f"Error during scrape: {e}")
            await interaction.followup.send(f"An error occurred while scraping: {e}", ephemeral=True)

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
        self.ctx.bot.active_recommended_messages[message.id] = self
        reaction_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for emoji in reaction_emojis[:len(self.recommended_ids)]:
            await message.add_reaction(emoji)
            logger.info(f"Added reaction {emoji} to refreshed message {message.id}")

class LatestReleasesView(View):
    def __init__(self, ctx, recent_items):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.recent_items = recent_items
        self.initiator_id = ctx.author.id
        # Add the select menu to the view.
        self.add_item(LatestReleasesDropdown(recent_items))
