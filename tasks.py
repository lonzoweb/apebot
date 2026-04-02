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

# Automated Quote Drops (from quote_drops table)
QUOTE_DROPS_ENABLED_KEY = "quote_drops_enabled"
QUOTE_DROPS_INTERVAL_KEY = "quote_drops_interval_hours"
LAST_QUOTE_DROP_TIME_KEY = "last_quote_drop_time"

# Daily Quote schedule keys (configurable from dashboard)
QUOTE_MORNING_HOUR_KEY = "quote_morning_hour"    # default 10
QUOTE_EVENING_HOUR_KEY = "quote_evening_hour"    # default 18

# Numerology keys
NUMEROLOGY_MORNING_HOUR_KEY  = "numerology_morning_hour"   # default 7 (7am)
NUMEROLOGY_MORNING_MIN_KEY   = "numerology_morning_min"    # default 0
NUMEROLOGY_EVENING_HOUR_KEY  = "numerology_evening_hour"   # default 22 (10pm)
NUMEROLOGY_EVENING_MIN_KEY   = "numerology_evening_min"    # default 0
NUMEROLOGY_CHANNEL_KEY       = "numerology_channel_id"
NUMEROLOGY_TODAY_DATE_KEY    = "numerology_today_date"     # ISO date of last morning post
NUMEROLOGY_TOMORROW_DATE_KEY = "numerology_tomorrow_date"  # ISO date of last evening preview

# Bulletin & Trial keys
BULLETIN_CHANNEL_KEY = "bulletin_channel_id"
WEEKLY_PURGE_ENABLED_KEY = "weekly_purge_enabled"
DAILY_TC_TIME_KEY = "daily_tc_time"
DAILY_TC_DATE_KEY = "daily_tc_last_date"
from config import MOD_CHANNEL_ID


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

def _normalize_quote(text: str) -> str:
    """
    Cleans up a quote by replacing internal newlines/tabs with spaces
    and collapsing multiple spaces into one. This prevents Discord 
    from splitting words mid-line due to hard-coded newlines.
    """
    if not text:
        return ""
    # Replace newlines, carriage returns, and tabs with spaces
    cleaned = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Collapse multiple spaces and strip
    return " ".join(cleaned.split()).strip()


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

    # Normalize to prevent word splitting
    quote = _normalize_quote(quote)

    embed = discord.Embed(
        title="🌅 Blessings to Apeiron",
        description=f"📜 {quote}",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="🕊️ Quote")
    # Post to bulletin if configured
    bulletin_id = await database.get_setting(BULLETIN_CHANNEL_KEY, "")
    if bulletin_id:
        bulletin_ch = guild.get_channel(int(bulletin_id))
        if bulletin_ch:
            await bulletin_ch.send(embed=embed)

    for ch in target_channels:
        await ch.send(embed=embed)

    await _save_quote_state(quote)
    await _set_tomorrow_quote(None)   # clear for next day
    _cached_quote = quote
    logger.info(f"✅ Morning quote sent: {quote[:60]}...")
    return quote


