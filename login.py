import os
import json
import time
import base64
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag # Import InvalidTag

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By # Import By
from selenium.webdriver.support.ui import WebDriverWait # Added for explicit waits
from selenium.webdriver.support import expected_conditions as EC # Added for explicit waits
from selenium.common.exceptions import NoSuchElementException, TimeoutException # Import NoSuchElementException and TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Create a variable headless and set it to False by default.
# Developer can toggle this Boolean to easily switch from headless to headful mode and vice versa.
headless = True

def _derive_key_from_password(password: bytes, salt: bytes) -> bytes:
    # PBKDF2-HMAC-SHA256 to derive a 256-bit key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(password)

def _decrypt_bytes(payload: dict, password: str) -> bytes:
    if payload["v"] != 1:
        raise ValueError("Unsupported payload version")

    salt = base64.b64decode(payload["s"])
    nonce = base64.b64decode(payload["n"])
    ct = base64.b64decode(payload["ct"])
    key = _derive_key_from_password(password.encode("utf-8"), salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)

def read_cookies(file_path):
    with open(file_path, 'r') as f:
        cookies = json.load(f)
    return cookies
def login_to_instagram(username): # Renamed function and added username parameter
    load_dotenv()
    decrypt_key = os.getenv("DECRYPT_KEY")
    if not decrypt_key:
        raise RuntimeError("DECRYPT_KEY is missing in environment/.env")

    encrypted_cookies_file = "cookies.json.encrypted"
    if not os.path.exists(encrypted_cookies_file):
        raise FileNotFoundError(f"{encrypted_cookies_file} not found to decrypt")

    with open(encrypted_cookies_file, "r", encoding="utf-8") as f:
        encrypted_payload = json.load(f)

    try:
        decrypted_bytes = _decrypt_bytes(encrypted_payload, decrypt_key)
        original_cookies = json.loads(decrypted_bytes.decode("utf-8"))
    except InvalidTag:
        print("Error: Invalid decryption key or corrupted cookies file.", flush=True)
        return None # Return None if decryption fails

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
    
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu") # Required for headless on Windows
    
    # Initialize WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        # Navigate to Instagram
        driver.get("https://www.instagram.com")

        # Prepare cookies for Selenium
        cookies_for_selenium = []
        for cookie in original_cookies:
            selenium_cookie = cookie.copy() # Create a copy to avoid modifying the original
            
            if 'expirationDate' in selenium_cookie:
                selenium_cookie['expiry'] = int(selenium_cookie['expirationDate'])
                del selenium_cookie['expirationDate']
            
            if 'sameSite' in selenium_cookie:
                if selenium_cookie['sameSite'] == 'unspecified':
                    del selenium_cookie['sameSite']
                elif selenium_cookie['sameSite'] == 'no_restriction':
                    selenium_cookie['sameSite'] = 'None'
                elif selenium_cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                    del selenium_cookie['sameSite']
            
            if 'storeId' in selenium_cookie:
                del selenium_cookie['storeId']
            if 'session' in selenium_cookie:
                del selenium_cookie['session']
            
            cookies_for_selenium.append(selenium_cookie)

        for cookie in cookies_for_selenium:
            driver.add_cookie(cookie)
        
        # Refresh page to apply cookies
        driver.refresh()
        print("Cookies loaded and page refreshed.", flush=True)
        
        # Keep the browser open for a few seconds to verify
        time.sleep(15) # Reduced sleep time

        # Check for the specified XPath and click it if it appears
        try:
            click_xpath = "/html[1]/body[1]/div[4]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[4]"
            element_to_click = driver.find_element(By.XPATH, click_xpath)
            element_to_click.click()
            print("Clicked the pop-up notification.", flush=True)
            time.sleep(2) # Wait a bit after clicking
        except NoSuchElementException:
            print("First XPath element not found, trying fallback XPath.", flush=True)
            try:
                fallback_click_xpath = "/html/body/div[2]/div[1]/div/div[2]/div/div/div/div/div/div/div[4]"
                element_to_click = driver.find_element(By.XPATH, fallback_click_xpath)
                element_to_click.click()
                print("Clicked the pop-up notification using fallback XPath.", flush=True)
                time.sleep(2) # Wait a bit after clicking
            except NoSuchElementException:
                print("Fallback XPath element to click not found, skipping click.", flush=True)
            except Exception as fallback_click_e:
                print(f"An unexpected error occurred while trying to click the fallback element: {fallback_click_e}", flush=True)
        except Exception as click_e:
            print(f"An unexpected error occurred while trying to click the element: {click_e}", flush=True)
        
        # Verify login by checking if the username is present on the page
        # This is a more robust check than relying on a specific XPath that might change
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//a[contains(@href, '/{username}/')]"))
            )
            print(f"Login successful as {username}.", flush=True)
            return driver # Return the driver instance
        except TimeoutException:
            print(f"Login verification failed for {username}. Username link not found.", flush=True)
            driver.quit()
            return None

    except Exception as e:
        print(f"An error occurred during login: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if driver:
            driver.quit()
        return None

if __name__ == "__main__":
    # This block is for testing login.py directly
    # You would need to provide a username for testing purposes
    # For example, by reading it from config.json or an environment variable
    print("Running login.py directly for testing purposes.", flush=True)
    # Assuming config.json has a 'username' key at the top level
    try:
        with open('config.json', 'r') as f:
            config_list = json.load(f)
        test_username = None
        for item in config_list:
            if 'username' in item:
                test_username = item['username']
                break
        
        if test_username:
            driver_instance = login_to_instagram(test_username)
            if driver_instance:
                print("Login successful in test mode. Browser will close in 10 seconds.", flush=True)
                time.sleep(10)
                driver_instance.quit()
            else:
                print("Login failed in test mode.", flush=True)
        else:
            print("Error: 'username' not found in config.json for testing login.py.", flush=True)
    except FileNotFoundError:
        print("Error: config.json not found.", flush=True)
    except Exception as e:
        print(f"An error occurred during direct login.py execution: {e}", flush=True)
