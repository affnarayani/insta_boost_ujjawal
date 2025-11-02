import json
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from login import login_to_instagram # Import the login function

def scrape_followers(driver, target_username):
    print(f"Navigating to https://www.instagram.com/{target_username}")
    driver.get(f"https://www.instagram.com/{target_username}")

    try:
        # Wait for the profile page to load and the followers link to be clickable
        # More robust way to find the followers link
        followers_link_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a/span"
        followers_link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, followers_link_xpath))
        )
        
        # Check for private account status
        private_account_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[1]/section/main/div/div/div[1]/div/div[1]/div[2]/div/div/span"
        try:
            private_account_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, private_account_xpath))
            )
            if "This account is private" in private_account_element.text:
                print("This account is private. The followers list cannot be scraped.")
                return # Exit the function
        except TimeoutException:
            # The private account element was not found, proceed as normal
            pass

        followers_count_text = followers_link.find_element(By.XPATH, ".//span/span").text if followers_link.find_elements(By.XPATH, ".//span/span") else followers_link.text
        if not followers_count_text: # Fallback if the inner span is not found
            followers_count_text = followers_link.find_element(By.XPATH, ".//span").text
        print(f"Followers link found: {int(followers_count_text.replace(',', ''))}, clicking it.")
        followers_link.click()
        time.sleep(15) # Give some time for the pop-up to appear

        # Wait for the followers dialog to appear using a more robust XPath
        # Look for a div with role="dialog" and then find the scrollable element within it.
        dialog_xpath = "/html/body/div[4]/div[2]/div/div/div[1]/div/div[2]/div/div/div"
        followers_dialog = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, dialog_xpath))
        )
        print("Followers dialog opened.")

        scrollable_element_xpath = "/html[1]/body[1]/div[4]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]"
        scrollable_element = WebDriverWait(followers_dialog, 10).until(
            EC.presence_of_element_located((By.XPATH, scrollable_element_xpath))
        )
        print("Scrollable element for followers list found.")

        # Load existing followers from the JSON file if it exists
        output_file = "scraped_followers.json"
        existing_followers = set()
        max_followers_to_scrape = 0

        # Read max_followers_to_scrape from config.json
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config_list = json.load(f)
            for item in config_list:
                if "max_followers_to_scrape" in item:
                    max_followers_to_scrape = item["max_followers_to_scrape"]
                    break
            print(f"Max followers to scrape: {max_followers_to_scrape}")
        except FileNotFoundError:
            print("Error: config.json not found. Cannot determine max_followers_to_scrape.")
            return
        except json.JSONDecodeError:
            print("Error: config.json is malformed. Cannot determine max_followers_to_scrape.")
            return
        except Exception as e:
            print(f"An error occurred while reading config.json: {e}")
            return
        
        # Check if scraped_followers.json exists and load its content
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                if file_content: # Check if file is not empty
                    data = json.loads(file_content)
                    username_scraped_in_file = data.get("username_scraped")

                    if username_scraped_in_file == target_username:
                        # If usernames match, load existing followers
                        if "followers" in data and isinstance(data["followers"], list):
                            existing_followers.update(data["followers"])
                        print(f"Loaded {len(existing_followers)} existing followers for {target_username} from {output_file}.")
                    else:
                        # If usernames don't match, clear the file content
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump({}, f) # Write an empty JSON object
                        print(f"Cleared {output_file} as target username '{target_username}' does not match previously scraped username '{username_scraped_in_file}'.")
                else:
                    print(f"Warning: {output_file} is empty. Starting with an empty list.")

            except json.JSONDecodeError:
                print(f"Warning: {output_file} is malformed. Clearing and starting with an empty list.")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f) # Clear the file
            except Exception as e:
                print(f"Error processing {output_file}: {e}. Starting with an empty list.")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f) # Clear the file
        else:
            print(f"{output_file} not found. A new file will be created.")

        scraped_followers = existing_followers.copy() # Initialize with existing followers
        followers_to_scrape_count = max_followers_to_scrape - len(existing_followers)
        print(f"Need to scrape {followers_to_scrape_count} more followers.")

        if followers_to_scrape_count <= 0:
            print(f"Already have {len(existing_followers)} followers, which is >= max_followers_to_scrape ({max_followers_to_scrape}). No new followers will be scraped.")
            return # Exit if no more followers are needed

        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
        while True:
            # Get all follower elements. Each follower is typically represented by a link to their profile.
            # We look for 'a' tags within the scrollable element that have an href attribute starting with '/'.
            # The username is usually in a span within this 'a' tag.
            follower_elements_xpath = ".//a[starts-with(@href, '/') and @role='link']"
            follower_elements = scrollable_element.find_elements(By.XPATH, follower_elements_xpath)
            
            for element in follower_elements:
                try:
                    # The username is usually the text of the 'a' tag itself or within a child span.
                    # Let's try to get the text directly from the 'a' tag, which is often the username.
                    username = element.text.strip()
                    if username and not username.startswith("See all"): # Filter out "See all" or similar non-username texts
                        if username not in scraped_followers:
                            scraped_followers.add(username)
                            print(f"Appended new follower: {username}")
                            
                            if len(scraped_followers) >= max_followers_to_scrape:
                                print(f"Reached max_followers_to_scrape ({max_followers_to_scrape}). Stopping scraping.")
                                # Save the current list and break
                                output_data = {
                                    "username_scraped": target_username,
                                    "followers": sorted(list(scraped_followers))[:max_followers_to_scrape] # Ensure only max_followers_to_scrape are saved
                                }
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                                print(f"Saved {len(scraped_followers)} followers to {output_file}.")
                                return # Exit the function after saving
                            
                            # Immediately save the updated list to JSON if not yet at max
                            output_data = {
                                "username_scraped": target_username,
                                "followers": sorted(list(scraped_followers))
                            }
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(output_data, f, ensure_ascii=False, indent=4)
                            print(f"Saved {len(scraped_followers)} followers to {output_file}.")
                except StaleElementReferenceException:
                    pass # Element might have become stale during scrolling

            # Scroll down
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
            time.sleep(5) # Wait for new content to load.

            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
            if new_height == last_height:
                print("Reached the bottom of the followers list.")
                break
            last_height = new_height
            print(f"Scraped {len(scraped_followers)} followers so far. Scrolling down...")

        print(f"Finished scraping. Total unique followers found: {len(scraped_followers)}")
        print(f"Final list of scraped followers saved to {output_file}")

    except TimeoutException:
        print("Timeout: Followers link or dialog not found within the expected time.")
    except NoSuchElementException as e:
        print(f"Element not found: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Read scrape_followers_username from config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config_list = json.load(f)
        
        scrape_followers_username = None
        username_for_login = None

        for item in config_list:
            if "scrape_followers_username" in item:
                scrape_followers_username = item["scrape_followers_username"]
            if "username" in item:
                username_for_login = item["username"]

        if not scrape_followers_username:
            raise ValueError("scrape_followers_username not found in config.json")
        if not username_for_login:
            raise ValueError("username for login not found in config.json")

        # Login to Instagram
        driver_instance = login_to_instagram(username_for_login)

        if driver_instance:
            scrape_followers(driver_instance, scrape_followers_username)
        else:
            print("Failed to get a driver instance. Exiting.")

    except FileNotFoundError:
        print("Error: config.json not found.")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An error occurred during the main execution: {e}")
