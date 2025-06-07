import requests
from bs4 import BeautifulSoup
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
PRODUCT_URLS = [
    "https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30"
]
IN_STOCK_KEYWORD = "Product Information"
DELIVERY_PINCODE = "560015" # You can change this to your local pincode
STATE_FILE = "notified_urls.txt"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# --- SELENIUM BROWSER SETUP ---
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# --- HELPER FUNCTIONS ---
def get_notified_urls():
    if not os.path.exists(STATE_FILE): return []
    with open(STATE_FILE, 'r') as f: return [line.strip() for line in f.readlines()]

def add_url_to_notified_list(url):
    with open(STATE_FILE, 'a') as f: f.write(url + '\n')

def send_telegram_notification(product_url):
    # This function remains the same
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram secrets are not set."); return
    message = f"🎉 **IN STOCK!** 🎉\n\nThe product is now available!\n\nBuy it here: {product_url}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully sent Telegram notification for {product_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Telegram notification: {e}")

# MODIFIED: This function now saves a screenshot and HTML if the pincode box isn't found
def check_stock(product_url):
    product_name = product_url.split('/')[-1]
    print(f"Checking: {product_name}")
    driver = setup_driver()
    try:
        driver.get(product_url)
        
        try:
            print("  Waiting 10 seconds for pincode input box to appear...")
            wait = WebDriverWait(driver, 10)
            pincode_input = wait.until(EC.visibility_of_element_located((By.ID, "delivery_pincode")))
            
            print("  Pincode box found. Entering pincode...")
            pincode_input.send_keys(DELIVERY_PINCODE)
            
            apply_button = driver.find_element(By.XPATH, "//button[contains(text(),'Apply')]")
            apply_button.click()
            print(f"  Clicked 'Apply' for pincode {DELIVERY_PINCODE}. Waiting for page to reload...")
            time.sleep(5)
            
        except TimeoutException:
            # THIS IS THE CRITICAL DIAGNOSTIC PART
            print("  Pincode box did not appear! Saving evidence...")
            # Take a picture of what the browser sees
            driver.save_screenshot(f"{product_name}_screenshot.png")
            # Save the HTML of the page it's stuck on
            with open(f"{product_name}_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("  Saved screenshot and HTML source for debugging.")
            # -------------------------------------

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        if IN_STOCK_KEYWORD in soup.get_text():
            print(f"  >>> IN STOCK! - {product_name}")
            return True
        else:
            print(f"  Product is OUT of stock.")
            return False
    except Exception as e:
        print(f"  An error occurred during the automation process: {e}")
        return False
    finally:
        driver.quit()
        
        # --- NEW ROBUST PINCODE LOGIC ---
        try:
            # Wait a maximum of 10 seconds for the pincode input box to be visible
            print("  Waiting for pincode input box to appear...")
            wait = WebDriverWait(driver, 10)
            # THIS IS THE CORRECTED SELECTOR
            pincode_input = wait.until(EC.visibility_of_element_located((By.ID, "delivery_pincode")))
            
            print("  Pincode box found. Entering pincode...")
            pincode_input.send_keys(DELIVERY_PINCODE)
            
            # Find and click the apply button
            apply_button = driver.find_element(By.XPATH, "//button[contains(text(),'Apply')]")
            apply_button.click()
            print(f"  Clicked 'Apply' for pincode {DELIVERY_PINCODE}. Waiting for page to reload...")
            # Wait a moment for the page to process the pincode
            time.sleep(5)
        except TimeoutException:
            # This will happen if the pincode box does NOT appear after 10 seconds.
            # We assume it's because the pincode is already set from a previous check in this run.
            print("  Pincode box did not appear (this is OK). Proceeding...")
        # --------------------------------

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        if IN_STOCK_KEYWORD in soup.get_text():
            print(f"  >>> IN STOCK! - {product_name}")
            return True
        else:
            print(f"  Product is OUT of stock for pincode {DELIVERY_PINCODE}.")
            return False
    except Exception as e:
        print(f"  An error occurred during the automation process: {e}")
        return False
    finally:
        driver.quit()

# --- MAIN SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Final Stock Checker ---")
    notified_urls = get_notified_urls()
    newly_found_urls = []
    for url in PRODUCT_URLS:
        if url in notified_urls:
            print(f"Skipping already notified item: {url.split('/')[-1]}")
            continue
        if check_stock(url):
            send_telegram_notification(url)
            newly_found_urls.append(url)
        # We removed the small sleep here because the browser launch/quit takes time
    if newly_found_urls:
        for url in newly_found_urls:
            add_url_to_notified_list(url)
        print("\nUpdated the notified list.")
    else:
        print("\nNo new products in stock for this cycle.")
    print("--- Stock Check Complete ---")
