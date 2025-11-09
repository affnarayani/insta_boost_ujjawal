import os
import json
import re
import requests # Import requests for session
from urllib.parse import urlparse
import time
from bs4 import BeautifulSoup # Import BeautifulSoup for HTML parsing
from PIL import Image # Import Pillow for image conversion
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from login import login_to_instagram # Import the login function

def get_post_id_from_url(post_url):
    """Extracts the post ID from an Instagram post URL."""
    match = re.search(r'/p/([^/]+)/', post_url)
    if match:
        return match.group(1)
    return None

def get_existing_posts(posts_folder):
    """Gets a set of post IDs already downloaded in the posts folder."""
    existing_ids = set()
    if os.path.exists(posts_folder):
        for filename in os.listdir(posts_folder):
            # Match files like {post_id}.jpg, {post_id}.png, {post_id}_1.jpg, etc.
            match = re.match(r'([a-zA-Z0-9_-]+)(?:_\d+)?\.(jpg|png)', filename) # Only look for jpg or png
            if match:
                existing_ids.add(match.group(1))
    return existing_ids

def download_image(session_obj, image_url, filepath):
    """Downloads an image from a URL to a specified filepath using the provided session."""
    try:
        response = session_obj.get(image_url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded: {filepath}", flush=True)
        return True
    except Exception as e:
        print(f"Error downloading {image_url} to {filepath}: {e}", flush=True)
        return False

def convert_webp_to_png(webp_path, png_path):
    """Converts a WebP image to PNG format."""
    try:
        with Image.open(webp_path) as img:
            img.save(png_path, "PNG")
        print(f"Converted {webp_path} to {png_path}", flush=True)
        return True
    except Exception as e:
        print(f"Error converting {webp_path} to PNG: {e}", flush=True)
        return False

def download_instagram_posts():
    """Downloads Instagram posts based on scraped_posts.json."""
    posts_folder = 'posts'
    if not os.path.exists(posts_folder):
        os.makedirs(posts_folder)
        print(f"Created folder: {posts_folder}", flush=True)

    # Get username from config.json
    username = None
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        for item in config_data:
            if 'username' in item:
                username = item['username']
                break
        if not username:
            print("Error: 'username' not found in config.json.", flush=True)
            return
    except FileNotFoundError:
        print("Error: config.json not found.", flush=True)
        return
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Check file format.", flush=True)
        return

    # Login and get the Selenium driver
    print(f"Attempting to log in as {username}...", flush=True)
    driver = None
    try:
        driver = login_to_instagram(username)
        if not driver:
            print("Failed to obtain a valid Selenium driver. Exiting.", flush=True)
            return
        print("Successfully obtained Selenium driver.", flush=True)

        # Create a requests session and add cookies from the Selenium driver
        session_obj = requests.Session()
        for cookie in driver.get_cookies():
            session_obj.cookies.set(
                cookie['name'],
                cookie['value'],
                domain=cookie['domain'],
                path=cookie['path'],
                secure=cookie['secure']
            )
        print("Requests session created with cookies.", flush=True)

        try:
            with open('scraped_posts.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            posts_to_download = data.get('posts', [])
        except FileNotFoundError:
            print("Error: scraped_posts.json not found.", flush=True)
            return
        except json.JSONDecodeError:
            print("Error: Could not decode scraped_posts.json. Check file format.", flush=True)
            return

        existing_ids = get_existing_posts(posts_folder)
        print(f"Found {len(existing_ids)} existing posts in '{posts_folder}'.", flush=True)

        for post_info in posts_to_download:
            post_url = post_info.get('post_url')
            if not post_url:
                continue

            post_id = get_post_id_from_url(post_url)
            if not post_id:
                print(f"Could not extract post ID from URL: {post_url}", flush=True)
                continue

            if post_id in existing_ids:
                print(f"Skipping post {post_id}: Already downloaded.", flush=True)
                continue

            print(f"Processing post: {post_url}", flush=True)
            try:
                driver.get(post_url)
                # Wait for the specific div to be present
                WebDriverWait(driver, 20).until( # Increased timeout to 20 seconds
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagu"))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Find the div with classes _aagu
                target_div = soup.find('div', class_=['_aagu'])
                
                if target_div:
                    # Find the div with class _aagv within _aagu
                    aagv_div = target_div.find('div', class_='_aagv')
                    if aagv_div:
                        # Find the img tag within _aagv
                        img_tag = aagv_div.find('img')
                        if img_tag and 'src' in img_tag.attrs:
                            src_value = img_tag['src']
                            # print(f"src=\"{src_value}\"") # Print the src value as requested
                            
                            webp_filepath = os.path.join(posts_folder, f"{post_id}.webp")
                            png_filepath = os.path.join(posts_folder, f"{post_id}.png")

                            if download_image(session_obj, src_value, webp_filepath):
                                if convert_webp_to_png(webp_filepath, png_filepath):
                                    os.remove(webp_filepath) # Delete the webp file after conversion
                                    print(f"Deleted temporary file: {webp_filepath}", flush=True)
                                    existing_ids.add(post_id) # Add to existing_ids after successful download and conversion
                                else:
                                    print(f"Failed to convert {webp_filepath} to PNG.", flush=True)
                            else:
                                print(f"Failed to download image for post {post_id}.", flush=True)
                        else:
                            print("src attribute not found in img tag within the _aagv div.", flush=True)
                    else:
                        print("Inner div (_aagv) not found within the target div (_aagu).", flush=True)
                else:
                    print("Target div (_aagu) not found on the page.", flush=True)
            except TimeoutException:
                print(f"Timeout waiting for elements on page: {post_url}", flush=True)
            except NoSuchElementException:
                print(f"Specific element not found on page: {post_url}", flush=True)
            except Exception as e:
                print(f"An error occurred while processing {post_url}: {e}", flush=True)
            time.sleep(2) # Be polite and wait a bit between requests

    finally:
        if driver:
            driver.quit()
            print("Browser closed.", flush=True)

if __name__ == "__main__":
    download_instagram_posts()
