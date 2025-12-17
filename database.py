"""
Database functions for Discord Bot
Handles all SQLite operations
"""

import sqlite3
import logging
import time
from contextlib import contextmanager
from config import DB_FILE  # Assumes DB_FILE is defined here

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE CONTEXT MANAGER (Core Connection Logic)
# ============================================================


@contextmanager
def get_db():
    """Context manager for safe database connections and transactions."""
    conn = sqlite3.connect(DB_FILE, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except sqlite3.IntegrityError as e:
        logger.warning(
            f"Database integrity error (likely expected unique constraint): {e}"
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        conn.close()


# ============================================================
# DATABASE INITIALIZATION (Unified)
# ============================================================


def init_db():
    """
    Initialize ALL database tables.
    (Quotes, Timezones, Activity, Balances, Tarot, GIF Tracker, Pink Votes, Inventory, Effects)
    """
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Quotes Table
            c.execute(
                "CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)"
            )

            # User Timezones Table
            c.execute(
                "CREATE TABLE IF NOT EXISTS user_timezones (user_id TEXT PRIMARY KEY, timezone TEXT, city TEXT)"
            )

            # Activity Tables
            c.execute(
                "CREATE TABLE IF NOT EXISTS activity_hourly (hour TEXT PRIMARY KEY, count INTEGER, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS activity_users (user_id TEXT PRIMARY KEY, count INTEGER, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

            # Tarot Settings
            c.execute(
                "CREATE TABLE IF NOT EXISTS tarot_settings (guild_id TEXT PRIMARY KEY, deck_name TEXT DEFAULT 'thoth')"
            )

            # GIF Tracker
            c.execute(
                "CREATE TABLE IF NOT EXISTS gif_tracker (gif_url TEXT PRIMARY KEY, count INTEGER DEFAULT 1, last_sent_by TEXT, last_sent_at TIMESTAMP)"
            )

            # 💰 Balances Table
            c.execute(
                "CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)"
            )

            # 💖 Pink Votes & Roles
            c.execute(
                "CREATE TABLE IF NOT EXISTS pink_votes (voted_id TEXT NOT NULL, voter_id TEXT NOT NULL, timestamp REAL NOT NULL, PRIMARY KEY (voted_id, voter_id))"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS masochist_roles (user_id TEXT PRIMARY KEY, removal_time REAL NOT NULL)"
            )

            # 📦 NEW: User Inventory Table
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, item_name)
                )
            """
            )

            # 🧿 NEW: Active Effects Table (Curse/Mute)
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS active_effects (
                    target_id TEXT PRIMARY KEY,
                    effect_name TEXT NOT NULL,
                    expiration_time REAL NOT NULL
                )
            """
            )

            # Add indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_quotes_text ON quotes(quote)")
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_timezones_id ON user_timezones(user_id)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_users_count ON activity_users(count DESC)"
            )

        logger.info("✅ Database tables initialized (all modules unified).")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)


# ============================================================
# PINK VOTE MANAGEMENT
# ============================================================


def update_pink_vote(voted_id: str, voter_id: str):
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pink_votes (voted_id, voter_id, timestamp) VALUES (?, ?, ?)",
            (voted_id, voter_id, now),
        )


def get_active_pink_vote_count(voted_id: str) -> int:
    with get_db() as conn:
        expiration_time = time.time() - 172800
        c = conn.execute(
            "SELECT COUNT(voter_id) FROM pink_votes WHERE voted_id = ? AND timestamp > ?",
            (voted_id, expiration_time),
        )
        return c.fetchone()[0]


def add_masochist_role_removal(user_id: str, removal_time: float):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO masochist_roles (user_id, removal_time) VALUES (?, ?)",
            (user_id, removal_time),
        )


def get_pending_role_removals() -> list:
    with get_db() as conn:
        now = time.time()
        c = conn.execute(
            "SELECT user_id FROM masochist_roles WHERE removal_time <= ?", (now,)
        )
        return [row[0] for row in c.fetchall()]


def remove_masochist_role_record(user_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM masochist_roles WHERE user_id = ?", (user_id,))


# ============================================================
# ECONOMY & INVENTORY FUNCTIONS
# ============================================================


def get_balance(user_id: int) -> int:
    user_id_str = str(user_id)
    with get_db() as conn:
        c = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (user_id_str,)
        )
        result = c.fetchone()
        return result[0] if result else 0


