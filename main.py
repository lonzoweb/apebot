"""
Discord Bot Main File
Contains all bot commands and event handlers
"""

# --- Standard Library Imports ---
import random
import asyncio
import os
import logging
import colorlog
import shutil
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import aiohttp  # Added for web session
import urllib.parse
import re

# --- Third-Party Imports ---
import discord
from discord.ext import commands
from discord.ext import tasks
import ephem

# --- Local Module Imports (REQUIRED for bot functionality) ---
# NOTE: Assuming all these are files/modules in the root (rws, tarot, hierarchy, etc.)
import rws
import tarot
import hierarchy
import activity
import battle
import database
import economy
import items
import crypto_api

# NOTE: Assuming these functions are available globally or defined in imported modules
from items import ITEM_REGISTRY, ITEM_ALIASES, aggressive_uwu, extract_gif_url
from config import *
from database import *
from helpers import *
from api import *


# ============================================================
# LOGGING CONFIGURATION (Colorized)
# ============================================================

log_format = (
    "%(log_color)s%(levelname)-8s%(reset)s | "
    "%(log_color)s%(name)-20s%(reset)s | "
    "%(white)s%(message)s"
)

formatter = colorlog.ColoredFormatter(
    log_format,
    datefmt=None,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red,bg_white",
    },
    style="%",
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

if root_logger.hasHandlers():
    root_logger.handlers.clear()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)

logging.getLogger("discord").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Assuming these are defined in config.py
# MASOCHIST_ROLE_ID = ...
# VOTE_THRESHOLD = ...
# ROLE_DURATION_SECONDS = ...

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
bot.aiohttp_session = None
bot.owner_timezone = None

bot_start_time = datetime.now()

# Global tracking for pull command with intermittent reinforcement (needs to be global)
last_used = {}
weather_user_cooldowns = {}
weather_user_hourly = {}
user_pull_usage = {}


@bot.event
async def on_ready():
    """Bot startup event: Performs all setup and initializations."""

    # 1. Setup external services
    if bot.aiohttp_session is None or bot.aiohttp_session.closed:
        bot.aiohttp_session = aiohttp.ClientSession()

    from api import set_bot_session

    set_bot_session(bot.aiohttp_session)

    # 2. Get owner timezone (Assuming this is for a specific user)
    if bot.owner_timezone is None:
        your_user_id = 154814148054745088  # Placeholder ID
        # Assuming get_user_timezone exists and is imported from helpers/database
        # tz, _ = get_user_timezone(your_user_id)
        # bot.owner_timezone = tz
        pass

    # 3. Initialize ALL Database Tables
    await bot.loop.run_in_executor(None, init_db)
    await bot.loop.run_in_executor(None, battle.init_battle_db)

    # 4. Load Cogs (This loads all commands and event listeners)
    try:
        # NOTE: Assuming activitycog is a valid cog file in the project
        await bot.load_extension("activitycog")
        logger.info("✅ Loaded ActivityCog.")
    except Exception as e:
        logger.error(f"❌ Failed to load ActivityCog: {e}", exc_info=True)

    # 5. Setup Background Tasks (Needs Guild ID for role management)
    if not bot.guilds:
        logger.error("Bot is not in any guilds! Cannot start tasks.")
        main_guild_id = None
    else:
        main_guild_id = bot.guilds[0].id

    if main_guild_id:
        # NOTE: Assuming tasks module and setup_tasks function exist
        # tasks.setup_tasks(bot, main_guild_id)
        logger.info(f"✅ Background tasks setup complete for Guild ID: {main_guild_id}")

    logger.info(f"✅ Logged in as {bot.user}")


# ============================================================
# BOT EVENTS
# ============================================================


async def get_or_create_webhook(channel):
    """Reuses existing webhook or creates one to mirror cursed users."""
    if not isinstance(channel, discord.TextChannel):
        return None
    try:
        webhooks = await channel.webhooks()
        for wh in webhooks:
            if wh.name == "EconomyBotProxy":
                return wh
        return await channel.create_webhook(name="EconomyBotProxy")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return None


