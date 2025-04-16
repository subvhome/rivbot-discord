import json
import logging
from core.logging_setup import logger
logger = logging.getLogger(__name__)

def load_config():
    try:
        with open("./data/config.json", "r") as f:
            logger.info("Loading config.json")
            config = json.load(f)
            logger.info("Config loaded successfully")
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config.json: {e}")
        raise