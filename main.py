"""
Discord Bot Main File - Refactored
Core bot initialization and event handlers only
Commands are organized into cogs/
"""

# --- Standard Library Imports ---
import asyncio
import os
import logging
import colorlog
import time
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Third-Party Imports ---
import discord
from discord.ext import commands

# --- Local Module Imports ---
import tasks
import battle
from items import aggressive_uwu
from config import TOKEN, COMMAND_PREFIX, AUTHORIZED_ROLES
from database import init_db, get_active_effect, remove_active_effect, get_user_timezone
from helpers import extract_gif_url
from database import increment_gif_count
import activity

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

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
bot.aiohttp_session = None
bot.owner_timezone = None
bot.start_time = datetime.now()

# Global state
bot.DEBUG_MODE = False


@bot.event
async def on_ready():
    """Bot startup event: Performs all setup and initializations."""

    logger.info(f"Starting {bot.user} (ID: {bot.user.id})")

    # 1. Setup external services
    if bot.aiohttp_session is None:
        bot.aiohttp_session = aiohttp.ClientSession()

    from api import set_bot_session
    set_bot_session(bot.aiohttp_session)

    # 2. Get owner timezone
    if bot.owner_timezone is None:
        your_user_id = 154814148054745088
        tz, _ = get_user_timezone(your_user_id)
        bot.owner_timezone = tz

    # 3. Initialize Database
    await bot.loop.run_in_executor(None, init_db)
    await bot.loop.run_in_executor(None, battle.init_battle_db)
    logger.info("✅ Database initialized")

    # 4. Load Cogs
    cogs = [
        "cogs.economy_cog",
        "cogs.utility_cog",
        "cogs.quotes_cog",
        "cogs.games_cog",
        "cogs.tarot_cog",
        "cogs.admin_cog",
        "activitycog",
    ]

    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}", exc_info=True)

    # 5. Setup Background Tasks
    if not bot.guilds:
        logger.error("Bot is not in any guilds! Cannot start tasks.")
        main_guild_id = None
    else:
        main_guild_id = bot.guilds[0].id

    if main_guild_id:
        tasks.setup_tasks(bot, main_guild_id)
        logger.info(f"✅ Background tasks started for Guild ID: {main_guild_id}")

    logger.info(f"✅ Bot ready! Logged in as {bot.user}")


# ============================================================
# HELPER FUNCTIONS
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


# ============================================================
# BOT EVENTS
# ============================================================

@bot.event
async def on_message(message):
    """Handle all message events with Curse Enforcement"""
    if message.author.bot:
        await bot.process_commands(message)
        return

    # Check if user has an active Muzzle or UwU effect
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
            # MUZZLE EFFECT
            if effect_name == "muzzle":
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                return  # Block further processing

            # UWU EFFECT
            elif effect_name == "uwu":
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
                        f"**ERROR: Bot lacks permission.** {message.author.display_name}: {transformed_text}"
                    )
                except Exception as e:
                    logger.error(f"Error in UwU mirroring: {e}")

                return  # Block further processing

    # Log activity
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    hour = now.strftime("%H")
    activity.log_activity_in_memory(str(message.author.id), hour)

    # Track GIFs
    gif_url = extract_gif_url(message)
    if gif_url:
        try:
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
    # Admins can use commands anywhere
    if ctx.author.guild_permissions.administrator:
        return True

    # Check debug mode
    if getattr(bot, 'DEBUG_MODE', False):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("🧱 The spirits are silent…")
            return False

    # Allow channels in these channel names
    ALLOWED_CHANNEL_NAMES = ["forum", "forum-livi", "emperor"]

    return ctx.channel.name in ALLOWED_CHANNEL_NAMES


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""

    # Check if the command has a specific, local error handler defined
    if hasattr(ctx.command, "on_error"):
        return

    # Silently ignore cooldown errors
    if isinstance(error, commands.CommandOnCooldown):
        return

    # Ignore unknown commands
    elif isinstance(error, commands.CommandNotFound):
        return

    # Handle specific permission errors
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")

    # Handle all other UNHANDLED errors
    else:
        logger.error(
            f"UNHANDLED COMMAND ERROR in {ctx.command}: {error}", exc_info=True
        )
        await ctx.send(f"❌ An unexpected error occurred: `{type(error).__name__}`")


@bot.event
async def on_error(event, *args, **kwargs):
    """Log errors without stopping the bot"""
    logger.error(f"Error in {event}", exc_info=True)


# ============================================================
# SHUTDOWN HANDLER
# ============================================================

import atexit


def cleanup_session():
    """Cleanup aiohttp session on shutdown"""
    if bot.aiohttp_session and not bot.aiohttp_session.closed:
        asyncio.run(bot.aiohttp_session.close())


atexit.register(cleanup_session)


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run(TOKEN)
