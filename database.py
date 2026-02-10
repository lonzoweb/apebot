import aiosqlite
import logging
import time
import random
from contextlib import asynccontextmanager
from config import DB_FILE
from exceptions import InsufficientTokens, ItemNotFoundError

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE CONTEXT MANAGER (Core Connection Logic)
# ============================================================


@asynccontextmanager
async def get_db():
    """Async context manager for safe database connections and transactions."""
    async with aiosqlite.connect(DB_FILE, timeout=20.0) as conn:
        try:
            yield conn
            await conn.commit()
        except aiosqlite.IntegrityError as e:
            logger.warning(
                f"Database integrity error (likely expected unique constraint): {e}"
            )
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise


# ============================================================
# DATABASE INITIALIZATION (Unified)
# ============================================================


async def init_db():
    """
    Initialize ALL database tables.
    (Quotes, Timezones, Activity, Balances, Tarot, GIF Tracker, Pink Votes, Inventory, Effects)
    """
    try:
        async with get_db() as conn:
            # Persistent performance optimizations
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")

            # Quotes Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)"
            )

            # User Timezones Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS user_timezones (user_id TEXT PRIMARY KEY, timezone TEXT, city TEXT)"
            )

            # Activity Tables
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS activity_hourly (hour TEXT PRIMARY KEY, count INTEGER, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS activity_users (user_id TEXT PRIMARY KEY, count INTEGER, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

            # Tarot Settings
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS tarot_settings (guild_id TEXT PRIMARY KEY, deck_name TEXT DEFAULT 'thoth')"
            )

            # GIF Tracker
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS gif_tracker (gif_url TEXT PRIMARY KEY, count INTEGER DEFAULT 1, last_sent_by TEXT, last_sent_at TIMESTAMP)"
            )

            # 💰 Balances Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)"
            )

            # 💖 Pink Votes & Roles
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS pink_votes (voted_id TEXT NOT NULL, voter_id TEXT NOT NULL, timestamp REAL NOT NULL, PRIMARY KEY (voted_id, voter_id))"
            )
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS masochist_roles (user_id TEXT PRIMARY KEY, removal_time REAL NOT NULL)"
            )

            # 📦 NEW: User Inventory Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, item_name)
                )
            """
            )

            # Global Settings Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS global_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)"
            )

            # Shard Claim Tracking Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS last_shard_claim (user_id TEXT PRIMARY KEY, last_claim REAL)"
            )

            # 🌑 NEW: Active Effects Table (Curse/Mute)
            # Migration check: If table exists with old column names, drop it
            async with conn.execute("PRAGMA table_info(active_effects)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
                if columns and "expires_at" not in columns:
                    logger.info("Outdated active_effects table found. Migrating...")
                    await conn.execute("DROP TABLE active_effects")

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_effects (
                    user_id TEXT NOT NULL,
                    effect_name TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (user_id, effect_name)
                )
            """
            )

            # ⏳ NEW: Global Cooldowns Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS global_cooldowns (
                    name TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL
                )
            """
            )

            # ⚙️ NEW: System Settings Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # 🤲 NEW: Daily Claims Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_claims (
                    user_id TEXT NOT NULL,
                    claim_type TEXT NOT NULL,
                    last_claim_date TEXT NOT NULL,
                    PRIMARY KEY (user_id, claim_type)
                )
            """
            )

            # 🌾 NEW: The Reaping State Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reaping_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    active INTEGER DEFAULT 0,
                    pool_amount INTEGER DEFAULT 0,
                    games_count INTEGER DEFAULT 0,
                    started_at REAL,
                    expires_at REAL
                )
            """
            )

            # 🌾 NEW: The Reaping Participants Table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reaping_participants (
                    user_id TEXT PRIMARY KEY,
                    contribution INTEGER DEFAULT 0
                )
            """
            )

            # Add indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_text ON quotes(quote)")
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_timezones_id ON user_timezones(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_users_count ON activity_users(count DESC)"
            )

            # Fade stats table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fade_stats (
                    user_id TEXT PRIMARY KEY,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0
                )
                """
            )

        logger.info("✅ Database tables initialized (all modules unified).")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)


# ============================================================
# PINK VOTE MANAGEMENT
# ============================================================


async def update_pink_vote(voted_id: str, voter_id: str):
    now = time.time()
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO pink_votes (voted_id, voter_id, timestamp) VALUES (?, ?, ?)",
            (voted_id, voter_id, now),
        )


async def get_active_pink_vote_count(voted_id: str) -> int:
    async with get_db() as conn:
        expiration_time = time.time() - 172800
        async with conn.execute(
            "SELECT COUNT(voter_id) FROM pink_votes WHERE voted_id = ? AND timestamp > ?",
            (voted_id, expiration_time),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def add_masochist_role_removal(user_id: str, removal_time: float):
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO masochist_roles (user_id, removal_time) VALUES (?, ?)",
            (user_id, removal_time),
        )


async def get_pending_role_removals() -> list:
    async with get_db() as conn:
        now = time.time()
        async with conn.execute(
            "SELECT user_id FROM masochist_roles WHERE removal_time <= ?", (now,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def remove_masochist_role_record(user_id: str):
    async with get_db() as conn:
        await conn.execute("DELETE FROM masochist_roles WHERE user_id = ?", (user_id,))


# ============================================================
# GLOBAL SETTINGS MANAGEMENT
# ============================================================


async def get_setting(key: str, default: str = None) -> str:
    async with get_db() as conn:
        async with conn.execute(
            "SELECT setting_value FROM global_settings WHERE setting_key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO global_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value),
        )


# ============================================================
# SHARD CLAIM MANAGEMENT
# ============================================================


async def can_claim_shard(user_id: int) -> bool:
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT last_claim FROM last_shard_claim WHERE user_id = ?", (user_id_str,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return True
            last_claim = row[0]
            # 6 hours = 21600 seconds
            return (time.time() - last_claim) >= 21600


async def record_shard_claim(user_id: int):
    user_id_str = str(user_id)
    now = time.time()
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO last_shard_claim (user_id, last_claim) VALUES (?, ?)",
            (user_id_str, now),
        )


# ============================================================
# ECONOMY & INVENTORY FUNCTIONS
# ============================================================


async def get_balance(user_id: int) -> int:
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (user_id_str,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def update_balance(user_id: int, amount: int):
    """Update user's balance. Amount can be positive (earnings) or negative (costs)."""
    user_id_str = str(user_id)
    
    # 🌓 MULTIPLIERS (Positive earnings only)
    if amount > 0:
        # Night Vision Check (Block income)
        nv_expires = await get_active_effect(user_id, "night_vision")
        if nv_expires and nv_expires > time.time():
            return

        # Blood Moon (2x)
        bm_multiplier = await get_blood_moon_multiplier()
        if bm_multiplier > 1:
            amount = int(amount * bm_multiplier)
            
        # Luck Curse (1.5x)
        luck_expires = await get_active_effect(user_id, "luck_curse")
        if luck_expires and luck_expires > time.time():
            amount = int(amount * 1.5)

    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO balances (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = MAX(0, balance + ?)
        """,
            (user_id_str, max(0, amount), amount),
        )

async def get_blood_moon_multiplier() -> int:
    """Returns 2 if Blood Moon is active, else 1."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT value FROM system_settings WHERE key = 'blood_moon_end'"
        ) as cursor:
            row = await cursor.fetchone()
            if row and float(row[0]) > time.time():
                return 2
    return 1

