import requests
from core.logging_setup import logger
import asyncio

def handle_api_response(response):
    if "error" in response:
        return None, response["error"]
    return response, None

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