@bot.event
async def on_message(message):
    """Handle all message events with Curse Enforcement"""
    if message.author.bot:
        await bot.process_commands(message)
        return

    # ============================================================
    # 🧿 CURSE ENFORCEMENT SECTION
    # ============================================================
    # Check if user has an active Muzzle or UwU effect
    # NOTE: Assuming get_active_effect, remove_active_effect exist in database.py
    effect_data = await bot.loop.run_in_executor(
        None, get_active_effect, message.author.id
    )

    if effect_data:
        effect_name, expiration_time = effect_data

        # If expired, remove from DB and let message through
        if time.time() > expiration_time:
            await bot.loop.run_in_executor(
                None, remove_active_effect, message.author.id
            )
        else:
            # --- MUZZLE EFFECT ---
            if effect_name == "muzzle":
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                return  # Block further processing

            # --- UWU EFFECT (Standardized) ---
            # NOTE: Removed 'saturn_uwu' check. Now only checks for 'uwu'
            elif effect_name == "uwu":
                # CRITICAL FIX: aggressive_uwu is imported from items.py and called without 'saturn' arg
                # NOTE: The definition of aggressive_uwu used here is the final, single-arg version
                transformed_text = aggressive_uwu(message.content)

                try:
                    await message.delete()
                    webhook = await get_or_create_webhook(message.channel)

                    if webhook:
                        await webhook.send(
                            content=transformed_text,
                            username=message.author.display_name,
                            avatar_url=message.author.display_avatar.url,
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    else:
                        await message.channel.send(
                            f"**{message.author.display_name}**: {transformed_text}"
                        )

                except discord.Forbidden:
                    await message.channel.send(
                        f"**ERROR: Bot lacks permission to delete original message.** Sending: **{message.author.display_name}**: {transformed_text}"
                    )
                except Exception as e:
                    logger.error(f"Error in UwU mirroring or webhook: {e}")

                return  # Block activity tracking and commands while cursed

    # ============================================================
    # 📊 NORMAL PROCESSING SECTION (Non-Cursed)
    # ============================================================

    # Log to in-memory buffer
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    hour = now.strftime("%H")
    # NOTE: Assuming activity.log_activity_in_memory exists
    activity.log_activity_in_memory(str(message.author.id), hour)

    # Track GIFs
    gif_url = extract_gif_url(message)
    if gif_url:
        try:
            # NOTE: Assuming increment_gif_count exists
            increment_gif_count(gif_url, message.author.id)
        except Exception as e:
            logger.error(f"Error tracking GIF: {e}")

    # Track battle messages
    await battle.on_message_during_battle(message)

    # Process commands
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    """Track reactions for active battles"""
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    await battle.on_reaction_during_battle(payload, channel)


@bot.check
async def globally_block_channels(ctx):
    """Block all commands except in allowed channels"""
    if ctx.author.guild_permissions.administrator:
        return True

    ALLOWED_CHANNEL_NAMES = [
        "forum",
        "forum-livi",
        "emperor",
    ]  # NOTE: Assuming this list is defined

    return ctx.channel.name in ALLOWED_CHANNEL_NAMES


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if hasattr(ctx.command, "on_error"):
        return

    if isinstance(error, commands.CommandOnCooldown):
        return

    elif isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")

    else:
        logger.error(
            f"UNHANDLED COMMAND ERROR in {ctx.command}: {error}", exc_info=True
        )
        await ctx.send(f"❌ An unexpected error occurred: `{type(error).__name__}`")


# ============================================================
# QUOTE COMMANDS
# ============================================================


@bot.command(name="quote")
@commands.cooldown(1, 3, commands.BucketType.user)
async def quote_command(ctx, *, keyword: str = None):
    # NOTE: Assuming load_quotes_from_db exists
    quotes = load_quotes_from_db()
    if not quotes:
        await ctx.send("⚠️ No quotes available.")
        return

    if keyword is None:
        if ctx.author.guild_permissions.administrator or any(
            role.name in AUTHORIZED_ROLES for role in ctx.author.roles
        ):
            quote = random.choice(quotes)
            embed = discord.Embed(
                title="📜 Quote", description=quote, color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in quotes if keyword.lower() in q.lower()]
        if matches:
            for match in matches[:5]:
                embed = discord.Embed(
                    description=f"📜 {match}", color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
            if len(matches) > 5:
                await ctx.send(
                    f"📊 Showing 5 of {len(matches)} matches. Be more specific!"
                )
        else:
            await ctx.send(f"🔍 No quotes found containing '{keyword}'")


@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    # NOTE: Assuming add_quote_to_db, ROLE_ADD_QUOTE exist
    if not (
        ctx.author.guild_permissions.administrator
        or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
    ):
        return await ctx.send("🚫 Peasant Detected")

    if len(quote_text) > 2000:
        return await ctx.send("❌ Quote too long (max 2000 characters)")

    try:
        add_quote_to_db(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"{quote_text}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error adding quote: {e}")
        await ctx.send("❌ Error adding quote")


@bot.command(name="editquote")
async def edit_quote_command(ctx, *, keyword: str):
    # NOTE: Assuming load_quotes_from_db, update_quote_in_db exist
    if not (
        ctx.author.guild_permissions.administrator
        or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
    ):
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = load_quotes_from_db()
    matches = [q for q in quotes if keyword.lower() in q.lower()]
    if not matches:
        await ctx.send(f"🔍 No quotes found containing '{keyword}'")
        return

    description = "\n".join(
        f"{i+1}. {q[:100]}..." if len(q) > 100 else f"{i+1}. {q}"
        for i, q in enumerate(matches)
    )
    embed = discord.Embed(
        title="Select a quote to edit (reply with number or 'cancel')",
        description=description,
        color=discord.Color.orange(),
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        if msg.content.lower() == "cancel":
            return await ctx.send("❌ Edit cancelled.")

        if not msg.content.isdigit() or not (1 <= int(msg.content) <= len(matches)):
            return await ctx.send("❌ Invalid selection. Edit cancelled.")

        index = int(msg.content) - 1
        old_quote = matches[index]

        await ctx.send(f"✏️ Enter the new version of the quote (or 'cancel'):")
        new_msg = await bot.wait_for("message", check=check, timeout=120)

        if new_msg.content.lower() == "cancel":
            return await ctx.send("❌ Edit cancelled.")

        new_quote = new_msg.content.strip()
        if len(new_quote) > 2000:
            return await ctx.send("❌ Quote too long (max 2000 characters)")

        update_quote_in_db(old_quote, new_quote)
        await ctx.send(f"✅ Quote updated.")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Edit cancelled.")


@bot.command(name="delquote")
async def delete_quote(ctx, *, keyword: str):
    # NOTE: Assuming search_quotes_by_keyword, delete_quote_by_id exist
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    results = search_quotes_by_keyword(keyword)
    if not results:
        return await ctx.send(f"🔍 No quotes found containing '{keyword}'")

    if len(results) > 1:
        formatted = "\n".join(
            f"{i+1}. {r[1][:80]}..." if len(r[1]) > 80 else f"{i+1}. {r[1]}"
            for i, r in enumerate(results)
        )
        await ctx.send(
            f"⚠️ Multiple quotes found containing '{keyword}'.\n{formatted}\n"
            f"Type the number (1–{len(results)}), or `cancel`."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            reply = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("⌛ Timed out. No quotes deleted.")

        if reply.content.lower() == "cancel":
            return await ctx.send("❎ Cancelled.")

        if not reply.content.isdigit() or not (1 <= int(reply.content) <= len(results)):
            return await ctx.send("❌ Invalid selection. Cancelled.")

        quote_id, quote_text = results[int(reply.content) - 1]
    else:
        quote_id, quote_text = results[0]

    await ctx.send(f'🗑️ Delete this quote?\n"{quote_text}"\nType `yes` to confirm.')

    def check_confirm(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        confirm = await bot.wait_for("message", timeout=30.0, check=check_confirm)
    except asyncio.TimeoutError:
        return await ctx.send("⌛ Timed out. Quote not deleted.")

    if confirm.content.lower() != "yes":
        return await ctx.send("❎ Cancelled.")

    try:
        delete_quote_by_id(quote_id)
        await ctx.send(f'✅ Deleted quote:\n"{quote_text}"')
    except Exception as e:
        logger.error(f"Error deleting quote: {e}")
        await ctx.send("❌ Error deleting quote")


@bot.command(name="listquotes")
async def list_quotes(ctx):
    # NOTE: Assuming load_quotes_from_db exists
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return
    quotes = load_quotes_from_db()
    if not quotes:
        await ctx.send("⚠️ No quotes available.")
        return

    quote_text = "\n\n".join(f"{i+1}. {q}" for i, q in enumerate(quotes))
    chunks = [quote_text[i : i + 1900] for i in range(0, len(quote_text), 1900)]

    try:
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=(
                    f"📜 All Quotes (Part {i+1}/{len(chunks)})"
                    if len(chunks) > 1
                    else "📜 All Quotes"
                ),
                description=chunk,
                color=discord.Color.blue(),
            )
            await ctx.author.send(embed=embed)
        await ctx.send("📬 Quotes sent to your DM!")
    except discord.Forbidden:
        await ctx.send("⚠️ Cannot DM you. Check privacy settings.")


@bot.command(name="daily")
@commands.cooldown(1, 5, commands.BucketType.user)
async def daily_command(ctx):
    # NOTE: Assuming tasks.get_daily_quote exists
    if ctx.author.guild_permissions.administrator or any(
        role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles
    ):
        daily_quote = tasks.get_daily_quote()
        if daily_quote:
            embed = discord.Embed(
                title="🌅 Blessings to Apeiron",
                description=f"📜 {daily_quote}",
                color=discord.Color.gold(),
            )
            embed.set_footer(text="🕊️ Daily Quote Recall")
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 Peasant Detected")


# ============================================================
# UTILITY COMMANDS
# ============================================================


@bot.command(name="ud")
@commands.cooldown(1, 5, commands.BucketType.user)
async def urban_command(ctx, *, term: str):
    # NOTE: Assuming urban_dictionary_lookup exists
    if len(term) > 100:
        return await ctx.send("❌ Term too long (max 100 characters)")

    data = await urban_dictionary_lookup(term)

    if not data:
        return await ctx.send("❌ Request timed out or an error occurred")

    if not data.get("list"):
        return await ctx.send(f"No definition found for **{term}**.")

    first = data["list"][0]
    definition = first["definition"][:1000]
    example = first.get("example", "")[:500]

    embed = discord.Embed(
        title=f"Definition of {term}",
        description=f"{definition}\n\n*Example: {example}*" if example else definition,
        color=discord.Color.dark_purple(),
    )
    await ctx.send(embed=embed)


@bot.command(name="flip")
@commands.cooldown(1, 5, commands.BucketType.user)
async def flip_command(ctx):
    """Flip a coin"""
    await asyncio.sleep(1)
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 **{result}**")


@bot.command(name="roll")
@commands.cooldown(1, 5, commands.BucketType.user)
async def roll_command(ctx):
    """Roll a random number between 1-33"""
    await asyncio.sleep(0.5)
    result = random.randint(1, 33)
    await ctx.send(f"{ctx.author.display_name} rolls 🎲 **{result}**")


@bot.command(name="8ball")
@commands.cooldown(1, 6, commands.BucketType.user)
async def eightball_command(ctx, *, question: str = None):
    """Ask the magic 8-ball a question"""
    if not question:
        return await ctx.send("❌ Ask a question cuh.")

    responses = [
        "You bet your fucking life.",
        "Absolutely, no doubt about it.",
        "100%. Go for it.",
        "Hell yeah.",
        "Ask me later, I'm busy.",
        "Unclear. Try again when I care bitch.",
        "Sheeeeit, ion know",
        "Hell no.",
        "Not a chance in hell.",
        "Absolutely fucking not.",
        "Are you stupid? No.",
        "In your dreams cuh.",
        "Nope. Don't even think about it cuh.",
    ]

    msg = await ctx.send(f"**{ctx.author.display_name}:** {question}\n🎱 *shaking...*")
    await asyncio.sleep(5)
    await msg.edit(
        content=f"**{ctx.author.display_name}:** {question}\n🎱 **{random.choice(responses)}**"
    )


@bot.command(name="tc")
async def tarot_card(ctx, action: str = None, deck_name: str = None):
    # NOTE: Assuming get_guild_tarot_deck, set_guild_tarot_deck, rws.draw_card, tarot.draw_card, etc. exist
    if action and action.lower() == "set":
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")
        if not deck_name:
            return await ctx.send("❌ Please specify a deck name: `thoth` or `rws`")
        deck_name = deck_name.lower()
        if deck_name not in ["thoth", "rws"]:
            return await ctx.send(
                f"❌ Unknown deck `{deck_name}`\nAvailable decks: `thoth`, `rws`"
            )
        set_guild_tarot_deck(ctx.guild.id, deck_name)
        deck_full_name = (
            "Aleister Crowley Thoth Tarot"
            if deck_name == "thoth"
            else "Rider-Waite-Smith Tarot"
        )
        await ctx.send(f"✅ Deck set to **{deck_full_name}**")
        return

    deck_setting = get_guild_tarot_deck(ctx.guild.id)
    deck_name_clean = str(deck_setting).lower().strip() if deck_setting else "thoth"

    if deck_name_clean == "rws":
        deck_module = rws
    else:
        deck_module = tarot

    async def execute_draw():
        card_key = deck_module.draw_card()
        await deck_module.send_tarot_card(ctx, card_key=card_key)

    user_id = ctx.author.id
    now = time.time()
    today = datetime.utcnow().date()

    if ctx.author.guild_permissions.administrator:
        await execute_draw()
        return

    if user_id not in user_usage or user_usage[user_id]["day"] != today:
        user_usage[user_id] = {
            "day": today,
            "count": 0,
            "last_used": 0,
            "next_cooldown": None,
        }

    user_data = user_usage[user_id]
    if user_data["count"] < 2:
        user_data["count"] += 1
        await execute_draw()
        return

    if user_data["next_cooldown"] is None:
        user_data["next_cooldown"] = random.triangular(16, 60, 33)

    cooldown = user_data["next_cooldown"]
    time_since_last = now - user_data["last_used"]

    if time_since_last < cooldown:
        messages = [
            "Rest...",
            "Patience...",
            "The abyss awaits...",
            "You will wait...",
            "Not on my watch...",
            "The void beckons...",
        ]
        await ctx.send(random.choice(messages))
        return

    user_data["last_used"] = now
    user_data["count"] += 1
    user_data["next_cooldown"] = None

    await execute_draw()


@bot.command(name="moon")
@commands.cooldown(1, 10, commands.BucketType.user)
async def moon_command(ctx):
    # NOTE: Assuming ephem functions and get_zodiac_sign, get_moon_phase_name, get_moon_phase_emoji exist
    try:
        now = ephem.now()
        moon = ephem.Moon()
        moon.compute(now)
        illumination = moon.phase / 100.0
        phase_name = get_moon_phase_name(illumination)
        phase_emoji = get_moon_phase_emoji(phase_name)
        moon_ecliptic = ephem.Ecliptic(moon)
        current_sign = get_zodiac_sign(moon_ecliptic.lon)
        next_new = ephem.next_new_moon(now)
        new_moon = ephem.Moon()
        new_moon.compute(next_new)
        new_moon_ecliptic = ephem.Ecliptic(new_moon)
        new_moon_sign = get_zodiac_sign(new_moon_ecliptic.lon)
        days_to_new = int((ephem.Date(next_new) - ephem.Date(now)))
        next_full = ephem.next_full_moon(now)
        full_moon = ephem.Moon()
        full_moon.compute(next_full)
        full_moon_ecliptic = ephem.Ecliptic(full_moon)
        full_moon_sign = get_zodiac_sign(full_moon_ecliptic.lon)
        days_to_full = int((ephem.Date(next_full) - ephem.Date(now)))
        new_date_str = ephem.Date(next_new).datetime().strftime("%B %d, %Y")
        full_date_str = ephem.Date(next_full).datetime().strftime("%B %d, %Y")

        embed = discord.Embed(title="Moon Phase", color=discord.Color.blue())
        embed.add_field(
            name="Current",
            value=f"{phase_emoji} **{phase_name}** ({int(illumination * 100)}% illuminated)\nMoon in: **{current_sign}**",
            inline=False,
        )
        embed.add_field(
            name="Upcoming",
            value=(
                f"**Next New Moon:** {new_date_str} (in {days_to_new} days)\n"
                f"Moon in: **{new_moon_sign}**\n\n"
                f"**Next Full Moon:** {full_date_str} (in {days_to_full} days)\n"
                f"Moon in: **{full_moon_sign}**"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in moon command: {e}", exc_info=True)
        await ctx.send(f"❌ Error calculating moon phase: {str(e)}")


@bot.command(name="lp")
@commands.cooldown(1, 5, commands.BucketType.user)
async def lifepathnumber_command(ctx, date: str = None):
    # NOTE: Assuming all helper functions exist: calculate_life_path, get_life_path_traits, get_chinese_zodiac_animal, etc.
    if not date:
        return await ctx.send(
            "❌ Please provide a date.\n"
            "**Format:** `.lp MM/DD/YYYY`\n"
            "**Example:** `.lp 05/15/1990`"
        )

    try:
        parts = date.split("/")
        if len(parts) != 3:
            raise ValueError("Invalid format")

        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])

        if not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
            raise ValueError("Invalid date values")

        life_path = calculate_life_path(month, day, year)
        traits = get_life_path_traits(life_path)
        zodiac_animal, zodiac_emoji = get_chinese_zodiac_animal(year)
        zodiac_element = get_chinese_zodiac_element(year)
        animal_traits = get_chinese_animal_traits(zodiac_animal)
        element_traits = get_chinese_element_traits(zodiac_element)
        today = datetime.now()
        age = today.year - year
        if (today.month, today.day) < (month, day):
            age -= 1
        generation = get_generation(year)
        date_obj = datetime(year, month, day)
        formatted_date = date_obj.strftime("%B %d, %Y")
        is_master = life_path in [11, 22, 33]

        embed = discord.Embed(title="Life Path Number", color=discord.Color.purple())
        embed.add_field(name="Birthday", value=formatted_date, inline=False)
        embed.add_field(
            name="Life Path",
            value=f"**{life_path}**" + (" (Master Number)" if is_master else ""),
            inline=False,
        )
        embed.add_field(name="Traits", value=traits, inline=False)
        compact_info = (
            f"{zodiac_element} {zodiac_animal} {zodiac_emoji} • {age} • {generation}"
        )
        embed.add_field(
            name="Chinese Zodiac • Age • Generation", value=compact_info, inline=False
        )
        embed.add_field(
            name=f"{zodiac_animal} Traits", value=animal_traits, inline=False
        )
        embed.add_field(
            name=f"{zodiac_element} Element", value=element_traits, inline=False
        )
        await ctx.send(embed=embed)

    except ValueError:
        await ctx.send(
            "❌ Invalid date format.\n"
            "**Format:** `.lp MM/DD/YYYY`\n"
            "**Example:** `.lp 05/15/1990`"
        )
    except Exception as e:
        logger.error(f"Error in life path command: {e}")
        await ctx.send("❌ Error calculating life path number.")


@bot.command(name="gifs")
@commands.cooldown(1, 10, commands.BucketType.user)
async def gifs_command(ctx):
    # NOTE: Assuming get_top_gifs, shorten_gif_url, get_gif_by_rank exist
    top_gifs = get_top_gifs(limit=10)

    if not top_gifs:
        return await ctx.send("📊 No GIFs tracked yet. Send some GIFs!")

    description = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, (gif_url, count, last_sent_by) in enumerate(top_gifs, start=1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        shortened = shorten_gif_url(gif_url)

        user = bot.get_user(int(last_sent_by))
        username = user.display_name if user else f"User#{last_sent_by[:4]}"

        description += f"{medal} **{count} sends** - `{shortened}` - @{username}\n"

    embed = discord.Embed(
        title="🏆 Top 10 Most Sent GIFs",
        description=description + "\n💡 React 1️⃣-🔟 to see a GIF!",
        color=discord.Color.purple(),
    )

    msg = await ctx.send(embed=embed)

    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i in range(min(len(top_gifs), 10)):
        await msg.add_reaction(reactions[i])

    def check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in reactions
            and reaction.message.id == msg.id
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        rank = reactions.index(str(reaction.emoji)) + 1
        gif_url = get_gif_by_rank(rank)

        if gif_url:
            await ctx.send(f"**#{rank} GIF:**\n{gif_url}")
    except asyncio.TimeoutError:
        pass


@bot.command(name="rev")
@commands.cooldown(1, 30, commands.BucketType.user)
async def reverse_command(ctx):
    # NOTE: Assuming extract_image, google_lens_fetch_results exist
    async with ctx.channel.typing():
        image_url = None
        if ctx.message.reference:
            try:
                replied = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                image_url = await extract_image(replied)
            except Exception as e:
                logger.error(f"Error fetching replied message: {e}")

        if not image_url:
            async for msg in ctx.channel.history(limit=20):
                image_url = await extract_image(msg)
                if image_url:
                    break

        if not image_url:
            return await ctx.reply("⚠️ No image found in the last 20 messages.")

        try:
            data = await google_lens_fetch_results(image_url, limit=3)
        except ValueError as e:
            return await ctx.reply(f"❌ Configuration error: {e}")
        except RuntimeError as e:
            return await ctx.reply(f"❌ Search error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in reverse search: {e}")
            return await ctx.reply(f"❌ Unexpected error: {type(e).__name__}")

        if not data or not data.get("results"):
            return await ctx.reply("❌ No similar images found.")

        embed = discord.Embed(
            title="🔍 Google Lens Reverse Image Search", color=discord.Color.blue()
        )

        for i, r in enumerate(data["results"], start=1):
            title_truncated = r["title"][:100] if r["title"] else "Untitled"
            field_name = f"{i}. {title_truncated}"
            field_value = (
                f"📌 Source: {r['source']}\n🔗 [View Image]({r['link']})"
                if r["link"]
                else f"📌 Source: {r['source']}"
            )
            embed.add_field(name=field_name, value=field_value, inline=False)

        if data.get("search_page"):
            embed.add_field(
                name="🌐 Full Search Results",
                value=f"[View on Google Lens]({data['search_page']})",
                inline=False,
            )

        embed.set_footer(text="Powered by SerpApi + Google Lens")
        embed.set_thumbnail(url=image_url)

        await ctx.reply(embed=embed)


@bot.command(name="stats")
async def stats_command(ctx):
    # NOTE: Assuming load_quotes_from_db exists
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return

    uptime_delta = datetime.now() - bot_start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    quote_count = len(load_quotes_from_db())

    embed = discord.Embed(title="📊 Bot Stats", color=discord.Color.teal())
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Quotes", value=str(quote_count), inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    await ctx.send(embed=embed)


@bot.command(name="gem")
async def gematria_command(ctx, *, text: str = None):
    # NOTE: Assuming fetch_message, calculate_all_gematria, reverse_reduction_values, reduce_to_single_digit exist
    if ctx.message.reference:
        reply_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        text = reply_msg.content

    if not text or not any(ch.isalnum() for ch in text):
        return await ctx.reply(
            "⚠️ No valid text found to evaluate.", mention_author=False
        )

    if len(text) > 53:
        return await ctx.reply("❌ Text exceeds limit.", mention_author=False)

    results = calculate_all_gematria(text)

    embed = discord.Embed(
        title=f"Gematria for: {text}", color=discord.Color.dark_grey()
    )

    embed.add_field(name="Hebrew", value=str(results["hebrew"]), inline=False)
    embed.add_field(name="English", value=str(results["english"]), inline=False)
    embed.add_field(name="Ordinal", value=str(results["ordinal"]), inline=False)
    embed.add_field(name="Reduction", value=str(results["reduction"]), inline=False)
    embed.add_field(name="Reverse", value=str(results["reverse"]), inline=False)
    embed.add_field(
        name="Reverse Reduction", value=str(results["reverse_reduction"]), inline=False
    )
    embed.add_field(name="Latin", value=str(results["latin"]), inline=False)
    embed.add_field(
        name="Reverse Sumerian", value=str(results["reverse_sumerian"]), inline=False
    )

    is_exempt = ctx.author.guild_permissions.administrator
    if not is_exempt:
        embed.set_footer(text=f"{ctx.author.display_name}")

    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="blessing")
async def blessing_command(ctx):
    # NOTE: Assuming CHANNEL_ID, TEST_CHANNEL_ID, ROLE_ADD_QUOTE exist
    if not (
        ctx.author.guild_permissions.administrator
        or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
    ):
        await ctx.send("🚫 Peasant Detected")
        return

    embed = discord.Embed(
        title="",
        description="**<a:3bluefire:1332813616696524914> Blessings to Apeiron <a:3bluefire:1332813616696524914>**",
        color=discord.Color.gold(),
    )

    # Placeholder for targets:
    targets = [ctx.channel]

    if not targets:
        await ctx.send("⚠️ No valid channels to send the blessing.")
        return

    for ch in targets:
        await ch.send(embed=embed)
    await ctx.send("✅ Blessings sent to channels.")


@bot.command(name="hierarchy")
@commands.cooldown(5, 60, commands.BucketType.user)
async def hierarchy_command(ctx, *, args: str = None):
    # NOTE: Assuming hierarchy functions and HIERARCHY_DB exist
    if args is None:
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)
        ):
            return await ctx.send(
                "🚫 Peasant Detected - Full hierarchy chart is restricted to authorized roles."
            )

        await hierarchy.send_hierarchy_chart(ctx)
        return

    args_lower = args.lower().strip()

    if args_lower.startswith("list"):
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)
        ):
            return await ctx.send(
                "🚫 Peasant Detected - Hierarchy list is restricted to authorized roles."
            )

        parts = args.split()
        page = 1
        if len(parts) > 1 and parts[1].isdigit():
            page = int(parts[1])

        await hierarchy.send_entity_list(ctx, page)
        return

    if args_lower == "random":
        entity_key = hierarchy.get_random_entity()
        await hierarchy.send_entity_details(ctx, entity_key)
        return

    if args_lower.startswith("search "):
        keyword = args[7:].strip()
        if not keyword:
            return await ctx.send(
                "❌ Please provide a search keyword. Usage: `.hierarchy search [keyword]`"
            )

        results = hierarchy.search_hierarchy(keyword)
        await hierarchy.send_search_results(ctx, results)
        return

    entity_key = args_lower.replace(" ", "_").replace("-", "_")

    if entity_key in hierarchy.HIERARCHY_DB:
        await hierarchy.send_entity_details(ctx, entity_key)
    else:
        results = hierarchy.search_hierarchy(args)
        if results:
            for key, entity in results:
                if entity["name"].lower() == args_lower:
                    await hierarchy.send_entity_details(ctx, key)
                    return

            await hierarchy.send_search_results(ctx, results)
        else:
            await ctx.send(
                f"❌ No entity found matching '{args}'. Try `.hierarchy search {args}` or `.hierarchy random`"
            )


