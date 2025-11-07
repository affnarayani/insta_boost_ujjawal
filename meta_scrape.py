import json
import time
import re # Import regex module
from selenium.webdriver.common.by import By
from login_meta import login_with_cookies, HEADLESS # Import the login function and HEADLESS variable

def load_blocked_users(filename="meta_blocked_users.txt"):
    """
    Loads a list of blocked users from a text file, one user per line.
    """
    try:
        with open(filename, 'r') as f:
            blocked_users = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(blocked_users)} blocked users from {filename}.")
        return blocked_users
    except FileNotFoundError:
        print(f"Warning: {filename} not found. No users will be blocked.")
        return []
    except Exception as e:
        print(f"Error loading blocked users from {filename}: {e}")
        return []

def extract_username_from_url(url):
    """
    Extracts the username from a Meta.ai URL.
    Example URL: "https://www.meta.ai/@iamrchiranjeevi/post/JD8AjjvsWML/?entrypoint=home_feed"
    """
    match = re.search(r"https://www\.meta\.ai/@([^/]+)/", url)
    if match:
        return match.group(1)
    return None

def get_meta_posts_scrape_count():
    """
    Fetches the value of 'meta_posts_scrape' from config.json.
    """
    try:
        with open('config.json', 'r') as f:
            config_list = json.load(f)
        for item in config_list:
            if "meta_posts_scrape" in item:
                return item["meta_posts_scrape"]
        return 0 # Default if not found
    except FileNotFoundError:
        print("Error: config.json not found.")
        return 0
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Check for valid JSON format.")
        return 0

def scrape_meta_ai_videos(driver, num_videos_to_scrape, existing_urls_set, blocked_users):
    """
    Scrapes video URLs from meta.ai using the new XPath pattern,
    ensuring only new, unique videos are counted towards the target.
    Filters out URLs from blocked users.
    Yields each new unique URL as it's found.
    """
    scraped_urls_current_run_set = set() # Use a set for efficient lookup of URLs scraped in the current run
    new_unique_videos_processed = 0
    index = 1 # Start with the first link
    scroll_attempts = 0
    max_scroll_attempts = num_videos_to_scrape * 5 # Allow more scroll attempts than videos to find enough new ones

    while new_unique_videos_processed < num_videos_to_scrape:
        xpath = f"(//a[@role='link'])[{index}]"
        try:
            video_element = driver.find_element(By.XPATH, xpath)
            video_url = video_element.get_attribute('href')
            
            # Validate URL
            if not video_url or not video_url.startswith("https://www.meta.ai/@"):
                index += 1 # Move to next index even if invalid
                continue

            # Extract username and check against blocked users
            username = extract_username_from_url(video_url)
            if username and username in blocked_users:
                print(f"Skipping URL from blocked user '{username}': {video_url}")
                index += 1
                continue

            # Check if URL is already scraped in this run or exists in the JSON file
            if video_url not in scraped_urls_current_run_set and video_url not in existing_urls_set:
                scraped_urls_current_run_set.add(video_url)
                new_unique_videos_processed += 1
                print(f"Scraped new unique video {new_unique_videos_processed}: {video_url}")
                scroll_attempts = 0 # Reset scroll attempts on successful scrape of a NEW video
                yield video_url # Yield the new unique URL
            else:
                pass # If URL is a duplicate (either in current run or existing), just move to next
        except Exception:
            # If an element is not found, try to scroll down
            print(f"Video element not found at XPath: {xpath}. Attempting to scroll... (Scroll attempt {scroll_attempts + 1}/{max_scroll_attempts})")
            
            if scroll_attempts >= max_scroll_attempts:
                print(f"Max scroll attempts ({max_scroll_attempts}) reached. Stopping scraping, found {new_unique_videos_processed} new unique videos.")
                break

            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(10) # Wait for 10 seconds after each scroll

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("No new content loaded after scrolling. Stopping scraping.")
                break # No new content, so stop

            scroll_attempts += 1
            # Do not increment index here, retry finding the element at the same index after scrolling
            continue 

        # Move to the next index
        index += 1

def main():
    target_url = "https://www.meta.ai"
    cookies_filename = "cookies_meta.json.encrypted"
    
    driver = None
    try:
        # Login to meta.ai
        driver = login_with_cookies(target_url, cookies_filename, headless=HEADLESS)
        if not driver:
            print("Failed to log in to Meta.ai. Exiting.")
            return

        print(f"Successfully logged in and redirected to {target_url}")

        # Get the number of posts to scrape from config.json
        num_videos_to_scrape = get_meta_posts_scrape_count()
        if num_videos_to_scrape == 0:
            print("No 'meta_posts_scrape' value found or it's 0 in config.json. Exiting.")
            return
        print(f"Configured to scrape {num_videos_to_scrape} videos.")

        # Load existing URLs from meta_scrape.json if it exists
        existing_posts_data = []
        try:
            with open('meta_scrape.json', 'r') as f:
                data = json.load(f)
                # Ensure existing data is in the new format or convert it
                if isinstance(data, list) and all(isinstance(item, dict) and "url" in item and "downloaded" in item for item in data):
                    existing_posts_data = data
                elif isinstance(data, list) and all(isinstance(item, str) for item in data):
                    # Convert old string-only format to new object format
                    existing_posts_data = [{"url": url, "downloaded": False} for url in data]
                    print("Converted old meta_scrape.json format to new object format.")
                else:
                    print("Warning: meta_scrape.json contains unexpected format. Starting with an empty list.")
                    existing_posts_data = []
            print(f"Loaded {len(existing_posts_data)} existing posts from meta_scrape.json")
        except FileNotFoundError:
            print("meta_scrape.json not found. A new file will be created.")
        except json.JSONDecodeError:
            print("Error: Could not decode meta_scrape.json. Starting with an empty list.")
            existing_posts_data = []

        # Extract just the URLs from existing_posts_data for the scraping logic
        existing_urls_set = {post["url"] for post in existing_posts_data}

        # Load blocked users
        blocked_users = load_blocked_users()

        # Scrape video URLs, passing existing_urls_set for filtering
        new_posts_count = 0
        for new_url_string in scrape_meta_ai_videos(driver, num_videos_to_scrape, existing_urls_set, blocked_users):
            new_post = {"url": new_url_string, "downloaded": False}
            existing_posts_data.insert(0, new_post) # Prepend new post
            existing_urls_set.add(new_url_string) # Add to set to prevent duplicates in current run
            new_posts_count += 1

            # Save the updated list to meta_scrape.json immediately
            with open('meta_scrape.json', 'w') as f:
                json.dump(existing_posts_data, f, indent=4)
            print(f"Appended new post to meta_scrape.json: {new_url_string}")

        print(f"Scraped {new_posts_count} new unique video URLs. Total posts saved: {len(existing_posts_data)} to meta_scrape.json")

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
    finally:
        if driver:
            # Wait for 15 seconds before closing the browser
            print("Waiting for 15 seconds before closing the browser...")
            time.sleep(15)
            driver.quit()
            print("Browser closed.")

if __name__ == "__main__":
    main()
