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
    conn = sqlite3.connect(DB_FILE, timeout=10.0)  # Add timeout
    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
    try:
        yield conn
        conn.commit()
    except sqlite3.IntegrityError as e:
        # Don't rollback on duplicate key errors
        logger.warning(f"Database integrity error (expected for duplicates): {e}")
        conn.commit()  # Commit what we can
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
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT UNIQUE
            )
        """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS user_timezones (
                user_id TEXT PRIMARY KEY,
                timezone TEXT,
                city TEXT
            )
        """
        )

        # --- NEW: Activity Tables ---
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_hourly (
                hour TEXT PRIMARY KEY,
                count INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_users (
                user_id TEXT PRIMARY KEY,
                count INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Add indexes for better query performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_quotes_text ON quotes(quote)")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_timezones_id ON user_timezones(user_id)"
        )
        # --- NEW: Activity Indexes ---
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_hourly_count ON activity_hourly(count DESC)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_users_count ON activity_users(count DESC)"
        )


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
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,))
            # Check if it was actually inserted
            if c.rowcount == 0:
                logger.warning(f"Quote already exists (skipped): {quote[:50]}...")
    except Exception as e:
        logger.error(f"Error adding quote: {e}")
        raise


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
            c.execute(
                "SELECT id, quote FROM quotes WHERE quote LIKE ?", (f"%{keyword}%",)
            )
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
            c.execute(
                "SELECT timezone, city FROM user_timezones WHERE user_id = ?",
                (str(user_id),),
            )
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
        c.execute(
            "INSERT OR REPLACE INTO user_timezones (user_id, timezone, city) VALUES (?, ?, ?)",
            (str(user_id), timezone_str, city),
        )


# tarot


def init_tarot_deck_settings():
    """Initialize tarot deck settings table"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS tarot_settings (
                guild_id TEXT PRIMARY KEY,
                deck_name TEXT DEFAULT 'thoth'
            )
        """
        )


def get_guild_tarot_deck(guild_id):
    """Get the current tarot deck for a guild"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT deck_name FROM tarot_settings WHERE guild_id = ?",
                (str(guild_id),),
            )
            result = c.fetchone()
            return result[0] if result else "thoth"
    except Exception as e:
        logger.error(f"Error getting tarot deck: {e}")
        return "thoth"


def set_guild_tarot_deck(guild_id, deck_name):
    """Set the tarot deck for a guild"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO tarot_settings (guild_id, deck_name) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET deck_name = ?
            """,
                (str(guild_id), deck_name, deck_name),
            )
    except Exception as e:
        logger.error(f"Error setting tarot deck: {e}")


# ============================================================
# GIF TRACKER FUNCTIONS
# ============================================================


def init_gif_table():
    """Initialize GIF tracker table"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS gif_tracker (
                gif_url TEXT PRIMARY KEY,
                count INTEGER DEFAULT 1,
                last_sent_by TEXT,
                last_sent_at TIMESTAMP
            )
        """
        )


def increment_gif_count(gif_url, user_id):
    """Increment GIF count or add new entry"""
    with get_db() as conn:
        c = conn.cursor()
        # *** DELETED: Delete GIFs older than two weeks ***
        # *** This is now handled by the background task cleanup_old_gifs() ***

        c.execute(
            """
            INSERT INTO gif_tracker (gif_url, count, last_sent_by, last_sent_at)
            VALUES (?, 1, ?, datetime('now'))
            ON CONFLICT(gif_url) DO UPDATE SET
                count = count + 1,
                last_sent_by = ?,
                last_sent_at = datetime('now')
        """,
            (gif_url, str(user_id), str(user_id)),
        )


def get_top_gifs(limit=10):
    """Get top GIFs by count"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT gif_url, count, last_sent_by 
                FROM gif_tracker 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            )
            return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting top GIFs: {e}")
        return []


def get_gif_by_rank(rank):
    """Get GIF URL by its rank position"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT gif_url 
                FROM gif_tracker 
                ORDER BY count DESC 
                LIMIT 1 OFFSET ?
            """,
                (rank - 1,),
            )
            result = c.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting GIF by rank: {e}")
        return None