@bot.command(name="key")
async def kek_command(ctx):
    # NOTE: Assuming last_used, update_balance exist
    REWARD_AMOUNT = 3
    is_admin = ctx.author.guild_permissions.administrator
    STICKER_ID = 1416504837436342324

    if not is_admin:
        current_time = time.time()
        cooldown_duration = 60
        if "key" in last_used:
            time_since_last_use = current_time - last_used["key"]
            if time_since_last_use < cooldown_duration:
                return

    try:
        sticker = await ctx.guild.fetch_sticker(STICKER_ID)
        await ctx.send(f"{ctx.author.display_name} ʰᵃˢ ᵖᵃᶦᵈ ᵗʳᶦᵇᵘᵗᵉ")

        for _ in range(6):
            await ctx.send(stickers=[sticker])

        await ctx.bot.loop.run_in_executor(
            None, update_balance, ctx.author.id, REWARD_AMOUNT
        )

        if not is_admin:
            last_used["key"] = time.time()

    except discord.NotFound:
        await ctx.reply(
            "❌ Sticker not found! Make sure it's from this server.",
            mention_author=False,
        )
    except discord.HTTPException as e:
        await ctx.reply(f"❌ Failed to send sticker: {e}", mention_author=False)


@bot.command(name="pull")
async def pull_command(ctx):
    # NOTE: Assuming user_pull_usage, execute_pull exist
    user_id = ctx.author.id
    now = time.time()

    if ctx.author.guild_permissions.administrator:
        await execute_pull(ctx)
        return

    if user_id not in user_pull_usage:
        user_pull_usage[user_id] = {
            "timestamps": [],
            "last_used": 0,
            "next_cooldown": None,
        }

    user_data = user_pull_usage[user_id]

    user_data["timestamps"] = [t for t in user_data["timestamps"] if now - t < 180]

    if len(user_data["timestamps"]) < 20:
        user_data["timestamps"].append(now)
        await execute_pull(ctx)
        return

    if user_data["next_cooldown"] is None:
        user_data["next_cooldown"] = random.triangular(8, 30, 15)

    cooldown = user_data["next_cooldown"]
    time_since_last = now - user_data["last_used"]

    if time_since_last < cooldown:
        messages = [
            "Rest...",
            "Patience...",
            "The abyss awaits...",
            "You will wait...",
            "Not on my watch...",
            "The void beckons...",
        ]
        await ctx.send(random.choice(messages))
        return

    user_data["last_used"] = now
    user_data["timestamps"].append(now)
    user_data["next_cooldown"] = None

    await execute_pull(ctx)


