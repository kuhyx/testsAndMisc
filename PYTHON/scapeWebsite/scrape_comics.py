import argparse
import os
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

# Initialize argument parser to accept the website URL as an argument
parser = argparse.ArgumentParser(description="Download images from a comic website.")
parser.add_argument("url", type=str, help="The URL of the website to start downloading images from")
args = parser.parse_args()

# Initialize WebDriver (Use the appropriate driver for your browser)
driver = webdriver.Chrome()

# Open the website from the passed argument
url = args.url
print(f"Opening the website: {url}")
driver.get(url)


# A function to download images by URL
def download_image(url):
    # Extract image name from URL
    image_name = os.path.basename(urlparse(url).path)

    # Check if the image already exists
    if os.path.exists(image_name):
        print(f"Image {image_name} already exists, skipping download.")
        return False
    print(f"Downloading image from URL: {url}")
    img_data = requests.get(url).content
    with open(image_name, "wb") as handler:
        handler.write(img_data)
    print(f"Image {image_name} downloaded successfully")
    return True


# No need to define a specific number of images now
count = 1

while True:
    print(f"Processing image {count}...")

    # Find the image element by its ID
    image_element = driver.find_element(By.ID, "cc-comic")

    # Get the image URL from the 'src' attribute
    image_url = image_element.get_attribute("src")
    print(f"Found image URL: {image_url}")

    # Download the image if it doesn't already exist
    if download_image(image_url):
        count += 1  # Increment count only if the image was downloaded

    # Try to find the 'Next' button by its class
    try:
        print("Clicking the 'Next' button to load the next image...")
        next_button = driver.find_element(By.CSS_SELECTOR, "a.cc-next")

        # Navigate to the URL in the 'href' of the next button
        next_button_url = next_button.get_attribute("href")
        driver.get(next_button_url)

    except:
        # If the 'Next' button is not found, it means we've reached the last image
        print("No 'Next' button found. Reached the end of images.")
        break

# Close the browser
print("All images processed, closing the browser.")
driver.quit()
