"""
Discord Bot Main File
Contains all bot commands and event handlers
"""

import discord
from discord.ext import commands
import random
import asyncio
import os
import shutil
import sqlite3
import tarot
import logging
import ephem
import hierarchy
import activity
import time
import urllib.parse
import battle
from datetime import timedelta
from datetime import datetime
from zoneinfo import ZoneInfo

# Import from other modules
from config import *
from database import *
from helpers import *
from api import *
import tasks

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
bot_start_time = datetime.now()

# ============================================================
# BOT EVENTS
# ============================================================


@bot.event
async def on_message(message):
    """Handle all message events"""
    # Don't track bot messages
    if message.author.bot:
        await bot.process_commands(message)
        return

    # Log activity with your timezone
    your_user_id = 154814148054745088
    timezone_name, _ = get_user_timezone(your_user_id)

    activity.log_message_activity(
        timestamp=message.created_at,
        user_id=str(message.author.id),
        username=message.author.display_name,
        user_timezone=timezone_name,
    )

    # Track GIFs from messages
    gif_url = extract_gif_url(message)
    if gif_url:
        try:
            increment_gif_count(gif_url, message.author.id)
        except Exception as e:
            logger.error(f"Error tracking GIF: {e}")

    # Track battle messages
    await battle.on_message_during_battle(message)

    # Process commands (must be at the end!)
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    """Track reactions for active battles"""
    # Ignore bot reactions
    if payload.user_id == bot.user.id:
        return

    # Get the channel
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

    # allow channels in these channel names
    ALLOWED_CHANNEL_NAMES = ["forum", "forum-livi", "emperor"]

    return ctx.channel.name in ALLOWED_CHANNEL_NAMES


@bot.event
async def on_ready():
    """Bot startup event"""
    init_db()
    init_gif_table()
    activity.init_activity_db()
    battle.init_battle_db()
    logger.info(f"✅ Logged in as {bot.user}")
    tasks.setup_tasks(bot)


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandOnCooldown):
        pass  # Silently ignore cooldown errors
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {type(error).__name__}")


# ============================================================
# QUOTE COMMANDS
# ============================================================


