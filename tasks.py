"""
Scheduled tasks for Discord Bot
Background tasks that run on intervals
"""

import discord
import random
import logging
import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import tasks

from config import CHANNEL_ID, TEST_CHANNEL_ID

# Constants
YOUR_GUILD_ID = 1167166210610298910
MASOCHIST_ROLE_ID = 1167184822129664113

import activity as activity_tracker
import database

logger = logging.getLogger(__name__)

# Global variable to store daily quote
daily_quote_of_the_day = None

# ============================================================
# TASK SETUP
# ============================================================


def setup_tasks(bot, guild_id: int):
    """
    Initialize and start scheduled tasks.
    """

    # --- 1. Daily Activity Cleanup Task (24 hours) ---
    @tasks.loop(hours=24)
    async def cleanup_activity_daily():
        """Clean up activity data older than 30 days once per day"""
        try:
            await activity_tracker.cleanup_old_activity(30)
        except Exception as e:
            logger.error(f"Error in activity cleanup: {e}", exc_info=True)

    @cleanup_activity_daily.before_loop
    async def before_cleanup_activity():
        await bot.wait_until_ready()
        logger.info("⏳ Activity cleanup task started (every 24 hours)")

    cleanup_activity_daily.start()

    # --- 2. Activity Flushing Task (5 minutes) ---
    @tasks.loop(minutes=5)
    async def flush_activity_frequent():
        """Flush batched activity data to database"""
        try:
            await activity_tracker.flush_activity_to_db()
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
        guild = bot.get_guild(guild_id)
        if not guild:
            return

        forum_channel = discord.utils.get(guild.text_channels, name="forum")
        emperor_channel = discord.utils.get(guild.text_channels, name="emperor")
        target_channels = [ch for ch in [forum_channel, emperor_channel] if ch]

        if not target_channels:
            return

        try:
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))

            if now_pt.hour == 10 and daily_quote_of_the_day is None:
                quotes = await database.load_quotes_from_db()
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

            elif now_pt.hour == 18 and daily_quote_of_the_day is not None:
                embed = discord.Embed(
                    description=f"📜 {daily_quote_of_the_day}",
                    color=discord.Color.dark_gold(),
                )
                embed.set_footer(text="🌇 Quote")
                for ch in target_channels:
                    await ch.send(embed=embed)

            if now_pt.hour == 19:
                daily_quote_of_the_day = None

        except Exception as e:
            logger.error(f"Error in daily_quote task: {e}", exc_info=True)

    @daily_quote.before_loop
    async def before_daily_quote():
        await bot.wait_until_ready()
        logger.info("⏳ Daily quote task started (hourly check)")

    daily_quote.start()

    async def handle_curse_expirations():
        """Helper to process expired curses"""
        try:
            expired_curses = await database.get_all_expired_effects()
            for user_id, effect_name in expired_curses:
                await database.remove_active_effect(int(user_id), effect_name)
                logger.info(f"🧹 Logic: Automatically removed expired {effect_name} from {user_id}")
        except Exception as e:
            logger.error(f"Error in curse cleanup: {e}")

    async def handle_role_expirations(guild):
        """Helper to process expired roles"""
        masochist_role = guild.get_role(MASOCHIST_ROLE_ID)
        if not masochist_role:
            return

        try:
            users_to_remove_ids = await database.get_pending_role_removals()
            for user_id_str in users_to_remove_ids:
                user_id = int(user_id_str)
                member = guild.get_member(user_id)

                if member and masochist_role in member.roles:
                    try:
                        await member.remove_roles(masochist_role, reason="Masochist role expired.")
                        logger.info(f"Removed Masochist role from {member.display_name}")
                        try:
                            await member.send(f"Your **{masochist_role.name}** role has expired!")
                        except discord.Forbidden:
                            pass
                    except Exception as e:
                        logger.error(f"Error removing role for {user_id}: {e}")

                await database.remove_masochist_role_record(user_id_str)
        except Exception as e:
            logger.error(f"Error in role removal: {e}")

    # --- 4. Unified Expiration Task (Roles & Item Curses) ---
    @tasks.loop(minutes=5.0)
    async def unified_cleanup_loop():
        """Checks for expired Masochist roles AND Item Curses/Mutes."""
        guild = bot.get_guild(guild_id)
        if not guild:
            return

        await handle_curse_expirations()
        await handle_role_expirations(guild)

    @unified_cleanup_loop.before_loop
    async def before_unified_cleanup_loop():
        await bot.wait_until_ready()
        logger.info("⏳ Unified cleanup task started (Roles & Item Curses)")

    unified_cleanup_loop.start()

    return daily_quote_of_the_day


def get_daily_quote():
    return daily_quote_of_the_day
