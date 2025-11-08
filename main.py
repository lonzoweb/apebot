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
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
async def on_ready():
    """Bot startup event"""
    init_db()
    init_gif_table()
    logger.info(f"✅ Logged in as {bot.user}")
    tasks.setup_tasks(bot)

@bot.event
async def on_message(message):
    """Track GIFs from messages"""
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Check if message contains a GIF
    gif_url = extract_gif_url(message)
    if gif_url:
        try:
            increment_gif_count(gif_url, message.author.id)
        except Exception as e:
            logger.error(f"Error tracking GIF: {e}")
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down! Try again in {error.retry_after:.1f} seconds.")
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
        if ctx.author.guild_permissions.administrator or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles):
            quote = random.choice(quotes)
            embed = discord.Embed(
                title="📜 Quote",
                description=quote,
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in quotes if keyword.lower() in q.lower()]
        if matches:
            for match in matches[:5]:  # Limit to 5 matches
                embed = discord.Embed(
                    description=f"📜 {match}",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
            if len(matches) > 5:
                await ctx.send(f"📊 Showing 5 of {len(matches)} matches. Be more specific!")
        else:
            await ctx.send(f"🔍 No quotes found containing '{keyword}'")

@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    """Add a new quote (Role required)"""
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        return await ctx.send("🚫 Peasant Detected")
    
    if len(quote_text) > 2000:
        return await ctx.send("❌ Quote too long (max 2000 characters)")
    
    try:
        add_quote_to_db(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"{quote_text}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error adding quote: {e}")
        await ctx.send("❌ Error adding quote")

@bot.command(name="editquote")
async def edit_quote_command(ctx, *, keyword: str):
    """Edit an existing quote (Role required)"""
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = load_quotes_from_db()
    matches = [q for q in quotes if keyword.lower() in q.lower()]
    if not matches:
        await ctx.send(f"🔍 No quotes found containing '{keyword}'")
        return

    # Display matches with numbering
    description = "\n".join(f"{i+1}. {q[:100]}..." if len(q) > 100 else f"{i+1}. {q}" for i, q in enumerate(matches))
    embed = discord.Embed(
        title="Select a quote to edit (reply with number or 'cancel')",
        description=description,
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=60)
        if msg.content.lower() == 'cancel':
            return await ctx.send("❌ Edit cancelled.")
        
        if not msg.content.isdigit() or not (1 <= int(msg.content) <= len(matches)):
            return await ctx.send("❌ Invalid selection. Edit cancelled.")
            
        index = int(msg.content) - 1
        old_quote = matches[index]

        await ctx.send(f"✏️ Enter the new version of the quote (or 'cancel'):")
        new_msg = await bot.wait_for('message', check=check, timeout=120)
        
        if new_msg.content.lower() == 'cancel':
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
        formatted = "\n".join(f"{i+1}. {r[1][:80]}..." if len(r[1]) > 80 else f"{i+1}. {r[1]}" for i, r in enumerate(results))
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
    await ctx.send(f"🗑️ Delete this quote?\n\"{quote_text}\"\nType `yes` to confirm.")

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
        await ctx.send(f"✅ Deleted quote:\n\"{quote_text}\"")
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
    chunks = [quote_text[i:i+1900] for i in range(0, len(quote_text), 1900)]
    
    try:
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"📜 All Quotes (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else "📜 All Quotes",
                description=chunk,
                color=discord.Color.blue()
            )
            await ctx.author.send(embed=embed)
        await ctx.send("📬 Quotes sent to your DM!")
    except discord.Forbidden:
        await ctx.send("⚠️ Cannot DM you. Check privacy settings.")