@bot.command(name="quote")
@commands.cooldown(1, 3, commands.BucketType.user)
async def quote_command(ctx, *, keyword: str = None):
    """Get a random quote or search by keyword"""
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
            for match in matches[:5]:  # Limit to 5 matches
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
    """Add a new quote (Role required)"""
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
    """Edit an existing quote (Role required)"""
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

    # Display matches with numbering
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
    """Delete a quote by keyword (Admin only)"""
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

    # Ask for confirmation
    await ctx.send(f'🗑️ Delete this quote?\n"{quote_text}"\nType `yes` to confirm.')

    def check_confirm(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        confirm = await bot.wait_for("message", timeout=30.0, check=check_confirm)
    except asyncio.TimeoutError:
        return await ctx.send("⌛ Timed out. Quote not deleted.")

    if confirm.content.lower() != "yes":
        return await ctx.send("❎ Cancelled.")

    # Delete confirmed
    try:
        delete_quote_by_id(quote_id)
        await ctx.send(f'✅ Deleted quote:\n"{quote_text}"')
    except Exception as e:
        logger.error(f"Error deleting quote: {e}")
        await ctx.send("❌ Error deleting quote")


@bot.command(name="listquotes")
async def list_quotes(ctx):
    """DM all quotes (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return
    quotes = load_quotes_from_db()
    if not quotes:
        await ctx.send("⚠️ No quotes available.")
        return

    # Split into multiple embeds if too long
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
    """Show today's quote"""
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
    """Look up a term on Urban Dictionary"""
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
    await asyncio.sleep(1)  # Dramatic pause
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 **{result}**")


@bot.command(name="roll")
@commands.cooldown(1, 5, commands.BucketType.user)
async def roll_command(ctx):
    """Roll a random number between 1-33"""
    await asyncio.sleep(0.5)  # Brief pause
    result = random.randint(1, 33)
    await ctx.send(f"{ctx.author.display_name} rolls 🎲 **{result}**")


@bot.command(name="8ball")
@commands.cooldown(1, 6, commands.BucketType.user)
async def eightball_command(ctx, *, question: str = None):
    """Ask the magic 8-ball a question"""
    if not question:
        return await ctx.send("❌ Ask a question cuh.")

    responses = [
        # Affirmative
        "You bet your fucking life.",
        "Absolutely, no doubt about it.",
        "100%. Go for it.",
        "Hell yeah.",
        "Does a bear shit in the woods?",
        "Is water wet cuh? Yes.",
        # Non-committal
        "Maybe, maybe not. Figure it out yourself.",
        "Ask me later, I'm busy.",
        "Unclear. Try again when I care bitch.",
        "Eh, could go either way.",
        "Sheeeeit, ion know",
        # Negative
        "Hell no.",
        "Not a chance in hell.",
        "Absolutely fucking not.",
        "Are you stupid? No.",
        "In your dreams cuh.",
        "Nope. Don't even think about it cuh.",
    ]

    # Send initial message with question
    msg = await ctx.send(f"**{ctx.author.display_name}:** {question}\n🎱 *shaking...*")

    # Dramatic pause (shaking the 8-ball)
    await asyncio.sleep(5)

    # Edit with the answer
    await msg.edit(
        content=f"**{ctx.author.display_name}:** {question}\n🎱 **{random.choice(responses)}**"
    )


import random, time
from datetime import datetime

# In-memory tracking
user_usage = (
    {}
)  # {'day': date, 'count': int, 'last_used': timestamp, 'next_cooldown': float}


@bot.command(name="tc")
async def tarot_card(ctx):
    """Draw a random tarot card with intermittent reinforcement"""
    user_id = ctx.author.id
    now = time.time()
    today = datetime.utcnow().date()

    # --- Admins bypass everything ---
    if ctx.author.guild_permissions.administrator:
        await tarot.send_tarot_card(ctx)
        return

    # --- Placeholder for future role bypass ---
    # bypass_role_name = "Tarot Master"
    # if any(role.name == bypass_role_name for role in ctx.author.roles):
    #     await tarot.send_tarot_card(ctx)
    #     return

    # Initialize/reset user tracking
    if user_id not in user_usage or user_usage[user_id]["day"] != today:
        user_usage[user_id] = {
            "day": today,
            "count": 0,
            "last_used": 0,
            "next_cooldown": None,
        }

    user_data = user_usage[user_id]

    # --- First 2 draws: no cooldown, immediate ---
    if user_data["count"] < 2:
        user_data["count"] += 1
        await tarot.send_tarot_card(ctx)
        return

    # --- Variable-ratio cooldown after first 2 draws ---
    # Generate cooldown if not already set
    if user_data["next_cooldown"] is None:
        user_data["next_cooldown"] = random.triangular(16, 60, 33)

    cooldown = user_data["next_cooldown"]
    time_since_last = now - user_data["last_used"]

    if time_since_last < cooldown:
        # Ambiguous “recharging” message
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

    # Successful draw: reset cooldown for next attempt
    user_data["last_used"] = now
    user_data["count"] += 1
    user_data["next_cooldown"] = None

    # Always random draw
    await tarot.send_tarot_card(ctx)


@bot.command(name="moon")
@commands.cooldown(1, 10, commands.BucketType.user)
async def moon_command(ctx):
    """Show current moon phase and upcoming moons"""
    try:
        # Get current date
        now = ephem.now()

        # Get moon info for current time
        moon = ephem.Moon()
        moon.compute(now)

        # Current phase info
        illumination = moon.phase / 100.0
        phase_name = get_moon_phase_name(illumination)
        phase_emoji = get_moon_phase_emoji(phase_name)

        # Get current zodiac sign
        moon_ecliptic = ephem.Ecliptic(moon)
        current_sign = get_zodiac_sign(moon_ecliptic.lon)

        # Find next new moon
        next_new = ephem.next_new_moon(now)
        new_moon = ephem.Moon()
        new_moon.compute(next_new)
        new_moon_ecliptic = ephem.Ecliptic(new_moon)
        new_moon_sign = get_zodiac_sign(new_moon_ecliptic.lon)
        days_to_new = int((ephem.Date(next_new) - ephem.Date(now)))

        # Find next full moon
        next_full = ephem.next_full_moon(now)
        full_moon = ephem.Moon()
        full_moon.compute(next_full)
        full_moon_ecliptic = ephem.Ecliptic(full_moon)
        full_moon_sign = get_zodiac_sign(full_moon_ecliptic.lon)
        days_to_full = int((ephem.Date(next_full) - ephem.Date(now)))

        # Format dates
        new_date_str = ephem.Date(next_new).datetime().strftime("%B %d, %Y")
        full_date_str = ephem.Date(next_full).datetime().strftime("%B %d, %Y")

        # Build embed
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
    """Calculate Life Path Number from birthdate"""
    if not date:
        return await ctx.send(
            "❌ Please provide a date.\n"
            "**Format:** `.lp MM/DD/YYYY`\n"
            "**Example:** `.lp 05/15/1990`"
        )

    try:
        # Parse date
        parts = date.split("/")
        if len(parts) != 3:
            raise ValueError("Invalid format")

        month = int(parts[0])
        day = int(parts[1])
        year = int(parts[2])

        # Validate
        if not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
            raise ValueError("Invalid date values")

        # Calculate life path
        life_path = calculate_life_path(month, day, year)
        traits = get_life_path_traits(life_path)

        # Format date nicely
        date_obj = datetime(year, month, day)
        formatted_date = date_obj.strftime("%B %d, %Y")

        # Check if master number
        is_master = life_path in [11, 22, 33]

        embed = discord.Embed(title="Life Path Number", color=discord.Color.purple())

        embed.add_field(name="Birthday", value=formatted_date, inline=False)

        embed.add_field(
            name="Life Path",
            value=f"**{life_path}**" + (" (Master Number)" if is_master else ""),
            inline=False,
        )

        embed.add_field(name="Traits", value=traits, inline=False)

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
    """Show top 10 most sent GIFs"""
    top_gifs = get_top_gifs(limit=10)

    if not top_gifs:
        return await ctx.send("📊 No GIFs tracked yet. Send some GIFs!")

    # Build leaderboard
    description = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, (gif_url, count, last_sent_by) in enumerate(top_gifs, start=1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        shortened = shorten_gif_url(gif_url)

        # Try to get username
        try:
            user = await bot.fetch_user(int(last_sent_by))
            username = user.display_name
        except:
            username = "Unknown"

        description += f"{medal} **{count} sends** - `{shortened}` - @{username}\n"

    embed = discord.Embed(
        title="🏆 Top 10 Most Sent GIFs",
        description=description + "\n💡 React 1️⃣-🔟 to see a GIF!",
        color=discord.Color.purple(),
    )

    msg = await ctx.send(embed=embed)

    # Add reaction numbers
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i in range(min(len(top_gifs), 10)):
        await msg.add_reaction(reactions[i])

    # Wait for reactions
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
        pass  # Timeout is fine, just ignore


@bot.command(name="rev")
@commands.cooldown(1, 30, commands.BucketType.user)
async def reverse_command(ctx):
    """Reverse search the most relevant image in chat using Google Lens"""
    async with ctx.channel.typing():
        # Try to pull image from reply first
        image_url = None
        if ctx.message.reference:
            try:
                replied = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                image_url = await extract_image(replied)
            except Exception as e:
                logger.error(f"Error fetching replied message: {e}")

        # If no reply → auto-scan recent chat for image
        if not image_url:
            async for msg in ctx.channel.history(limit=20):
                image_url = await extract_image(msg)
                if image_url:
                    break

        if not image_url:
            return await ctx.reply("⚠️ No image found in the last 20 messages.")

        # Perform Google Lens search
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

        # Format results
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
    """Show bot statistics (Admin only)"""
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
    # If the command is replying to a message → use that text instead
    if ctx.message.reference:
        reply_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        text = reply_msg.content

    # Reject non-text (stickers, gifs, emojis, embeds, etc.)
    if not text or not any(ch.isalnum() for ch in text):
        return await ctx.reply(
            "⚠️ No valid text found to evaluate.", mention_author=False
        )

    # Character limit check (53 characters)
    if len(text) > 53:
        return await ctx.reply("❌ Text exceeds limit.", mention_author=False)

    results = calculate_all_gematria(text)

    from helpers import reverse_reduction_values, reduce_to_single_digit

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

    # Add username in footer (skip for admins)
    EXEMPT_ROLE_ID = None  # Replace with your role ID if you want role exemption

    is_exempt = ctx.author.guild_permissions.administrator
    if EXEMPT_ROLE_ID:
        is_exempt = is_exempt or discord.utils.get(ctx.author.roles, id=EXEMPT_ROLE_ID)

    if not is_exempt:
        embed.set_footer(text=f"{ctx.author.display_name}")

    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="blessing")
async def blessing_command(ctx):
    """Send a Blessings message to channels (Role required)"""
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
    main_channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None
    targets = [c for c in [main_channel, test_channel] if c]
    if not targets:
        await ctx.send("⚠️ No valid channels to send the blessing.")
        return

    for ch in targets:
        await ch.send(embed=embed)
    await ctx.send("✅ Blessings sent to channels.")


@bot.command(name="hierarchy")
@commands.cooldown(5, 60, commands.BucketType.user)
async def hierarchy_command(ctx, *, args: str = None):
    """Fallen angel and demon hierarchy system"""

    # No arguments - show full chart (AUTHORIZED ONLY)
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

    # Parse arguments
    args_lower = args.lower().strip()

    # Check for 'list' command (AUTHORIZED ONLY)
    if args_lower.startswith("list"):
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)
        ):
            return await ctx.send(
                "🚫 Peasant Detected - Hierarchy list is restricted to authorized roles."
            )

        # Extract page number if provided
        parts = args.split()
        page = 1
        if len(parts) > 1 and parts[1].isdigit():
            page = int(parts[1])

        await hierarchy.send_entity_list(ctx, page)
        return

    # Check for 'random' command (EVERYONE)
    if args_lower == "random":
        entity_key = hierarchy.get_random_entity()
        await hierarchy.send_entity_details(ctx, entity_key)
        return

    # Check for 'search' command (EVERYONE)
    if args_lower.startswith("search "):
        keyword = args[7:].strip()  # Remove 'search ' prefix
        if not keyword:
            return await ctx.send(
                "❌ Please provide a search keyword. Usage: `.hierarchy search [keyword]`"
            )

        results = hierarchy.search_hierarchy(keyword)
        await hierarchy.send_search_results(ctx, results)
        return

    # Otherwise, treat as entity name lookup (EVERYONE)
    entity_key = args_lower.replace(" ", "_").replace("-", "_")

    # Try to find the entity
    if entity_key in hierarchy.HIERARCHY_DB:
        await hierarchy.send_entity_details(ctx, entity_key)
    else:
        # Try fuzzy search by name
        results = hierarchy.search_hierarchy(args)
        if results:
            # If exact match found, show it
            for key, entity in results:
                if entity["name"].lower() == args_lower:
                    await hierarchy.send_entity_details(ctx, key)
                    return

            # Otherwise show search results
            await hierarchy.send_search_results(ctx, results)
        else:
            await ctx.send(
                f"❌ No entity found matching '{args}'. Try `.hierarchy search {args}` or `.hierarchy random`"
            )


