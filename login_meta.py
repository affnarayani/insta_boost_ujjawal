import json
import time
import traceback
import os
import base64
from datetime import datetime
from secrets import token_bytes
from dotenv import load_dotenv
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse # Moved import to top

HEADLESS = True

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
    salt = base64.b64decode(payload["s"])
    nonce = base64.b64decode(payload["n"])
    ciphertext = base64.b64decode(payload["ct"])
    key = _derive_key_from_password(password.encode("utf-8"), salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

def login_with_cookies(url, cookies_file, headless=False, window_size="1920,1080"):
    """
    Logs into a website using cookies from a JSON file, prints cookie expiration,
    waits for 30 seconds, and then closes the browser.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--window-size={window_size}")
    
    # Anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
    
    # Set download directory
    download_dir = os.path.join(os.getcwd(), "videos")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False, # To auto download the file
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True # To download PDFs directly
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # You might need to specify the path to your chromedriver executable
    # service = Service('/path/to/chromedriver') 
    driver = webdriver.Chrome(options=chrome_options) # If chromedriver is in PATH, no service needed
    
    # Inject script to hide navigator.webdriver property on new documents
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    try:
        # 1. Navigate to the site first to set the domain for cookies
        driver.get(url)

        # Extract the base domain from the target URL for filtering cookies
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        if base_domain.startswith("www."):
            base_domain = base_domain[4:] # Remove 'www.' for broader matching

        # 2. Load cookies from the JSON file
        load_dotenv()
        key = os.getenv("DECRYPT_KEY")
        if not key:
            raise RuntimeError("DECRYPT_KEY is missing in environment/.env")

        with open(cookies_file, 'r') as f:
            encrypted_payload = json.load(f)
        
        decrypted_bytes = _decrypt_bytes(encrypted_payload, key)
        all_cookies = json.loads(decrypted_bytes.decode('utf-8'))
        
        # Store filtered cookies to print their expiration later
        filtered_cookies = []

        # 3. Filter and add relevant cookies to the browser
        for cookie in all_cookies:
            # Only add cookies relevant to the target domain
            if 'domain' in cookie and (base_domain in cookie['domain'] or cookie['domain'].endswith(f".{base_domain}")):
                # Selenium expects 'expiry' instead of 'expires' and as an int
                if 'expires' in cookie:
                    cookie['expiry'] = int(cookie['expires'])
                    del cookie['expires']
                
                # Remove 'sameSite' if it's an empty string or an invalid value, as Selenium expects 'Strict', 'Lax', or 'None'
                if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                    del cookie['sameSite']
                
                # Remove 'domain' to avoid InvalidCookieDomainException, Selenium will set it correctly
                if 'domain' in cookie:
                    del cookie['domain']
                
                driver.add_cookie(cookie)
                filtered_cookies.append(cookie) # Add to filtered list
            else:
                # Optionally print a message for skipped cookies
                # print(f"Skipping cookie for domain: {cookie.get('domain', 'N/A')}")
                pass
        
        # 4. Refresh the page to apply the cookies
        driver.refresh()
        print(f"Successfully loaded cookies and refreshed {url}")

        # 5. Print cookie expiration time (example: looking for a session cookie)
        session_cookie_count = 0
        for cookie in filtered_cookies: # Iterate over filtered_cookies
            if 'expiry' in cookie:
                expiry_timestamp = cookie['expiry']
                expiry_datetime = datetime.fromtimestamp(expiry_timestamp)
                print(f"Cookie '{cookie.get('name', 'N/A')}' expires on: {expiry_datetime}")
            else:
                session_cookie_count += 1
        
        if session_cookie_count > 0:
            print(f"{session_cookie_count} session cookie(s) found with no explicit expiration time.")

        # 6. Wait for 30 seconds
    except FileNotFoundError:
        print(f"Error: Cookies file '{cookies_file}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc()) # Print full traceback for debugging
        return None
    
    return driver

if __name__ == "__main__":
    # Ensure you have a cookies_meta.json file in the same directory
    # and that it contains valid cookies for meta.ai
    target_url = "https://www.meta.ai"
    cookies_filename = "cookies_meta.json.encrypted"
    driver = login_with_cookies(target_url, cookies_filename)
    if driver:
        print("Login successful. Driver is active.")
        # Keep the browser open for a while or perform further actions
        time.sleep(30) 
        driver.quit()
        print("Browser closed.")
