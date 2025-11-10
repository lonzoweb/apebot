"""
Server Activity Tracker Module
Tracks message activity over rolling 30-day period
"""

import discord
import logging

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from collections import defaultdict
from database import get_db
from database import get_user_timezone
from zoneinfo import ZoneInfo

# ============================================================
# DATABASE FUNCTIONS
# ============================================================


def convert_hourly_to_timezone(hourly_data, date_str, timezone_name):
    """Convert hourly activity dict from UTC to user's timezone"""
    if not timezone_name or timezone_name == "None":
        return hourly_data  # No conversion

    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        return hourly_data

    converted = {hour: 0 for hour in range(24)}

    # Create UTC datetime objects for the given date
    for hour, count in hourly_data.items():
        utc_dt = datetime.strptime(f"{date_str} {hour}", "%Y-%m-%d %H")
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))

        local_dt = utc_dt.astimezone(tz)
        converted[local_dt.hour] += count

    return converted


def init_activity_db():
    """Initialize activity tracking tables"""
    with get_db() as conn:
        c = conn.cursor()
        # Hourly message counts
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_hourly (
                date TEXT,
                hour INTEGER,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (date, hour)
            )
        """
        )
        # User activity per day
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_users (
                date TEXT,
                user_id TEXT,
                username TEXT,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (date, user_id)
            )
        """
        )


def log_message_activity(timestamp, user_id, username, user_timezone=None):
    """Log a message in the activity tracker in the user's timezone."""
    # Convert to user's timezone if available
    if user_timezone:
        try:
            tz = ZoneInfo(user_timezone)
            timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        except Exception as e:
            logger.warning(f"Failed to convert timezone for user {user_id}: {e}")

    # Get date and hour in local time
    date_str = timestamp.strftime("%Y-%m-%d")
    hour = timestamp.hour

    with get_db() as conn:
        c = conn.cursor()

        # Hourly count
        c.execute(
            """
            INSERT INTO activity_hourly (date, hour, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT(date, hour)
            DO UPDATE SET message_count = message_count + 1
        """,
            (date_str, hour),
        )

        # User count
        c.execute(
            """
            INSERT INTO activity_users (date, user_id, username, message_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(date, user_id)
            DO UPDATE SET message_count = message_count + 1,
                          username = ?
        """,
            (date_str, user_id, username, username),
        )


def cleanup_old_activity():
    """Remove activity data older than 30 days"""
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM activity_hourly WHERE date < ?", (cutoff_date,))
        c.execute("DELETE FROM activity_users WHERE date < ?", (cutoff_date,))


def get_day_activity(date_str):
    """Get hourly activity for a specific day"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT hour, message_count 
            FROM activity_hourly 
            WHERE date = ?
            ORDER BY hour
        """,
            (date_str,),
        )

        # Create dict with all 24 hours (0 if no data)
        hourly_data = {hour: 0 for hour in range(24)}
        for hour, count in c.fetchall():
            hourly_data[hour] = count

        return hourly_data


def get_day_top_users(date_str, limit=5):
    """Get top users for a specific day"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT username, message_count
            FROM activity_users
            WHERE date = ?
            ORDER BY message_count DESC
            LIMIT ?
        """,
            (date_str, limit),
        )
        return c.fetchall()


def get_month_overview(ctx):
    """Get daily totals for last 30 days"""
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    start_date = now - timedelta(days=30)
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT date, SUM(message_count) as total
            FROM activity_hourly
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
        """,
            (start_date.strftime("%Y-%m-%d"),),
        )

        return c.fetchall()


def get_week_overview(ctx):
    """Get daily totals for last 7 days"""
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    start_date = now - timedelta(days=7)

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT date, SUM(message_count) as total
            FROM activity_hourly
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
        """,
            (start_date.strftime("%Y-%m-%d"),),
        )

        return c.fetchall()


# ============================================================
# VISUALIZATION FUNCTIONS
# ============================================================


def create_bar(value, max_value, width=10):
    """Create ASCII bar chart"""
    if max_value == 0:
        return "░" * width

    filled = int((value / max_value) * width)
    return "▓" * filled + "░" * (width - filled)


from zoneinfo import ZoneInfo
from datetime import datetime, timedelta


