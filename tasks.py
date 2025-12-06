"""
Scheduled tasks for Discord Bot
Background tasks that run on intervals
"""

import discord
import random
import logging
import asyncio  # New import for run_in_executor logic
from datetime import datetime
import activity as activity_tracker
from zoneinfo import ZoneInfo
from discord.ext import tasks
from config import CHANNEL_ID, TEST_CHANNEL_ID
from database import load_quotes_from_db

logger = logging.getLogger(__name__)

# Global variable to store daily quote
daily_quote_of_the_day = None

# ============================================================
# TASK SETUP
# ============================================================


def setup_tasks(bot):
    """Initialize and start scheduled tasks"""

    # --- 1. Daily Activity Cleanup Task (24 hours) ---

    @tasks.loop(hours=24)
    async def cleanup_activity_daily():
        """Clean up activity data older than 30 days once per day"""
        try:
            # CRITICAL FIX: Run blocking I/O in a separate thread
            await bot.loop.run_in_executor(
                None, activity_tracker.cleanup_old_activity, 30
            )
        except Exception as e:
            logger.error(f"Error in activity cleanup: {e}", exc_info=True)

    @cleanup_activity_daily.before_loop
    async def before_cleanup_activity():
        await bot.wait_until_ready()
        logger.info("⏳ Activity cleanup task started (every 24 hours)")

    cleanup_activity_daily.start()

    # --- 2. Activity Flushing Task (30 minutes) ---

    @tasks.loop(minutes=30)
    async def flush_activity_frequent():
        """Flush batched activity data to database (now in a separate thread)"""
        try:
            # CRITICAL FIX: Run blocking I/O in a separate thread
            await bot.loop.run_in_executor(None, activity_tracker.flush_activity_to_db)
        except Exception as e:
            logger.error(f"Error in activity flush: {e}", exc_info=True)

    @flush_activity_frequent.before_loop
    async def before_flush_activity():
        await bot.wait_until_ready()
        # Log message updated to reflect 30-minute loop
        logger.info("⏳ Activity flush task started (every 30 minutes)")

    flush_activity_frequent.start()

    # --- 3. Daily Quote Task (Hourly check) ---

    @tasks.loop(hours=1)
    async def daily_quote():
        """Send daily quotes at scheduled times (10 AM and 6 PM PT)"""
        global daily_quote_of_the_day

        # Get guild (your server)
        guild = bot.guilds[0] if bot.guilds else None
        if not guild:
            logger.warning("Bot not in any guilds")
            return

        # Find channels by name (NOTE: Fetching by ID is faster if available)
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

            # Morning (10 AM PT) - Check if it's the 10 o'clock hour
            if now_pt.hour == 10 and daily_quote_of_the_day is None:

                # CRITICAL FIX: Run blocking quote loading in a separate thread
                quotes = await bot.loop.run_in_executor(None, load_quotes_from_db)

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

            # Evening (6 PM PT) - Check if it's the 18 o'clock hour
            elif now_pt.hour == 18 and daily_quote_of_the_day is not None:
                embed = discord.Embed(
                    description=f"📜 {daily_quote_of_the_day}",
                    color=discord.Color.dark_gold(),
                )
                embed.set_footer(text="🌇 Quote")
                for ch in target_channels:
                    await ch.send(embed=embed)
                logger.info(f"✅ Sent 6PM quote to {len(target_channels)} channel(s)")

            # Reset the quote after 7 PM (19:00) so a new one is picked tomorrow morning
            if now_pt.hour == 19:
                daily_quote_of_the_day = None

        except Exception as e:
            logger.error(f"Error in daily_quote task: {e}")

    @daily_quote.before_loop
    async def before_daily_quote():
        """Wait for bot to be ready before starting daily quote task"""
        await bot.wait_until_ready()
        logger.info("⏳ Daily quote task started (hourly check)")

    # Start the task
    daily_quote.start()

    return daily_quote_of_the_day


def get_daily_quote():
    """Get the current daily quote"""
    return daily_quote_of_the_day
