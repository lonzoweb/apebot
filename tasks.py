"""
Scheduled tasks for Discord Bot
Background tasks that run on intervals
"""

import discord
import random
import logging
import activity
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import tasks
from config import CHANNEL_ID, TEST_CHANNEL_ID
from database import load_quotes_from_db

logger = logging.getLogger(__name__)

# Global variable to store daily quote
daily_quote_of_the_day = None

# ============================================================
# DAILY QUOTE TASK
# ============================================================


def setup_tasks(bot):
    """Initialize and start scheduled tasks"""

    @tasks.loop(minutes=1)
    async def daily_quote():
        """Send daily quotes at scheduled times (10 AM and 6 PM PT)"""
        global daily_quote_of_the_day

        # Get guild (your server)
        guild = bot.guilds[0] if bot.guilds else None
        if not guild:
            logger.warning("Bot not in any guilds")
            return

        # Find channels by name
        forum_channel = discord.utils.get(guild.text_channels, name="forum")
        emperor_channel = discord.utils.get(guild.text_channels, name="emperor")

        # Collect valid channels
        target_channels = [ch for ch in [forum_channel, emperor_channel] if ch]

        if not target_channels:
            logger.warning(
                "No valid channels found for daily quote (forum or emperor)."
            )
            return

        try:
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            current_time = now_pt.strftime("%H:%M")

            # Morning (10 AM PT)
            if current_time == "10:00":
                quotes = load_quotes_from_db()
                if quotes:
                    daily_quote_of_the_day = random.choice(quotes)
                    embed = discord.Embed(
                        title="🌅 Blessings to Apeiron",
                        description=f"📜 {daily_quote_of_the_day}",
                        color=discord.Color.gold(),
                    )
                    embed.set_footer(text="🕊️ Quote")
                    for ch in target_channels:
                        await ch.send(embed=embed)
                    logger.info(
                        f"✅ Sent 10AM quote to {len(target_channels)} channel(s)"
                    )

            # Evening (6 PM PT)
            elif current_time == "18:00" and daily_quote_of_the_day:
                embed = discord.Embed(
                    description=f"📜 {daily_quote_of_the_day}",
                    color=discord.Color.dark_gold(),
                )
                embed.set_footer(text="🌇 Quote")
                for ch in target_channels:
                    await ch.send(embed=embed)
                logger.info(f"✅ Sent 6PM quote to {len(target_channels)} channel(s)")
        except Exception as e:
            logger.error(f"Error in daily_quote task: {e}")

    @daily_quote.before_loop
    async def before_daily_quote():
        """Wait for bot to be ready before starting daily quote task"""
        await bot.wait_until_ready()
        logger.info("⏳ Daily quote task started")

    # Start the task
    daily_quote.start()

    return daily_quote_of_the_day

    # activity cleanup

    async def cleanup_activity_task():
        """Clean up activity data older than 30 days (run daily)"""
        activity.cleanup_old_activity()


def get_daily_quote():
    """Get the current daily quote"""
    return daily_quote_of_the_day
