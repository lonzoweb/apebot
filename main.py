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
import signal
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
from database import (
    init_db,
    add_active_effect,
    get_all_active_effects,
    remove_active_effect,
    get_user_timezone,
    increment_gif_count,
    get_yap_level,
    has_item
)
from helpers import extract_gif_url
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

# ============================================================
# YAP SYSTEM (Spam Enforcement)
# ============================================================

class YapManager:
    """Manages command frequency tracking with 20s windows."""
    def __init__(self):
        self.usage = {} # {user_id: [timestamps]}

    def check_spam(self, user_id: int, is_gold: bool) -> tuple[bool, int]:
        """Returns (triggered_muzzle, duration_sec)."""
        now = time.time()
        limit = 10 if is_gold else 5
        window = 20
        duration = 60 if is_gold else 180 # 1m or 3m
        
        if user_id not in self.usage:
            self.usage[user_id] = []
        
        # Clean old timestamps
        self.usage[user_id] = [t for t in self.usage[user_id] if now - t < window]
        self.usage[user_id].append(now)
        
        if len(self.usage[user_id]) >= limit:
            return True, duration
        return False, 0

bot.yap_manager = YapManager()


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
        tz, _ = await get_user_timezone(your_user_id)
        bot.owner_timezone = tz

    # 3. Initialize Database
    await init_db()
    await battle.init_battle_db()
    logger.info("✅ Database initialized")

    # 4. Load Cogs
    cogs = [
        "cogs.economy_cog",
        "cogs.utility_cog",
        "cogs.quotes_cog",
        "cogs.games_cog",
        "cogs.tarot_cog",
        "cogs.admin_cog",
        "cogs.image_cog",
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


async def get_log_channel(guild):
    """Finds a log channel named 'bot-logs' or 'system-logs'."""
    if not guild: return None
    return discord.utils.get(guild.text_channels, name="bot-logs") or \
           discord.utils.get(guild.text_channels, name="system-logs")


# ============================================================
# BOT EVENTS
# ============================================================


@bot.event
async def on_message(message):
    """Handle all message events with Curse Enforcement"""
    if message.author.bot:
        await bot.process_commands(message)
        return

    # Check for active Muzzle or UwU effects
    effects = await get_all_active_effects(message.author.id)
    is_muzzled = False
    is_uwu = False

    for effect_name, expiration_time in effects:
        if time.time() > expiration_time:
            await remove_active_effect(message.author.id, effect_name)
            continue
        
        if effect_name == "muzzle":
            is_muzzled = True
        elif effect_name == "uwu":
            is_uwu = True

    if is_muzzled:
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        return

    if is_uwu:
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        transformed_text = aggressive_uwu(message.content)
        try:
            if transformed_text:
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
        except Exception as e:
            logger.error(f"Error in UwU webhook: {e}")
        return

    # Log activity
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    hour = now.strftime("%H")
    activity.log_activity_in_memory(str(message.author.id), hour)

    # Track GIFs
    gif_url = extract_gif_url(message)
    if gif_url:
        try:
            await increment_gif_count(gif_url, message.author.id)
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
async def globally_block_commands(ctx):
    """Block all commands except in allowed channels or if muzzled/uwud."""
    # Admins and Capos can use commands anywhere and are immune to curses/spam checks
    is_capo = any(role.name == "Capo" for role in ctx.author.roles)
    if ctx.author.guild_permissions.administrator or is_capo:
        return True

    # Check debug mode
    if getattr(bot, "DEBUG_MODE", False):
        return False

    # Allow channels in these channel names
    ALLOWED_CHANNEL_NAMES = ["forum", "forum-livi", "bot-logs"]
    if ctx.channel.name not in ALLOWED_CHANNEL_NAMES:
        return False

    # Block if muzzled or uwud
    effects = await get_all_active_effects(ctx.author.id)
    for effect_name, expiration in effects:
        if time.time() < expiration and effect_name in ["muzzle", "uwu"]:
            return False

    # YAP SYSTEM (20s Window)
    is_gold = await has_item(ctx.author.id, "gold_card")
    triggered, duration = bot.yap_manager.check_spam(ctx.author.id, is_gold)
    if triggered:
        await add_active_effect(ctx.author.id, "muzzle", duration)
        msg = "for yapping" if not is_gold else "for excessive yapping"
        mins = int(duration / 60)
        await ctx.reply(f"{ctx.author.mention} muzzled for {mins}m {msg}.", mention_author=False)
        return False

    return True


@bot.tree.interaction_check
async def global_interaction_check(interaction: discord.Interaction):
    """Global check for slash commands - block muzzled/uwud users."""
    if interaction.user.guild_permissions.administrator:
        return True

    effects = await get_all_active_effects(interaction.user.id)
    for effect_name, expiration in effects:
        if time.time() < expiration and effect_name in ["muzzle", "uwu"]:
            await interaction.response.send_message(
                "❌ Your voice is currently suppressed.", ephemeral=True
            )
            return False
    return True


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""

    # Check if the command has a specific, local error handler defined
    if hasattr(ctx.command, "on_error"):
        return

    # Cooldown feedback
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        time_hint = f"{int(minutes)}m {int(seconds)}s" if minutes > 0 else f"{int(seconds)}s"
        return await ctx.reply(
            f"⏳ **PATIENCE.** The shadows need time to settle. Try again in `{time_hint}`.",
            mention_author=False,
            delete_after=10
        )

    # Ignore unknown commands
    elif isinstance(error, commands.CommandNotFound):
        return

    # Handle specific permission errors
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")

    # Silence unauthorized channel errors
    elif isinstance(error, commands.CheckFailure):
        return

    # REDIRECT ERRORS TO LOGS (with simple rate limiting to prevent 429s)
    elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound, commands.CommandInvokeError)):
        # Simple local rate limiting for errors
        if not hasattr(bot, "_error_cooldowns"):
            bot._error_cooldowns = {}
        
        error_key = f"{ctx.command.name}:{str(error)}"
        now = time.time()
        if now - bot._error_cooldowns.get(error_key, 0) < 60:
            return # Don't spam same error for same command more than once per minute

        bot._error_cooldowns[error_key] = now

        log_channel = await get_log_channel(ctx.guild)
        if log_channel:
            embed = discord.Embed(
                title=f"⚠️ System Error: {type(error).__name__}",
                description=f"**User**: {ctx.author.mention} ({ctx.author.id})\n**Command**: `{ctx.message.content}`\n**Error**: `{error}`",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)
        
        # Don't show technical MemberNotFound or InvokeErrors in public
        if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            return await ctx.reply("❌ That soul is not found in this realm.", mention_author=False)
        return # Silence CommandInvokeError in public

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

