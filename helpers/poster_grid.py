import io
import math
from PIL import Image, ImageOps
import requests
from concurrent.futures import ThreadPoolExecutor
from core.logging_setup import logger
async def create_poster_grid(poster_info):
    """
    Create a poster grid image.

    If `resize_grid` is True, images are resized to fixed width/height and arranged in a grid.
    If False, original image sizes are preserved, and a best-fit grid is calculated.
    """
    resize_grid = False  # Set to True to resize, False for original sizes

    # Used only if resize_grid is True
    IMAGE_WIDTH = 150
    IMAGE_HEIGHT = 220
    GRID_COLUMNS = 2

    posters = []
    placeholder_size = (IMAGE_WIDTH if resize_grid else 200, IMAGE_HEIGHT if resize_grid else 300)
    placeholder = Image.new("RGB", placeholder_size, color=(50, 50, 50))

    for info in poster_info:
        url = info.get("poster_url")
        if url:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    if resize_grid:
                        img = ImageOps.fit(img, (IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
                    posters.append(img)
                else:
                    posters.append(placeholder)
            except Exception as e:
                logger.error(f"Error fetching poster from {url}: {e}")
                posters.append(placeholder)
        else:
            posters.append(placeholder)

    total = len(posters)
    columns = GRID_COLUMNS if resize_grid else 2  # Use fixed 2-column grid even when not resizing
    rows = math.ceil(total / columns)

    # Determine image size
    if resize_grid:
        img_width = IMAGE_WIDTH
        img_height = IMAGE_HEIGHT
    else:
        # Use max width and height of the images to compute consistent grid spacing
        img_width = max(img.width for img in posters)
        img_height = max(img.height for img in posters)

    grid_width = columns * img_width
    grid_height = rows * img_height
    grid = Image.new("RGB", (grid_width, grid_height), color=(0, 0, 0))

    for idx, poster in enumerate(posters):
        row = idx // columns
        col = idx % columns
        x = col * img_width
        y = row * img_height
        grid.paste(poster, (x, y))

    return grid