async def execute_pull(ctx):
    # NOTE: Assuming update_balance, economy.format_balance, symbols defined globally/locally
    await asyncio.sleep(1)

    symbols = {
        "common": ["🏴‍☠️", "🗝️", "🗡️", "🃏", "🪦"],
        "medium": ["🔱", "🦇", "⭐"],
        "rare": ["💎", "👑", "<:emoji_name:1427107096670900226>"],
    }
    weighted_pool = symbols["common"] * 10 + symbols["medium"] * 4 + symbols["rare"] * 1
    msg = await ctx.send("🎲 | 🎲 | 🎲")
    delays = [0.12, 0.15, 0.18, 0.22, 0.28, 0.33]

    for d in delays:
        await asyncio.sleep(d)
        spin = [random.choice(list(weighted_pool)) for _ in range(3)]
        await msg.edit(content=f"{spin[0]} | {spin[1]} | {spin[2]}")

    roll = random.random()

    if roll < 0.01:
        symbol = random.choice(symbols["rare"])
        result = [symbol, symbol, symbol]
    elif roll < 0.085:
        pool = symbols["common"] + symbols["medium"]
        symbol = random.choice(pool)
        result = [symbol, symbol, symbol]
    elif roll < 0.235:
        symbol = random.choice(weighted_pool)
        other = random.choice([s for s in weighted_pool if s != symbol])
        pattern = random.choice(
            [[symbol, symbol, other], [symbol, other, symbol], [other, symbol, symbol]]
        )
        result = pattern
    elif roll < 0.46:
        symbol = random.choice(weighted_pool)
        near = random.choice([s for s in weighted_pool if s != symbol])
        pattern = random.choice([[symbol, symbol, near], [near, symbol, symbol]])
        result = pattern
    else:
        result = random.sample(weighted_pool, 3)

    r1, r2, r3 = result
    winnings = 0

    if r1 == r2 == r3:
        if r1 in symbols["rare"]:
            winnings = 100
            final_msg = f"{r1} | {r2} | {r3}\n**JACKPOT!** {r1}\n{ctx.author.mention}"
        else:
            winnings = 20
            medium_msgs = ["**Hit!**", "**Score!**", "**Got em!**", "**Connect!**"]
            final_msg = f"{r1} | {r2} | {r3}\n{random.choice(medium_msgs)} {r1}\n{ctx.author.mention}"

    elif r1 == r2 or r2 == r3 or r1 == r3:
        winnings = 5
        winning_symbol = r1 if r1 == r2 else (r2 if r2 == r3 else r1)
        small_msgs = ["Push.", "Match.", "Pair.", "Almost."]
        final_msg = f"{r1} | {r2} | {r3}\n{random.choice(small_msgs)} {winning_symbol}\n{ctx.author.mention}"

    else:
        winnings = 0
        insults = [
            "Pathetic.",
            "Trash.",
            "Garbage.",
            "Awful.",
            "Weak.",
            "Embarrassing.",
            "Yikes.",
            "Oof.",
            "Cringe.",
            "Terrible.",
            "Horrendous.",
            "Tragic.",
            "Broke.",
            "Washed.",
            "Cooked.",
            "Mid.",
            "Kys.",
            "Loser.",
            "It's over.",
        ]
        final_msg = (
            f"{r1} | {r2} | {r3}\n{random.choice(insults)}\n{ctx.author.mention}"
        )

    if winnings > 0:
        await ctx.bot.loop.run_in_executor(
            None, update_balance, ctx.author.id, winnings
        )
        formatted_winnings = economy.format_balance(winnings)
        final_msg += f"\n\nYou received {formatted_winnings}!"

    await asyncio.sleep(0.3)
    await msg.edit(content=final_msg)


