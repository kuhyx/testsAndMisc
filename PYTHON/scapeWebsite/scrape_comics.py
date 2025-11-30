"""Download comic images from a website using Selenium."""

import argparse
import logging
import os
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO)

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
logging.info(f"Opening the website: {url}")
driver.get(url)


# A function to download images by URL
def download_image(url: str) -> bool:
    """Download an image from a URL and save it locally."""
    # Extract image name from URL
    image_name = os.path.basename(urlparse(url).path)

    # Check if the image already exists
    if os.path.exists(image_name):
        logging.info(f"Image {image_name} already exists, skipping download.")
        return False
    logging.info(f"Downloading image from URL: {url}")
    img_data = requests.get(url, timeout=REQUEST_TIMEOUT).content
    with open(image_name, "wb") as handler:
        handler.write(img_data)
    logging.info(f"Image {image_name} downloaded successfully")
    return True


# No need to define a specific number of images now
count = 1

while True:
    logging.info(f"Processing image {count}...")

    # Find the image element by its ID
    image_element = driver.find_element(By.ID, "cc-comic")

    # Get the image URL from the 'src' attribute
    image_url = image_element.get_attribute("src")
    logging.info(f"Found image URL: {image_url}")

    # Download the image if it doesn't already exist
    if download_image(image_url):
        count += 1  # Increment count only if the image was downloaded

    # Try to find the 'Next' button by its class
    try:
        logging.info("Clicking the 'Next' button to load the next image...")
        next_button = driver.find_element(By.CSS_SELECTOR, "a.cc-next")

        # Navigate to the URL in the 'href' of the next button
        next_button_url = next_button.get_attribute("href")
        driver.get(next_button_url)

    except Exception:
        # If the 'Next' button is not found, it means we've reached the last image
        logging.info("No 'Next' button found. Reached the end of images.")
        break

# Close the browser
logging.info("All images processed, closing the browser.")
driver.quit()