#  key

# Dictionary to store the last time the command was used
last_used = {}


@bot.command(name="key")
async def kek_command(ctx):
    """Sends a specific sticker 6 times (1 min cooldown for non-admins)"""

    # Check if user is admin
    is_admin = ctx.author.guild_permissions.administrator

    # Check cooldown (only for non-admins)
    if not is_admin:
        current_time = time.time()
        cooldown_duration = 60  # 1 minute in seconds

        if "key" in last_used:
            time_since_last_use = current_time - last_used["key"]
            if time_since_last_use < cooldown_duration:
                return  # Silently ignore the command

    # Replace with your actual sticker ID
    STICKER_ID = (
        1416504837436342324  # Get this from right-clicking the sticker -> Copy ID
    )

    try:
        sticker = await ctx.guild.fetch_sticker(STICKER_ID)

        # Send tribute message for everyone
        await ctx.send(f"{ctx.author.display_name} ʰᵃˢ ᵖᵃᶦᵈ ᵗʳᶦᵇᵘᵗᵉ")

        for _ in range(6):
            await ctx.send(stickers=[sticker])

        # Only update cooldown after successful execution for non-admins
        if not is_admin:
            last_used["key"] = time.time()

    except discord.NotFound:
        await ctx.reply(
            "❌ Sticker not found! Make sure it's from this server.",
            mention_author=False,
        )
    except discord.HTTPException as e:
        await ctx.reply(f"❌ Failed to send sticker: {e}", mention_author=False)


