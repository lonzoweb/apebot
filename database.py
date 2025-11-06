"""
Database functions for Discord Bot
Handles all SQLite operations
"""

import sqlite3
import logging
from contextlib import contextmanager
from config import DB_FILE

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE CONTEXT MANAGER
# ============================================================

@contextmanager
def get_db():
    """Context manager for safe database connections"""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT UNIQUE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_timezones (
                user_id TEXT PRIMARY KEY,
                timezone TEXT,
                city TEXT
            )
        """)

# ============================================================
# QUOTE FUNCTIONS
# ============================================================

def load_quotes_from_db():
    """Load all quotes from database"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT quote FROM quotes")
            return [row[0] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error loading quotes: {e}")
        return []

def add_quote_to_db(quote):
    """Add a new quote to database"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,))

def update_quote_in_db(old_quote, new_quote):
    """Update an existing quote"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE quotes SET quote = ? WHERE quote = ?", (new_quote, old_quote))

def search_quotes_by_keyword(keyword):
    """Search for quotes containing keyword"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, quote FROM quotes WHERE quote LIKE ?", (f"%{keyword}%",))
            return c.fetchall()
    except Exception as e:
        logger.error(f"Error searching quotes: {e}")
        return []

def delete_quote_by_id(quote_id):
    """Delete a quote by ID"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))

# ============================================================
# TIMEZONE FUNCTIONS
# ============================================================

def get_user_timezone(user_id):
    """Get user's timezone settings"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT timezone, city FROM user_timezones WHERE user_id = ?", (str(user_id),))
            row = c.fetchone()
            if row:
                return row[0], row[1]
    except Exception as e:
        logger.error(f"Error getting user timezone: {e}")
    return None, None

def set_user_timezone(user_id, timezone_str, city):
    """Set user's timezone"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_timezones (user_id, timezone, city) VALUES (?, ?, ?)",
                  (str(user_id), timezone_str, city))
