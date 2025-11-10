import json
import time
import re
import os
from datetime import datetime # Import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from login import login_to_instagram # Import the login function

def parse_follower_count(count_str):
    """
    Parses a string representing a follower count into an integer.
    Handles commas, 'K' for thousands, and 'M' for millions.
    """
    count_str = count_str.replace(',', '') # Remove commas
    if 'K' in count_str:
        return int(float(count_str.replace('K', '')) * 1000)
    elif 'M' in count_str:
        return int(float(count_str.replace('M', '')) * 1000000)
    else:
        return int(count_str)

def get_instagram_followers(username):
    driver = None
    try:
        # Use the login_to_instagram function from login.py
        # Assuming the username for login can be passed directly or retrieved from config.json
        # For this task, we'll assume a generic login is sufficient, or the user will provide a username.
        # If a specific username is needed for login, it should be passed here.
        # For now, let's try to read it from config.json as login.py does in its __main__ block.
        
        # Read username from config.json
        test_username = None
        try:
            with open('config.json', 'r') as f:
                config_list = json.load(f)
            for item in config_list:
                if 'username' in item:
                    test_username = item['username']
                    break
        except FileNotFoundError:
            print("Error: config.json not found. Cannot retrieve username for login.", flush=True)
            return None
        except Exception as e:
            print(f"Error reading username from config.json: {e}", flush=True)
            return None

        if not test_username:
            print("Error: 'username' not found in config.json. Cannot proceed with login.", flush=True)
            return None

        driver = login_to_instagram(test_username)
        if not driver:
            print("Failed to log in to Instagram.", flush=True)
            return None

        profile_url = f"https://www.instagram.com/{username}/"
        driver.get(profile_url)

        # Wait for the followers element to be present
        # The XPath provided: /html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a/span/span/span
        # This XPath is very specific and might change. A more robust approach would be to find an element
        # that contains "followers" text and then navigate to its sibling/child for the count.
        # However, for this task, we will use the provided XPath.
        
        # Add a sleep to allow page to load completely before trying to find elements
        time.sleep(5) 

        followers_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a/span/span/span"
        
        try:
            # Wait for the element to be visible
            followers_element = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.XPATH, followers_xpath))
            )
            follower_count_str = followers_element.get_attribute("title")
            if not follower_count_str:
                # Fallback if title attribute is empty, try text content
                follower_count_str = followers_element.text

            if follower_count_str:
                total_followers = parse_follower_count(follower_count_str)
                print(f"Total number of followers for {username}: {total_followers}", flush=True)
                
                # Save follower count to growth.json
                save_follower_count_to_json(total_followers)
                
                return total_followers
            else:
                print(f"Could not retrieve follower count string for {username}.", flush=True)
                return None
        except TimeoutException:
            print(f"Timeout: Followers element not found for {username} at XPath: {followers_xpath}", flush=True)
            # Try a more generic approach if the specific XPath fails
            try:
                # Look for elements that contain "followers" text
                followers_text_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/followers')]")
                for elem in followers_text_elements:
                    # The actual count might be in a child span or a sibling
                    # This is a heuristic and might need adjustment based on actual page structure
                    count_match = re.search(r'(\d[\d,.]*[KM]?)', elem.text)
                    if count_match:
                        count_str = count_match.group(1)
                        total_followers = parse_follower_count(count_str)
                        print(f"Total number of followers for {username} (generic search): {total_followers}", flush=True)
                        return total_followers
            except Exception as e:
                print(f"Error during generic followers search: {e}", flush=True)
            return None
        except NoSuchElementException:
            print(f"NoSuchElementException: Followers element not found for {username} at XPath: {followers_xpath}", flush=True)
            return None
        except Exception as e:
            print(f"An error occurred while getting follower count: {e}", flush=True)
            return None

    except Exception as e:
        print(f"An error occurred in get_instagram_followers: {e}", flush=True)
        return None
    finally:
        if driver:
            driver.quit()

def save_follower_count_to_json(follower_count):
    """
    Saves the follower count to growth.json with the current date.
    If today's date already exists, it does not append the data.
    """
    growth_file = "growth.json"
    today_date = datetime.now().strftime("%d-%m-%Y")
    
    data = []
    if os.path.exists(growth_file):
        try:
            with open(growth_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {growth_file} is empty or malformed. Starting with an empty list.", flush=True)
            data = []

    # Check if today's date already exists in the data
    date_exists = False
    for entry in data:
        if today_date in entry:
            date_exists = True
            break

    if not date_exists:
        data.append({today_date: follower_count})
        with open(growth_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Follower count for {today_date} saved to {growth_file}.", flush=True)
    else:
        print(f"Data for {today_date} already exists in {growth_file}. Skipping save.", flush=True)

if __name__ == "__main__":
    # Fetch target_username from config.json
    target_username = None
    try:
        with open('config.json', 'r') as f:
            config_list = json.load(f)
        for item in config_list:
            if 'username' in item:
                target_username = item['username']
                break
    except FileNotFoundError:
        print("Error: config.json not found. Cannot retrieve target username.", flush=True)
    except Exception as e:
        print(f"Error reading target username from config.json: {e}", flush=True)

    if target_username:
        get_instagram_followers(target_username)
    else:
        print("Target username not found in config.json. Exiting.", flush=True)
