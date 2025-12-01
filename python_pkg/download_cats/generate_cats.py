"""Download cat images from TheCatAPI.

Fetches cat images in batches and saves them to a local directory.
"""

import json
import logging
from pathlib import Path

import requests

_logger = logging.getLogger(__name__)

MAX_REQUESTS = 90
REQUEST_TIMEOUT = 30  # seconds


def _download_single_image(image_url: str) -> None:
    """Download and save a single image from URL.

    Args:
        image_url: The URL of the image to download.
    """
    try:
        # Get the image content
        resp = requests.get(image_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()  # Raise an exception for HTTP errors

        # Extract the image name from the URL
        image_name = Path(image_url).name
        image_path = Path("./CATS2/") / image_name

        # Save the image to the directory
        with image_path.open("wb") as file:
            file.write(resp.content)

        _logger.info("Saved %s as %s", image_url, image_path)

    except requests.exceptions.RequestException:
        _logger.exception("Failed to download %s", image_url)


requests_send = 0
while requests_send < MAX_REQUESTS:
    res = requests.get(
        "https://api.thecatapi.com/v1/images/search?limit=100&api_key=",
        timeout=REQUEST_TIMEOUT,
    )
    requests_send += 1
    response = json.loads(res.text)
    urls = [cat.get("url") for cat in response]

    Path("./CATS2").mkdir(parents=True, exist_ok=True)
    for url in urls:
        _download_single_image(url)
