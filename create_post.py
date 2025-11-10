import os
import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from login import login_to_instagram # Import the login function
from dotenv import load_dotenv
import google.generativeai as genai

def create_instagram_post(driver, video_path, description):
    try:
        # Navigate to the create post page (or click the create button)
        # Instagram's "create new post" button is usually a plus icon.
        # We need to find its XPath or other locator.
        # Let's assume a common XPath for the create button. This might need adjustment.
        print("Attempting to find and click the 'Create new post' button...", flush=True)
        create_button_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/a/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, create_button_xpath))
        ).click()
        print("Clicked 'Create new post' button.", flush=True)
        time.sleep(5)

        # Click "Post" button in the dropdown
        print("Attempting to find and click the 'Post' button in the dropdown...", flush=True)
        post_dropdown_button_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/div/div/div[1]/a[1]/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, post_dropdown_button_xpath))
        ).click()
        print("Clicked 'Post' button in the dropdown.", flush=True)
        time.sleep(15) # Wait for 15 seconds for the dynamic pop-up to appear

        # Upload video file directly to the hidden input element
        print(f"Attempting to upload video from: {video_path}", flush=True)
        # The file input element is usually hidden, so we need to find it and send keys to it.
        # This XPath might need to be more specific if there are multiple file inputs.
        # We are bypassing the click on "Select from computer" as it often causes issues in headless environments.
        file_input_xpath = "//input[@type='file']"
        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, file_input_xpath))
        )
        file_input.send_keys(os.path.abspath(video_path))
        print("Video file sent to input field.", flush=True)
        time.sleep(15) # Give time for the video to load/process and for the "videos are now reels" pop-up to appear

        # Check for "videos are now reels" notification pop-up (optional)
        print("Checking for 'videos are now reels' notification pop-up...", flush=True)
        reels_notification_button_xpath = "//button[text()='OK']"
        try:
            reels_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, reels_notification_button_xpath))
            )
            reels_button.click()
            print("Clicked button in 'videos are now reels' pop-up.", flush=True)
            time.sleep(5)

        except TimeoutException:
            print("'Videos are now reels' pop-up did not appear or button not found, or resize/original buttons not found.", flush=True)
        except NoSuchElementException:
            print("'Videos are now reels' pop-up did not appear or button not found.", flush=True)

        # Locate and click the image resize button
        print("Attempting to find and click the image resize button...", flush=True)
        time.sleep(120)
        image_resize_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[2]/div/button"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, image_resize_button_xpath))
        ).click()
        print("Clicked image resize button.", flush=True)
        time.sleep(5)

        # Locate and click the "Original" button in the pop-up
        print("Attempting to find and click the 'Original' button...", flush=True)
        original_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[1]/div/div[1]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, original_button_xpath))
        ).click()
        print("Clicked 'Original' button.", flush=True)
        time.sleep(5) # Wait for 5 seconds after clicking "Original" button

        # Click 'Next' button
        print("Attempting to click 'Next' button after video upload...", flush=True)
        next_button_xpath = "//div[text()='Next']"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
        ).click()
        print("Clicked 'Next' button.", flush=True)
        time.sleep(5)

        # Click 'Next' button again (for filters/edits, usually)
        print("Attempting to click 'Next' button again...", flush=True)
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
        ).click()
        print("Clicked 'Next' button again.", flush=True)
        time.sleep(5)

        # Add description
        print("Attempting to add description...", flush=True)
        description_textarea_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[1]/div[2]/div/div[1]/div[1]"
        description_textarea = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, description_textarea_xpath))
        )
        description_textarea.click()
        print("Clicked description textarea.", flush=True)
        for char in description:
            description_textarea.send_keys(char)
            time.sleep(0.1) # Simulate human typing speed
        print("Description added character by character.", flush=True)
        time.sleep(5)

        # Click 'Share' button
        print("Attempting to click 'Share' button...", flush=True)
        share_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[1]/div/div/div/div[3]/div/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, share_button_xpath))
        ).click()
        print("Clicked 'Share' button. Post is being shared...", flush=True)
        time.sleep(60) # Give time for the post to upload and share

        print("Post created successfully!", flush=True)
        return True

    except TimeoutException:
        print("Timeout: Element not found or not clickable within the specified time.", flush=True)
        return False
    except NoSuchElementException:
        print("No such element: An element required for posting was not found.", flush=True)
        return False
    except Exception as e:
        print(f"An error occurred during post creation: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Load username from config.json
    try:
        with open('config.json', 'r') as f:
            config_list = json.load(f)
        username = None
        for item in config_list:
            if 'username' in item:
                username = item['username']
                break
        if username is None:
            raise ValueError("Username not found in config.json")
    except FileNotFoundError:
        print("Error: config.json not found.", flush=True)
        exit()
    except Exception as e:
        print(f"Error loading username from config.json: {e}", flush=True)
        exit()

    driver = None
    try:
        # Load environment variables
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env file.")

        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.GenerativeModel("gemini-2.5-flash")

        # Generate description using Gemini API
        prompt = "Generate an Instagram post description in max 12 words, in Hinglish, without inverted commas, asterisks, or emojis. Also, provide relevant hashtags. The context for all posts is: iss Instagram account mein main mahakaal aur jyotirling ke photos / videos upload karta hoon. har post aisa hi hone wala hai."
        
        print("Generating description using Gemini API...", flush=True)
        response = client.generate_content(prompt)
        generated_description = response.text.strip()
        
        print(f"Generated Description: {generated_description}", flush=True)

        driver = login_to_instagram(username)
        if driver:
            print("Login successful. Proceeding to create post.", flush=True)
            
            # Find the first video in the 'videos' folder
            videos_folder = "videos"
            video_files = [f for f in os.listdir(videos_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
            
            if video_files:
                first_video_path = os.path.join(videos_folder, video_files[0])
                description = generated_description
                
                print(f"Uploading video: {first_video_path}", flush=True)
                success = create_instagram_post(driver, first_video_path, description)
                
                if success:
                    print("Instagram post creation process completed.", flush=True)
                    # Delete the video file after successful upload
                    try:
                        os.remove(first_video_path)
                        print(f"Deleted uploaded video file: {first_video_path}", flush=True)
                    except OSError as e:
                        print(f"Error deleting video file {first_video_path}: {e}", flush=True)
                else:
                    print("Instagram post creation process failed.", flush=True)
            else:
                print(f"No video files found in the '{videos_folder}' folder.", flush=True)
        else:
            print("Login failed. Cannot proceed with post creation.", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("Waiting for 15 seconds before closing the browser.", flush=True)
            time.sleep(15)
            driver.quit()
            print("Browser closed.", flush=True)
