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

            # .key Command — image gallery & send counts
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS key_settings (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_url TEXT    NOT NULL,
                    label     TEXT    DEFAULT '',
                    is_active INTEGER DEFAULT 0,
                    added_at  TEXT    DEFAULT (datetime('now'))
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS key_config (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            # GIF Tracker
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS gif_tracker (gif_url TEXT PRIMARY KEY, count INTEGER DEFAULT 1, last_sent_by TEXT, last_sent_at TIMESTAMP)"
            )

            # 💰 Balances Table
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)"
            )

            # 💖 Legacy Pink Votes & Roles (will be migrated)
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS pink_votes (voted_id TEXT NOT NULL, voter_id TEXT NOT NULL, timestamp REAL NOT NULL, PRIMARY KEY (voted_id, voter_id))"
            )
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS masochist_roles (user_id TEXT PRIMARY KEY, removal_time REAL NOT NULL)"
            )

            # 🎨 Generalized Colour Roles
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS color_roles (
                    color_name TEXT PRIMARY KEY,
                    role_id TEXT NOT NULL,
                    vote_threshold INTEGER NOT NULL,
                    duration_days REAL NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS color_role_votes (
                    color_name TEXT NOT NULL,
                    voted_id TEXT NOT NULL,
                    voter_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    PRIMARY KEY (color_name, voted_id, voter_id),
                    FOREIGN KEY (color_name) REFERENCES color_roles(color_name) ON DELETE CASCADE
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS color_role_expirations (
                    user_id TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    color_name TEXT NOT NULL,
                    removal_time REAL NOT NULL,
                    PRIMARY KEY (user_id, role_id),
                    FOREIGN KEY (color_name) REFERENCES color_roles(color_name) ON DELETE CASCADE
                )
                """
            )

            # 🛡️ Trial System
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trials (
                    user_id TEXT NOT NULL,
                    guild_id TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    message_id TEXT,
                    status TEXT DEFAULT 'pending',
                    PRIMARY KEY (user_id, guild_id)
                )
                """
            )

            # COMMAND USAGE TRACKING
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS command_usage (
                    command_name TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
                """
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

            await conn.execute(
                "CREATE TABLE IF NOT EXISTS global_settings (key TEXT PRIMARY KEY, value TEXT)"
            )
            
            # 🔄 Run Migration
            await migrate_to_color_roles(conn)
        
            logger.info("✅ Database tables and migrations verified.")

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

            # 📜 Quote Drops Table (separate from daily quotes)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quote_drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quote TEXT UNIQUE,
                    added_by TEXT,
                    added_at REAL
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

            # 🐦 Twitter/X Follow Request Queue
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS follow_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    requested_at REAL NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
                """
            )

            # 🏆 Hall of Fame — Settings
            # Migration check: add blacklisted_users if missing
            async with conn.execute("PRAGMA table_info(hof_settings)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
                if columns and "blacklisted_users" not in columns:
                    logger.info("Adding blacklisted_users to hof_settings...")
                    await conn.execute("ALTER TABLE hof_settings ADD COLUMN blacklisted_users TEXT DEFAULT '[]'")

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hof_settings (
                    guild_id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    threshold INTEGER DEFAULT 3,
                    emojis TEXT DEFAULT '["⭐"]',
                    ignored_channels TEXT DEFAULT '[]',
                    locked_messages TEXT DEFAULT '[]',
                    trashed_messages TEXT DEFAULT '[]',
                    blacklisted_users TEXT DEFAULT '[]'
                )
                """
            )

            # 🏆 Hall of Fame — Entries
            # Migration: add voice_url if missing
            async with conn.execute("PRAGMA table_info(hof_entries)") as cursor:
                hof_cols = [row[1] for row in await cursor.fetchall()]
                if hof_cols and "voice_url" not in hof_cols:
                    logger.info("Adding voice_url to hof_entries...")
                    await conn.execute("ALTER TABLE hof_entries ADD COLUMN voice_url TEXT")
                if hof_cols and "trigger_emoji" not in hof_cols:
                    logger.info("Adding trigger_emoji to hof_entries...")
                    await conn.execute("ALTER TABLE hof_entries ADD COLUMN trigger_emoji TEXT")

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hof_entries (
                    orig_message_id TEXT PRIMARY KEY,
                    orig_channel_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    hof_message_id TEXT,
                    star_count INTEGER DEFAULT 0,
                    content TEXT,
                    image_url TEXT,
                    jump_url TEXT,
                    voice_url TEXT,
                    trigger_emoji TEXT,
                    created_at REAL NOT NULL
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users_xp (
                    user_id TEXT PRIMARY KEY,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    last_xp_time REAL DEFAULT 0
                )
                """
            )
            # 🚀 Optimization: Index for Leaderboard
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_xp_leaderboard ON users_xp (level DESC, xp DESC)")

            # ⚙️ Leveling System — Settings (Coefficients, Rounding, Range, etc.)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS level_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

            # ✖️ Leveling System — Multipliers (Role or Channel)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS level_multipliers (
                    target_id TEXT PRIMARY KEY,
                    multiplier REAL DEFAULT 1.0
                )
                """
            )

            # 🎁 Leveling System — Reward Roles
            # Migration check: add stack_role if missing
            async with conn.execute("PRAGMA table_info(reward_roles)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
                if columns and "stack_role" not in columns:
                    logger.info("Adding stack_role to reward_roles...")
                    await conn.execute("ALTER TABLE reward_roles ADD COLUMN stack_role INTEGER DEFAULT 1")

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reward_roles (
                    level INTEGER PRIMARY KEY,
                    role_id TEXT NOT NULL,
                    stack_role INTEGER DEFAULT 1
                )
                """
            )

            # 🏷️ Leveling System — Server Roles Cache (For Dashboard)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS server_roles_cache (
                    role_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT,
                    position INTEGER
                )
                """
            )

            # 📺 Leveling System — Server Channels Cache (For Dashboard)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS server_channels_cache (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT
                )
                """
            )

            # 👤 Leveling System — User Profile Cache (For Dashboard)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile_cache (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    avatar_url TEXT,
                    last_updated INTEGER
                )
                """
            )
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_updated ON user_profile_cache (last_updated)")

            # 🎨 Rank Card Preferences (per-user font + theme)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rank_card_prefs (
                    user_id      TEXT PRIMARY KEY,
                    font         TEXT DEFAULT 'Avenger',
                    theme        TEXT DEFAULT 'vampire',
                    display_type TEXT DEFAULT 'username'
                )
                """
            )
            
            # 🏢 Channel Assignments (Main, Spam, Admin, Error)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_config (
                    role TEXT PRIMARY KEY,
                    channel_id TEXT
                )
                """
            )
            
            # 🛑 Command Restrictions (Checkbox matrix)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS command_restrictions (
                    command_name TEXT,
                    channel_role TEXT,
                    is_allowed INTEGER DEFAULT 0,
                    PRIMARY KEY(command_name, channel_role)
                )
                """
            )
            # Migration: Ensure display_type column exists for users who already had the table
            try:
                await conn.execute("ALTER TABLE rank_card_prefs ADD COLUMN display_type TEXT DEFAULT 'username'")
            except Exception:
                pass # Already exists

            # 🔢 NUMEROLOGY — Number Descriptions (1-9, 11, 22, 33)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS numerology_number_desc (
                    num INTEGER PRIMARY KEY,
                    description TEXT DEFAULT ''
                )
                """
            )

            # 🔢 NUMEROLOGY — Combination Readings (primary × secondary)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS numerology_combos (
                    primary_num INTEGER NOT NULL,
                    secondary_num INTEGER NOT NULL,
                    combo_desc TEXT DEFAULT '',
                    PRIMARY KEY (primary_num, secondary_num)
                )
                """
            )

            # 🛒 SHOP — Item Price Overrides
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS item_prices (
                    item_key TEXT PRIMARY KEY,
                    price INTEGER NOT NULL
                )
                """
            )

            await conn.commit()

        # ── ONE-TIME BACKFILL: HoF → quote_drops (REMOVE AFTER FIRST DEPLOY) ──
        try:
            import re as _re
            _emoji_pat = _re.compile(
                r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
                r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251'
                r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
                r'\U00002600-\U000026FF\U0000FE0F]+'
            )
            async with get_db() as conn:
                async with conn.execute("""
                    SELECT content, author_id FROM hof_entries
                    WHERE hof_message_id IS NOT NULL
                      AND content IS NOT NULL AND content != ''
                      AND (image_url IS NULL OR image_url = '')
                      AND (voice_url IS NULL OR voice_url = '')
                """) as cursor:
                    hof_rows = await cursor.fetchall()
                
                _added = 0
                for _content, _author in hof_rows:
                    _text = _content.strip()
                    _text = _re.sub(r'<a?:\w+:\d+>', '', _text)
                    _text = _emoji_pat.sub('', _text).strip()
                    if _re.search(r'https?://\S+', _text):
                        continue
                    if not _text or len(_text) > 25:
                        continue
                    import time as _t
                    await conn.execute(
                        "INSERT OR IGNORE INTO quote_drops (quote, added_by, added_at) VALUES (?, ?, ?)",
                        (_text, _author, _t.time())
                    )
                    _added += 1
                await conn.commit()
                if _added:
                    logger.info(f"📜 Backfilled {_added} HoF entries into quote_drops.")
        except Exception as _e:
            logger.warning(f"HoF backfill skipped or failed: {_e}")
        # ── END ONE-TIME BACKFILL ──

        logger.info("✅ Database tables initialized (all modules unified).")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)


async def get_user_rank(user_id: int) -> int:
    """Return 1-indexed server rank by XP (higher XP = lower rank number)."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM users_xp WHERE xp > (SELECT xp FROM users_xp WHERE user_id = ?)",
            (str(user_id),),
        ) as cur:
            row = await cur.fetchone()
            return (row[0] + 1) if row else 1


