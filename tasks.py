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
        main_channel = bot.get_channel(CHANNEL_ID)
        test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None
        if not main_channel and not test_channel:
            logger.warning("No valid channels found for daily quote.")
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
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="🕊️ Quote")
                    for ch in [main_channel, test_channel]:
                        if ch:
                            await ch.send(embed=embed)
                    logger.info("✅ Sent 10AM quote")

            # Evening (6 PM PT)
            elif current_time == "18:00" and daily_quote_of_the_day:
                embed = discord.Embed(
                    description=f"📜 {daily_quote_of_the_day}",
                    color=discord.Color.dark_gold()
                )
                embed.set_footer(text="🌇 Quote")
                for ch in [main_channel, test_channel]:
                    if ch:
                        await ch.send(embed=embed)
                logger.info("✅ Sent 6PM quote")
        except Exception as e:
            logger.error(f"Error in daily_quote task: {e}")

    # activity cleanup

    async def cleanup_activity_task():
        """Clean up activity data older than 30 days (run daily)"""
        activity.cleanup_old_activity()

    @daily_quote.before_loop
    async def before_daily_quote():
        """Wait for bot to be ready before starting daily quote task"""
        await bot.wait_until_ready()
        logger.info("⏳ Daily quote task started")

    # Start the task
    daily_quote.start()
    
    return daily_quote_of_the_day

def get_daily_quote():
    """Get the current daily quote"""
    return daily_quote_of_the_day
