"""Download comic images from a website using Selenium."""

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

_logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # seconds

# Initialize argument parser to accept the website URL as an argument
parser = argparse.ArgumentParser(description="Download images from a comic website.")
parser.add_argument(
    "url", type=str, help="The URL of the website to start downloading images from"
)
args = parser.parse_args()

# Initialize WebDriver (Use the appropriate driver for your browser)
driver = webdriver.Chrome()

# Open the website from the passed argument
url = args.url
_logger.info("Opening the website: %s", url)
driver.get(url)


# A function to download images by URL
def download_image(url: str) -> bool:
    """Download an image from a URL and save it locally."""
    # Extract image name from URL
    image_name = Path(urlparse(url).path).name
    image_path = Path(image_name)

    # Check if the image already exists
    if image_path.exists():
        _logger.info("Image %s already exists, skipping download.", image_name)
        return False
    _logger.info("Downloading image from URL: %s", url)
    img_data = requests.get(url, timeout=REQUEST_TIMEOUT).content
    with image_path.open("wb") as handler:
        handler.write(img_data)
    _logger.info("Image %s downloaded successfully", image_name)
    return True


# No need to define a specific number of images now
count = 1

while True:
    _logger.info("Processing image %s...", count)

    # Find the image element by its ID
    image_element = driver.find_element(By.ID, "cc-comic")

    # Get the image URL from the 'src' attribute
    image_url = image_element.get_attribute("src")
    _logger.info("Found image URL: %s", image_url)

    # Download the image if it doesn't already exist
    if download_image(image_url):
        count += 1  # Increment count only if the image was downloaded

    # Try to find the 'Next' button by its class
    try:
        _logger.info("Clicking the 'Next' button to load the next image...")
        next_button = driver.find_element(By.CSS_SELECTOR, "a.cc-next")

        # Navigate to the URL in the 'href' of the next button
        next_button_url = next_button.get_attribute("href")
        driver.get(next_button_url)

    except NoSuchElementException:
        # If the 'Next' button is not found, it means we've reached the last image
        _logger.info("No 'Next' button found. Reached the end of images.")
        break

# Close the browser
_logger.info("All images processed, closing the browser.")
driver.quit()