async def get_rank_card_prefs(user_id: int) -> dict:
    async with get_db() as conn:
        async with conn.execute(
            "SELECT font, theme, display_type FROM rank_card_prefs WHERE user_id = ?",
            (str(user_id),),
        ) as cur:
            row = await cur.fetchone()
            if row:
                return {"font": row[0], "theme": row[1], "display_type": row[2] or "username"}
            return {"font": "Avenger", "theme": "vampire", "display_type": "username"}


async def set_rank_card_prefs(user_id: int, font: str = None, theme: str = None, display_type: str = None):
    prefs = await get_rank_card_prefs(user_id)
    new_font  = font  if font  else prefs["font"]
    new_theme = theme if theme else prefs["theme"]
    new_disp  = display_type if display_type else prefs["display_type"]
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO rank_card_prefs (user_id, font, theme, display_type) VALUES (?, ?, ?, ?)",
            (str(user_id), new_font, new_theme, new_disp),
        )
        await conn.commit()


# ============================================================
# COLOUR ROLE MANAGEMENT
# ============================================================

async def migrate_to_color_roles(conn):
    """One-time migration from static pink tables to dynamic color_roles."""
    from config import MASOCHIST_ROLE_ID, VOTE_THRESHOLD
    
    # Check if migration already ran
    async with conn.execute("SELECT COUNT(*) FROM color_roles") as cur:
        row = await cur.fetchone()
        if row and row[0] > 0:
            return

    # Seed initial roles
    await conn.execute(
        "INSERT OR IGNORE INTO color_roles (color_name, role_id, vote_threshold, duration_days) VALUES (?, ?, ?, ?)",
        ('pink', str(MASOCHIST_ROLE_ID), VOTE_THRESHOLD, 2.0)
    )
    await conn.execute(
        "INSERT OR IGNORE INTO color_roles (color_name, role_id, vote_threshold, duration_days) VALUES (?, ?, ?, ?)",
        ('green', '', 7, 2.0)
    )

    # Migrate pink votes if table exists
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO color_role_votes (color_name, voted_id, voter_id, timestamp) "
            "SELECT 'pink', voted_id, voter_id, timestamp FROM pink_votes"
        )
    except Exception as e:
        logger.debug(f"Migration: pink_votes table not found or already empty: {e}")

    # Migrate pink expirations if table exists
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO color_role_expirations (user_id, role_id, color_name, removal_time) "
            "SELECT user_id, ?, 'pink', removal_time FROM masochist_roles",
            (str(MASOCHIST_ROLE_ID),)
        )
    except Exception as e:
        logger.debug(f"Migration: masochist_roles table not found or already empty: {e}")


