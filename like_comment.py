import json
import os
import time
from dotenv import load_dotenv
from colorama import Fore, Style, init
import google.generativeai as genai # Import google.generativeai

# Initialize Colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# --- CRITICALLY IMPORTANT: Do not change anything in login.py or scrape_posts.py ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from login import login_to_instagram # Import the login function

# XPath and CSS selectors (to be saved in variables)
LIKE_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/section/main/div/div[1]/div/div[2]/div/div[3]/section[1]/div[1]/span[1]/div/div"

# Previous comments top 6 xpaths
COMMENT_XPATHS = [
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]",
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]",
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[3]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]",
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[4]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]",
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[5]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]",
    "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[2]/div[6]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/span[1]"
]

COMMENT_TEXTAREA_CSS_SELECTOR = "textarea[placeholder='Add a comment…']"
COMMENT_TEXTAREA_FALLBACK_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/section/main/div/div[1]/div/div[2]/div/div[4]/section/div/form"
POST_BUTTON_XPATH = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/section/main/div/div[1]/div/div[2]/div/div[4]/section/div/form/div/div[2]/div"

def reorder_user_dict_keys(user_dict, username, post_url=None):
    liked_commented_key = f"{username}_liked_commented"
    liked_commented_url_key = f"{username}_liked_commented_url"

    # Ensure these keys exist before reordering
    if liked_commented_key not in user_dict:
        user_dict[liked_commented_key] = False # Default value
    if liked_commented_url_key not in user_dict:
        user_dict[liked_commented_url_key] = None # Default value

    # Update values
    user_dict[liked_commented_key] = True
    user_dict[liked_commented_url_key] = post_url

    ordered_keys = []
    # Collect keys in desired order
    for key in user_dict.keys():
        if key == liked_commented_key:
            ordered_keys.append(key)
            ordered_keys.append(liked_commented_url_key)
        elif key == liked_commented_url_key:
            continue # Already added with liked_commented_key
        else:
            ordered_keys.append(key)
    
    # Create a new dictionary with ordered keys
    reordered_dict = {key: user_dict[key] for key in ordered_keys if key in user_dict}
    return reordered_dict

def read_config():
    """Reads the config.json file and returns its content as a dictionary."""
    with open('config.json', 'r') as f:
        config_list = json.load(f)
    
    config = {}
    for item in config_list:
        config.update(item)
    return config

def check_accounts_left_to_process(username):
    """
    Checks if there are any accounts in followed_unfollowed.json that still need to be liked/commented.
    An account is considered processed if its '{username}_liked_commented' key is true.
    """
    try:
        with open('followed_unfollowed.json', 'r') as f:
            followed_data = json.load(f)
    except FileNotFoundError:
        print(f"{Fore.RED}Error: followed_unfollowed.json not found.{Style.RESET_ALL}")
        return False
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Could not decode followed_unfollowed.json. Please check if it's a valid JSON file.{Style.RESET_ALL}")
        return False

    for user_dict in followed_data:
        for key, value in user_dict.items():
            if key.endswith("_followed") and value:
                target_username = key.replace("_followed", "")
                liked_commented_key = f"{target_username}_liked_commented"
                if not user_dict.get(liked_commented_key, False):
                    return True # Found an account that needs processing
    return False # No accounts left to process

def extract_post_id(post_url):
    """Extracts the post ID from an Instagram post URL."""
    parts = post_url.split('/p/')
    if len(parts) > 1:
        post_id_part = parts[1].split('/')[0]
        return post_id_part
    return None

def get_first_post_url(driver, target_username):
    """
    Navigates to the user's profile and retrieves the URL of the first visible post.
    Does not scroll or save to scraped_posts.json.
    """
    profile_url = f"https://www.instagram.com/{target_username}/"
    driver.get(profile_url)

    try:
        # Wait for the profile page to load, specifically looking for a post link
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/p/')]"))
        )
        # Find the first post element
        post_element = driver.find_element(By.XPATH, "//a[contains(@href, '/p/')]")
        return post_element.get_attribute('href')
    except TimeoutException:
        print(f"{Fore.YELLOW}No posts found or profile is private for {target_username}.{Style.RESET_ALL}")
        return None
    except NoSuchElementException:
        print(f"{Fore.YELLOW}No post elements found on profile page for {target_username}.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Error getting first post URL for {target_username}: {e}{Style.RESET_ALL}")
        return None