def format_day_activity(date_str, hourly_data, top_users, ctx):
    """Format daily activity as text"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = date_obj.strftime("%A, %B %d")

    total_messages = sum(hourly_data.values())
    max_hour_count = max(hourly_data.values()) if hourly_data else 0
    peak_hour = max(hourly_data.items(), key=lambda x: x[1])[0] if total_messages else 0

    lines = [f"📊 **Activity for {day_name}**", "─" * 40]

    for hour in range(24):
        count = hourly_data[hour]
        bar = create_bar(count, max_hour_count, 10)
        hour_12 = hour % 12 or 12
        am_pm = "AM" if hour < 12 else "PM"
        peak_marker = " 🔥" if hour == peak_hour and count else ""
        lines.append(f"`{hour_12:02d}:00 {am_pm}` {bar} {count:>4} msgs{peak_marker}")

    lines.append("─" * 40)
    lines.append(f"**Total:** {total_messages:,} messages")
    if total_messages:
        peak_12 = peak_hour % 12 or 12
        peak_am_pm = "AM" if peak_hour < 12 else "PM"
        lines.append(
            f"**Peak Hour:** {peak_12}:00 {peak_am_pm} ({hourly_data[peak_hour]} msgs)"
        )

    # Top users
    if top_users:
        lines.append("")
        lines.append("👥 **Top Users:**")
        for i, (username, count) in enumerate(top_users, 1):
            percentage = (count / total_messages * 100) if total_messages else 0
            lines.append(f"{i}. {username} - {count} msgs ({percentage:.1f}%)")

    return "\n".join(lines)


def format_week_overview(daily_data, ctx):
    """Format weekly overview with local timezone shift."""
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    if not daily_data:
        return "📊 **Activity - Last 7 Days**\n\nNo activity data available."

    total_messages = sum(count for _, count in daily_data)
    avg_per_day = total_messages / len(daily_data) if daily_data else 0
    max_day = max(daily_data, key=lambda x: x[1])
    max_count = max_day[1]

    lines = ["📊 **Activity - Last 7 Days**", "─" * 40]
    for date_str, count in daily_data:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if timezone:
            date_obj = date_obj.replace(tzinfo=timezone)
        day_name = date_obj.strftime("%a, %b %d")
        bar = create_bar(count, max_count, 10)
        today_marker = " (Today)" if date_str == today_str else ""
        lines.append(f"`{day_name}` {bar} {count:>4} msgs{today_marker}")

    lines.append("─" * 40)
    lines.append(f"**Total:** {total_messages:,} messages")
    lines.append(f"**Avg/Day:** {avg_per_day:.0f} msgs")
    max_date_display = datetime.strptime(max_day[0], "%Y-%m-%d").strftime("%a, %b %d")
    lines.append(f"**Most Active:** {max_date_display} ({max_day[1]:,} msgs)")

    return "\n".join(lines)


def format_month_overview(daily_data, ctx):
    """Format monthly overview with local timezone shift."""
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    if not daily_data:
        return "📊 **Activity - Last 30 Days**\n\nNo activity data available."

    total_messages = sum(count for _, count in daily_data)
    avg_per_day = total_messages / len(daily_data) if daily_data else 0
    max_day = max(daily_data, key=lambda x: x[1])
    max_count = max_day[1]

    lines = ["📊 **Activity - Last 30 Days**", "─" * 40]
    for date_str, count in daily_data:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        if timezone:
            date_obj = date_obj.replace(tzinfo=timezone)
        display_date = date_obj.strftime("%b %d")
        bar = create_bar(count, max_count, 10)
        today_marker = " (Today)" if date_str == today_str else ""
        lines.append(f"`{display_date}` {bar} {count:>4} msgs{today_marker}")

    lines.append("─" * 40)
    lines.append(f"**Total:** {total_messages:,} messages")
    lines.append(f"**Avg/Day:** {avg_per_day:.0f} msgs")
    max_date_display = datetime.strptime(max_day[0], "%Y-%m-%d").strftime("%b %d")
    lines.append(f"**Most Active:** {max_date_display} ({max_day[1]:,} msgs)")

    return "\n".join(lines)


# ============================================================
# DISCORD FUNCTIONS
# ============================================================


async def send_day_activity(ctx, date_str):
    """Send activity report for a specific day"""
    # Get hourly data from DB
    hourly_data = get_day_activity(date_str)

    # Get user's timezone
    timezone_name, _ = get_user_timezone(ctx.author.id)

    # Convert hourly data to user's timezone
    hourly_data = convert_hourly_to_timezone(hourly_data, date_str, timezone_name)

    # Get top users
    top_users = get_day_top_users(date_str, limit=5)

    # Format output
    output = format_day_activity(date_str, hourly_data, top_users, ctx)

    # Split into chunks if too long
    chunks = [output[i : i + 1900] for i in range(0, len(output), 1900)]

    # Send as embeds
    for chunk in chunks:
        embed = discord.Embed(description=chunk, color=discord.Color.blue())
        await ctx.send(embed=embed)


async def send_month_overview(ctx):
    """Send monthly overview"""
    # Get user's timezone
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    start_date = now - timedelta(days=30)

    # Pull raw daily totals
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT date, SUM(message_count) as total
            FROM activity_hourly
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
            """,
            (start_date.strftime("%Y-%m-%d"),),
        )
        daily_data = c.fetchall()

    output = format_month_overview(daily_data, ctx)

    # Split into chunks if needed
    chunks = [output[i : i + 1900] for i in range(0, len(output), 1900)]
    for chunk in chunks:
        embed = discord.Embed(description=chunk, color=discord.Color.blue())
        await ctx.send(embed=embed)