async def get_color_role_configs() -> list:
    """Returns all configured color roles."""
    async with get_db() as conn:
        async with conn.execute("SELECT color_name, role_id, vote_threshold, duration_days FROM color_roles") as cursor:
            rows = await cursor.fetchall()
            return [
                {"name": r[0], "role_id": r[1], "vote_threshold": r[2], "duration_days": r[3]}
                for r in rows
            ]


async def get_color_role_config(name: str) -> dict:
    """Returns configuration for a specific color role."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT role_id, vote_threshold, duration_days FROM color_roles WHERE color_name = ?",
            (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"role_id": row[0], "vote_threshold": row[1], "duration_days": row[2]}
            return None


async def set_color_role_config(name: str, role_id: str, threshold: int, duration: float):
    """Upserts a color role configuration."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO color_roles (color_name, role_id, vote_threshold, duration_days) VALUES (?, ?, ?, ?)",
            (name, str(role_id), threshold, duration)
        )


async def delete_color_role_config(name: str):
    """Deletes a color role configuration."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM color_roles WHERE color_name = ?", (name,))


async def update_color_vote(color_name: str, voted_id: str, voter_id: str):
    """Records a vote for a color role."""
    now = time.time()
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO color_role_votes (color_name, voted_id, voter_id, timestamp) VALUES (?, ?, ?, ?)",
            (color_name, str(voted_id), str(voter_id), now)
        )


async def get_active_color_vote_count(color_name: str, voted_id: str) -> int:
    """Counts active votes for a color role within the 48h expiration window."""
    async with get_db() as conn:
        expiration_time = time.time() - 172800 # Fixed 48h vote window
        async with conn.execute(
            "SELECT COUNT(voter_id) FROM color_role_votes WHERE color_name = ? AND voted_id = ? AND timestamp > ?",
            (color_name, str(voted_id), expiration_time)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def add_color_role_expiration(user_id: str, role_id: str, color_name: str, removal_time: float):
    """Schedules a color role for removal."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO color_role_expirations (user_id, role_id, color_name, removal_time) VALUES (?, ?, ?, ?)",
            (str(user_id), str(role_id), color_name, removal_time)
        )


