"""
Lightweight Activity Tracking for Discord Bot
Batches activity data in memory, writes to DB periodically
Tracks: Most active hours, Most active users
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from discord.ext import tasks

logger = logging.getLogger(__name__)

# ============================================================
# IN-MEMORY ACTIVITY BUFFER (Batched)
# ============================================================

# Store activity in memory, flush to DB every 5 minutes
activity_buffer = {
    "hourly": defaultdict(int),  # {"HH": count, "09": 42, ...}
    "users": defaultdict(int),  # {"user_id": count, "123456": 127, ...}
}

BUFFER_SIZE_THRESHOLD = 1000  # Flush when we hit this many events


def log_activity_in_memory(user_id: str, hour: str):
    """Log activity to in-memory buffer (not database)"""
    activity_buffer["hourly"][hour] += 1
    activity_buffer["users"][user_id] += 1

    # If buffer gets too big, trigger flush
    total_events = sum(activity_buffer["hourly"].values())
    if total_events >= BUFFER_SIZE_THRESHOLD:
        # Flush will happen on next scheduled task (every 5 min)
        # Or you could async flush here if needed
        pass


def flush_activity_to_db(db_module):
    """Write batched activity data to database"""
    try:
        from database import get_db

        with get_db() as conn:
            c = conn.cursor()

            # Batch insert hourly data
            for hour, count in activity_buffer["hourly"].items():
                c.execute(
                    """
                    INSERT INTO activity_hourly (hour, count) VALUES (?, ?)
                    ON CONFLICT(hour) DO UPDATE SET count = count + ?
                """,
                    (hour, count, count),
                )

            # Batch insert user data
            for user_id, count in activity_buffer["users"].items():
                c.execute(
                    """
                    INSERT INTO activity_users (user_id, count) VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET count = count + ?
                """,
                    (user_id, count, count),
                )

            conn.commit()

        # Clear buffer after flush
        activity_buffer["hourly"].clear()
        activity_buffer["users"].clear()
        logger.info(
            f"✅ Activity data flushed to database - Hourly: {len(activity_buffer['hourly'])} entries, Users: {len(activity_buffer['users'])} entries"
        )

    except Exception as e:
        logger.error(f"Error flushing activity: {e}", exc_info=True)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================


def init_activity_db():
    """Initialize activity tables with indexes"""
    from database import get_db

    try:
        with get_db() as conn:
            c = conn.cursor()

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

            # Add indexes
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_hourly_count ON activity_hourly(count DESC)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_users_count ON activity_users(count DESC)"
            )

        logger.info("✅ Activity tables initialized")
    except Exception as e:
        logger.error(f"Error initializing activity DB: {e}")


# ============================================================
# QUERY FUNCTIONS
# ============================================================


def get_most_active_hours(limit=5):
    """Get top active hours"""
    from database import get_db

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT hour, count FROM activity_hourly 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            )
            return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting active hours: {e}")
        return []


def get_most_active_users(limit=10):
    """Get top active users"""
    from database import get_db

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT user_id, count FROM activity_users 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            )
            return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []


def get_total_messages():
    """Get total messages tracked"""
    from database import get_db

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(count) FROM activity_hourly")
            result = c.fetchone()
            return result[0] if result[0] else 0
    except Exception as e:
        logger.error(f"Error getting total messages: {e}")
        return 0


# ============================================================
# SETUP BACKGROUND TASK
# ============================================================


def setup_activity_tasks(bot):
    """Initialize background flushing task"""

    @tasks.loop(minutes=5)
    async def flush_activity():
        """Flush buffered activity to database every 5 minutes"""
        flush_activity_to_db(None)

    @flush_activity.before_loop
    async def before_flush():
        await bot.wait_until_ready()
        logger.info("⏳ Activity flush task started (every 5 minutes)")

    flush_activity.start()
