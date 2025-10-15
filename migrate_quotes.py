import sqlite3
import os

# Path to your SQLite DB (must match your bot)
DB_FILE = "/app/data/quotes.db"  # or wherever your bot DB is
QUOTES_FILE = "quotes.txt"       # path to your old quotes file

# Make sure DB exists
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# Connect to DB
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Create table if it doesn't exist
c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL
)
""")
conn.commit()

# Read quotes from quotes.txt
if os.path.exists(QUOTES_FILE):
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        # Insert into DB
        c.execute("INSERT INTO quotes (text) VALUES (?)", (line,))
    conn.commit()
    print(f"✅ Migrated {len(lines)} quotes to {DB_FILE}")
else:
    print("⚠️ quotes.txt not found!")

conn.close()