# weather

# Add this at the top with your other dictionaries
weather_user_cooldowns = {}  # Track per-user cooldowns (3 sec)
weather_user_hourly = {}  # Track per-user hourly usage


@bot.command(name="w")
async def weather_command(ctx, *, location: str = None):
    """Gets current weather for a location (zip code, city, neighborhood, etc.)"""

    # If no location provided, try to get user's saved location
    if not location:
        timezone_name, city = get_user_timezone(ctx.author.id)
        if city:
            location = city
        else:
            await ctx.reply(
                "❌ Please provide a location or set your location with `.location <city>`",
                mention_author=False,
            )
            return

    # Check if user is admin
    is_admin = ctx.author.guild_permissions.administrator

    if not is_admin:
        current_time = time.time()
        user_id = ctx.author.id

        # Check per-user cooldown (3 seconds)
        if user_id in weather_user_cooldowns:
            time_since_last = current_time - weather_user_cooldowns[user_id]
            if time_since_last < 3:
                return  # Silently ignore

        # Check per-user hourly limit (30 per hour)
        if user_id not in weather_user_hourly:
            weather_user_hourly[user_id] = []

        # Remove entries older than 1 hour
        weather_user_hourly[user_id] = [
            t for t in weather_user_hourly[user_id] if current_time - t < 3600
        ]

        if len(weather_user_hourly[user_id]) >= 30:
            return  # Silently ignore

        # Update usage tracking
        weather_user_cooldowns[user_id] = current_time
        weather_user_hourly[user_id].append(current_time)

    API_KEY = "904009bb087585331892946d3b7a5386"

    if API_KEY == "YOUR_API_KEY_HERE":
        await ctx.reply("❌ Weather API key not configured!", mention_author=False)
        return

    # Smart format: if it's "city state", convert to "city,state,us"
    location_parts = location.lower().split()
    us_states = {
        "california",
        "ca",
        "texas",
        "tx",
        "florida",
        "fl",
        "new york",
        "ny",
        "pennsylvania",
        "pa",
        "illinois",
        "il",
        "ohio",
        "oh",
        "georgia",
        "ga",
        "north carolina",
        "nc",
        "michigan",
        "mi",
        "new jersey",
        "nj",
        "virginia",
        "va",
        "washington",
        "wa",
        "arizona",
        "az",
        "massachusetts",
        "ma",
        "tennessee",
        "tn",
        "indiana",
        "in",
        "missouri",
        "mo",
        "maryland",
        "md",
        "wisconsin",
        "wi",
        "colorado",
        "co",
        "minnesota",
        "mn",
        "south carolina",
        "sc",
        "alabama",
        "al",
        "louisiana",
        "la",
        "kentucky",
        "ky",
        "oregon",
        "or",
        "oklahoma",
        "ok",
        "connecticut",
        "ct",
        "utah",
        "ut",
        "iowa",
        "ia",
        "nevada",
        "nv",
        "arkansas",
        "ar",
        "mississippi",
        "ms",
        "kansas",
        "ks",
        "new mexico",
        "nm",
        "nebraska",
        "ne",
        "idaho",
        "id",
        "west virginia",
        "wv",
        "hawaii",
        "hi",
        "new hampshire",
        "nh",
        "maine",
        "me",
        "rhode island",
        "ri",
        "montana",
        "mt",
        "delaware",
        "de",
        "south dakota",
        "sd",
        "north dakota",
        "nd",
        "alaska",
        "ak",
        "vermont",
        "vt",
        "wyoming",
        "wy",
    }

    if len(location_parts) == 2 and location_parts[1] in us_states:
        # Convert "stockton california" to "stockton,ca,us"
        location = f"{location_parts[0]},{location_parts[1]},us"

    # URL encode the location to handle spaces
    encoded_location = urllib.parse.quote(location)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_location}&appid={API_KEY}&units=metric"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract weather data
                    location_name = data["name"]
                    country = data["sys"]["country"]
                    temp_c = data["main"]["temp"]
                    temp_f = (temp_c * 9 / 5) + 32
                    condition = data["weather"][0]["description"].title()

                    # Format output
                    weather_msg = f"**{location_name}, {country}**\n{condition} • {temp_f:.1f}°F / {temp_c:.1f}°C"
                    await ctx.send(weather_msg)

                elif response.status == 404:
                    await ctx.reply(
                        f"❌ Location '{location}' not found!", mention_author=False
                    )
                elif response.status == 401:
                    await ctx.reply(
                        "❌ Invalid API key! Check your OpenWeatherMap API key.",
                        mention_author=False,
                    )
                else:
                    await ctx.reply(
                        f"❌ Failed to fetch weather data. Status: {response.status}",
                        mention_author=False,
                    )

    except Exception as e:
        await ctx.reply(f"❌ Error: {e}", mention_author=False)


