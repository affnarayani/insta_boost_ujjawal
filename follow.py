import json
import time
import os
from datetime import datetime
from colorama import Fore, Style, init
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Initialize Colorama
init(autoreset=True)

# Import login function from login.py
from login import login_to_instagram

# XPaths
PUBLIC_ACCOUNT_FOLLOW_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/section[1]/div/div/div/div/div[1]/button"
PRIVATE_ACCOUNT_FOLLOW_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/section[1]/div/div/div/div/div/button"
NUMBER_OF_FOLLOWERS_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a/span/span/span"
NUMBER_OF_FOLLOWING_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[3]/a/span/span/span"

def parse_number_with_comma(text):
    """Parses a string number that may contain commas, K (thousands), or M (millions) into an integer."""
    text = text.replace(',', '')
    if text.endswith('K'):
        return int(float(text[:-1]) * 1000)
    elif text.endswith('M'):
        return int(float(text[:-1]) * 1_000_000)
    else:
        return int(text)

def read_config():
    """Reads and parses the config.json file."""
    with open('config.json', 'r') as f:
        config_list = json.load(f)
    config = {}
    for item in config_list:
        config.update(item)
    return config

def read_scraped_followers():
    """Reads and parses the scraped_followers.json file."""
    with open('scraped_followers.json', 'r') as f:
        data = json.load(f)
    return data.get('followers', [])

def update_followed_unfollowed_json(username_to_store):
    """Updates the followed_unfollowed.json file with the followed account."""
    file_path = 'followed_unfollowed.json'
    data = []
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = [] # Handle empty or malformed JSON

    new_entry = {
        f"{username_to_store}_followed": True,
        f"{username_to_store}_unfollowed": False,
        f"{username_to_store}_liked_commented": False,
        "timestamp": datetime.now().isoformat()
    }
    data.append(new_entry)

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"{Fore.GREEN}Successfully recorded follow activity for {username_to_store}.{Style.RESET_ALL}")

def get_already_followed_users():
    """Reads followed_unfollowed.json and returns a set of usernames already followed."""
    file_path = 'followed_unfollowed.json'
    already_followed = set()
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                for entry in data:
                    for key, value in entry.items():
                        if key.endswith('_followed') and value is True:
                            username = key.replace('_followed', '')
                            already_followed.add(username)
            except json.JSONDecodeError:
                pass # Handle empty or malformed JSON
    return already_followed

def main():
    config = read_config()
    follow_private = config.get('follow_private', False)
    ratio_condition_str = config.get('follower_to_following_ratio', 'ratio > 1')
    instagram_username = config.get('username')

    if not instagram_username:
        print(f"{Fore.RED}Error: Instagram username not found in config.json.{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}Attempting to log in to Instagram...{Style.RESET_ALL}")
    driver = login_to_instagram(instagram_username)
    if not driver:
        print(f"{Fore.RED}Failed to log in. Exiting.{Style.RESET_ALL}")
        return

    followers_to_check = read_scraped_followers()
    if not followers_to_check:
        print(f"{Fore.YELLOW}No followers found in scraped_followers.json to process.{Style.RESET_ALL}")
        driver.quit()
        return

    already_followed_users = get_already_followed_users()
    print(f"{Fore.CYAN}Already followed users: {already_followed_users}{Style.RESET_ALL}")

    followed_one_account = False
    for target_username in followers_to_check:
        if followed_one_account:
            break # Exit after following one account

        if target_username in already_followed_users:
            print(f"{Fore.YELLOW}Skipping {target_username}: Already followed.{Style.RESET_ALL}")
            continue

        print(f"\n{Fore.BLUE}Processing profile: {target_username}{Style.RESET_ALL}")
        profile_url = f"https://www.instagram.com/{target_username}/"
        driver.get(profile_url)
        time.sleep(3) # Give time for the page to load

        try:
            # Check if the account is private
            try:
                driver.find_element(By.XPATH, "//h2[contains(text(), 'This Account is Private')]")
                is_private = True
                print(f"{Fore.YELLOW}Account {target_username} is private.{Style.RESET_ALL}")
            except NoSuchElementException:
                is_private = False
                print(f"{Fore.GREEN}Account {target_username} is public.{Style.RESET_ALL}")

            if is_private and not follow_private:
                print(f"{Fore.YELLOW}Skipping private account {target_username} as per config.{Style.RESET_ALL}")
                continue

            # Get followers and following counts
            try:
                followers_text = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, NUMBER_OF_FOLLOWERS_XPATH))
                ).text
                followers_count = parse_number_with_comma(followers_text)
                print(f"{Fore.MAGENTA}Followers: {followers_count}{Style.RESET_ALL}")
            except (NoSuchElementException, TimeoutException):
                print(f"{Fore.RED}Could not find followers count for {target_username}. Skipping.{Style.RESET_ALL}")
                continue

            try:
                following_text = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, NUMBER_OF_FOLLOWING_XPATH))
                ).text
                following_count = parse_number_with_comma(following_text)
                print(f"{Fore.MAGENTA}Following: {following_count}{Style.RESET_ALL}")
            except (NoSuchElementException, TimeoutException):
                print(f"{Fore.RED}Could not find following count for {target_username}. Skipping.{Style.RESET_ALL}")
                continue

            if following_count == 0:
                print(f"{Fore.YELLOW}Skipping {target_username}: Following count is zero, cannot calculate ratio.{Style.RESET_ALL}")
                continue

            ratio = followers_count / following_count
            print(f"{Fore.MAGENTA}Follower to Following Ratio: {ratio:.2f}{Style.RESET_ALL}")

            # Evaluate ratio condition
            condition_met = False
            try:
                # Safely evaluate the condition string
                # Create a dictionary for the local scope of eval
                eval_globals = {"ratio": ratio}
                condition_met = eval(ratio_condition_str, {}, eval_globals)
                print(f"{Fore.CYAN}Condition '{ratio_condition_str}' evaluated to: {condition_met}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error evaluating ratio condition '{ratio_condition_str}': {e}{Style.RESET_ALL}")
                continue

            if condition_met:
                print(f"{Fore.GREEN}Ratio condition met for {target_username}. Attempting to follow.{Style.RESET_ALL}")
                follow_button_xpath = PRIVATE_ACCOUNT_FOLLOW_BUTTON_XPATH if is_private else PUBLIC_ACCOUNT_FOLLOW_BUTTON_XPATH
                try:
                    follow_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, follow_button_xpath))
                    )
                    if follow_button.text.lower() == "follow":
                        follow_button.click()
                        print(f"{Fore.GREEN}Successfully clicked follow button for {target_username}.{Style.RESET_ALL}")
                        update_followed_unfollowed_json(target_username)
                        followed_one_account = True
                        break # Exit after following one account
                    else:
                        print(f"{Fore.YELLOW}Follow button not in 'Follow' state for {target_username}. Skipping.{Style.RESET_ALL}")
                except (NoSuchElementException, TimeoutException):
                    print(f"{Fore.RED}Follow button not found or not clickable for {target_username}. Skipping.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Ratio condition not met for {target_username}. Skipping.{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}An unexpected error occurred while processing {target_username}: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"{Fore.CYAN}Waiting for 15 seconds before closing the browser...{Style.RESET_ALL}")
    time.sleep(15) # Wait for 15 seconds after activity

    driver.quit()
    print(f"{Fore.CYAN}Program finished.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
