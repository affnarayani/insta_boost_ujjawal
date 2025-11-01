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
from selenium.common.exceptions import NoSuchElementException # Import NoSuchElementException
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
def login_with_cookies(cookies_file):
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
        print("Error: Invalid decryption key or corrupted cookies file.")
        return # Exit the function if decryption fails

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

        # Load cookies
        # original_cookies = read_cookies(cookies_file) # This line is no longer needed

        # Prepare cookies for Selenium
        cookies_for_selenium = []
        for cookie in original_cookies:
            selenium_cookie = cookie.copy() # Create a copy to avoid modifying the original
            
            if 'expirationDate' in selenium_cookie:
                selenium_cookie['expiry'] = int(selenium_cookie['expirationDate'])
                del selenium_cookie['expirationDate']
            
            # Remove 'sameSite' if it's 'unspecified' or 'no_restriction' as Selenium might not like it
            # Selenium expects 'SameSite' to be 'Strict', 'Lax', or 'None'
            if 'sameSite' in selenium_cookie:
                # Selenium expects 'SameSite' to be 'Strict', 'Lax', or 'None'
                # Remove if 'unspecified' or any other invalid value
                if selenium_cookie['sameSite'] == 'unspecified':
                    del selenium_cookie['sameSite']
                elif selenium_cookie['sameSite'] == 'no_restriction':
                    selenium_cookie['sameSite'] = 'None' # 'no_restriction' maps to 'None' in Selenium
                elif selenium_cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                    del selenium_cookie['sameSite'] # Remove any other invalid sameSite values
            
            # Remove 'storeId' and 'session' as they are not expected by Selenium
            if 'storeId' in selenium_cookie:
                del selenium_cookie['storeId']
            if 'session' in selenium_cookie:
                del selenium_cookie['session']
            
            cookies_for_selenium.append(selenium_cookie)

        for cookie in cookies_for_selenium:
            driver.add_cookie(cookie)
        
        # Refresh page to apply cookies
        driver.refresh()
        print("Cookies loaded and page refreshed.")
        
        # Keep the browser open for a few seconds to verify
        time.sleep(10)

        # Read config.json to get the expected name
        with open('config.json', 'r') as f:
            config = json.load(f)
        expected_name = config[0]['name']

        # Check the XPath for the text value
        xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/section[1]/main[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/span[1]/span[1]/div[1]/span[1]"
        try:
            element = driver.find_element(By.XPATH, xpath)
            found_text = element.text
            if found_text == expected_name:
                print(f"Found text: {found_text}")
                print("Login successful.")
                
                # Check for the specified XPath and click it if it appears
                try:
                    click_xpath = "/html[1]/body[1]/div[4]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[4]"
                    element_to_click = driver.find_element(By.XPATH, click_xpath)
                    element_to_click.click()
                    print("Clicked the pop-up notification.")
                    time.sleep(5) # Wait a bit after clicking
                except NoSuchElementException:
                    print("XPath element to click not found, skipping click.")
                except Exception as click_e:
                    print(f"An unexpected error occurred while trying to click the element: {click_e}")

            else:
                print(f"Logged into unexpected account. Found text: '{found_text}' does not match expected name: '{expected_name}'")
        except Exception:
            print("Login unsuccessful: XPath element not found.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Print the full traceback for better debugging
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    cookies_json_file = "cookies.json.encrypted"
    login_with_cookies(cookies_json_file)
