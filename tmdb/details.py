import requests
from core.logging_setup import logger
import logging

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
