"""
Scheduled tasks for Discord Bot
Background tasks that run on intervals
"""

import discord
import random
import logging
import asyncio
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo
from discord.ext import tasks

from config import CHANNEL_ID, TEST_CHANNEL_ID, GUILD_ID

# Constants
MASOCHIST_ROLE_ID = 1167184822129664113

import activity as activity_tracker
import database

logger = logging.getLogger(__name__)

# ============================================================
# HELPERS — persist quote state to DB so reboots don't lose it
# ============================================================

QUOTE_DATE_KEY    = "quote_date"         # ISO date string of last 10am fire
QUOTE_TEXT_KEY    = "daily_quote_text"   # The actual quote text
PENDING_Q_KEY     = "pending_quotes"     # JSON list of candidates
TOMORROW_Q_KEY    = "tomorrow_quote"     # Admin-picked quote
CANDIDATES_SENT_KEY = "candidates_sent_date"  # ISO date string of last candidate send
PV_MSG_ID_KEY     = "pv_message_id"      # ID of the current candidate voting message


async def _get_today_str() -> str:
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


async def _load_quote_state():
    """Load today's persisted quote state from DB. Returns (quote_str_or_None, date_str_or_None)."""
    quote_text = await database.get_setting(QUOTE_TEXT_KEY)
    quote_date = await database.get_setting(QUOTE_DATE_KEY)
    return quote_text, quote_date


async def _save_quote_state(quote_text: str):
    today = await _get_today_str()
    await database.set_setting(QUOTE_TEXT_KEY, quote_text)
    await database.set_setting(QUOTE_DATE_KEY, today)


async def _get_pending_quotes():
    import json
    raw = await database.get_setting(PENDING_Q_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


async def _set_pending_quotes(candidates: list):
    import json
    await database.set_setting(PENDING_Q_KEY, json.dumps(candidates))


async def _get_tomorrow_quote():
    return await database.get_setting(TOMORROW_Q_KEY)


async def _set_tomorrow_quote(quote: str | None):
    await database.set_setting(TOMORROW_Q_KEY, quote or "")


async def _get_candidates_sent_date():
    return await database.get_setting(CANDIDATES_SENT_KEY)


async def _set_candidates_sent_date(date_str: str):
    await database.set_setting(CANDIDATES_SENT_KEY, date_str)


# Public accessors for quotes_cog
async def get_daily_quote_async():
    quote_text, quote_date = await _load_quote_state()
    today = await _get_today_str()
    if quote_date == today and quote_text:
        return quote_text
    return None


# Legacy sync accessor (kept for compatibility — returns None if called before event loop runs)
_cached_quote = None
def get_daily_quote():
    return _cached_quote


# ============================================================
# CORE QUOTE SEND LOGIC (called by task + startup catch-up)
# ============================================================

async def _send_morning_quote(bot, guild, target_channels):
    """Pick and send the 10am quote. Returns the quote string."""
    global _cached_quote
    quotes = await database.load_quotes_from_db()
    if not quotes:
        return None

    # Use admin-picked quote if set, otherwise random
    tomorrow_q = await _get_tomorrow_quote()
    if tomorrow_q and tomorrow_q in quotes:
        quote = tomorrow_q
    else:
        quote = random.choice(quotes)

    embed = discord.Embed(
        title="🌅 Blessings to Apeiron",
        description=f"📜 {quote}",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="🕊️ Quote")
    for ch in target_channels:
        await ch.send(embed=embed)

    await _save_quote_state(quote)
    await _set_tomorrow_quote(None)   # clear for next day
    _cached_quote = quote
    logger.info(f"✅ Morning quote sent: {quote[:60]}...")
    return quote


async def _send_evening_quote(bot, guild, target_channels, emperor_channel, quote):
    """Repost the quote at 6pm, then send candidates to #emperor."""
    embed = discord.Embed(
        description=f"📜 {quote}",
        color=discord.Color.dark_gold(),
    )
    embed.set_footer(text="🌇 Quote")
    for ch in target_channels:
        await ch.send(embed=embed)

    # Send 3 candidates to #emperor
    if emperor_channel:
        await _send_candidates(bot, emperor_channel, quote)


async def _send_candidates(bot, emperor_channel, today_quote):
    """Picks 3 random candidate quotes and sends them to #emperor."""
    today = await _get_today_str()
    last_sent = await _get_candidates_sent_date()
    if last_sent == today:
        logger.info("Candidates already sent today, skipping.")
        return

    try:
        all_quotes = await database.load_quotes_from_db()
        pool = [q for q in all_quotes if q != today_quote]
        if not pool:
            return

        candidates = random.sample(pool, min(3, len(pool)))
        await _set_pending_quotes(candidates)
        await _set_candidates_sent_date(today)

        # Also update bot attributes for the cog
        bot.pending_quotes = candidates
        bot.tomorrow_quote = None

        lines = "\n\n".join(f"**{i+1}.** {q}" for i, q in enumerate(candidates))
        pick_embed = discord.Embed(
            title="📋 Tomorrow's Quote — Choose One",
            description=lines,
            color=discord.Color.blurple(),
        )
        pick_embed.set_footer(text="React with 1, 2, or 3 to pick tomorrow's quote · .pv revote to regenerate")
        msg = await emperor_channel.send(embed=pick_embed)
        
        # Add reactions for easy voting
        NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]
        for emoji in NUMBER_EMOJIS[:len(candidates)]:
            await msg.add_reaction(emoji)
            
        await database.set_setting(PV_MSG_ID_KEY, str(msg.id))
        logger.info("✅ Quote candidates sent to #emperor with reactions.")
    except Exception as e:
        logger.error(f"Error sending quote candidates: {e}", exc_info=True)