async def send_week_overview(ctx):
    """Send weekly overview"""
    # Get user's timezone
    timezone_name, _ = get_user_timezone(ctx.author.id)
    timezone = (
        ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    )
    now = datetime.now(timezone) if timezone else datetime.now()
    start_date = now - timedelta(days=7)

    # Pull raw daily totals
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT date, SUM(message_count) as total
            FROM activity_hourly
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
            """,
            (start_date.strftime("%Y-%m-%d"),),
        )
        daily_data = c.fetchall()

    # Adjust each day's hourly data for timezone if you want hourly breakdown
    # Otherwise, daily totals are fine
    output = format_week_overview(daily_data, ctx)

    # Split into chunks if needed
    chunks = [output[i : i + 1900] for i in range(0, len(output), 1900)]
    for chunk in chunks:
        embed = discord.Embed(description=chunk, color=discord.Color.blue())
        await ctx.send(embed=embed)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_user_local_date(user_id, date_input=None):
    """Return the date string (YYYY-MM-DD) in the user's timezone"""
    timezone_name, _ = get_user_timezone(user_id)
    tz = ZoneInfo(timezone_name) if timezone_name and timezone_name != "None" else None
    now = datetime.now(tz) if tz else datetime.now()

    if not date_input or date_input.lower() in ["today", "now"]:
        local_date = now
    elif date_input.lower() in ["yesterday", "yday"]:
        local_date = now - timedelta(days=1)
    else:
        # Check for day names
        day_names = {
            "monday": 0,
            "mon": 0,
            "tuesday": 1,
            "tue": 1,
            "tues": 1,
            "wednesday": 2,
            "wed": 2,
            "thursday": 3,
            "thu": 3,
            "thur": 3,
            "thurs": 3,
            "friday": 4,
            "fri": 4,
            "saturday": 5,
            "sat": 5,
            "sunday": 6,
            "sun": 6,
        }
        lower = date_input.lower().strip()
        if lower in day_names:
            target_weekday = day_names[lower]
            current_weekday = now.weekday()
            days_back = (current_weekday - target_weekday) % 7
            local_date = now - timedelta(days=days_back)
        else:
            # MM/DD or YYYY-MM-DD
            try:
                if "/" in date_input:
                    m, d = map(int, date_input.split("/"))
                    local_date = datetime(now.year, m, d)
                else:
                    local_date = datetime.strptime(date_input, "%Y-%m-%d")
            except Exception:
                local_date = now

    return local_date.strftime("%Y-%m-%d")


def parse_date_input(date_input, user_id=None):
    """Parse various date formats to YYYY-MM-DD"""
    # Get user's timezone if provided
    timezone = None
    if user_id:
        timezone_name, _ = get_user_timezone(user_id)
        if timezone_name and timezone_name != "None":
            timezone = ZoneInfo(timezone_name)

    today = datetime.now(timezone) if timezone else datetime.now()

    # Handle day names (monday, tuesday, etc.)
    day_names = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "tues": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thur": 3,
        "thurs": 3,
        "friday": 4,
        "fri": 4,
        "saturday": 5,
        "sat": 5,
        "sunday": 6,
        "sun": 6,
    }

    date_lower = date_input.lower().strip()

    # Check for day names
    if date_lower in day_names:
        target_weekday = day_names[date_lower]
        current_weekday = today.weekday()

        # Find most recent occurrence of that day
        days_back = (current_weekday - target_weekday) % 7
        if days_back == 0:
            days_back = 0  # Today if it matches

        target_date = today - timedelta(days=days_back)
        return target_date.strftime("%Y-%m-%d")

    # Check for special keywords
    if date_lower in ["today", "now"]:
        return today.strftime("%Y-%m-%d")

    if date_lower in ["yesterday", "yday"]:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Try parsing date formats like "11/4", "11-4", "2024-11-04"
    try:
        # Try MM/DD format
        if "/" in date_input:
            parts = date_input.split("/")
            if len(parts) == 2:
                month, day = int(parts[0]), int(parts[1])
                year = today.year
                target_date = datetime(year, month, day)
                return target_date.strftime("%Y-%m-%d")

        # Try YYYY-MM-DD format
        if "-" in date_input and len(date_input) >= 8:
            target_date = datetime.strptime(date_input, "%Y-%m-%d")
            return target_date.strftime("%Y-%m-%d")
    except:
        pass

    return None