@bot.command(name="daily")
@commands.cooldown(1, 5, commands.BucketType.user)
async def daily_command(ctx):
    """Show today's quote"""
    if ctx.author.guild_permissions.administrator or any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles):
        daily_quote = tasks.get_daily_quote()
        if daily_quote:
            embed = discord.Embed(
                title="🌅 Blessings to Apeiron",
                description=f"📜 {daily_quote}",
                color=discord.Color.gold()
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
        color=discord.Color.dark_purple()
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
    await ctx.send(f"🎲 **{result}**")

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
    await msg.edit(content=f"**{ctx.author.display_name}:** {question}\n🎱 **{random.choice(responses)}**")

@bot.command(name="tc")
@commands.cooldown(10, 60, commands.BucketType.user)
async def tarot_card(ctx, *, search: str = None):
    """Draw a random tarot card or search for a specific one"""
    if search:
        card_key = tarot.search_card(search)
        if card_key:
            await tarot.send_tarot_card(ctx, card_key=card_key)
        else:
            await ctx.send(f"🔍 No card found matching '{search}'")
    else:
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
        embed = discord.Embed(
            title="Moon Phase",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Current",
            value=f"{phase_emoji} **{phase_name}** ({int(illumination * 100)}% illuminated)\nMoon in: **{current_sign}**",
            inline=False
        )
        
        embed.add_field(
            name="Upcoming",
            value=(
                f"**Next New Moon:** {new_date_str} (in {days_to_new} days)\n"
                f"Moon in: **{new_moon_sign}**\n\n"
                f"**Next Full Moon:** {full_date_str} (in {days_to_full} days)\n"
                f"Moon in: **{full_moon_sign}**"
            ),
            inline=False
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
        
        embed = discord.Embed(
            title="Life Path Number",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Birthday",
            value=formatted_date,
            inline=False
        )
        
        embed.add_field(
            name="Life Path",
            value=f"**{life_path}**" + (" (Master Number)" if is_master else ""),
            inline=False
        )
        
        embed.add_field(
            name="Traits",
            value=traits,
            inline=False
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
    """Show top 10 most sent GIFs"""
    top_gifs = get_top_gifs(limit=10)
    
    if not top_gifs:
        return await ctx.send("📊 No GIFs tracked yet. Send some GIFs!")
    
    # Build leaderboard
    description = ""
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (gif_url, count, last_sent_by) in enumerate(top_gifs, start=1):
        medal = medals[i-1] if i <= 3 else f"{i}."
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
        color=discord.Color.purple()
    )
    
    msg = await ctx.send(embed=embed)
    
    # Add reaction numbers
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i in range(min(len(top_gifs), 10)):
        await msg.add_reaction(reactions[i])
    
    # Wait for reactions
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
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
                replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
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
            title="🔍 Google Lens Reverse Image Search",
            color=discord.Color.blue()
        )
        
        for i, r in enumerate(data["results"], start=1):
            title_truncated = r['title'][:100] if r['title'] else "Untitled"
            field_name = f"{i}. {title_truncated}"
            field_value = f"📌 Source: {r['source']}\n🔗 [View Image]({r['link']})" if r['link'] else f"📌 Source: {r['source']}"
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        if data.get("search_page"):
            embed.add_field(
                name="🌐 Full Search Results",
                value=f"[View on Google Lens]({data['search_page']})",
                inline=False
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
    
    embed = discord.Embed(
        title="📊 Bot Stats",
        color=discord.Color.teal()
    )
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Quotes", value=str(quote_count), inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="blessing")
async def blessing_command(ctx):
    """Send a Blessings message to channels (Role required)"""
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        await ctx.send("🚫 Peasant Detected")
        return

    embed = discord.Embed(
        title="",
        description="**<a:3bluefire:1332813616696524914> Blessings to Apeiron <a:3bluefire:1332813616696524914>**",
        color=discord.Color.gold()
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
async def location_command(ctx, *, args: str):
    """Set your timezone location"""
    args_split = args.split()
    target_member = ctx.author
    location_query = args

    # Check if authorized role and mention is included
    if ctx.message.mentions:
        if has_authorized_role(ctx.author):
            target_member = ctx.message.mentions[0]
            location_query = " ".join(word for word in args_split if not word.startswith("<@"))
        else:
            await ctx.send("🚫 You are not authorized to set other users' locations.")
            return

    timezone_name, city = await lookup_location(location_query)
    if not timezone_name:
        await ctx.send(f"❌ Could not find a location matching '{location_query}'.")
        return

    await ctx.send(f"I found **{city}**. Confirm this as the location for {target_member.display_name}? (yes/no)")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        if msg.content.lower() == "yes":
            set_user_timezone(target_member.id, timezone_name, city)
            await ctx.send(f"✅ Location set for {target_member.display_name} as **{city}**.")
        else:
            await ctx.send("❌ Location setting cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Location setting cancelled.")

@bot.command(name="time")
async def time_command(ctx, member: discord.Member = None):
    """Check time for a user"""
    if not member:
        member = ctx.author
    timezone_name, city = get_user_timezone(member.id)
    if not timezone_name or not city:
        await ctx.send(f"❌ {member.display_name} has not set their location yet. Use `.location <city>`.")
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
    await ctx.send(f"🗄️ DB file: {DB_FILE}\nExists: {exists}\nSize: {size} bytes")

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
        await ctx.send(f"✅ Successfully wrote \"{quote_text}\" to {DB_FILE}")
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
            c.execute("CREATE TABLE quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)")
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
                c_new.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,))
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

# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    bot.run(TOKEN)