# ============================================================
# ACTIVITY COMMAND
# ============================================================


@bot.command(name="activity")
async def activity_command(ctx, *, args: str = None):
    """View server activity statistics (Admin only)"""
    try:
        # Admin only check
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send(
                "🚫 Peasant Detected - Activity tracker is for administrators only."
            )

        # No arguments - show help
        if args is None:
            help_text = """
📊 **Activity Tracker Commands**

**View Specific Day:**
`.activity today` - Today's hourly activity
`.activity yesterday` - Yesterday's activity
`.activity monday` - Most recent Monday
`.activity 11/4` - Specific date (MM/DD)

**View Overview:**
`.activity week` - Last 7 days overview
`.activity month` - Last 30 days overview

**Examples:**
`.activity friday` - Last Friday's hourly breakdown
`.activity 11/21` - Nov 21st hourly breakdown
`.activity week` - Daily totals for last 7 days
"""
            embed = discord.Embed(description=help_text, color=discord.Color.blue())
            await ctx.send(embed=embed)
            return

        args_lower = args.lower().strip()

        # Check for overview commands
        if args_lower == "month":
            await activity.send_month_overview(ctx)
            return

        if args_lower == "week":
            await activity.send_week_overview(ctx)
            return

        # Try to parse as date
        date_str = activity.parse_date_input(args, ctx.author.id)

        if date_str:
            await activity.send_day_activity(ctx, date_str)
        else:
            await ctx.send(
                f"❌ Could not parse date '{args}'. Try: `today`, `monday`, `11/4`, or `.activity` for help."
            )
    except Exception as e:
        logger.error(f"Error in activity command: {e}", exc_info=True)
        await ctx.send(f"❌ An error occurred: {type(e).__name__}")


