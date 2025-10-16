import sqlite3
import os

DB_FILE = "/app/data/quotes.db"

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Delete duplicate rows (case-insensitive, trimmed)
c.execute("""
DELETE FROM quotes
WHERE id NOT IN (
  SELECT MIN(id)
  FROM quotes
  GROUP BY TRIM(LOWER(text))
)
""")

conn.commit()

# Clean trailing or extra quotes
c.execute("SELECT id, text FROM quotes")
rows = c.fetchall()
cleaned = 0
for rid, text in rows:
    cleaned_text = text.strip().strip('"').strip("'").strip()
    if cleaned_text != text:
        c.execute("UPDATE quotes SET text = ? WHERE id = ?", (cleaned_text, rid))
        cleaned += 1

conn.commit()
conn.close()

print("✅ Database cleaned.")
print(f"Removed duplicates and fixed {cleaned} quotes.")