async def set_blood_moon(duration_sec: int):
    """Set the blood moon end timestamp."""
    end_time = time.time() + duration_sec
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value) VALUES ('blood_moon_end', ?)",
            (str(end_time),)
        )


async def set_balance(user_id: int, new_balance: int):
    """Set a user's balance to an exact amount (for .baledit command)"""
    user_id_str = str(user_id)
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO balances (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = ?
        """,
            (user_id_str, new_balance, new_balance),
        )


async def get_potential_victims(exclude_ids: list, min_balance: int = 1):
    """Get user IDs with at least min_balance, excluding specific IDs."""
    async with get_db() as conn:
        if not exclude_ids:
            query = "SELECT user_id FROM balances WHERE balance >= ?"
            params = (min_balance,)
        else:
            placeholders = ", ".join(["?"] * len(exclude_ids))
            query = f"SELECT user_id FROM balances WHERE balance >= ? AND user_id NOT IN ({placeholders})"
            params = (min_balance,) + tuple(str(uid) for uid in exclude_ids)

        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def transfer_tokens(sender_id: int, recipient_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    sender_id_str, recipient_id_str = str(sender_id), str(recipient_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (sender_id_str,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                raise InsufficientTokens(amount, row[0] if row else 0)
        await conn.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (amount, sender_id_str),
        )
        await conn.execute(
            """
            INSERT INTO balances (user_id, balance) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        """,
            (recipient_id_str, amount, amount),
        )
        return True


async def atomic_purchase(user_id: int, item_name: str, cost: int, quantity: int = 1) -> bool:
    """Handles token deduction and item addition in ONE transaction."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?", (user_id_str,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < cost:
                raise InsufficientTokens(cost, row[0] if row else 0)

        # Deduct balance
        await conn.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (cost, user_id_str),
        )
        # Add to inventory
        await conn.execute(
            """
            INSERT INTO user_inventory (user_id, item_name, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?
        """,
            (user_id_str, item_name, quantity, quantity),
        )
        return True


async def get_user_inventory(user_id: int) -> dict:
    """Retrieves all items and quantities for a user."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND quantity > 0",
            (user_id_str,),
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def remove_item_from_inventory(user_id: int, item_name: str) -> bool:
    """Consumes 1 item from user inventory. Returns True if successful."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ? AND quantity > 0",
            (user_id_str, item_name),
        ) as cursor:
            if cursor.rowcount > 0:
                await conn.execute("DELETE FROM user_inventory WHERE quantity <= 0")
                return True
            return False


