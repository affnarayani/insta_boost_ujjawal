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
        print("Attempting to find and click the 'Create new post' button...")
        create_button_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/a/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, create_button_xpath))
        ).click()
        print("Clicked 'Create new post' button.")
        time.sleep(5)

        # Click "Post" button in the dropdown
        print("Attempting to find and click the 'Post' button in the dropdown...")
        post_dropdown_button_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/div/div/div[1]/a[1]/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, post_dropdown_button_xpath))
        ).click()
        print("Clicked 'Post' button in the dropdown.")
        time.sleep(15) # Wait for 15 seconds for the dynamic pop-up to appear

        # Click "Select from computer" button in the dynamic pop-up
        print("Attempting to find and click the 'Select from computer' button...")
        select_from_computer_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div[2]/div/button"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, select_from_computer_button_xpath))
        ).click()
        print("Clicked 'Select from computer' button.")
        time.sleep(5)

        # Upload video file
        print(f"Attempting to upload video from: {video_path}")
        # The file input element is usually hidden, so we need to find it and send keys to it.
        # This XPath might need to be more specific if there are multiple file inputs.
        file_input_xpath = "//input[@type='file']"
        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, file_input_xpath))
        )
        file_input.send_keys(os.path.abspath(video_path))
        print("Video file sent to input field.")
        time.sleep(15) # Give time for the video to load/process and for the "videos are now reels" pop-up to appear

        # Check for "videos are now reels" notification pop-up (optional)
        print("Checking for 'videos are now reels' notification pop-up...")
        reels_notification_button_xpath = "/html/body/div[5]/div[2]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]/div/div[2]/button"
        try:
            reels_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, reels_notification_button_xpath))
            )
            reels_button.click()
            print("Clicked button in 'videos are now reels' pop-up.")
            time.sleep(5)

        except TimeoutException:
            print("'Videos are now reels' pop-up did not appear or button not found, or resize/original buttons not found.")
        except NoSuchElementException:
            print("'Videos are now reels' pop-up did not appear or button not found.")

        # Locate and click the image resize button
        print("Attempting to find and click the image resize button...")
        image_resize_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[2]/div/button/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, image_resize_button_xpath))
        ).click()
        print("Clicked image resize button.")
        time.sleep(5)

        # Locate and click the "Original" button in the pop-up
        print("Attempting to find and click the 'Original' button...")
        original_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[1]/div/div[1]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, original_button_xpath))
        ).click()
        print("Clicked 'Original' button.")
        time.sleep(5) # Wait for 5 seconds after clicking "Original" button

        # Click 'Next' button
        print("Attempting to click 'Next' button after video upload...")
        next_button_xpath = "//div[text()='Next']"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
        ).click()
        print("Clicked 'Next' button.")
        time.sleep(5)

        # Click 'Next' button again (for filters/edits, usually)
        print("Attempting to click 'Next' button again...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, next_button_xpath))
        ).click()
        print("Clicked 'Next' button again.")
        time.sleep(5)

        # Add description
        print("Attempting to add description...")
        description_textarea_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[1]/div[2]/div/div[1]/div[1]"
        description_textarea = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, description_textarea_xpath))
        )
        description_textarea.click()
        print("Clicked description textarea.")
        for char in description:
            description_textarea.send_keys(char)
            time.sleep(0.1) # Simulate human typing speed
        print("Description added character by character.")
        time.sleep(5)

        # Click 'Share' button
        print("Attempting to click 'Share' button...")
        share_button_xpath = "/html/body/div[5]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[1]/div/div/div/div[3]/div/div"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, share_button_xpath))
        ).click()
        print("Clicked 'Share' button. Post is being shared...")
        time.sleep(60) # Give time for the post to upload and share

        print("Post created successfully!")
        return True

    except TimeoutException:
        print("Timeout: Element not found or not clickable within the specified time.")
        return False
    except NoSuchElementException:
        print("No such element: An element required for posting was not found.")
        return False
    except Exception as e:
        print(f"An error occurred during post creation: {e}")
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
        print("Error: config.json not found.")
        exit()
    except Exception as e:
        print(f"Error loading username from config.json: {e}")
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
        
        print("Generating description using Gemini API...")
        response = client.generate_content(prompt)
        generated_description = response.text.strip()
        
        print(f"Generated Description: {generated_description}")

        driver = login_to_instagram(username)
        if driver:
            print("Login successful. Proceeding to create post.")
            
            # Find the first video in the 'videos' folder
            videos_folder = "videos"
            video_files = [f for f in os.listdir(videos_folder) if f.endswith(('.mp4', '.mov', '.avi'))]
            
            if video_files:
                first_video_path = os.path.join(videos_folder, video_files[0])
                description = generated_description
                
                print(f"Uploading video: {first_video_path}")
                success = create_instagram_post(driver, first_video_path, description)
                
                if success:
                    print("Instagram post creation process completed.")
                    # Delete the video file after successful upload
                    try:
                        os.remove(first_video_path)
                        print(f"Deleted uploaded video file: {first_video_path}")
                    except OSError as e:
                        print(f"Error deleting video file {first_video_path}: {e}")
                else:
                    print("Instagram post creation process failed.")
            else:
                print(f"No video files found in the '{videos_folder}' folder.")
        else:
            print("Login failed. Cannot proceed with post creation.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("Waiting for 15 seconds before closing the browser.")
            time.sleep(15)
            driver.quit()
            print("Browser closed.")