@bot.command(name="pink")
async def pink_command(ctx, member: discord.Member):
    # NOTE: Assuming update_pink_vote, get_active_pink_vote_count, add_masochist_role_removal, MASOCHIST_ROLE_ID, VOTE_THRESHOLD, ROLE_DURATION_SECONDS exist
    if member.id == ctx.author.id:
        return await ctx.reply(
            "❌ You can't vote for yourself... unless you're into that?",
            mention_author=False,
        )
    if member.bot:
        return await ctx.reply(
            "❌ Bots are immune to this torture.", mention_author=False
        )

    masochist_role = ctx.guild.get_role(MASOCHIST_ROLE_ID)
    if not masochist_role:
        return await ctx.send(
            f"❌ Error: The configured role ID ({MASOCHIST_ROLE_ID}) was not found on this server."
        )

    bot_member = ctx.guild.me

    if not bot_member.guild_permissions.manage_roles:
        return await ctx.send(
            "🛑 **SETUP ERROR:** I do not have the **`Manage Roles`** permission. "
            "I cannot assign or remove the Masochist role until this is fixed."
        )

    if bot_member.top_role.position <= masochist_role.position:
        return await ctx.send(
            f"🛑 **HIERARCHY ERROR:** My highest role (`{bot_member.top_role.name}`) is not positioned above "
            f"da target role (`{masochist_role.name}`). "
            "Pwease move my wowe higher than da Masochist wowe in da se-w-sewvew settings."
        )

    if masochist_role in member.roles:
        return await ctx.reply(
            f"❌ {member.display_name} awweady has da {masochist_role.name} wowe.",
            mention_author=False,
        )

    voted_id_str = str(member.id)
    voter_id_str = str(ctx.author.id)

    await ctx.bot.loop.run_in_executor(
        None, update_pink_vote, voted_id_str, voter_id_str
    )

    vote_count = await ctx.bot.loop.run_in_executor(
        None, get_active_pink_vote_count, voted_id_str
    )

    if vote_count >= VOTE_THRESHOLD:

        try:
            await member.add_roles(
                masochist_role, reason="Weached 7 pink votes in 48 houws."
            )

            removal_time = time.time() + ROLE_DURATION_SECONDS
            await ctx.bot.loop.run_in_executor(
                None, add_masochist_role_removal, voted_id_str, removal_time
            )

            await ctx.send(
                f"🎉 **PAYMENT DUE!** {member.mention} has weached **{VOTE_THRESHOLD} pink votes** in 48 houws and has been assigned da **{masochist_role.name}** wowe fow 2 days!"
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ Intewnaw Ewwow: Faiwed two assign wowe due two unexpected pewmissions issue."
            )

    else:
        needed = VOTE_THRESHOLD - vote_count
        await ctx.send(
            f"{member.display_name} nyow has **{vote_count}/{VOTE_THRESHOLD}** pink votes. "
            f"**{needed} mowe** needed two pink nyame dis foow."
        )