async def get_pending_color_role_expirations() -> list:
    """Returns roles that are due for removal."""
    async with get_db() as conn:
        now = time.time()
        async with conn.execute(
            "SELECT user_id, role_id, color_name FROM color_role_expirations WHERE removal_time <= ?", (now,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r[0], "role_id": r[1], "color_name": r[2]} for r in rows]


async def remove_color_role_expiration(user_id: str, role_id: str):
    """Deletes a role expiration record."""
    async with get_db() as conn:
        await conn.execute(
            "DELETE FROM color_role_expirations WHERE user_id = ? AND role_id = ?",
            (str(user_id), str(role_id))
        )


# Backward compatibility helpers (delegates to new generalized functions)
async def update_pink_vote(voted_id: str, voter_id: str):
    await update_color_vote('pink', voted_id, voter_id)

async def get_active_pink_vote_count(voted_id: str) -> int:
    return await get_active_color_vote_count('pink', voted_id)

async def add_masochist_role_removal(user_id: str, removal_time: float):
    from config import MASOCHIST_ROLE_ID
    await add_color_role_expiration(user_id, str(MASOCHIST_ROLE_ID), 'pink', removal_time)

async def get_pending_role_removals() -> list:
    pending = await get_pending_color_role_expirations()
    return [p["user_id"] for p in pending if p["color_name"] == 'pink']

async def remove_masochist_role_record(user_id: str):
    from config import MASOCHIST_ROLE_ID
    await remove_color_role_expiration(user_id, str(MASOCHIST_ROLE_ID))


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
# NUMEROLOGY CONTENT
# ============================================================


async def get_numerology_number_desc(num: int) -> str:
    """Get the description for a numerology number (primary or secondary)."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT description FROM numerology_number_desc WHERE num = ?", (num,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_numerology_number_desc(num: int, description: str):
    """Set the description for a numerology number."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO numerology_number_desc (num, description) VALUES (?, ?)",
            (num, description)
        )
        await conn.commit()


async def get_numerology_combo(primary_num: int, secondary_num: int) -> str:
    """Get the combination reading for a primary+secondary pair."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT combo_desc FROM numerology_combos WHERE primary_num = ? AND secondary_num = ?",
            (primary_num, secondary_num)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_numerology_combo(primary_num: int, secondary_num: int, combo_desc: str):
    """Set the combination reading for a primary+secondary pair."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO numerology_combos (primary_num, secondary_num, combo_desc) VALUES (?, ?, ?)",
            (primary_num, secondary_num, combo_desc)
        )
        await conn.commit()


