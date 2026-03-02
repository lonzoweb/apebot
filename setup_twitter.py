"""
One-time setup: manually paste your Twitter/X browser cookies to generate twitter_cookies.json
Run: python3 setup_twitter.py

HOW TO GET YOUR COOKIES (takes ~60 seconds):
  1. Open x.com in Chrome/Firefox and log in normally
  2. Press F12 (DevTools) → go to the "Application" tab (Chrome) or "Storage" tab (Firefox)
  3. In the left sidebar: Storage → Cookies → https://x.com
  4. Find and copy the values for 'auth_token' and 'ct0'
  5. Paste them below when prompted
"""

import json
import os

print("=== Twitter/X Cookie Setup (Browser Method) ===")
print()
print("1. Open x.com in your browser and log in")
print("2. Open DevTools (F12) → Application tab → Cookies → https://x.com")
print("3. Copy the values for 'auth_token' and 'ct0'")
print()

auth_token = input("Paste 'auth_token' value: ").strip()
ct0        = input("Paste 'ct0' value:        ").strip()

if not auth_token or not ct0:
    print("\n❌ Both values are required. Exiting.")
    exit(1)

# twikit's load_cookies / save_cookies uses httpx's cookie format.
# Providing the two key auth cookies is sufficient for read operations.
cookies = {
    "auth_token": auth_token,
    "ct0":        ct0,
}

cookies_file = os.getenv("TWITTER_COOKIES_FILE", "twitter_cookies.json")
with open(cookies_file, "w") as f:
    json.dump(cookies, f, indent=2)

print(f"\n✅ Cookies saved to: {cookies_file}")
print("The .x command will now work. Don't commit this file — it's your session token.")