@pink_command.error
async def pink_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Pwease mention a usew two vote fow, {ctx.author.mention}. Usage: `.pink @UsewMention`"
        )
        return

    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            f"❌ I couwd nyot find dat usew in da sewvew. Pwease twy again wif a pwopaw mention."
        )
        return

    else:
        raise error


@bot.command(name="gr")
async def give_role_command(ctx, member: discord.Member = None, role_alias: str = None):
    # NOTE: Assuming ROLE_ALIASES is defined globally
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    if not member or not role_alias:
        available = ", ".join(f"`{alias}`" for alias in ROLE_ALIASES.keys())
        return await ctx.send(
            f"❌ Usage: `.give @usew <wowe_awias>`\nAvaiwabwe awiases: {available}"
        )

    role_alias = role_alias.lower()

    if role_alias not in ROLE_ALIASES:
        available = ", ".join(f"`{alias}`" for alias in ROLE_ALIASES.keys())
        return await ctx.send(
            f"❌ Unknown wowe awias: `{role_alias}`\nAvaiwabwe awiases: {available}"
        )

    role_id = ROLE_ALIASES[role_alias]
    role = ctx.guild.get_role(int(role_id))

    if not role:
        return await ctx.send(
            f"❌ Wowe nyot found. Pwease check da wowe ID fow `{role_alias}` in da configuwation."
        )

    try:
        if role in member.roles:
            await member.remove_roles(role)
            embed = discord.Embed(
                title="🗑️ Wowe Wemoved",
                description=f"{member.mention} nyow nyot has da **{role.name}** wowe.",
                color=discord.Color.orange(),
            )
            embed.set_footer(text=f"Wemoved by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await member.add_roles(role)
            embed = discord.Embed(
                title="✅ Wowe Gwanted",
                description=f"{member.mention} has been given da **{role.name}** wowe.",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Given by {ctx.author.display_name}")
            await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have pewmission two nyyanage dis wowe.")
    except Exception as e:
        logger.error(f"Ewwow nyyanaging wowe: {e}")
        await ctx.send(f"❌ Ewwow nyyanaging wowe: {type(e).__name__}")


@bot.command(name="qd")
async def quick_delete_command(ctx, *, message: str = None):
    """Quick delete - deletes your message after 1 second"""
    await asyncio.sleep(1)
    try:
        await ctx.message.delete()
    except:
        pass


# ============================================================
# ECONOMY COMMANDS
# ============================================================


@bot.command(name="balance", aliases=["bal", "tokens"])
async def balance_command(ctx, member: discord.Member = None):
    """
    Shows your current token balance.
    Admins can check another user's balance: .balance @user
    """
    await economy.handle_balance_command(ctx, member)


@bot.command(name="send")
async def send_command(ctx, member: discord.Member, amount: int):
    """Transfer tokens to another user. Usage: .send @user <amount>"""
    await economy.handle_send_command(ctx, member, amount)


@bot.command(name="baladd")
@commands.has_permissions(administrator=True)
async def adminadd_command(ctx, member: discord.Member, amount: int):
    """[ADMIN] Manually add tokens to a user. Usage: .baladd @user <amount>"""
    await economy.handle_admin_modify_command(ctx, member, amount, operation="add")


@bot.command(name="balremove")
@commands.has_permissions(administrator=True)
async def adminremove_command(ctx, member: discord.Member, amount: int):
    """[ADMIN] Manually remove tokens from a user. Usage: .balremove @user <amount>"""
    await economy.handle_admin_modify_command(ctx, member, amount, operation="remove")


@bot.command(name="torture")
async def torture_command(ctx):
    # NOTE: Assuming torture.get_random_torture_method and torture_cooldowns exist
    user_id = ctx.author.id
    current_time = time.time()

    if user_id in torture_cooldowns:
        time_since_last = current_time - torture_cooldowns[user_id]
        if time_since_last < 15:
            return

    torture_cooldowns[user_id] = current_time

    method = torture.get_random_torture_method()

    embed = discord.Embed(
        title=f"🩸 Torture Method: {method['name']}",
        description=method["description"],
        color=discord.Color.dark_red(),
    )

    embed.add_field(name="Origin", value=method["origin"], inline=True)
    embed.add_field(name="Era", value=method["era"], inline=True)

    await ctx.send(embed=embed)


@bot.command(name="time")
async def time_command(ctx, member: discord.Member = None):
    # NOTE: Assuming get_user_timezone exists
    if ctx.message.reference and not member:
        try:
            reply_msg = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            member = reply_msg.author
        except:
            pass

    if not member:
        member = ctx.author

    timezone_name, city = get_user_timezone(member.id)
    if not timezone_name or not city:
        await ctx.send(
            f"❌ {member.display_name} has not set their location yet. Use `.location <city>`."
        )
        return
    try:
        now = datetime.now(ZoneInfo(timezone_name))
        time_str = now.strftime("%-I:%M %p").lower()
        await ctx.send(f"{time_str} in {city}")
    except Exception as e:
        logger.error(f"Error getting time: {e}")
        await ctx.send(f"❌ Error getting time: {e}")


# ============================================================
# DATABASE MAINTENANCE COMMANDS (Admin only)
# ============================================================


@bot.command(name="dbcheck")
async def db_check(ctx):
    # NOTE: Assuming DB_FILE, get_db, load_quotes_from_db, get_user_timezone exist
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    exists = os.path.exists(DB_FILE)
    size = os.path.getsize(DB_FILE) if exists else 0

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM quotes")
            quote_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM activity_hourly")
            activity_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM user_timezones")
            tz_count = c.fetchone()[0]

            await ctx.send(
                f"🗄️ **Database Status**\n"
                f"File: `{DB_FILE}`\n"
                f"Size: {size:,} bytes\n"
                f"Quotes: {quote_count}\n"
                f"Activity Records: {activity_count}\n"
                f"Timezones: {tz_count}"
            )
    except Exception as e:
        await ctx.send(f"❌ Database error: {e}")


@bot.command(name="dbintegrity")
async def db_integrity(ctx):
    # NOTE: Assuming get_db exists
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("PRAGMA integrity_check")
            result = c.fetchone()[0]

            if result == "ok":
                await ctx.send("✅ Database integrity check passed!")
            else:
                await ctx.send(f"⚠️ Database integrity issues: {result}")
    except Exception as e:
        await ctx.send(f"❌ Error checking integrity: {e}")


@bot.command(name="testactivity")
async def test_activity(ctx):
    # NOTE: Assuming log_activity_in_memory exists in activity module
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    from activity import activity_buffer, log_activity_in_memory
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    hour = now.strftime("%H")

    log_activity_in_memory(str(ctx.author.id), hour)
    log_activity_in_memory(str(ctx.author.id), hour)
    log_activity_in_memory("999999999", hour)

    total_hourly = sum(activity_buffer["hourly"].values())
    total_users = sum(activity_buffer["users"].values())

    await ctx.send(
        f"✅ Added 3 test messages to buffer\n"
        f"Buffer hourly: {dict(activity_buffer['hourly'])}\n"
        f"Buffer users: {dict(activity_buffer['users'])}\n"
        f"Total hourly count: {total_hourly}\n"
        f"Total user count: {total_users}"
    )


@bot.command(name="showquotes")
async def show_quotes(ctx):
    # NOTE: Assuming load_quotes_from_db exists
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    quotes = load_quotes_from_db()
    sample = quotes[-3:] if len(quotes) >= 3 else quotes
    await ctx.send(f"Loaded {len(quotes)} quotes.\nLast 3:\n" + "\n".join(sample))


@bot.command(name="dbcheckwrite")
async def db_check_write(ctx, *, quote_text: str = "test write"):
    # NOTE: Assuming get_db, DB_FILE exist
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote_text,))
        await ctx.send(f'✅ Successfully wrote "{quote_text}" to {DB_FILE}')
    except Exception as e:
        logger.error(f"DB write error: {e}")
        await ctx.send(f"❌ Write failed: {e}")


