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
    # For this test, let's ONLY check the product you know is in stock
    "https://shop.amul.com/en/product/amul-kool-protein-milkshake-or-kesar-180-ml-or-pack-of-30"
]
DELIVERY_PINCODE = "560015" # Your pincode

# --- SELENIUM BROWSER SETUP ---
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# --- DIAGNOSTIC SCRIPT ---
if __name__ == "__main__":
    print("--- Starting Diagnostic Capture ---")
    
    for url in PRODUCT_URLS:
        product_name = url.split('/')[-1]
        print(f"Diagnosing: {product_name}")
        driver = setup_driver()
        try:
            driver.get(url)
            try:
                print("  Waiting 10 seconds for pincode input box (id='search')...")
                wait = WebDriverWait(driver, 10)
                pincode_input = wait.until(EC.visibility_of_element_located((By.ID, "search")))
                print("  Pincode box found. Entering pincode...")
                pincode_input.send_keys(DELIVERY_PINCODE + Keys.RETURN)
                print(f"  Entered pincode {DELIVERY_PINCODE} and pressed Enter.")
                
            except TimeoutException:
                print("  Pincode box did not appear. Assuming it's already set.")

            # Wait a generous amount of time for the final page to load
            print("  Waiting 10 seconds for page to fully render...")
            time.sleep(10)

            # --- THE EVIDENCE CAPTURE ---
            print("  Capturing final page state...")
            driver.save_screenshot(f"{product_name}_final_screenshot.png")
            with open(f"{product_name}_final_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("  Screenshot and HTML saved.")
            # ---------------------------

        except Exception as e:
            print(f"  An error occurred during the automation process: {e}")
        finally:
            driver.quit()
            
    print("--- Diagnostic Capture Complete ---")
