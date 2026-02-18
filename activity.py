"""
Lightweight Activity Tracking for Discord Bot
Batches activity data in memory, writes to DB periodically
Tracks: Most active hours, Most active users
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

# NOTE: The database module must define get_db()
from database import get_db

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
    # NOTE: user_id must be stored as a string
    activity_buffer["hourly"][hour] += 1
    activity_buffer["users"][user_id] += 1

    # Optional: If buffer gets too big, log a warning
    total_events = sum(activity_buffer["hourly"].values())
    if total_events >= BUFFER_SIZE_THRESHOLD:
        logger.debug(
            f"Activity buffer size ({total_events}) hit threshold. Will flush soon."
        )


async def flush_activity_to_db():
    """Write batched activity data to database"""
    # Use 'try...finally' to ensure the buffer clears even if one part fails.

    # 1. Capture and clear the data immediately
    hourly_data = dict(activity_buffer["hourly"])
    user_data = dict(activity_buffer["users"])

    activity_buffer["hourly"].clear()
    activity_buffer["users"].clear()

    # 2. Flush to DB
    try:
        async with get_db() as conn:
            # Batch update hourly data
            if hourly_data:
                hourly_items = [(hour, count, count) for hour, count in hourly_data.items()]
                await conn.executemany(
                    """
                    INSERT INTO activity_hourly (hour, count, last_updated) VALUES (?, ?, datetime('now'))
                    ON CONFLICT(hour) DO UPDATE SET 
                        count = count + ?,
                        last_updated = datetime('now')
                    """,
                    hourly_items,
                )

            # Batch update user data
            if user_data:
                user_items = [(user_id, count, count) for user_id, count in user_data.items()]
                await conn.executemany(
                    """
                    INSERT INTO activity_users (user_id, count, last_updated) VALUES (?, ?, datetime('now'))
                    ON CONFLICT(user_id) DO UPDATE SET 
                        count = count + ?,
                        last_updated = datetime('now')
                    """,
                    user_items,
                )

            # The context manager (get_db) handles conn.commit()

        logger.info(
            f"✅ Activity data flushed to database - Hourly: {len(hourly_data)} keys, Users: {len(user_data)} keys"
        )

    except Exception as e:
        logger.error(f"Error flushing activity: {e}", exc_info=True)


# ============================================================
# QUERY & CLEANUP FUNCTIONS (Rely on database.get_db)
# ============================================================


async def init_activity_tables():
    """Placeholder to call the init_db logic from the database file"""
    from database import init_db

    await init_db()
    logger.info("✅ Activity tables initialized (via database.init_db)")


async def get_most_active_hours(limit=5):
    """Get top active hours"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT hour, count FROM activity_hourly 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting active hours: {e}")
        return []


async def get_most_active_users(limit=10):
    """Get top active users"""
    try:
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT user_id, count FROM activity_users 
                ORDER BY count DESC 
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []


async def get_total_messages():
    """Get total messages tracked"""
    try:
        async with get_db() as conn:
            async with conn.execute("SELECT SUM(count) FROM activity_hourly") as cursor:
                result = await cursor.fetchone()
                return result[0] if result and result[0] else 0
    except Exception as e:
        logger.error(f"Error getting total messages: {e}")
        return 0


async def cleanup_old_activity(days=30):
    """Delete activity data older than X days"""
    try:
        # Calculate cutoff date in ISO format
        cutoff_datetime = datetime.now() - timedelta(days=days)
        cutoff_date = cutoff_datetime.isoformat()

        async with get_db() as conn:
            # The WHERE clause uses the last_updated TIMESTAMP field
            async with conn.execute(
                "DELETE FROM activity_hourly WHERE last_updated < ?", (cutoff_date,)
            ) as cursor:
                hourly_rows = cursor.rowcount

            async with conn.execute(
                "DELETE FROM activity_users WHERE last_updated < ?", (cutoff_date,)
            ) as cursor:
                user_rows = cursor.rowcount

        logger.info(
            f"✅ Cleaned up activity data older than {days} days. Deleted {hourly_rows} hourly entries and {user_rows} user entries."
        )

    except Exception as e:
        logger.error(f"Error cleaning up activity: {e}")


async def get_recent_active_users(limit=10):
    """
    Get users active in the last ~10 minutes.
    Merges the current memory buffer with recently updated users in the DB.
    Returns a list of (user_id, total_count) sorted by activity.
    """
    # 1. Get current buffer data
    combined_activity = defaultdict(int)
    for uid, count in activity_buffer["users"].items():
        combined_activity[uid] += count

    # 2. Query DB for users active in the last 10 minutes (to cover the 5m flush gap)
    try:
        async with get_db() as conn:
            # We look for users updated in the last 10 mins. 
            # We use their total count as a proxy for 'most active'
            async with conn.execute(
                """
                SELECT user_id, count FROM activity_users 
                WHERE last_updated > datetime('now', '-10 minutes')
                ORDER BY count DESC
                LIMIT ?
            """, (limit * 2,)
            ) as cursor:
                db_users = await cursor.fetchall()
                for uid_str, count in db_users:
                    # Merge: use the max or sum? 
                    # Sum might overcount if they just flushed, but it's safe for 'most active'
                    combined_activity[uid_str] += count
    except Exception as e:
        logger.error(f"Error merging DB activity: {e}")

    # 3. Sort and limit
    sorted_users = sorted(
        combined_activity.items(), key=lambda x: x[1], reverse=True
    )
    return sorted_users[:limit]


# Set init_activity_tables as the function to call on startup
# You must call this from your main bot file or Cog setup.
