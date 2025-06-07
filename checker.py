import requests
from bs4 import BeautifulSoup
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
PRODUCT_URLS = [
    "https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30"
]
IN_STOCK_KEYWORD = "Add to Cart" # Change this back to "Product Information" to run your test
STATE_FILE = "notified_urls.txt"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- SELENIUM BROWSER SETUP ---
def setup_driver():
    """Configures the Selenium browser for running in GitHub Actions."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run without a visible browser window
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# --- FUNCTIONS ---
def get_notified_urls():
    if not os.path.exists(STATE_FILE): return []
    with open(STATE_FILE, 'r') as f: return [line.strip() for line in f.readlines()]

def add_url_to_notified_list(url):
    with open(STATE_FILE, 'a') as f: f.write(url + '\n')

def send_telegram_notification(product_url):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram secrets not set.")
        return
    message = f"🎉 **IN STOCK!** 🎉\n\nThe product is now available!\n\nBuy it here: {product_url}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully sent Telegram notification for {product_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Telegram notification: {e}")

# --- NEW check_stock FUNCTION USING SELENIUM ---
def check_stock(product_url):
    """Checks a single product using a full browser to render JavaScript."""
    print(f"Checking: {product_url.split('/')[-1]}")
    driver = setup_driver()
    try:
        driver.get(product_url)
        # Wait for a few seconds for all JavaScript to load
        time.sleep(5) 
        
        # Now get the page source AFTER JavaScript has run
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        if IN_STOCK_KEYWORD in soup.get_text():
            print(f"  >>> IN STOCK! - {product_url.split('/')[-1]}")
            return True
        return False
    except Exception as e:
        print(f"  An error occurred fetching the page with Selenium: {e}")
        return False
    finally:
        # IMPORTANT: Always close the browser
        driver.quit()

# --- MAIN SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Scheduled Stock Check with Selenium ---")
    notified_urls = get_notified_urls()
    newly_found_urls = []
    for url in PRODUCT_URLS:
        if url in notified_urls:
            print(f"Skipping already notified item: {url.split('/')[-1]}")
            continue
        if check_stock(url):
            send_telegram_notification(url)
            newly_found_urls.append(url)
    if newly_found_urls:
        for url in newly_found_urls:
            add_url_to_notified_list(url)
        print("\nUpdated the notified list.")
    else:
        print("\nNo new products in stock.")
    print("--- Stock Check Complete ---")