async def update_inventory(user_id: int, item_name: str, quantity: int):
    """Sets the quantity of an item in user inventory. Deletes if quantity <= 0."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        if quantity <= 0:
            await conn.execute(
                "DELETE FROM user_inventory WHERE user_id = ? AND item_name = ?",
                (user_id_str, item_name),
            )
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO user_inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                (user_id_str, item_name, quantity),
            )


async def transfer_item(sender_id: int, receiver_id: int, item_name: str) -> bool:
    """Move 1 item from sender's inventory to receiver's."""
    sender_id_str = str(sender_id)
    receiver_id_str = str(receiver_id)
    
    async with get_db() as conn:
        # 1. Deduct from sender if quantity > 0
        async with conn.execute(
            "UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ? AND quantity > 0",
            (sender_id_str, item_name),
        ) as cursor:
            if cursor.rowcount == 0:
                return False

        # 2. Add to receiver
        await conn.execute(
            """
            INSERT INTO user_inventory (user_id, item_name, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1
        """,
            (receiver_id_str, item_name),
        )
        
        # 3. Clean up sender's empty slot
        await conn.execute("DELETE FROM user_inventory WHERE quantity <= 0")
        
        return True


async def reset_economy_data():
    """Wipes all rows from balances and user_inventory tables. Standard reset."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM balances")
        await conn.execute("DELETE FROM user_inventory")
        # Optional: also clear daily claims if we want a fresh start
        await conn.execute("DELETE FROM daily_claims")
    logger.info("⚠️ ECONOMY RESET: All balances and inventories cleared.")


# ============================================================
# ACTIVE EFFECT MANAGEMENT
# ============================================================


async def add_active_effect(target_id: int, effect_name: str, duration_sec: float):
    """Applies an effect. PRIMARY KEY (user_id, effect_name) allows multiple different effects."""
    target_id_str = str(target_id)
    expiration = time.time() + duration_sec
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO active_effects (user_id, effect_name, expires_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id, effect_name) DO UPDATE SET expires_at = ?
        """,
            (target_id_str, effect_name, expiration, expiration),
        )


async def get_active_effect(target_id: int, effect_name: str) -> float:
    """Returns the expiration timestamp of a specific effect, or None."""
    target_id_str = str(target_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT expires_at FROM active_effects WHERE user_id = ? AND effect_name = ?",
            (target_id_str, effect_name),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_all_active_effects(target_id: int) -> list:
    """Returns a list of (effect_name, expires_at) for a user."""
    target_id_str = str(target_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT effect_name, expires_at FROM active_effects WHERE user_id = ?",
            (target_id_str,),
        ) as cursor:
            return await cursor.fetchall()


async def remove_active_effect(target_id: int, effect_name: str = None):
    """Clears effects. If effect_name is provided, clears only that one."""
    target_id_str = str(target_id)
    async with get_db() as conn:
        if effect_name:
            await conn.execute(
                "DELETE FROM active_effects WHERE user_id = ? AND effect_name = ?",
                (target_id_str, effect_name),
            )
        else:
            await conn.execute("DELETE FROM active_effects WHERE user_id = ?", (target_id_str,))


async def get_all_expired_effects() -> list:
    """Gets list of (user_id, effect_name) whose effects have expired."""
    async with get_db() as conn:
        now = time.time()
        async with conn.execute(
            "SELECT user_id, effect_name FROM active_effects WHERE expires_at <= ?", (now,)
        ) as cursor:
            return await cursor.fetchall()


# ============================================================
# QUOTE FUNCTIONS (EXISTING)
# ============================================================


async def load_quotes_from_db():
    """Load all quotes from database"""
    try:
        async with get_db() as conn:
            async with conn.execute("SELECT quote FROM quotes") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error loading quotes: {e}")
        return []


async def add_quote_to_db(quote):
    """Add a new quote to database"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                "INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,)
            ) as cursor:
                if cursor.rowcount == 0:
                    logger.warning(f"Quote already exists (skipped): {quote[:50]}...")
    except Exception as e:
        logger.error(f"Error adding quote: {e}")
        raise


