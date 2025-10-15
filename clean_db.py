import sqlite3

DB_FILE = "/app/data/quotes.db"

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Fetch all quotes
c.execute("SELECT id, text FROM quotes")
rows = c.fetchall()

for qid, text in rows:
    cleaned = text.strip().strip('"').rstrip(',')
    if cleaned != text:
        c.execute("UPDATE quotes SET text = ? WHERE id = ?", (cleaned, qid))

conn.commit()
conn.close()
print("✅ Cleaned all existing quotes in the database")