async def get_all_numerology_number_descs() -> dict:
    """Get all number descriptions as a dict {num: description}."""
    async with get_db() as conn:
        async with conn.execute("SELECT num, description FROM numerology_number_desc ORDER BY num") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def get_all_numerology_combos() -> list:
    """Get all combo entries as list of {primary_num, secondary_num, combo_desc}."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT primary_num, secondary_num, combo_desc FROM numerology_combos ORDER BY primary_num, secondary_num"
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"primary_num": r[0], "secondary_num": r[1], "combo_desc": r[2]} for r in rows]


async def seed_numerology_defaults():
    """Seed the database with default numerology descriptions and combos if empty."""
    import numerology as num_engine
    
    async with get_db() as conn:
        # 1. Number Descs
        async with conn.execute("SELECT COUNT(*) FROM numerology_number_desc") as cur:
            count = (await cur.fetchone())[0]
            if count == 0:
                for num, desc in num_engine.DEFAULT_NUMBER_DESCS.items():
                    await conn.execute(
                        "INSERT OR IGNORE INTO numerology_number_desc (num, description) VALUES (?, ?)",
                        (num, desc)
                    )
        
        # 2. Combos
        async with conn.execute("SELECT COUNT(*) FROM numerology_combos") as cur:
            count = (await cur.fetchone())[0]
            if count == 0:
                for (p, s), desc in num_engine.DEFAULT_COMBOS.items():
                    await conn.execute(
                        "INSERT OR IGNORE INTO numerology_combos (primary_num, secondary_num, combo_desc) VALUES (?, ?, ?)",
                        (p, s, desc)
                    )
        await conn.commit()


# ============================================================
# SHOP PRICING
# ============================================================

async def get_item_price(item_key: str) -> int:
    """Get item price from DB override, fallback to ITEM_REGISTRY."""
    from items import ITEM_REGISTRY
    async with get_db() as conn:
        async with conn.execute("SELECT price FROM item_prices WHERE item_key = ?", (item_key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            
            # Fallback
            return ITEM_REGISTRY.get(item_key, {}).get("cost", 999999)

async def set_item_price(item_key: str, price: int):
    """Override an item's price in the database."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO item_prices (item_key, price) VALUES (?, ?)",
            (item_key, price)
        )
        await conn.commit()

async def get_all_item_prices() -> dict:
    """Returns all price overrides as {item_key: price}."""
    async with get_db() as conn:
        async with conn.execute("SELECT item_key, price FROM item_prices") as cursor:
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}


# ============================================================
# CHANNEL CONFIG & COMMAND RESTRICTIONS
# ============================================================

async def get_channel_assigns() -> dict:
    """Returns a dict mapping role -> channel_id."""
    async with get_db() as conn:
        async with conn.execute("SELECT role, channel_id FROM channel_config") as cursor:
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}

async def set_channel_assign(role: str, channel_id: str):
    async with get_db() as conn:
        if not channel_id:
            await conn.execute("DELETE FROM channel_config WHERE role = ?", (role,))
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO channel_config (role, channel_id) VALUES (?, ?)",
                (role, channel_id)
            )

async def get_command_restrictions() -> dict:
    """Returns { 'role': { 'command_name': True/False } }"""
    res = {}
    async with get_db() as conn:
        async with conn.execute("SELECT command_name, channel_role, is_allowed FROM command_restrictions") as cursor:
            rows = await cursor.fetchall()
            for cmd, role, allowed in rows:
                if role not in res:
                    res[role] = {}
                res[role][cmd] = bool(allowed)
    return res

async def set_command_restriction(command_name: str, role: str, is_allowed: bool):
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO command_restrictions (command_name, channel_role, is_allowed) VALUES (?, ?, ?)",
            (command_name, role, 1 if is_allowed else 0)
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


async def get_top_balances(limit: int = 20) -> list:
    """Returns a list of (user_id, balance) for the wealthiest users."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT user_id, balance FROM balances ORDER BY balance DESC LIMIT ?",
            (limit,),
        ) as cursor:
            return await cursor.fetchall()


async def cap_all_balances(max_bal: int):
    """Enforces a hard cap on all user balances."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE balances SET balance = ? WHERE balance > ?",
            (max_bal, max_bal),
        )


async def clear_user_inventory(user_id: int):
    """Wipes all items from a user's inventory."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        await conn.execute(
            "DELETE FROM user_inventory WHERE user_id = ?",
            (user_id_str,),
        )


async def apply_wealth_tax(tax_rate: float = 0.10, threshold: int = 1000):
    """Deducts a percentage from balances over a certain threshold."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE balances SET balance = CAST(balance * (1 - ?) AS INTEGER) WHERE balance > ?",
            (tax_rate, threshold),
        )


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


