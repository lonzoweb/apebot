"""
Scheduled tasks for Discord Bot
Background tasks that run on intervals
"""

import discord
import random
import logging
import asyncio
import time  # Added for time.time() checks in the removal loop
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import tasks

# Assuming these are imported from your config or defined globally:
from config import CHANNEL_ID, TEST_CHANNEL_ID  # Assuming config imports

# Assuming these constants are available:
YOUR_GUILD_ID = 1167166210610298910  # <<< REPLACE THIS
MASOCHIST_ROLE_ID = 1167184822129664113  # Your confirmed role ID

import activity as activity_tracker
import database  # Required for role removal database calls

logger = logging.getLogger(__name__)

# Global variable to store daily quote
daily_quote_of_the_day = None

# ============================================================
# TASK SETUP
# ============================================================


def setup_tasks(bot, guild_id: int):
    """
    Initialize and start scheduled tasks.
    The main guild ID is now passed in to ensure the role removal works correctly.
    """

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
        logger.info("⏳ Activity flush task started (every 30 minutes)")

    flush_activity_frequent.start()

    # --- 3. Daily Quote Task (Hourly check) ---

    @tasks.loop(hours=1)
    async def daily_quote():
        """Send daily quotes at scheduled times (10 AM and 6 PM PT)"""
        global daily_quote_of_the_day

        # Get guild using the ID passed to setup_tasks
        guild = bot.get_guild(guild_id)
        if not guild:
            logger.warning("Bot not in the main guild for quote tasks.")
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
                quotes = await bot.loop.run_in_executor(
                    None, database.load_quotes_from_db
                )  # Corrected function call

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
            logger.error(f"Error in daily_quote task: {e}", exc_info=True)

    @daily_quote.before_loop
    async def before_daily_quote():
        """Wait for bot to be ready before starting daily quote task"""
        await bot.wait_until_ready()
        logger.info("⏳ Daily quote task started (hourly check)")

    daily_quote.start()

    # --- 4. Role Removal Task (Every 5 minutes) ---

    @tasks.loop(minutes=5.0)
    async def role_removal_loop():
        """Checks the database for users whose Masochist role should be removed."""

        guild = bot.get_guild(guild_id)  # Use the ID passed to setup_tasks
        if not guild:
            logger.warning(f"Role Removal Loop: Guild ID {guild_id} not found.")
            return

        masochist_role = guild.get_role(MASOCHIST_ROLE_ID)
        if not masochist_role:
            logger.error(f"Role Removal Loop: Role ID {MASOCHIST_ROLE_ID} not found.")
            return

        try:
            # 1. Get users whose removal time has passed (Asynchronous database operation)
            users_to_remove_ids = await bot.loop.run_in_executor(
                None, database.get_pending_role_removals
            )

            if not users_to_remove_ids:
                return

            # 2. Process Removals
            for user_id_str in users_to_remove_ids:
                user_id = int(user_id_str)
                member = guild.get_member(user_id)

                if member and masochist_role in member.roles:
                    try:
                        # Remove the role from the member
                        await member.remove_roles(
                            masochist_role,
                            reason="48 hour Masochist role duration expired.",
                        )
                        logger.info(
                            f"Removed Masochist role from {member.display_name} ({user_id})"
                        )

                        # Optional: Send a DM
                        try:
                            await member.send(
                                f"Your **{masochist_role.name}** role has expired after 2 days!"
                            )
                        except discord.Forbidden:
                            pass

                    except discord.Forbidden:
                        logger.warning(
                            f"Failed to remove role from {user_id}: Bot lacks permissions."
                        )

                    except Exception as e:
                        logger.error(
                            f"Error removing role for {user_id}: {e}", exc_info=True
                        )

                # 3. Cleanup: Remove the record from the database regardless of role removal success
                await bot.loop.run_in_executor(
                    None, database.remove_masochist_role_record, user_id_str
                )

        except Exception as e:
            logger.error(f"Error in role_removal_loop: {e}", exc_info=True)

    @role_removal_loop.before_loop
    async def before_role_removal_loop():
        await bot.wait_until_ready()
        logger.info("⏳ Role removal task started (every 5 minutes)")

    role_removal_loop.start()

    # --- End of setup_tasks ---
    return daily_quote_of_the_day


def get_daily_quote():
    """Get the current daily quote"""
    return daily_quote_of_the_day