async def shutdown(sig, loop):
    """Gracefully shutdown the bot and cleanup resources"""
    logger.info(f"🛑 Received signal {sig.name}, starting graceful shutdown...")
    
    # 0. Flush activity data
    try:
        from activity import flush_activity_to_db
        await flush_activity_to_db()
        logger.info("📦 Activity data flushed to database.")
    except Exception as e:
        logger.error(f"Failed to flush activity on shutdown: {e}")

    # 1. Stop the bot (disconnects from Discord)
    if not bot.is_closed():
        await bot.close()
        logger.info("📡 Discord connection closed.")
    
    # 2. Close aiohttp session
    if bot.aiohttp_session and not bot.aiohttp_session.closed:
        await bot.aiohttp_session.close()
        logger.info("🌐 HTTP session closed.")
    
    # 3. Cancel all remaining tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"🧹 Cancelling {len(tasks)} pending tasks...")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    loop.stop()
    logger.info("✨ Shutdown complete.")


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    logger.info("Starting bot...")
    
    loop = asyncio.get_event_loop()
    
    # Register signal handlers for SIGINT (Ctrl+C) and SIGTERM (Railway/Docker)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
        except NotImplementedError:
            # Fallback for Windows if needed, though Railway is Linux
            pass

    try:
        loop.run_until_complete(bot.start(TOKEN))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if not loop.is_closed():
            loop.close()