def main():
    print(f"{Fore.CYAN}Starting like_comment.py script...{Style.RESET_ALL}")

    browser = None
    gemini_client = None

    try:
        # Read config.json to get the username
        print(f"{Fore.YELLOW}Reading config.json to get username...{Style.RESET_ALL}")
        config = read_config()
        username = config.get('username')
        if not username:
            raise ValueError("Username not found in config.json")
        print(f"{Fore.GREEN}Successfully loaded username: {username} from config.json.{Style.RESET_ALL}")

        # Check if there are accounts left to process before launching the browser
        print(f"{Fore.YELLOW}Checking for accounts left to like/comment...{Style.RESET_ALL}")
        if not check_accounts_left_to_process(username):
            print(f"{Fore.GREEN}No accounts left to like and comment. Exiting.{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}Accounts found to like/comment. Proceeding with login.{Style.RESET_ALL}")

        # Step 1: Use instagram login session from login.py
        print(f"{Fore.YELLOW}Logging in to Instagram...{Style.RESET_ALL}")
        browser = login_to_instagram(username)
        if not browser:
            print(f"{Fore.RED}Failed to log in to Instagram. Exiting.{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}Successfully logged in to Instagram.{Style.RESET_ALL}")

        # Step 2: Read followed_unfollowed.json to understand its structure
        print(f"{Fore.YELLOW}Reading followed_unfollowed.json to understand data structure...{Style.RESET_ALL}")
        with open('followed_unfollowed.json', 'r') as f:
            followed_data = json.load(f)
        print(f"{Fore.GREEN}Successfully loaded followed_unfollowed.json.{Style.RESET_ALL}")

        # Step 3: Read scrape_posts.py to understand post scraping and private account detection
        # Initialize GEMINI_API client
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            gemini_client = genai.GenerativeModel('gemini-2.5-flash')
            print(f"{Fore.GREEN}GEMINI_API client initialized with model 'gemini-2.5-flash'.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error initializing GEMINI_API client: {e}{Style.RESET_ALL}")
            print(f"{Fore.RED}Please ensure 'google-generativeai' is installed and GEMINI_API_KEY is set in .env.{Style.RESET_ALL}")
            return

        print(f"{Fore.YELLOW}Searching for users to like/comment...{Style.RESET_ALL}")
        user_processed = False
        for user_dict in followed_data: # Iterate through the list of user dictionaries
            for username_key, user_data_value in list(user_dict.items()): # Iterate through items of each user dictionary
                if username_key.endswith("_followed") and user_data_value: # Check if user is followed
                    username = username_key.replace("_followed", "")
                    liked_commented_key = f"{username}_liked_commented"

                    if not user_dict.get(liked_commented_key, False): # Check within the current user_dict
                        print(f"{Fore.BLUE}Found user '{username}' to process.{Style.RESET_ALL}")

                        # Get the first post URL for the user
                        print(f"{Fore.YELLOW}Attempting to get the first post URL for {username}...{Style.RESET_ALL}")
                        post_to_process = get_first_post_url(browser, username)
                        
                        if not post_to_process:
                            print(f"{Fore.YELLOW}No valid post URL found for {username}. Skipping.{Style.RESET_ALL}")
                            updated_user_dict = reorder_user_dict_keys(user_dict, username, None)
                            for i, item in enumerate(followed_data):
                                if item is user_dict:
                                    followed_data[i] = updated_user_dict
                                    break
                            with open('followed_unfollowed.json', 'w') as f:
                                json.dump(followed_data, f, indent=4)
                            continue

                        print(f"{Fore.BLUE}Navigating to post: {post_to_process}{Style.RESET_ALL}")
                        browser.get(post_to_process)
                        time.sleep(5) # Wait for page to load

                        # Like the post
                        try:
                            print(f"{Fore.YELLOW}Attempting to like the post...{Style.RESET_ALL}")
                            like_button = WebDriverWait(browser, 10).until(
                                EC.element_to_be_clickable((By.XPATH, LIKE_BUTTON_XPATH))
                            )
                            like_button.click()
                            print(f"{Fore.GREEN}Post liked successfully.{Style.RESET_ALL}")
                            time.sleep(5) # Added 5 seconds delay
                        except TimeoutException:
                            print(f"{Fore.RED}Like button not found or not clickable. Post might already be liked or XPath changed.{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}Error liking post: {e}{Style.RESET_ALL}")

                        # Scrape previous comments
                        comments = []
                        print(f"{Fore.YELLOW}Scraping previous comments...{Style.RESET_ALL}")
                        for i, xpath in enumerate(COMMENT_XPATHS):
                            try:
                                comment_element = WebDriverWait(browser, 2).until(
                                    EC.presence_of_element_located((By.XPATH, xpath))
                                )
                                comments.append(comment_element.text)
                                print(f"{Fore.MAGENTA}Comment {i+1}: {comment_element.text}{Style.RESET_ALL}")
                            except TimeoutException:
                                print(f"{Fore.YELLOW}Less than 6 comments or no more comments found.{Style.RESET_ALL}")
                                break
                            except Exception as e:
                                print(f"{Fore.RED}Error scraping comment {i+1}: {e}{Style.RESET_ALL}")
                                break
                        time.sleep(5) # Added 5 seconds delay
                        
                        if not comments:
                            print(f"{Fore.YELLOW}No comments found on this post. Skipping this post and user.{Style.RESET_ALL}")
                            updated_user_dict = reorder_user_dict_keys(user_dict, username, post_to_process)
                            for i, item in enumerate(followed_data):
                                if item is user_dict:
                                    followed_data[i] = updated_user_dict
                                    break
                            with open('followed_unfollowed.json', 'w') as f:
                                json.dump(followed_data, f, indent=4)
                            user_processed = True
                            break # Exit after processing one user
                        
                    # Generate a comment using GEMINI_API
                    print(f"{Fore.YELLOW}Analyzing comments and generating a new comment...{Style.RESET_ALL}")
                    try:
                        prompt = f"Analyze the following Instagram comments and generate a new, relevant, and positive comment. Keep it concise, engaging, and ready for publication. Do not use any asterisk (*) symbols or emojis. Comments: {'; '.join(comments)}"
                        response = gemini_client.generate_content(contents=prompt)
                        generated_comment = response.text.strip()
                        print(f"{Fore.GREEN}Generated comment: {generated_comment}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}Error generating comment with GEMINI_API: {e}. Using a default comment.{Style.RESET_ALL}")
                        generated_comment = "Great post!"
                    time.sleep(5) # Added 5 seconds delay

                    # Post the comment
                    try:
                        print(f"{Fore.YELLOW}Attempting to post the comment...{Style.RESET_ALL}")
                        # Re-locate comment_textarea before interacting
                        comment_textarea = WebDriverWait(browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, COMMENT_TEXTAREA_CSS_SELECTOR))
                        )
                        comment_textarea.click()
                        time.sleep(1) # Small delay after click to allow DOM to settle
                        # Re-locate comment_textarea after clicking it, as the DOM might have changed
                        comment_textarea = WebDriverWait(browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, COMMENT_TEXTAREA_CSS_SELECTOR))
                        )
                        for char in generated_comment:
                            comment_textarea.send_keys(char)
                            time.sleep(0.1) # Simulate human typing speed
                        time.sleep(2) # Wait for the post button to enable

                        # Re-locate post_button before interacting
                        post_button = WebDriverWait(browser, 10).until(
                            EC.element_to_be_clickable((By.XPATH, POST_BUTTON_XPATH))
                        )
                        post_button.click()
                        print(f"{Fore.GREEN}Comment posted successfully.{Style.RESET_ALL}")
                        time.sleep(5) # Wait for comment to be posted

                        # Update followed_unfollowed.json after successful comment
                        print(f"{Fore.YELLOW}Updating followed_unfollowed.json for {username} after successful comment...{Style.RESET_ALL}")
                        updated_user_dict = reorder_user_dict_keys(user_dict, username, post_to_process)
                        for i, item in enumerate(followed_data):
                            if item is user_dict:
                                followed_data[i] = updated_user_dict
                                break
                        with open('followed_unfollowed.json', 'w') as f:
                            json.dump(followed_data, f, indent=4)
                        print(f"{Fore.GREEN}Updated followed_unfollowed.json for {username}.{Style.RESET_ALL}")
                        user_processed = True
                        break # Exit after processing one user

                    except TimeoutException as e:
                        if "textarea[placeholder='Add a comment…']" in str(e):
                            print(f"{Fore.RED}Error: Comment text area not found or not clickable. CSS Selector: {COMMENT_TEXTAREA_CSS_SELECTOR}. XPath Fallback: {COMMENT_TEXTAREA_FALLBACK_XPATH}. Error: {e}{Style.RESET_ALL}")
                        elif POST_BUTTON_XPATH in str(e):
                            print(f"{Fore.RED}Error: Post button not found or not clickable. XPath: {POST_BUTTON_XPATH}. Error: {e}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}Timeout error while posting comment: {e}{Style.RESET_ALL}")
                    except StaleElementReferenceException as e:
                        print(f"{Fore.RED}Stale element reference error while posting comment. This often means the page changed after an element was found. The problematic locators are likely: CSS Selector: {COMMENT_TEXTAREA_CSS_SELECTOR} or XPath: {POST_BUTTON_XPATH}. Error: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}Error posting comment: {e}{Style.RESET_ALL}")
                        # In case of an error, still mark the user as processed to avoid re-attempting the same problematic post
                        print(f"{Fore.YELLOW}Updating followed_unfollowed.json for {username} due to error...{Style.RESET_ALL}")
                        updated_user_dict = reorder_user_dict_keys(user_dict, username, post_to_process)
                        for i, item in enumerate(followed_data):
                            if item is user_dict:
                                followed_data[i] = updated_user_dict
                                break
                        with open('followed_unfollowed.json', 'w') as f:
                            json.dump(followed_data, f, indent=4)
                        print(f"{Fore.GREEN}Updated followed_unfollowed.json for {username}.{Style.RESET_ALL}")
                        user_processed = True
                        break # Exit after processing one user
                
                if user_processed:
                    break # Exit the inner loop if a user was processed
            
            if user_processed:
                break # Exit the outer loop if a user was processed

        if not user_processed:
            print(f"{Fore.YELLOW}No users found with '_liked_commented': false or no suitable posts found. Exiting.{Style.RESET_ALL}")

    except FileNotFoundError as e:
        print(f"{Fore.RED}Error: Required file not found - {e}. Please ensure all necessary files are in the current directory.{Style.RESET_ALL}")
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Could not decode followed_unfollowed.json. Please check if it's a valid JSON file.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
    finally:
        if browser:
            print(f"{Fore.CYAN}Waiting 15 seconds before closing browser...{Style.RESET_ALL}")
            time.sleep(15)
            browser.quit()
            print(f"{Fore.CYAN}Browser closed.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Script finished.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
