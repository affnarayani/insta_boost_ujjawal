import requests
from bs4 import BeautifulSoup
import os
import re
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HEADLESS = True # Set to True for headless mode, False for headful mode

def download_pinterest_board_images(username, board_name):
    board_url = f"https://in.pinterest.com/{username}/{board_name}/"
    print(f"Fetching board: {board_url}", flush=True)

    # Set up Selenium WebDriver
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
    
    # You might need to specify the path to your chromedriver executable
    # service = Service(executable_path="path/to/chromedriver")
    driver = webdriver.Chrome(options=chrome_options) #, service=service)

    try:
        driver.get(board_url)
        # Wait for the page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        print(f"Timeout while loading the board URL: {board_url}", flush=True)
        driver.quit()
        return
    except Exception as e:
        print(f"Error fetching the board URL with Selenium: {e}", flush=True)
        driver.quit()
        return

    image_urls = set()
    scroll_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        scroll_count += 1
        print(f"Scrolled {scroll_count} times.", flush=True)

        # Wait to load page
        time.sleep(3)

        # Get new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Extract image URLs after each scroll
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Check for "More like this" section
        more_like_this_section = soup.find('div', string=re.compile(r'More like this', re.IGNORECASE))
        if more_like_this_section:
            print("Reached 'More like this' section. Waiting 5 seconds before stopping scraping.", flush=True)
            time.sleep(5) # Wait for 5 seconds as requested
            break

        # Strategy 1: Look for image URLs in script tags
        regex_patterns = [
            r'https://i\.pinimg\.com/(?:originals|564x|236x|736x|474x|600x)/[a-f0-9]{2}/[a-f0-9]{2}/[a-f0-9]{32}\.(?:jpg|jpeg|png|gif)',
            r'https://i\.pinimg\.com/photos/[a-f0-9]{32}/(?:originals|564x|236x|736x|474x|600x)/[a-f0-9]{32}\.(?:jpg|jpeg|png|gif)'
        ]

        for script in soup.find_all('script'):
            if script.string:
                for pattern in regex_patterns:
                    matches = re.findall(pattern, script.string)
                    for match in matches:
                        original_url = re.sub(r'/(564x|236x|736x|474x|600x)/', '/originals/', match)
                        image_urls.add(original_url)

        # Strategy 2: Look for image URLs directly in <img> tags
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if src and 'i.pinimg.com' in src:
                original_url = re.sub(r'/(564x|236x|736x|474x|600x)/', '/originals/', src)
                image_urls.add(original_url)
            
            data_src = img_tag.get('data-src')
            if data_src and 'i.pinimg.com' in data_src:
                original_url = re.sub(r'/(564x|236x|736x|474x|600x)/', '/originals/', data_src)
                image_urls.add(original_url)
        
        print(f"Images found so far: {len(image_urls)}", flush=True)

        if new_height == last_height:
            print("No more content to scroll. Stopping.", flush=True)
            break
        last_height = new_height
    
    driver.quit()

    if not image_urls:
        print("No image URLs found on the board page using any method. Make sure the username and board name are correct and the board is public.", flush=True)
        return

    # Create a directory to save images
    save_directory = "images"
    if os.path.exists(save_directory):
        print(f"Clearing existing images in: {save_directory}", flush=True)
        shutil.rmtree(save_directory)
    os.makedirs(save_directory, exist_ok=True)
    print(f"Saving images to: {save_directory}", flush=True)

    total_images = len(image_urls)
    print(f"Found {total_images} images.", flush=True)

    for i, img_url in enumerate(image_urls):
        try:
            img_response = requests.get(img_url, stream=True)
            img_response.raise_for_status()
            
            # Extract filename from URL
            filename = os.path.join(save_directory, os.path.basename(img_url))
            
            with open(filename, 'wb') as f:
                for chunk in img_response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloading {i+1}/{total_images}: {filename}", flush=True)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {img_url}: {e}", flush=True)

import json

def main():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Please make sure it exists in the same directory.", flush=True)
        return
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Please check its format.", flush=True)
        return

    pinterest_config = next((item for item in config if "pinterest_username_board" in item), None)

    if pinterest_config and "pinterest_username_board" in pinterest_config:
        username_board = pinterest_config["pinterest_username_board"]
        if '/' not in username_board:
            print("Invalid format for 'pinterest_username_board' in config.json. Please use username/boardname.", flush=True)
            return
        username, board_name = username_board.split('/', 1)
        download_pinterest_board_images(username.strip(), board_name.strip())
    else:
        print("Error: 'pinterest_username_board' not found in config.json.", flush=True)

if __name__ == "__main__":
    main()
