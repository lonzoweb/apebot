"""
One-time setup script: logs into Twitter/X and saves session cookies to twitter_cookies.json
Run this ONCE from the apebot directory:  python setup_twitter.py
"""

import asyncio

async def main():
    try:
        from twikit import Client
    except ImportError:
        print("❌ twikit not installed. Run: pip install twikit")
        return

    print("=== Twitter/X Cookie Setup ===")
    print("Enter your Twitter/X credentials. They are only used locally to create cookies.")
    print()

    username = input("Username (without @): ").strip()
    email    = input("Email address:        ").strip()
    password = input("Password:             ").strip()

    client = Client(language="en-US")

    print("\nLogging in...")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )
    except Exception as e:
        print(f"\n❌ Login failed: {e}")
        print("Make sure your credentials are correct and your account is not locked.")
        return

    cookies_file = "twitter_cookies.json"
    client.save_cookies(cookies_file)
    print(f"\n✅ Cookies saved to: {cookies_file}")
    print("The .x command will now work. Don't share this file — it's your session token.")
    print()
    print("If you're deploying on Railway, add this file to your repo OR set the")
    print("TWITTER_COOKIES_FILE env var to point to a mounted path.")

asyncio.run(main())