# ---- cmds  # '''
'''
@bot.command(name="commands")
async def commands_command(ctx):
    """Show command list (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return

    commands_list = [
        "**Quote Commands:**",
        "`.quote [keyword]` - Get a random quote or search",
        "`.addquote <quote>` - Add a new quote",
        "`.editquote <keyword>` - Edit an existing quote",
        "`.delquote <keyword>` - Delete a quote",
        "`.daily` - Show today's quote",
        "`.listquotes` - DM all quotes",
        "",
        "**Utility Commands:**",
        "`.rev` - Reverse image search",
        "`.flip` - Flip a coin",
        "`.roll` - Roll 1-33",
        "`.8ball <question>` - Ask the magic 8-ball",
        "`.gifs` - Top 10 most sent GIFs",
        "`.ud <term>` - Urban Dictionary lookup",
        "`.location <city>` - Set your timezone",
        "`.time [@user]` - Check time for user",
        "",
        "**Admin Commands:**",
        "`.stats` - Show bot statistics",
        "`.blessing` - Send blessing message",
        "`.commands` - Show this list"
    ]
    embed = discord.Embed(
        title="📜 Available Commands",
        description="\n".join(commands_list),
        color=discord.Color.blue()
    )
    try:
        await ctx.author.send(embed=embed)
        await ctx.send("📬 I've sent you a DM with the command list!")
    except discord.Forbidden:
        await ctx.send("⚠️ I cannot DM you. Please check your privacy settings.")
--- #
'''
# ============================================================
# TIMEZONE COMMANDS
# ============================================================


