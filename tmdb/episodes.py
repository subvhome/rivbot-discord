import requests
import logging
from core.logging_setup import logger

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