async def update_quote_in_db(old_quote, new_quote):
    """Update an existing quote"""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE quotes SET quote = ? WHERE quote = ?", (new_quote, old_quote)
        )


async def search_quotes_by_keyword(keyword):
    """Search for quotes containing keyword"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                "SELECT id, quote FROM quotes WHERE quote LIKE ?", (f"%{keyword}%",)
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error searching quotes: {e}")
        return []


async def delete_quote_by_id(quote_id):
    """Delete a quote by ID"""
    async with get_db() as conn:
        await conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))


# ============================================================
# TIMEZONE FUNCTIONS (EXISTING)
# ============================================================


async def get_user_timezone(user_id):
    """Get user's timezone settings"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                "SELECT timezone, city FROM user_timezones WHERE user_id = ?",
                (str(user_id),),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0], row[1]
    except Exception as e:
        logger.error(f"Error getting user timezone: {e}")
    return None, None


async def set_user_timezone(user_id, timezone_str, city):
    """Set user's timezone"""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO user_timezones (user_id, timezone, city) VALUES (?, ?, ?)",
            (str(user_id), timezone_str, city),
        )


# ============================================================
# TAROT FUNCTIONS (EXISTING)
# ============================================================


async def get_guild_tarot_deck(guild_id):
    """Get the current tarot deck for a guild"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                "SELECT deck_name FROM tarot_settings WHERE guild_id = ?",
                (str(guild_id),),
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else "thoth"
    except Exception as e:
        logger.error(f"Error getting tarot deck: {e}")
        return "thoth"


async def set_guild_tarot_deck(guild_id, deck_name):
    """Set the tarot deck for a guild"""
    try:
        async with get_db() as conn:
            await conn.execute(
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


async def increment_gif_count(gif_url, user_id):
    """Increment GIF count or add new entry"""
    async with get_db() as conn:
        await conn.execute(
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


async def get_top_gifs(limit=10):
    """Get top GIFs by count"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT gif_url, count, last_sent_by 
                FROM gif_tracker 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting top GIFs: {e}")
        return []


async def get_gif_by_rank(rank):
    """Get GIF URL by its rank position"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT gif_url 
                FROM gif_tracker 
                ORDER BY count DESC 
                LIMIT 1 OFFSET ?
            """,
                (rank - 1,),
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting GIF by rank: {e}")
        return None


async def cleanup_old_data():
    """Removes expired votes and old activity to save disk space on Railway."""
    async with get_db() as conn:
        now = time.time()
        # Remove pink votes older than 48 hours
        await conn.execute("DELETE FROM pink_votes WHERE timestamp <= ?", (now - 172800,))
        # Remove activity logs older than 30 days (optional)
        await conn.execute(
            "DELETE FROM activity_hourly WHERE last_updated < datetime('now', '-30 days')"
        )

# ============================================================
# GLOBAL COOLDOWNS
# ============================================================


async def get_global_cooldown(name: str) -> float:
    """Returns the expiration timestamp (epoch) for a global cooldown, or 0 if none."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT expires_at FROM global_cooldowns WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return 0


async def set_global_cooldown(name: str, duration_sec: int):
    """Sets a global cooldown for the specified name and duration."""
    expires_at = time.time() + duration_sec
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO global_cooldowns (name, expires_at) VALUES (?, ?)",
            (name, expires_at),
        )


# ============================================================
# SYSTEM SETTINGS & DAILY CLAIMS
# ============================================================


async def is_economy_on() -> bool:
    """Checks if the global economy is enabled."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT value FROM system_settings WHERE key = 'economy_enabled'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0] == "True"
            return True  # Default to True


