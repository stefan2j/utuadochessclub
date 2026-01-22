import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
# We create a specific folder to store the robot's brain (cookies/passwords)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(BASE_DIR, "ChromeProfile")

def setup_persistent_browser():
    print("🤖 Opening the Robot Browser with Memory...")
    print(f"📂 Profile data will be saved to: {PROFILE_PATH}")

    chrome_options = Options()
    
    # This is the magic line that saves the login info
    chrome_options.add_argument(f"user-data-dir={PROFILE_PATH}")
    
    # Keep browser open
    chrome_options.add_experimental_option("detach", True)
    
    # Disable annoying popups
    chrome_options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
    
    print("🌍 Going to Facebook...")
    driver.get("https://www.facebook.com")
    
    print("\n" + "="*50)
    print("🚨 YOUR MISSION:")
    print("1. Log in manually (if asked).")
    print("2. Handle any 2FA/Captchas manually.")
    print("3. CRITICAL: Switch your profile to 'A Tu Alcance' manually.")
    print("4. Once you are on the 'A Tu Alcance' News Feed, CLOSE the browser.")
    print("="*50 + "\n")

if __name__ == "__main__":
    setup_persistent_browser()