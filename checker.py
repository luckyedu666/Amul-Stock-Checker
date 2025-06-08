import requests
from bs4 import BeautifulSoup
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
IN_STOCK_KEYWORD = "Add to Cart"
DELIVERY_PINCODE = "560015"
STATE_FILE = "out_of_stock_memory.txt"
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

# --- STATE MANAGEMENT FUNCTIONS ---
def get_previously_out_of_stock():
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def update_out_of_stock_memory(oos_urls):
    with open(STATE_FILE, 'w') as f:
        for url in oos_urls:
            f.write(url + '\n')

# --- HELPER FUNCTIONS ---
def send_telegram_notification(product_url):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram secrets are not set."); return
    message = f"IN STOCK!\n\nThe product is now available!\n\nBuy it here: {product_url}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully sent Telegram notification for {product_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Telegram notification: {e}")

# --- CORE LOGIC with FULL LOGGING ---
def check_stock(product_url):
    product_name = product_url.split('/')[-1]
    print(f"Checking: {product_name}")
    driver = setup_driver()
    try:
        driver.get(product_url)
        try:
            # Re-enabled print statements for full visibility
            print("  Waiting for pincode input box (id='search')...")
            wait = WebDriverWait(driver, 10)
            pincode_input = wait.until(EC.visibility_of_element_located((By.ID, "search")))
            print("  Pincode box found.")
            
            pincode_input.send_keys(DELIVERY_PINCODE)
            print(f"  Typed pincode {DELIVERY_PINCODE}.")
            time.sleep(3)

            print("  Waiting for the clickable suggestion link...")
            suggestion_xpath = f"//a[.//p[text()='{DELIVERY_PINCODE}']]"
            suggestion_button = wait.until(EC.element_to_be_clickable((By.XPATH, suggestion_xpath)))
            
            print("  Precise suggestion found. Clicking it...")
            suggestion_button.click()
            
            print("  Pincode submitted successfully. Waiting for page to reload...")
            time.sleep(5)
            
        except TimeoutException:
            print("  Pincode box did not appear. Assuming pincode is already set.")

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        add_to_cart_link = soup.select_one("a.add-to-cart")
        
        if add_to_cart_link and 'disabled' not in add_to_cart_link.get('class', []):
            print(f"  >>> IN STOCK! - Found active 'add-to-cart' link.")
            return True
        else:
            print(f"  Product is OUT of stock.")
            return False
    except Exception as e:
        print(f"  An error occurred: {e}")
        return False 
    finally:
        driver.quit()

# --- MAIN SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Smart Stock Checker ---")
    
    previously_out_of_stock = get_previously_out_of_stock()
    print(f"Loaded {len(previously_out_of_stock)} items from previous out-of-stock memory.")
    
    current_out_of_stock = set()

    for url in PRODUCT_URLS:
        is_in_stock = check_stock(url)
        
        if is_in_stock:
            if url in previously_out_of_stock:
                print(f"  STATUS CHANGE: Item is back in stock! Sending notification.")
                send_telegram_notification(url)
            else:
                print("  Status is still 'In Stock'. No notification needed.")
        else:
            current_out_of_stock.add(url)
            
    update_out_of_stock_memory(current_out_of_stock)
    print(f"\nUpdated memory: Saved {len(current_out_of_stock)} out-of-stock items for next run.")
    print("--- Stock Check Complete ---")