async def _send_evening_quote(bot, guild, target_channels, emperor_channel, quote):
    """Repost the quote at 6pm, then send candidates to #emperor."""
    # Normalize to prevent word splitting
    quote = _normalize_quote(quote)

    embed = discord.Embed(
        description=f"📜 {quote}",
        color=discord.Color.dark_gold(),
    )
    embed.set_footer(text="🌇 Quote")
    # Post to bulletin if configured
    bulletin_id = await database.get_setting(BULLETIN_CHANNEL_KEY, "")
    if bulletin_id:
        bulletin_ch = guild.get_channel(int(bulletin_id))
        if bulletin_ch:
            _embed = discord.Embed(description=f"📜 {quote}", color=discord.Color.dark_gold())
            _embed.set_footer(text="🌇 Evening Quote")
            await bulletin_ch.send(embed=_embed)

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

            from database import get_channel_assigns
            assigns = await database.get_channel_assigns()
            main_ch_id = assigns.get("main")
            
            forum_channel    = discord.utils.get(guild.text_channels, name="forum")
            emperor_channel  = discord.utils.get(guild.text_channels, name="emperor")
            target_channels  = [ch for ch in [forum_channel, emperor_channel] if ch]
            
            if main_ch_id:
                main_ch = guild.get_channel(int(main_ch_id))
                if main_ch and main_ch not in target_channels:
                    target_channels.append(main_ch)

            if not target_channels:
                return

            quote_text, quote_date = await _load_quote_state()
            today_quote_exists = (quote_date == today_str and quote_text)

            # Read configurable hours (defaults: 10am morning, 6pm evening)
            q_morning = int(await database.get_setting(QUOTE_MORNING_HOUR_KEY, "10"))
            q_evening = int(await database.get_setting(QUOTE_EVENING_HOUR_KEY, "18"))

            # ── Morning quote ──────────────────────────────────────────
            if hour == q_morning and minute == 0 and not today_quote_exists:
                quote = await _send_morning_quote(bot, guild, target_channels)
                _cached_quote = quote

            # ── Evening repost + candidates ────────────────────────────
            elif hour == q_evening and minute == 0:
                # Re-fetch in case we rebooted between morning and evening
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

            from database import get_channel_assigns
            assigns = await database.get_channel_assigns()
            main_ch_id = assigns.get("main")
            
            forum_channel   = discord.utils.get(guild.text_channels, name="forum")
            emperor_channel = discord.utils.get(guild.text_channels, name="emperor")
            target_channels = [ch for ch in [forum_channel, emperor_channel] if ch]
            
            if main_ch_id:
                main_ch = guild.get_channel(int(main_ch_id))
                if main_ch and main_ch not in target_channels:
                    target_channels.append(main_ch)

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

    # --- Numerology Task ---
    async def _send_numerology_reading(bot, guild, target_date, label: str):
        """Send the numerology reading for target_date to the configured channel."""
        import numerology as num_engine

        channel_id_str = await database.get_setting(NUMEROLOGY_CHANNEL_KEY, "")
        if not channel_id_str:
            channel = discord.utils.get(guild.text_channels, name="forum")
            if not channel:
                logger.warning("Numerology: no channel configured and no #forum found, skipping.")
                return
        else:
            channel = guild.get_channel(int(channel_id_str))
            if not channel:
                logger.warning(f"Numerology: channel {channel_id_str} not found, skipping.")
                return

        try:
            embed = await num_engine.get_embed(target_date, database, label=label)
            await channel.send(embed=embed)
            
            # Also post to "main" if different from "channel"
            from database import get_channel_assigns
            assigns = await database.get_channel_assigns()
            main_ch_id = assigns.get("main")
            if main_ch_id and int(main_ch_id) != channel.id:
                main_ch = guild.get_channel(int(main_ch_id))
                if main_ch:
                    await main_ch.send(embed=embed)
            
            # Post to bulletin if configured
            bulletin_id = await database.get_setting(BULLETIN_CHANNEL_KEY, "")
            if bulletin_id:
                bulletin_ch = guild.get_channel(int(bulletin_id))
                if bulletin_ch:
                    await bulletin_ch.send(embed=embed)
            
            logger.info(f"✅ Numerology embed sent for {target_date} ({label})")
        except Exception as e:
            logger.error(f"Error sending numerology reading: {e}", exc_info=True)

    @tasks.loop(minutes=1)
    async def daily_numerology():
        """
        Runs every minute. Fires numerology posts at configurable times.
        Schedule (America/Los_Angeles):
          [morning_hour]:00  — post today's reading
          [evening_hour]:00  — post tomorrow's preview
        """
        try:
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            today_str = now_pt.date().isoformat()
            hour, minute = now_pt.hour, now_pt.minute

            guild = bot.get_guild(guild_id)
            if not guild:
                return

            morning_hour = int(await database.get_setting(NUMEROLOGY_MORNING_HOUR_KEY, "7"))
            evening_hour = int(await database.get_setting(NUMEROLOGY_EVENING_HOUR_KEY, "22"))

            # ── Morning: today's reading ────────────────────────────────────
            if hour == morning_hour and minute == 0:
                already_sent = await database.get_setting(NUMEROLOGY_TODAY_DATE_KEY, "")
                if already_sent != today_str:
                    from datetime import date as _date
                    await _send_numerology_reading(bot, guild, now_pt.date(), "Daily Numerology Reading 🌅")
                    await database.set_setting(NUMEROLOGY_TODAY_DATE_KEY, today_str)

            # ── Evening: tomorrow's preview ─────────────────────────────────
            elif hour == evening_hour and minute == 0:
                already_sent = await database.get_setting(NUMEROLOGY_TOMORROW_DATE_KEY, "")
                if already_sent != today_str:
                    from datetime import date as _date, timedelta as _td
                    tomorrow = now_pt.date() + _td(days=1)
                    await _send_numerology_reading(bot, guild, tomorrow, "Tomorrow's Numerology Preview 🌙")
                    await database.set_setting(NUMEROLOGY_TOMORROW_DATE_KEY, today_str)

        except Exception as e:
            logger.error(f"Error in daily_numerology task: {e}", exc_info=True)

    @daily_numerology.before_loop
    async def before_daily_numerology():
        await bot.wait_until_ready()

        # ── STARTUP CATCH-UP ─────────────────────────────────────────
        try:
            import numerology as num_engine
            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            today_str = now_pt.date().isoformat()
            hour = now_pt.hour

            guild = bot.get_guild(guild_id)
            if not guild:
                return

            morning_hour = int(await database.get_setting(NUMEROLOGY_MORNING_HOUR_KEY, "7"))
            evening_hour = int(await database.get_setting(NUMEROLOGY_EVENING_HOUR_KEY, "22"))

            already_today = await database.get_setting(NUMEROLOGY_TODAY_DATE_KEY, "")
            already_tomorrow = await database.get_setting(NUMEROLOGY_TOMORROW_DATE_KEY, "")

            # Rebooted between morning and evening: check if morning was missed
            if morning_hour <= hour < evening_hour and already_today != today_str:
                logger.info("Numerology catch-up: missed morning reading, sending now.")
                await _send_numerology_reading(bot, guild, now_pt.date(), "Daily Numerology Reading 🌅")
                await database.set_setting(NUMEROLOGY_TODAY_DATE_KEY, today_str)

            # Rebooted after evening: check if evening preview was missed
            elif hour >= evening_hour and already_tomorrow != today_str:
                from datetime import timedelta as _td
                tomorrow = now_pt.date() + _td(days=1)
                logger.info("Numerology catch-up: missed evening preview, sending now.")
                await _send_numerology_reading(bot, guild, tomorrow, "Tomorrow's Numerology Preview 🌙")
                await database.set_setting(NUMEROLOGY_TOMORROW_DATE_KEY, today_str)

        except Exception as e:
            logger.error(f"Numerology startup catch-up error: {e}", exc_info=True)

        logger.info("⏳ Daily numerology task started (every minute, exact-time triggers)")

    daily_numerology.start()

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

    async def handle_trial_expirations(guild):
        try:
            active_trials = await database.get_active_trials()
            now = time.time()
            admin_log_ch = guild.get_channel(int(MOD_CHANNEL_ID))
            if not admin_log_ch:
                return

            for user_id, guild_id, start_time, end_time, message_id in active_trials:
                if now >= end_time and not message_id:
                    # Trial expired, send decision embed to admin log
                    target_member = guild.get_member(int(user_id))
                    mention = target_member.mention if target_member else f"User `{user_id}`"
                    
                    embed = discord.Embed(
                        title="⚖️ Trial Expiration: Decision Required",
                        description=f"The 4-day trial for {mention} has expired.\n\nPlease select an action below:",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Start Time", value=f"<t:{int(start_time)}:F>", inline=True)
                    embed.add_field(name="End Time", value=f"<t:{int(end_time)}:F>", inline=True)
                    embed.set_footer(text="🎓 Graduate | ⏳ Extend (4d) | 🥾 Kick")
                    
                    msg = await admin_log_ch.send(embed=embed)
                    await msg.add_reaction("🎓")
                    await msg.add_reaction("⏳")
                    await msg.add_reaction("🥾")
                    
                    await database.update_trial_message(user_id, guild_id, str(msg.id))
                    logger.info(f"⚖️ Trial expired for {user_id}, sent decision embed.")
        except Exception as e:
            logger.error(f"Error in trial cleanup: {e}", exc_info=True)

    # --- 4. Unified Expiration Task (Roles & Item Curses) ---
    @tasks.loop(minutes=5.0)
    async def unified_cleanup_loop():
        guild = bot.get_guild(guild_id)
        if not guild:
            return
        await handle_curse_expirations()
        await handle_role_expirations(guild)
        await handle_trial_expirations(guild)

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

    # --- 6. Automated Quote Drops (Every X hours) ---
    @tasks.loop(minutes=15.0)
    async def quote_drop_loop():
        """
        Sends a random quote from the 'quote_drops' table at configurable intervals.
        Only fires if someone has chatted within the last 30 minutes. 
        If no activity, it skips the 'turn' and waits for the next interval.
        """
        try:
            enabled = await database.get_setting(QUOTE_DROPS_ENABLED_KEY, "0") == "1"
            if not enabled:
                return

            # Default to 8 hours if unset
            interval_hours_str = await database.get_setting(QUOTE_DROPS_INTERVAL_KEY, "8")
            try:
                interval_hours = float(interval_hours_str)
            except ValueError:
                interval_hours = 8.0

            last_drop_str = await database.get_setting(LAST_QUOTE_DROP_TIME_KEY, "0")
            try:
                last_drop_time = float(last_drop_str)
            except ValueError:
                last_drop_time = 0.0

            now = time.time()
            if now - last_drop_time < (interval_hours * 3600):
                return

            # Window triggered: Check for activity in the last 30 minutes
            if await activity_tracker.has_recent_activity(30):
                guild = bot.get_guild(guild_id)
                if not guild:
                    return

                # Get target channel (main)
                from database import get_channel_assigns, get_random_quote_drop
                assigns = await get_channel_assigns()
                channel_id = assigns.get("main") # Should be mapped in dashboard
                
                if not channel_id:
                    # Fallback to forum if main not set
                    forum = discord.utils.get(guild.text_channels, name="forum")
                    channel = forum
                    if not forum:
                        logger.warning("Quote drop loop: No 'main' channel or 'forum' found. Skipping.")
                        return
                else:
                    channel = guild.get_channel(int(channel_id))
                
                if not channel:
                    return

                # Pick random quote drop
                quote = await get_random_quote_drop()
                if not quote:
                    logger.warning("Quote drop loop: No quotes found in 'quote_drops' table.")
                    return

                # Send
                await channel.send(quote)
                await database.set_setting(LAST_QUOTE_DROP_TIME_KEY, str(now))
                logger.info(f"🚀 Automated quote drop sent to {channel.name}: {quote[:50]}...")
            else:
                # SKIP TURN: Advance 'last_drop_time' so we wait a full interval before trying again
                await database.set_setting(LAST_QUOTE_DROP_TIME_KEY, str(now))
                logger.info("💤 Quote drop loop: Skipping turn due to inactivity (last 30m).")

        except Exception as e:
            logger.error(f"Error in quote_drop_loop: {e}", exc_info=True)

    @quote_drop_loop.before_loop
    async def before_quote_drop_loop():
        await bot.wait_until_ready()

    quote_drop_loop.start()

    # --- 7. Daily Tarot Task (Daily TC) ---
    @tasks.loop(seconds=10)
    async def daily_tc_task():
        try:
            trigger_now = await database.get_setting("trigger_daily_tc", "0") == "1"
            if not trigger_now:
                return

            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            today_str = now_pt.date().isoformat()

            guild = bot.get_guild(guild_id)
            if not guild:
                return

            if trigger_now:
                bulletin_id = await database.get_setting(BULLETIN_CHANNEL_KEY, "")
                if bulletin_id:
                    channel = guild.get_channel(int(bulletin_id))
                    if channel:
                        import tarot
                        import rws
                        import manara
                        from database import get_admin_config
                        config = await get_admin_config()
                        deck_name = config.get("tarot_deck", "thoth").lower().strip()
                        
                        dev_mode = False # Placeholder or get from config
                        if deck_name == "rws":
                            deck_module = rws
                        elif deck_name == "manara":
                            deck_module = manara
                        else:
                            deck_module = tarot

                        card_key = deck_module.draw_card()
                        date_str = now_pt.strftime("%m/%d/%y")
                        await channel.send(f"🎴 **Pull for {date_str}**")
                        await deck_module.send_tarot_card(channel, card_key=card_key)
                        await database.set_setting(DAILY_TC_DATE_KEY, today_str)
                        await database.set_setting("trigger_daily_tc", "0")
                        logger.info(f"🎴 Manual Daily TC triggered and sent for {today_str}")
                else:
                    # If flag was set but bulletin not configured, reset it anyway to avoid loop
                    await database.set_setting("trigger_daily_tc", "0")

        except Exception as e:
            logger.error(f"Error in daily_tc_task: {e}", exc_info=True)

    @daily_tc_task.before_loop
    async def before_daily_tc():
        await bot.wait_until_ready()

    daily_tc_task.start()

    # --- 8. Weekly Bulletin Purge ---
    @tasks.loop(hours=1)
    async def weekly_bulletin_purge():
        """Sunday at 11:59 PM (23:59)"""
        try:
            enabled = await database.get_setting(WEEKLY_PURGE_ENABLED_KEY, "0") == "1"
            if not enabled:
                return

            now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
            purge_interval = await database.get_setting("bulletin_purge_interval", "weekly")
            
            # Condition for purge: 
            # - Daily: midnight (hour 0)
            # - Weekly: Sunday (weekday 6) at 11:59 PM (hour 23)
            do_purge = False
            if purge_interval == "daily" and now_pt.hour == 0:
                do_purge = True
            elif purge_interval == "weekly" and now_pt.weekday() == 6 and now_pt.hour == 23:
                do_purge = True

            if do_purge:
                bulletin_id = await database.get_setting(BULLETIN_CHANNEL_KEY, "")
                if bulletin_id:
                    guild = bot.get_guild(guild_id)
                    channel = guild.get_channel(int(bulletin_id))
                    if channel:
                        logger.info(f"🧹 Starting {purge_interval} bulletin purge...")
                        await channel.purge(limit=1000, reason=f"{purge_interval.capitalize()} scheduled purge")

        except Exception as e:
            logger.error(f"Error in bulletin purge: {e}", exc_info=True)

    @weekly_bulletin_purge.before_loop
    async def before_weekly_purge():
        await bot.wait_until_ready()

    weekly_bulletin_purge.start()