# ============================================================
# QUOTE DROPS (Separate from daily quotes)
# ============================================================

async def add_quote_drop(quote: str, added_by: str = None):
    """Add a quote to the quote drops table."""
    import time as _time
    try:
        async with get_db() as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO quote_drops (quote, added_by, added_at) VALUES (?, ?, ?)",
                (quote, added_by, _time.time())
            )
    except Exception as e:
        logger.error(f"Error adding quote drop: {e}")
        raise

async def get_random_quote_drop():
    """Get a single random quote drop."""
    try:
        async with get_db() as conn:
            async with conn.execute("SELECT quote FROM quote_drops ORDER BY RANDOM() LIMIT 1") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting random quote drop: {e}")
        return None

async def get_all_quote_drops():
    """Get all quote drops (for dashboard)."""
    try:
        async with get_db() as conn:
            async with conn.execute("SELECT id, quote, added_by, added_at FROM quote_drops ORDER BY id DESC") as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error loading quote drops: {e}")
        return []

async def delete_quote_drop(quote_id: int):
    """Delete a quote drop by ID."""
    try:
        async with get_db() as conn:
            await conn.execute("DELETE FROM quote_drops WHERE id = ?", (quote_id,))
    except Exception as e:
        logger.error(f"Error deleting quote drop: {e}")
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
# .key COMMAND SETTINGS
# ============================================================

DEFAULT_IMAGE_URL = "https://i.imgur.com/GQxOYGn.png"


async def get_key_settings():
    """Return the full .key config: active image URL, gallery, and send counts."""
    async with get_db() as conn:
        # Gallery
        async with conn.execute(
            "SELECT id, image_url, label, is_active, added_at FROM key_settings ORDER BY added_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()

        images = [
            {"id": r[0], "url": r[1], "label": r[2], "is_active": bool(r[3]), "added_at": r[4]}
            for r in rows
        ]
        active_url = next((i["url"] for i in images if i["is_active"]), DEFAULT_IMAGE_URL)

        # Config values
        async with conn.execute(
            "SELECT key, value FROM key_config WHERE key IN ('send_count_user', 'send_count_admin')"
        ) as cursor:
            cfg_rows = await cursor.fetchall()

        cfg = {r[0]: int(r[1]) for r in cfg_rows}
        return {
            "active_url": active_url,
            "images": images,
            "send_count_user": cfg.get("send_count_user", 2),
            "send_count_admin": cfg.get("send_count_admin", 6),
        }


async def add_key_image(image_url: str, label: str = ""):
    """Add an image to the .key gallery and set it as active. Trims to 10 entries."""
    async with get_db() as conn:
        # Deactivate all others
        await conn.execute("UPDATE key_settings SET is_active = 0")
        # Insert new (active)
        await conn.execute(
            "INSERT INTO key_settings (image_url, label, is_active) VALUES (?, ?, 1)",
            (image_url, label),
        )
        # Trim to newest 10
        await conn.execute(
            """
            DELETE FROM key_settings WHERE id NOT IN (
                SELECT id FROM key_settings ORDER BY added_at DESC LIMIT 10
            )
            """
        )


async def set_key_active_image(image_id: int):
    """Set a specific gallery image as active."""
    async with get_db() as conn:
        await conn.execute("UPDATE key_settings SET is_active = 0")
        await conn.execute("UPDATE key_settings SET is_active = 1 WHERE id = ?", (image_id,))


async def delete_key_image(image_id: int):
    """Delete an image from the gallery. If it was active, no image will be active (bot uses fallback)."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM key_settings WHERE id = ?", (image_id,))


async def set_key_config(send_count_user: int, send_count_admin: int):
    """Save the send count settings for .key."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO key_config (key, value) VALUES ('send_count_user', ?)",
            (str(send_count_user),),
        )
        await conn.execute(
            "INSERT OR REPLACE INTO key_config (key, value) VALUES ('send_count_admin', ?)",
            (str(send_count_admin),),
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


# ============================================================
# TWITTER/X FOLLOW REQUEST QUEUE
# ============================================================


async def add_follow_request(requester_id: int, username: str) -> int:
    """Queue a follow request. Returns the new request ID."""
    async with get_db() as conn:
        async with conn.execute(
            "INSERT INTO follow_requests (requester_id, username, requested_at) VALUES (?, ?, ?)",
            (str(requester_id), username.lower(), time.time()),
        ) as cursor:
            return cursor.lastrowid


async def get_pending_follow_requests() -> list:
    """Return all pending follow requests as (id, requester_id, username, requested_at)."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT id, requester_id, username, requested_at FROM follow_requests WHERE status = 'pending' ORDER BY requested_at ASC"
        ) as cursor:
            return await cursor.fetchall()


async def get_follow_request(request_id: int):
    """Return a single request row or None."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT id, requester_id, username, requested_at, status FROM follow_requests WHERE id = ?",
            (request_id,),
        ) as cursor:
            return await cursor.fetchone()


