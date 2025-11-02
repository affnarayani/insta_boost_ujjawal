import json
import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from login import login_to_instagram # Assuming login.py has a function named login_to_instagram that returns a WebDriver instance

def read_config():
    with open('config.json', 'r') as f:
        config_list = json.load(f)
    
    config = {}
    for item in config_list:
        config.update(item)
    return config

def extract_post_id(post_url):
    parts = post_url.split('/p/')
    if len(parts) > 1:
        post_id_part = parts[1].split('/')[0]
        return post_id_part
    return None

def save_scraped_posts(posts_data, target_username, filename="scraped_posts.json"):
    filepath = filename
    
    file_content = {"scraped_username": target_username, "posts": []}
    existing_post_ids = set()

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                loaded_content = json.load(f)
                if loaded_content.get("scraped_username") == target_username:
                    file_content = loaded_content
                    for post in file_content.get("posts", []):
                        post_id = extract_post_id(post.get("post_url", ""))
                        if post_id:
                            existing_post_ids.add(post_id)
                else:
                    print(f"Scraping for a new username '{target_username}'. Clearing previous data for '{loaded_content.get('scraped_username')}' from {filepath}.")
                    # Empty the 'posts' folder
                    posts_folder = "posts"
                    if os.path.exists(posts_folder) and os.path.isdir(posts_folder):
                        for filename in os.listdir(posts_folder):
                            file_path = os.path.join(posts_folder, filename)
                            try:
                                if os.path.isfile(file_path) or os.path.islink(file_path):
                                    os.unlink(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                                print(f"Removed {file_path}")
                            except Exception as e:
                                print(f"Failed to delete {file_path}. Reason: {e}")
                        print(f"Emptied the '{posts_folder}' folder.")
            except json.JSONDecodeError:
                print(f"Existing {filepath} is empty or malformed. Starting fresh.")
    
    new_unique_posts = []
    for post in posts_data:
        post_id = extract_post_id(post.get("post_url", ""))
        if post_id and post_id not in existing_post_ids:
            new_unique_posts.append(post)
            existing_post_ids.add(post_id)

    file_content["posts"].extend(new_unique_posts)

    with open(filepath, 'w') as f:
        json.dump(file_content, f, indent=4)
    print(f"Saved {len(new_unique_posts)} new posts to {filepath}. Total posts for {target_username}: {len(file_content['posts'])}")

def scrape_posts_only(driver, target_username):
    profile_url = f"https://www.instagram.com/{target_username}/"
    driver.get(profile_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile picture')]"))
        )
    except TimeoutException:
        print(f"Could not load profile page for {target_username}. It might be private or not exist.")
        return

    print(f"Starting to scrape posts for {target_username} as we scroll...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # Load existing post IDs to avoid re-scraping
    existing_post_ids_from_file = set()
    filepath = "scraped_posts.json"
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                loaded_content = json.load(f)
                if loaded_content.get("scraped_username") == target_username:
                    for post in loaded_content.get("posts", []):
                        post_id = extract_post_id(post.get("post_url", ""))
                        if post_id:
                            existing_post_ids_from_file.add(post_id)
            except json.JSONDecodeError:
                pass # Handled in save_scraped_posts, but good to be safe

    seen_post_ids_in_session = set()
    total_scraped_count = 0

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3) # Wait for new content to load

        # Find all post elements
        post_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
        
        new_posts_to_save = []
        for element in post_elements:
            href = element.get_attribute('href')
            if href:
                post_id = extract_post_id(href)
                if post_id and post_id not in existing_post_ids_from_file and post_id not in seen_post_ids_in_session:
                    seen_post_ids_in_session.add(post_id)
                    new_posts_to_save.append({"post_url": href})
        
        if new_posts_to_save:
            save_scraped_posts(new_posts_to_save, target_username)
            total_scraped_count += len(new_posts_to_save)
            print(f"Currently scraped {total_scraped_count} new unique post URLs in this session.")

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Reached end of scrollable content.")
            break
        last_height = new_height

    print(f"Finished scraping. Total new unique post URLs found in this session: {total_scraped_count}")

    if total_scraped_count == 0 and not existing_post_ids_from_file:
        print("No posts found. This might be due to an empty profile, privacy settings, or a change in Instagram's HTML structure.")


def main():
    config = read_config()
    username = config.get('username')
    scrape_posts_username = config.get('scrape_posts_username')

    if not username or not scrape_posts_username:
        print("Error: 'username' or 'scrape_posts_username' not found in config.json")
        return

    print(f"Attempting to log in as {username}...")
    driver = login_to_instagram(username) # Call the login function from login.py

    if driver:
        print(f"Successfully logged in. Scraping posts for {scrape_posts_username}...")
        scrape_posts_only(driver, scrape_posts_username)
        print("Scraping complete.")
        driver.quit()
    else:
        print("Login failed. Exiting.")

if __name__ == "__main__":
    main()