@bot.command(name="location")
async def location_command(ctx, *, args: str = None):
    """Set your timezone location"""
    # Check if location provided
    if not args:
        return await ctx.send(
            "❌ Please provide a location. Usage: `.location Los Angeles`"
        )

    args_split = args.split()
    target_member = ctx.author
    location_query = args

    # Check if authorized role and mention is included
    if ctx.message.mentions:
        if has_authorized_role(ctx.author):
            target_member = ctx.message.mentions[0]
            location_query = " ".join(
                word for word in args_split if not word.startswith("<@")
            )
        else:
            await ctx.send("🚫 You are not authorized to set other users' locations.")
            return

    timezone_name, city = await lookup_location(location_query)
    if not timezone_name:
        await ctx.send(f"❌ Could not find a location matching '{location_query}'.")
        return

    await ctx.send(
        f"I found **{city}**. Confirm this as the location for {target_member.display_name}? (yes/no)"
    )

    def check(m):
        return (
            m.author == ctx.author
            and m.channel == ctx.channel
            and m.content.lower() in ["yes", "no"]
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        if msg.content.lower() == "yes":
            set_user_timezone(target_member.id, timezone_name, city)
            await ctx.send(
                f"✅ Location set for {target_member.display_name} as **{city}**."
            )
        else:
            await ctx.send("❌ Location setting cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Location setting cancelled.")


@bot.command(name="time")
async def time_command(ctx, member: discord.Member = None):
    """Check time for a user"""

    # Check if replying to a message
    if ctx.message.reference and not member:
        try:
            reply_msg = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            member = reply_msg.author
        except:
            pass

    # Default to command author if no member specified
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
    """Check database status (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    exists = os.path.exists(DB_FILE)
    size = os.path.getsize(DB_FILE) if exists else 0

    # Check all tables
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Count quotes
            c.execute("SELECT COUNT(*) FROM quotes")
            quote_count = c.fetchone()[0]

            # Count activity records
            c.execute("SELECT COUNT(*) FROM activity_hourly")
            activity_count = c.fetchone()[0]

            # Count timezone records
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
    """Check database integrity (Admin only)"""
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


@bot.command(name="showquotes")
async def show_quotes(ctx):
    """Show sample quotes (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    quotes = load_quotes_from_db()
    sample = quotes[-3:] if len(quotes) >= 3 else quotes
    await ctx.send(f"Loaded {len(quotes)} quotes.\nLast 3:\n" + "\n".join(sample))


@bot.command(name="dbcheckwrite")
async def db_check_write(ctx, *, quote_text: str = "test write"):
    """Test database write (Admin only)"""
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


@bot.command(name="fixdb")
async def fix_db(ctx):
    """Reinitialize database with backup (Admin only)"""
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


@bot.command(name="mergequotes")
async def merge_quotes(ctx):
    """Merge quotes from backup (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    old_db = f"{DB_FILE}.bak"
    if not os.path.exists(old_db):
        return await ctx.send("❌ No backup file found to merge.")

    try:
        conn_new = sqlite3.connect(DB_FILE)
        conn_old = sqlite3.connect(old_db)
        c_new = conn_new.cursor()
        c_old = conn_old.cursor()

        c_old.execute("SELECT quote FROM quotes")
        rows = c_old.fetchall()
        count = 0
        for (quote,) in rows:
            try:
                c_new.execute(
                    "INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,)
                )
                count += 1
            except Exception:
                pass
        conn_new.commit()
        await ctx.send(f"✅ Merged {count} quotes from backup into the new database.")
    except Exception as e:
        logger.error(f"Error merging: {e}")
        await ctx.send(f"❌ Error merging: {e}")
    finally:
        conn_old.close()
        conn_new.close()


# battle cmd


@bot.command(name="vb")
async def battle_command(ctx, *args):
    """Reaction battle system (Admin/Caporegime only to start/stop, everyone can view scoreboard)

    Usage:
    .vb @user1 @user2  - Start battle
    .vb stop           - End current battle
    .vb top            - View scoreboard (everyone)
    """

    # Handle scoreboard (everyone can use)
    if len(args) == 1 and args[0].lower() == "top":
        await battle.show_scoreboard(ctx)
        return

    # Permission check for start/stop: Admin or Caporegime role
    if not (
        ctx.author.guild_permissions.administrator
        or any(role.name == "Caporegime" for role in ctx.author.roles)
    ):
        return await ctx.send("🚫 Peasant Detected")

    # Handle stop command
    if len(args) == 1 and args[0].lower() == "stop":
        await battle.stop_battle(ctx)
        return

    # Check for two mentions to start battle
    if len(ctx.message.mentions) != 2:
        return await ctx.send(
            "⚔️ **Battle Commands**\n\n"
            "`.vb @user1 @user2` - Start a battle (Admin/Caporegime)\n"
            "`.vb stop` - End current battle (Admin/Caporegime)\n"
            "`.vb top` - View scoreboard (Everyone)"
        )

    user1 = ctx.message.mentions[0]
    user2 = ctx.message.mentions[1]

    await battle.start_battle(ctx, user1, user2)


# archive cmd


@bot.command(name="archive")
async def archive_forum(ctx, which: str = None):
    """Archive forum channels and create fresh replacements (Admin only)

    Usage:
    .archive forum       - Archive #forum only
    .archive forum-livi  - Archive #forum-livi only
    .archive both        - Archive both channels
    """

    # Admin only
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")

    # Validate input
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

    # Determine which channels to archive
    if which == "both":
        channels_to_archive = ["forum", "forum-livi"]
    else:
        channels_to_archive = [which]

    # Archive each channel
    for channel_name in channels_to_archive:
        try:
            # Get the channel by exact name
            old_channel = get_forum_channel(guild, channel_name)

            if not old_channel:
                await ctx.send(f"⚠️ Channel `#{channel_name}` not found. Skipping...")
                continue

            # Store channel properties
            category = old_channel.category
            position = old_channel.position

            # Generate archive name with current date
            now = datetime.now()
            archive_name = f"{channel_name}-{now.strftime('%b-%Y').lower()}"  # e.g., "forum-nov-2024"

            # Rename old channel to archive
            await old_channel.edit(name=archive_name)

            # Move to archive category and sync permissions
            ARCHIVE_CATEGORY_ID = 1439078260402159626
            archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)

            if archive_category:
                await old_channel.edit(
                    category=archive_category,
                    sync_permissions=True,  # Inherit category permissions
                )
                await ctx.send(
                    f"📦 Channel `#{channel_name}` archived as `#{archive_name}` and moved to archive category"
                )

            # Create new fresh channel with same settings
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                position=position,
                overwrites=old_channel.overwrites,  # Copy permissions
                topic=old_channel.topic,
                slowmode_delay=old_channel.slowmode_delay,
                nsfw=old_channel.nsfw,
            )

            # Send confirmation in new channel
            await new_channel.send(
                f"✨ **#{channel_name} channel created!** The old channel has been archived."
            )

            logger.info(
                f"{channel_name} archived by {ctx.author} - Old: {old_channel.id}, New: {new_channel.id}"
            )

        except Exception as e:
            logger.error(f"Error archiving {channel_name}: {e}")
            await ctx.send(f"❌ Error archiving `#{channel_name}`: {e}")

    await ctx.send("✅ Archived")


# debug cmd

# Global debug flag
DEBUG_MODE = False


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


# Global check that blocks commands when debug mode is on
@bot.check
async def globally_block_during_debug(ctx):
    # Always allow administrators (so you can turn debug off)
    if ctx.author.guild_permissions.administrator:
        return True

    # Block all other commands if debug mode is active
    if DEBUG_MODE:
        await ctx.send("🧱 The spirits are silent…")
        return False

    return True


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    bot.run(TOKEN)
