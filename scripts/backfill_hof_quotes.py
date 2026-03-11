"""
One-off script: backfill quote_drops with existing HoF entries
that are text-only and ≤25 characters.

Run this where the bot's DB lives. It auto-detects the DB path.
"""
import asyncio
import aiosqlite
import os
import re
import time
import sys

# Try to import config for DB path, otherwise use common locations
DB_FILE = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.expanduser("~/Repos/apebot"))
    from config import DB_FILE as _dbf
    # config.DB_FILE is the quotes DB, but bot data uses get_db() which uses a different path
    # Let's check the database module
    from database import DB_FILE as _dbf2
    DB_FILE = _dbf2
except Exception:
    pass

# Fallback paths
if not DB_FILE or not os.path.exists(DB_FILE):
    for candidate in [
        "/app/data/quotes.db",
        os.path.expanduser("~/Repos/apebot/apeiron.db"),
        os.path.expanduser("~/Repos/apebot/data/quotes.db"),
    ]:
        if os.path.exists(candidate):
            DB_FILE = candidate
            break

if not DB_FILE:
    print("ERROR: Could not find the bot database. Set DB_FILE manually.")
    sys.exit(1)

EMOJI_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
    r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251'
    r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
    r'\U00002600-\U000026FF\U0000FE0F]+'
)

async def main():
    print(f"Using DB: {DB_FILE}")
    
    async with aiosqlite.connect(DB_FILE) as db:
        # Ensure quote_drops table exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quote_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT UNIQUE,
                added_by TEXT,
                added_at REAL
            )
        """)
        await db.commit()

        # Check if hof_entries table exists
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hof_entries'") as cursor:
            if not await cursor.fetchone():
                print("hof_entries table does not exist in this database.")
                print("This script needs to run where the bot's full DB lives (production).")
                return

        # Fetch text-only HoF entries that have been posted
        async with db.execute("""
            SELECT content, author_id FROM hof_entries
            WHERE hof_message_id IS NOT NULL
              AND content IS NOT NULL
              AND content != ''
              AND (image_url IS NULL OR image_url = '')
              AND (voice_url IS NULL OR voice_url = '')
        """) as cursor:
            rows = await cursor.fetchall()
        
        print(f"Found {len(rows)} text-only HoF entries. Filtering to ≤25 chars...")
        
        added = 0
        skipped = 0
        for content, author_id in rows:
            text = content.strip()
            # Strip custom Discord emoji
            text = re.sub(r'<a?:\w+:\d+>', '', text).strip()
            # Strip unicode emoji
            text = EMOJI_PATTERN.sub('', text).strip()
            # Skip URLs
            if re.search(r'https?://\S+', text):
                continue
            
            if not text or len(text) > 25:
                continue
            
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO quote_drops (quote, added_by, added_at) VALUES (?, ?, ?)",
                    (text, author_id, time.time())
                )
                added += 1
                print(f"  + \"{text}\"")
            except Exception as e:
                skipped += 1
                print(f"  SKIP: {e}")
        
        await db.commit()
        print(f"\nDone! Added {added} quotes to quote_drops ({skipped} skipped/duplicates).")

        # Show total count
        async with db.execute("SELECT COUNT(*) FROM quote_drops") as cursor:
            row = await cursor.fetchone()
            print(f"Total quotes in quote_drops: {row[0]}")

asyncio.run(main())