@bot.command(name="flushactivity")
async def flush_activity_manual(ctx):
    # NOTE: Assuming flush_activity_to_db exists in activity module
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    try:
        from activity import flush_activity_to_db

        flush_activity_to_db(None)
        await ctx.send("✅ Activity flushed to database!")
    except Exception as e:
        logger.error(f"Error flushing: {e}")
        await ctx.send(f"❌ Error: {e}")


@bot.command(name="fixdb")
async def fix_db(ctx):
    # NOTE: Assuming DB_FILE, get_db exist
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    if os.path.exists(DB_FILE):
        backup_path = f"{DB_FILE}.bak"
        shutil.copy2(DB_FILE, backup_path)
        await ctx.send(f"📦 Backed up old DB to {backup_path}")

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS quotes")
            c.execute(
                "CREATE TABLE quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)"
            )
        await ctx.send(f"✅ Reinitialized quotes table at {DB_FILE}")
    except Exception as e:
        logger.error(f"Error fixing DB: {e}")
        await ctx.send(f"❌ Error: {e}")


@bot.command(name="archive")
async def archive_forum(ctx, which: str = None):
    # NOTE: Assuming get_forum_channel, ARCHIVE_CATEGORY_ID exist
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    valid_options = ["forum", "forum-livi", "both"]
    if which not in valid_options:
        return await ctx.send(
            "⚠️ Usage:\n"
            "`.archive forum` - Archive #forum\n"
            "`.archive forum-livi` - Archive #forum-livi\n"
            "`.archive both` - Archive both channels"
        )

    guild = ctx.guild
    channels_to_archive = []

    if which == "both":
        channels_to_archive = ["forum", "forum-livi"]
    else:
        channels_to_archive = [which]

    for channel_name in channels_to_archive:
        try:
            old_channel = get_forum_channel(guild, channel_name)

            if not old_channel:
                await ctx.send(f"⚠️ Channel `#{channel_name}` not found. Skipping...")
                continue

            category = old_channel.category
            position = old_channel.position
            now = datetime.now()
            archive_name = f"{channel_name}-{now.strftime('%b-%Y').lower()}"

            await old_channel.edit(name=archive_name)

            ARCHIVE_CATEGORY_ID = 1439078260402159626
            archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)

            if archive_category:
                await old_channel.edit(
                    category=archive_category,
                    sync_permissions=True,
                )
                await ctx.send(
                    f"📦 Channel `#{channel_name}` archived as `#{archive_name}` and moved to archive category"
                )

            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                position=position,
                overwrites=old_channel.overwrites,
                topic=old_channel.topic,
                slowmode_delay=old_channel.slowmode_delay,
                nsfw=old_channel.nsfw,
            )

            await new_channel.send(
                f"✨ **#{channel_name} channel created!** The old channel has been archived."
            )

            logger.info(
                f"{channel_name} archived by {ctx.author} - Old: {old_channel.id}, New: {new_channel.id}"
            )

        except Exception as e:
            logger.error(f"Error archiving {channel_name}: {e}")
            await ctx.send(f"❌ Error archiving `#{channel_name}`: {e}")