async def update_follow_request_status(request_id: int, status: str):
    """Set status to 'approved' or 'denied'."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE follow_requests SET status = ? WHERE id = ?",
            (status, request_id),
        )


async def has_pending_follow_request(username: str) -> bool:
    """Check if an account already has a pending request."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT id FROM follow_requests WHERE username = ? AND status = 'pending'",
            (username.lower(),),
        ) as cursor:
            return await cursor.fetchone() is not None

# ============================================================
# LEVELING SYSTEM FUNCTIONS
# ============================================================


async def get_user_xp_data(user_id: int) -> dict:
    """Returns (xp, level, last_xp_time) for a user."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT xp, level, last_xp_time FROM users_xp WHERE user_id = ?",
            (user_id_str,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"xp": row[0], "level": row[1], "last_xp_time": row[2]}
            return {"xp": 0, "level": 0, "last_xp_time": 0}


async def update_user_xp(user_id: int, xp: int, level: int, last_xp_time: float):
    """Updates or inserts a user's XP data."""
    user_id_str = str(user_id)
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO users_xp (user_id, xp, level, last_xp_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                xp = excluded.xp,
                level = excluded.level,
                last_xp_time = excluded.last_xp_time
        """,
            (user_id_str, xp, level, last_xp_time),
        )


async def get_level_settings() -> dict:
    """Returns all leveling settings as a dict."""
    async with get_db() as conn:
        async with conn.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def set_level_setting(key: str, value: str):
    """Sets a leveling setting."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO level_settings (key, value) VALUES (?, ?)",
            (key, value),
        )


async def get_level_multipliers() -> dict:
    """Returns all role/channel multipliers."""
    async with get_db() as conn:
        async with conn.execute("SELECT target_id, multiplier FROM level_multipliers") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def set_level_multiplier(target_id: str, multiplier: float):
    """Sets a multiplier for a target (role/channel)."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO level_multipliers (target_id, multiplier) VALUES (?, ?)",
            (target_id, multiplier),
        )


async def remove_level_multiplier(target_id: str):
    """Removes a multiplier."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM level_multipliers WHERE target_id = ?", (target_id,))


async def get_reward_roles() -> list:
    """Returns list of all level-role rewards with stacking info."""
    async with get_db() as conn:
        async with conn.execute("SELECT level, role_id, stack_role FROM reward_roles") as cursor:
            rows = await cursor.fetchall()
            return [{"level": row[0], "role_id": row[1], "stack_role": bool(row[2])} for row in rows]


async def set_reward_role(level: int, role_id: str, stack_role: int = 1):
    """Sets a role reward for a specific level."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO reward_roles (level, role_id, stack_role) VALUES (?, ?, ?)",
            (level, role_id, stack_role),
        )


async def remove_reward_role(level: int):
    """Removes a role reward."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM reward_roles WHERE level = ?", (level,))


async def get_top_levels(limit: int = 50) -> list:
    """Returns top users by level and XP, joining with profile cache."""
    async with get_db() as conn:
        query = """
            SELECT u.user_id, u.xp, u.level, p.username, p.avatar_url 
            FROM users_xp u
            LEFT JOIN user_profile_cache p ON u.user_id = p.user_id
            ORDER BY u.level DESC, u.xp DESC 
            LIMIT ?
        """
        async with conn.execute(query, (limit,)) as cursor:
            return await cursor.fetchall()

# ============================================================
# SERVER ROLES CACHE (For Dashboard)
# ============================================================

async def sync_server_roles(roles_data: list):
    """Update the cache of server roles. roles_data is list of (role_id, name, color, position)."""
    async with get_db() as conn:
        # Use OR REPLACE instead of global DELETE to be safer in multi-guild or partial syncs
        await conn.executemany(
            "INSERT OR REPLACE INTO server_roles_cache (role_id, name, color, position) VALUES (?, ?, ?, ?)",
            roles_data
        )
        await conn.commit()

