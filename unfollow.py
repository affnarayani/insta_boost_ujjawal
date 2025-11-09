import json
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Import the login function from login.py
from login import login_to_instagram

# Initialize Colorama
init(autoreset=True)

# Define XPaths
FOLLOWING_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/section[1]/div/div/div/div/div[1]/button"
DYNAMIC_POPUP_XPATH = "/html/body/div[4]/div[2]/div/div/div[1]/div/div[2]/div/div/div"
UNFOLLOW_BUTTON_XPATH = "/html/body/div[4]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[8]/div[1]"

def print_step(message, color=Fore.CYAN):
    print(f"{color}{message}{Style.RESET_ALL}", flush=True)

def unfollow_account():
    print_step("Starting unfollow process...", Fore.MAGENTA)

    # 1. Read config.json
    unfollow_after_days = 7
    username_to_login = None
    try:
        with open('config.json', 'r') as f:
            config_list = json.load(f)
        
        config_dict = {}
        for item in config_list:
            config_dict.update(item)

        unfollow_after_days = config_dict.get('unfollow_after_days', 7)
        username_to_login = config_dict.get('username')
        
        if not username_to_login:
            print_step("Error: 'username' not found in config.json. Cannot log in.", Fore.RED, flush=True)
            return
        print_step(f"Config loaded: unfollow_after_days={unfollow_after_days}, username={username_to_login}", Fore.GREEN, flush=True)
    except FileNotFoundError:
        print_step("Error: config.json not found.", Fore.RED, flush=True)
        return
    except json.JSONDecodeError:
        print_step("Error: Could not decode config.json. Check file format.", Fore.RED, flush=True)
        return

    # 2. Read followed_unfollowed.json
    try:
        with open('followed_unfollowed.json', 'r+') as f:
            followed_data = json.load(f)
        print_step("Followed/Unfollowed data loaded.", Fore.GREEN, flush=True)
    except FileNotFoundError:
        print_step("Error: followed_unfollowed.json not found.", Fore.RED, flush=True)
        return
    except json.JSONDecodeError:
        print_step("Error: Could not decode followed_unfollowed.json. Check file format.", Fore.RED, flush=True)
        return

    # 3. Find an eligible account to unfollow before launching the browser
    eligible_account_info = None
    eligible_account_index = -1

    for i, account_info in enumerate(followed_data):
        username_prefix = None
        followed_status = False
        unfollowed_status = False
        timestamp_str = None

        for key, value in account_info.items():
            if key.endswith('_followed'):
                username_prefix = key.replace('_followed', '')
                followed_status = value
            elif key.endswith('_unfollowed'):
                unfollowed_status = value
            elif key == 'timestamp':
                timestamp_str = value
        
        if username_prefix and followed_status is True and unfollowed_status is False:
            if timestamp_str:
                try:
                    followed_timestamp = datetime.fromisoformat(timestamp_str)
                    current_timestamp = datetime.now()
                    
                    if current_timestamp - followed_timestamp >= timedelta(days=unfollow_after_days):
                        print_step(f"Found eligible account to unfollow: {username_prefix}", Fore.YELLOW, flush=True)
                        eligible_account_info = account_info
                        eligible_account_index = i
                        break # Found one, no need to search further
                    else:
                        print_step(f"Account {username_prefix} not yet eligible for unfollow (less than {unfollow_after_days} days).", Fore.YELLOW, flush=True)
                except ValueError:
                    print_step(f"Warning: Invalid timestamp format for {username_prefix}. Skipping.", Fore.YELLOW, flush=True)
            else:
                print_step(f"Warning: Timestamp not found for {username_prefix}. Skipping.", Fore.YELLOW, flush=True)
        elif username_prefix and unfollowed_status is True:
            print_step(f"Account {username_prefix} already unfollowed. Skipping.", Fore.YELLOW, flush=True)

    if not eligible_account_info:
        print_step("No eligible accounts found to unfollow in this run. Exiting without launching browser.", Fore.YELLOW, flush=True)
        return # Exit if no eligible account

    # Proceed with browser launch and unfollow if an eligible account was found
    print_step(f"Attempting to log in as {username_to_login}...", Fore.YELLOW, flush=True)
    driver = login_to_instagram(username_to_login)
    if not driver:
        print_step("Failed to log in to Instagram. Exiting.", Fore.RED, flush=True)
        return
    print_step("Successfully logged in.", Fore.GREEN, flush=True)

    # Unfollow the eligible account
    username_prefix = None
    for key in eligible_account_info.keys():
        if key.endswith('_followed'):
            username_prefix = key.replace('_followed', '')
            break

    if username_prefix:
        # Navigate to the user's profile
        profile_url = f"https://www.instagram.com/{username_prefix}/"
        print_step(f"Navigating to {profile_url}", Fore.BLUE, flush=True)
        driver.get(profile_url)
        time.sleep(15) # Give time for the page to load

        try:
            # Click 'Following' button
            print_step("Clicking 'Following' button...", Fore.BLUE, flush=True)
            following_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, FOLLOWING_BUTTON_XPATH))
            )
            following_button.click()
            time.sleep(15) # Delay after click

            # Click 'Unfollow' button on the dynamic pop-up
            print_step("Clicking 'Unfollow' button on pop-up...", Fore.BLUE, flush=True)
            unfollow_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, UNFOLLOW_BUTTON_XPATH))
            )
            unfollow_button.click()
            time.sleep(15) # Delay after click

            print_step(f"Successfully unfollowed {username_prefix}!", Fore.GREEN, flush=True)

            # Update followed_unfollowed.json
            followed_data[eligible_account_index][f"{username_prefix}_unfollowed"] = True
            followed_data[eligible_account_index]['timestamp'] = datetime.now().isoformat()
            with open('followed_unfollowed.json', 'w') as f:
                json.dump(followed_data, f, indent=4)
            print_step(f"Updated status for {username_prefix} in followed_unfollowed.json", Fore.GREEN, flush=True)
            
        except (NoSuchElementException, TimeoutException) as e:
            print_step(f"Could not unfollow {username_prefix}: {e}", Fore.RED, flush=True)
        except Exception as e:
            print_step(f"An unexpected error occurred while unfollowing {username_prefix}: {e}", Fore.RED, flush=True)
    else:
        print_step("Error: Could not determine username for unfollow.", Fore.RED, flush=True)

    # 5. Wait before closing the browser
    print_step("Waiting 15 seconds before closing the browser...", Fore.CYAN, flush=True)
    time.sleep(15)
    driver.quit()
    print_step("Browser closed. Unfollow process finished.", Fore.MAGENTA, flush=True)

if __name__ == "__main__":
    unfollow_account()