async def set_economy_status(status: bool):
    """Sets the global economy status."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value) VALUES ('economy_enabled', ?)",
            (str(status),),
        )


async def can_claim_daily(user_id: int, claim_type: str) -> bool:
    """Checks if a user can claim their daily reward."""
    today = time.strftime("%Y-%m-%d")
    async with get_db() as conn:
        async with conn.execute(
            "SELECT last_claim_date FROM daily_claims WHERE user_id = ? AND claim_type = ?",
            (str(user_id), claim_type),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] != today:
                return True
            return False


async def record_daily_claim(user_id: int, claim_type: str):
    """Records a daily claim for a user."""
    today = time.strftime("%Y-%m-%d")
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO daily_claims (user_id, claim_type, last_claim_date) VALUES (?, ?, ?)",
            (str(user_id), claim_type, today),
        )





# ============================================================
# THE REAPING FUNCTIONS
# ============================================================


async def start_reaping(duration_seconds: int = 1800):
    """Starts The Reaping event (30 minutes default)."""
    async with get_db() as conn:
        end_time = time.time() + duration_seconds
        await conn.execute(
            """
            INSERT OR REPLACE INTO reaping_state (id, active, pool_amount, games_count, started_at, expires_at)
            VALUES (1, 1, 0, 0, ?, ?)
        """,
            (time.time(), end_time),
        )


async def is_reaping_active() -> bool:
    """Check if The Reaping is currently active."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT active, expires_at FROM reaping_state WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            active, expires_at = row
            if active and expires_at and time.time() < expires_at:
                return True
            return False


async def add_reaping_tithe(user_id: int, amount: int):
    """Add tokens to the reaping pool and track participant contribution."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        # Update pool
        await conn.execute(
            "UPDATE reaping_state SET pool_amount = pool_amount + ?, games_count = games_count + 1 WHERE id = 1",
            (amount,),
        )
        # Track participant
        await conn.execute(
            """
            INSERT INTO reaping_participants (user_id, contribution) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET contribution = contribution + ?
        """,
            (user_id_str, amount, amount),
        )


async def get_reaping_state():
    """Get current reaping state."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT active, pool_amount, games_count, expires_at FROM reaping_state WHERE id = 1"
        ) as cursor:
            return await cursor.fetchone()


async def get_reaping_participants():
    """Get list of all participants (user_ids)."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT user_id FROM reaping_participants"
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def end_reaping():
    """End The Reaping event, split 80% pool among participants, and clear state."""
    async with get_db() as conn:
        # Get pool and participants
        async with conn.execute("SELECT pool_amount FROM reaping_state WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            pool = row[0] if row else 0

        async with conn.execute("SELECT user_id FROM reaping_participants") as cursor:
            rows = await cursor.fetchall()
            participants = [row[0] for row in rows]

        winner_count = 0
        payout_per_person = 0
        burned = 0
        
        count = len(participants)
        if count > 0 and pool > 0:
            total_payout = int(pool * 0.8)
            payout_per_person = total_payout // count
            burned = pool - (payout_per_person * count) # Remainder goes to void
            winner_count = count

            if payout_per_person > 0:
                for uid in participants:
                    await conn.execute(
                        """
                        INSERT INTO balances (user_id, balance) VALUES (?, ?) 
                        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
                        """,
                        (str(uid), payout_per_person, payout_per_person)
                    )

        # Cleanup
        await conn.execute("UPDATE reaping_state SET active = 0, pool_amount = 0, games_count = 0 WHERE id = 1")
        await conn.execute("DELETE FROM reaping_participants")

        return winner_count, payout_per_person, burned


# ============================================================
# FADE STATS MANAGEMENT
# ============================================================

async def record_fade_result(user_id: int, won: bool):
    """Record a fade win or loss for a user."""
    user_id_str = str(user_id)
    field = "wins" if won else "losses"
    async with get_db() as conn:
        await conn.execute(
            f"""
            INSERT INTO fade_stats (user_id, {field}) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET {field} = {field} + 1
            """,
            (user_id_str,)
        )


async def get_fade_stats(user_id: int) -> dict:
    """Get fade stats for a user. Returns {'wins': int, 'losses': int}."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT wins, losses FROM fade_stats WHERE user_id = ?",
            (user_id_str,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"wins": row[0], "losses": row[1]}
            return {"wins": 0, "losses": 0}

# ============================================================
# YAP SYSTEM SETTINGS
# ============================================================

async def get_yap_level() -> str:
    """Get the global yap level (low/high). Defaults to high."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT value FROM system_settings WHERE key = 'yap_level'"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "high"

async def set_yap_level(level: str):
    """Set the global yap level (low/high)."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO system_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            ("yap_level", level.lower(), level.lower()),
        )

async def has_item(user_id: int, item_name: str) -> bool:
    """Check if a user has at least one of a specific item."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?",
            (user_id_str, item_name),
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0] > 0) if row else False
