import re
import requests
import logging
from core.logging_setup import logger

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
                if len(data.get("results", [])) < 20:
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