def update_balance(user_id: int, amount: int):
    user_id_str = str(user_id)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO balances (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        """,
            (user_id_str, amount, amount),
        )


def transfer_tokens(sender_id: int, recipient_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    sender_id_str, recipient_id_str = str(sender_id), str(recipient_id)
    with get_db() as conn:
        c = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (sender_id_str,)
        )
        row = c.fetchone()
        if not row or row[0] < amount:
            return False
        conn.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (amount, sender_id_str),
        )
        conn.execute(
            """
            INSERT INTO balances (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        """,
            (recipient_id_str, amount, amount),
        )
        return True


def atomic_purchase(user_id: int, item_name: str, cost: int) -> bool:
    """Handles token deduction and item addition in ONE transaction."""
    user_id_str = str(user_id)
    with get_db() as conn:
        c = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (user_id_str,)
        )
        row = c.fetchone()
        if not row or row[0] < cost:
            return False

        # Deduct balance
        conn.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (cost, user_id_str),
        )
        # Add to inventory
        conn.execute(
            """
            INSERT INTO user_inventory (user_id, item_name, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1
        """,
            (user_id_str, item_name),
        )
        return True


def get_user_inventory(user_id: int) -> dict:
    """Retrieves all items and quantities for a user."""
    user_id_str = str(user_id)
    with get_db() as conn:
        c = conn.execute(
            "SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND quantity > 0",
            (user_id_str,),
        )
        return {row[0]: row[1] for row in c.fetchall()}


def remove_item_from_inventory(user_id: int, item_name: str) -> bool:
    """Consumes 1 item from user inventory. Returns True if successful."""
    user_id_str = str(user_id)
    with get_db() as conn:
        c = conn.execute(
            "UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ? AND quantity > 0",
            (user_id_str, item_name),
        )
        return c.rowcount > 0


# ============================================================
# ACTIVE EFFECT MANAGEMENT
# ============================================================


def add_active_effect(target_id: int, effect_name: str, duration_sec: float):
    """Applies a curse. PRIMARY KEY on target_id enforces one curse at a time."""
    target_id_str = str(target_id)
    expiration = time.time() + duration_sec
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_effects (target_id, effect_name, expiration_time) VALUES (?, ?, ?)",
            (target_id_str, effect_name, expiration),
        )


def get_active_effect(target_id: int) -> tuple:
    """Returns (effect_name, expiration_time) or None."""
    target_id_str = str(target_id)
    with get_db() as conn:
        c = conn.execute(
            "SELECT effect_name, expiration_time FROM active_effects WHERE target_id = ?",
            (target_id_str,),
        )
        return c.fetchone()


def remove_active_effect(target_id: int):
    target_id_str = str(target_id)
    with get_db() as conn:
        conn.execute("DELETE FROM active_effects WHERE target_id = ?", (target_id_str,))


def get_all_expired_effects() -> list:
    """Gets list of target_ids whose curses have expired."""
    with get_db() as conn:
        now = time.time()
        c = conn.execute(
            "SELECT target_id FROM active_effects WHERE expiration_time <= ?", (now,)
        )
        return [row[0] for row in c.fetchall()]


# ============================================================
# QUOTE FUNCTIONS (EXISTING)
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
# TIMEZONE FUNCTIONS (EXISTING)
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


# ============================================================
# TAROT FUNCTIONS (EXISTING)
# ============================================================


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
# GIF TRACKER FUNCTIONS (EXISTING)
# ============================================================


def increment_gif_count(gif_url, user_id):
    """Increment GIF count or add new entry"""
    with get_db() as conn:
        c = conn.cursor()

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


def cleanup_old_data():
    """Removes expired votes and old activity to save disk space on Railway."""
    with get_db() as conn:
        now = time.time()
        # Remove pink votes older than 48 hours
        conn.execute("DELETE FROM pink_votes WHERE timestamp <= ?", (now - 172800,))
        # Remove activity logs older than 30 days (optional)
        conn.execute(
            "DELETE FROM activity_hourly WHERE last_updated < datetime('now', '-30 days')"
        )
