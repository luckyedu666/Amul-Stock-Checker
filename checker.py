import requests
from bs4 import BeautifulSoup
import time
import os

# --- CONFIGURATION ---
PRODUCT_URLS = [
    "https://shop.amul.com/en/product/amul-high-protein-buttermilk-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
    "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30"
]
IN_STOCK_KEYWORD = "Product Information"
STATE_FILE = "notified_urls.txt"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- FUNCTIONS ---
def get_notified_urls():
    if not os.path.exists(STATE_FILE):
        return []
    with open(STATE_FILE, 'r') as f:
        return [line.strip() for line in f.readlines()]

def add_url_to_notified_list(product_url):
    with open(STATE_FILE, 'a') as f:
        f.write(product_url + '\n')

def send_telegram_notification(product_url):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram secrets are not set.")
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

def check_stock(product_url):
    print(f"Checking: {product_url.split('/')[-1]}")
    try:
        response = requests.get(product_url, headers=HEADERS)
        response.raise_for_status()
        if IN_STOCK_KEYWORD in response.text:
            print(f"  >>> IN STOCK! - {product_url.split('/')[-1]}")
            return True
        return False
    except requests.exceptions.RequestException as e:
        print(f"  An error occurred fetching the page: {e}")
        return False

# --- MAIN SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Scheduled Stock Check ---")
    notified_urls = get_notified_urls()
    newly_found_urls = []
    for url in PRODUCT_URLS:
        if url in notified_urls:
            print(f"Skipping already notified item: {url.split('/')[-1]}")
            continue
        if check_stock(url):
            send_telegram_notification(url)
            newly_found_urls.append(url)
        time.sleep(2)
    if newly_found_urls:
        for url in newly_found_urls:
            add_url_to_notified_list(url)
        print("\nUpdated the notified list.")
    else:
        print("\nNo new products in stock.")
    print("--- Stock Check Complete ---")