async def get_cached_roles() -> dict:
    """Returns dict of role_id -> {name, color, position}."""
    async with get_db() as conn:
        async with conn.execute("SELECT role_id, name, color, position FROM server_roles_cache") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: {"name": row[1], "color": row[2], "position": row[3]} for row in rows}

async def sync_server_channels(channels_data: list):
    """Update the cache of server channels. channels_data is list of (channel_id, name, type)."""
    async with get_db() as conn:
        await conn.executemany(
            "INSERT OR REPLACE INTO server_channels_cache (channel_id, name, type) VALUES (?, ?, ?)",
            channels_data
        )
        await conn.commit()

async def get_cached_channels() -> dict:
    """Returns dict of channel_id -> {name, type}."""
    async with get_db() as conn:
        async with conn.execute("SELECT channel_id, name, type FROM server_channels_cache") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: {"name": row[1], "type": row[2]} for row in rows}

# ============================================================
# USER PROFILE CACHE (For Dashboard)
# ============================================================

async def sync_user_profile(user_id: int, username: str, avatar_url: str):
    """Update or insert a user's profile info into the cache."""
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO user_profile_cache (user_id, username, avatar_url, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                avatar_url = excluded.avatar_url,
                last_updated = excluded.last_updated
            """,
            (str(user_id), username, avatar_url, int(time.time()))
        )

# ============================================================
# LEVELING CALCULATIONS
# ============================================================

def calculate_level_for_xp(xp: int, c3: float, c2: float, c1: float, rounding: int) -> int:
    """Calculate level from XP using the cubic formula."""
    if xp <= 0: return 0
    
    # Simple iterative approach as solving cubic is complex and L is usually small (0-150)
    level = 0
    while True:
        L = level + 1
        req = (c3 * (L**3) + c2 * (L**2) + c1 * L)
        if rounding > 0:
            req = round(req / rounding) * rounding
        
        if xp >= req:
            level += 1
        else:
            break
            
    return level


# ============================================================
# COMMAND USAGE TRACKING
# ============================================================

async def increment_command_usage(command_name: str):
    """Increment the usage count for a given command."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO command_usage (command_name, count) VALUES (?, 1) "
            "ON CONFLICT(command_name) DO UPDATE SET count = count + 1",
            (command_name,)
        )
        await conn.commit()

async def get_command_usage_stats(limit: int = 15):
    """Get the top most used commands."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT command_name, count FROM command_usage ORDER BY count DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [{"name": r[0], "count": r[1]} for r in rows]

# ============================================================
# TRIAL SYSTEM HELPERS
# ============================================================

async def add_trial(user_id: str, guild_id: str, start_time: float, end_time: float):
    """Add a new trial to the database."""
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO trials (user_id, guild_id, start_time, end_time, status) VALUES (?, ?, ?, ?, 'pending') "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET start_time = excluded.start_time, end_time = excluded.end_time, status = 'pending', message_id = NULL",
            (user_id, guild_id, start_time, end_time)
        )
        await conn.commit()

async def get_active_trials():
    """Get all trials that are still pending."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT user_id, guild_id, start_time, end_time, message_id FROM trials WHERE status = 'pending'"
        ) as cursor:
            rows = await cursor.fetchall()
        return rows

async def update_trial_message(user_id: str, guild_id: str, message_id: str):
    """Update the message ID of the trial decision embed."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE trials SET message_id = ? WHERE user_id = ? AND guild_id = ?",
            (message_id, user_id, guild_id)
        )
        await conn.commit()

async def update_trial_status(user_id: str, guild_id: str, status: str):
    """Update the status of a trial (e.g., 'graduated', 'extended', 'kicked')."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE trials SET status = ? WHERE user_id = ? AND guild_id = ?",
            (status, user_id, guild_id)
        )
        await conn.commit()

async def get_trial(user_id: str, guild_id: str):
    """Get a specific trial entry."""
    async with get_db() as conn:
        async with conn.execute(
            "SELECT start_time, end_time, message_id, status FROM trials WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cursor:
            return await cursor.fetchone()

async def update_trial_end_time(user_id: str, guild_id: str, end_time: float):
    """Extend or update the trial end time."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE trials SET end_time = ?, message_id = NULL WHERE user_id = ? AND guild_id = ?",
            (end_time, user_id, guild_id)
        )
        await conn.commit()