# ============================================================
# TASK SETUP
# ============================================================


def setup_tasks(bot, guild_id: int):
    """Initialize and start scheduled tasks."""

    # --- 1. Daily Activity Cleanup Task (24 hours) ---
    @tasks.loop(hours=24)
    async def cleanup_activity_daily():
        try:
            await activity_tracker.cleanup_old_activity(30)
        except Exception as e:
            logger.error(f"Error in activity cleanup: {e}", exc_info=True)

    @cleanup_activity_daily.before_loop
    async def before_cleanup_activity():
        await bot.wait_until_ready()

    cleanup_activity_daily.start()

    # --- 2. Activity Flushing Task (5 minutes) ---
    @tasks.loop(minutes=5)
    async def flush_activity_frequent():
        try:
            await activity_tracker.flush_activity_to_db()
        except Exception as e:
            logger.error(f"Error in activity flush: {e}", exc_info=True)

    @flush_activity_frequent.before_loop
    async def before_flush_activity():
        await bot.wait_until_ready()

    flush_activity_frequent.start()

    # --- 3. Daily Quote Task ---
    @tasks.loop(minutes=1)
    async def daily_quote():
        """
        Runs every minute. Fires quote events at exact times.
        Uses DB-persisted state so reboots don't break the schedule.

        Schedule (America/Los_Angeles):
          10:00  — pick & post morning quote to #forum + #emperor
          18:00  — repost evening quote + send 3 candidates to #emperor
          19:00  — reset state for next day
        """
        global _cached_quote

        try:
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            today_str = now_pt.date().isoformat()
            hour, minute = now_pt.hour, now_pt.minute

            guild = bot.get_guild(guild_id)
            if not guild:
                return

            forum_channel    = discord.utils.get(guild.text_channels, name="forum")
            emperor_channel  = discord.utils.get(guild.text_channels, name="emperor")
            target_channels  = [ch for ch in [forum_channel, emperor_channel] if ch]

            if not target_channels:
                return

            quote_text, quote_date = await _load_quote_state()
            today_quote_exists = (quote_date == today_str and quote_text)

            # ── 10:00 AM — morning quote ──────────────────────────────
            if hour == 10 and minute == 0 and not today_quote_exists:
                quote = await _send_morning_quote(bot, guild, target_channels)
                _cached_quote = quote

            # ── 6:00 PM — evening repost + candidates ─────────────────
            elif hour == 18 and minute == 0:
                # Re-fetch in case we rebooted between 10am and 6pm
                quote_text, quote_date = await _load_quote_state()
                if quote_text and quote_date == today_str:
                    await _send_evening_quote(
                        bot, guild, target_channels, emperor_channel, quote_text
                    )
                else:
                    logger.warning("6pm quote: no morning quote found in DB for today, skipping.")

            # ── 7:00 PM — reset for next day ──────────────────────────
            elif hour == 19 and minute == 0:
                _cached_quote = None
                bot.pending_quotes = []
                bot.tomorrow_quote = None
                # Clear DB state so morning fires fresh tomorrow
                await database.set_setting(QUOTE_DATE_KEY, "")
                await database.set_setting(QUOTE_TEXT_KEY, "")

        except Exception as e:
            logger.error(f"Error in daily_quote task: {e}", exc_info=True)

    @daily_quote.before_loop
    async def before_daily_quote():
        await bot.wait_until_ready()

        # ── STARTUP CATCH-UP ─────────────────────────────────────────
        # If the bot rebooted during the day, check what we missed.
        try:
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            today_str = now_pt.date().isoformat()
            hour = now_pt.hour

            guild = bot.get_guild(guild_id)
            if not guild:
                return

            forum_channel   = discord.utils.get(guild.text_channels, name="forum")
            emperor_channel = discord.utils.get(guild.text_channels, name="emperor")
            target_channels = [ch for ch in [forum_channel, emperor_channel] if ch]

            quote_text, quote_date = await _load_quote_state()
            today_quote_exists = (quote_date == today_str and quote_text)

            # Rebooted between 10am–6pm: morning quote already sent, nothing to catch up
            if 10 <= hour < 18 and today_quote_exists:
                global _cached_quote
                _cached_quote = quote_text
                bot.pending_quotes = await _get_pending_quotes()
                bot.tomorrow_quote = await _get_tomorrow_quote() or None
                logger.info(f"✅ Quote state restored from DB: '{quote_text[:50]}...'")

            # Rebooted between 10am–6pm but no morning quote at all — send it now
            elif 10 <= hour < 18 and not today_quote_exists and target_channels:
                logger.info("Catch-up: missed 10am quote, sending now.")
                quote = await _send_morning_quote(bot, guild, target_channels)
                _cached_quote = quote

            # Rebooted after 6pm: check if candidates were sent already
            elif hour >= 18 and today_quote_exists:
                _cached_quote = quote_text
                bot.pending_quotes = await _get_pending_quotes()
                bot.tomorrow_quote = await _get_tomorrow_quote() or None

                last_sent = await _get_candidates_sent_date()
                if last_sent != today_str and emperor_channel:
                    logger.info("Catch-up: missed 6pm candidate send, sending now.")
                    await _send_evening_quote(
                        bot, guild, target_channels, emperor_channel, quote_text
                    )

            # Rebooted after 6pm but no morning quote: pick + send both morning style
            elif hour >= 18 and not today_quote_exists and target_channels:
                logger.info("Catch-up: missed entire day — sending quote and candidates now.")
                quote = await _send_morning_quote(bot, guild, target_channels)
                _cached_quote = quote
                if quote and emperor_channel:
                    await _send_candidates(bot, emperor_channel, quote)

        except Exception as e:
            logger.error(f"Startup catch-up error: {e}", exc_info=True)

        logger.info("⏳ Daily quote task started (every minute, exact-time triggers)")

    daily_quote.start()

    MUZZLE_EFFECTS = {"muzzle", "uwu"}

    async def handle_curse_expirations():
        from main import remove_muzzle_role
        try:
            expired_curses = await database.get_all_expired_effects()
            guild = bot.get_guild(guild_id)
            for user_id, effect_name in expired_curses:
                await database.remove_active_effect(int(user_id), effect_name)
                # If the expired effect held the hexed role, strip it now
                if effect_name in MUZZLE_EFFECTS and guild:
                    # Only remove the role if the user has no OTHER active muzzle-type effects
                    remaining = await database.get_all_active_effects(int(user_id))
                    still_muzzled = any(e[0] in MUZZLE_EFFECTS for e in remaining)
                    if not still_muzzled:
                        member = guild.get_member(int(user_id))
                        if member:
                            await remove_muzzle_role(member)
                            logger.info(f"🔓 Hexed role removed from {member.display_name} (effect '{effect_name}' expired)")
        except Exception as e:
            logger.error(f"Error in curse cleanup: {e}")

    async def handle_role_expirations(guild):
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
        guild = bot.get_guild(guild_id)
        if not guild:
            return
        await handle_curse_expirations()
        await handle_role_expirations(guild)

    @unified_cleanup_loop.before_loop
    async def before_unified_cleanup_loop():
        await bot.wait_until_ready()

    unified_cleanup_loop.start()

    # --- 5. Daily Wealth Tax (24 hours) ---
    @tasks.loop(hours=24)
    async def wealth_tax_loop():
        try:
            await database.apply_wealth_tax(0.10, 1000)
            logger.info("💸 Wealth tax applied.")
        except Exception as e:
            logger.error(f"Error in wealth tax task: {e}", exc_info=True)

    @wealth_tax_loop.before_loop
    async def before_wealth_tax():
        await bot.wait_until_ready()

    wealth_tax_loop.start()