@bot.command(name="debug")
@commands.has_permissions(administrator=True)
async def toggle_debug(ctx, state: str = None):
    """Toggle debug mode on/off. When on, only admins can use commands."""
    global DEBUG_MODE

    if state is None:
        await ctx.send(
            f"🔧 Debug mode is currently **{'ON' if DEBUG_MODE else 'OFF'}**."
        )
        return

    state = state.lower()
    if state in ["on", "true", "enable"]:
        DEBUG_MODE = True
        await ctx.send(
            "🧰 Debug mode **enabled** — only administrators can use commands."
        )
    elif state in ["off", "false", "disable"]:
        DEBUG_MODE = False
        await ctx.send("✅ Debug mode **disabled** — all users can use commands again.")
    else:
        await ctx.send("Usage: `!debug on` or `!debug off`")


@bot.check
async def globally_block_during_debug(ctx):
    if ctx.author.guild_permissions.administrator:
        return True
    if DEBUG_MODE:
        await ctx.send("🧱 The spirits are silent…")
        return False
    return True


@bot.event
async def on_error(event, *args, **kwargs):
    """Log errors without stopping the bot"""
    logger.error(f"Error in {event}", exc_info=True)


import atexit


def cleanup_session():
    if bot.aiohttp_session and not bot.aiohttp_session.closed:
        asyncio.run(bot.aiohttp_session.close())


atexit.register(cleanup_session)

if __name__ == "__main__":
    bot.run(TOKEN)
