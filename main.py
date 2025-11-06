import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import sqlite3
import time
import json
import shutil
import io
import aiohttp
import urllib.parse
import tempfile
import logging
from contextlib import contextmanager

# ==== LOGGING SETUP ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
OPENCAGE_KEY = os.getenv("OPENCAGE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

if not OPENCAGE_KEY:
    raise ValueError("OPENCAGE_KEY environment variable is missing!")
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY environment variable is missing!")
    
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo", "Caporegime"]
DAILY_COMMAND_ROLE = "Patrizio"  # role for using .daily
ROLE_ADD_QUOTE = "Caporegime"    # Only this role or admin can add/edit quotes

DB_FILE = "/app/data/quotes.db"  # Make sure this path matches Railway volume
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None
bot_start_time = datetime.now()

# ---- DATABASE ----

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        # Quotes table
        c.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT UNIQUE
            )
        """)
        # Timezone table
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_timezones (
                user_id TEXT PRIMARY KEY,
                timezone TEXT,
                city TEXT
            )
        """)

def load_quotes_from_db():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT quote FROM quotes")
            quotes = [row[0] for row in c.fetchall()]
            return quotes
    except Exception as e:
        logger.error(f"Error loading quotes: {e}")
        return []

def add_quote_to_db(quote):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,))

def update_quote_in_db(old_quote, new_quote):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE quotes SET quote = ? WHERE quote = ?", (new_quote, old_quote))

def get_user_timezone(user_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT timezone, city FROM user_timezones WHERE user_id = ?", (str(user_id),))
            row = c.fetchone()
            if row:
                return row[0], row[1]
    except Exception as e:
        logger.error(f"Error getting user timezone: {e}")
    return None, None

def set_user_timezone(user_id, timezone_str, city):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_timezones (user_id, timezone, city) VALUES (?, ?, ?)",
                  (str(user_id), timezone_str, city))

# ---- HELPER FUNCTIONS ----

async def google_lens_fetch_results(image_url: str, limit: int = 3):
    """
    Fetch reverse image search results from Google Lens via SerpApi.
    Returns dict with 'results' (list) and 'search_page' (str)
    """
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY environment variable not set")

    search_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": SERPAPI_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"SerpApi returned HTTP {resp.status}: {error_text[:200]}")
                data = await resp.json()
    except asyncio.TimeoutError:
        raise RuntimeError("Request to SerpApi timed out")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Network error: {e}")

    # Parse results from Google Lens
    results = []
    visual_matches = data.get("visual_matches", [])
    
    for match in visual_matches[:limit]:
        title = match.get("title", "Untitled")
        link = match.get("link", "")
        source = match.get("source", "Unknown source")
        thumbnail = match.get("thumbnail", "")
        
        results.append({
            "title": title,
            "link": link,
            "thumbnail": thumbnail,
            "source": source
        })

    search_metadata = data.get("search_metadata", {})
    search_page = search_metadata.get("google_lens_url", "")

    return {
        "results": results,
        "search_page": search_page
    }

async def send_random_quote(channel, blessing=False):
    global daily_quote_of_the_day
    quotes = load_quotes_from_db()
    if not quotes:
        logger.warning("No quotes in database")
        return
    daily_quote_of_the_day = random.choice(quotes)
    title = "🌅 Blessings to Apeiron" if blessing else None
    embed = discord.Embed(
        title=title,
        description=f"📜 {daily_quote_of_the_day}",
        color=discord.Color.gold() if blessing else discord.Color.dark_gold()
    )
    embed.set_footer(text="🕊️ Daily Quote" if blessing else "🌇 Quote")
    await channel.send(embed=embed)
    
async def lookup_location(query):
    url = f"https://api.opencagedata.com/geocode/v1/json"
    params = {"q": query, "key": OPENCAGE_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    logger.error(f"OpenCage API returned {resp.status}")
                    return None, None
                data = await resp.json()
    except asyncio.TimeoutError:
        logger.error("OpenCage API timeout")
        return None, None
    except Exception as e:
        logger.error(f"OpenCage API error: {e}")
        return None, None
        
    if data.get("results"):
        first = data["results"][0]
        timezone_name = first["annotations"]["timezone"]["name"]
        components = first["components"]
        city = components.get("city") or components.get("town") or components.get("village") or components.get("state") or query
        return timezone_name, city
    return None, None

def has_authorized_role(member):
    return any(role.name in AUTHORIZED_ROLES for role in member.roles) or member.guild_permissions.administrator

async def extract_image(message):
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image"):
                return att.url

    if message.embeds:
        for embed in message.embeds:
            if embed.image:
                return embed.image.url
            if embed.thumbnail:
                return embed.thumbnail.url

    return None

# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    logger.info(f"✅ Logged in as {bot.user}")
    daily_quote.start()

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down! Try again in {error.retry_after:.1f} seconds.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {type(error).__name__}")

# ---- COMMANDS ----

@bot.command(name="ud")
@commands.cooldown(1, 5, commands.BucketType.user)
async def urban_command(ctx, *, term: str):
    """Look up a term on Urban Dictionary"""
    if len(term) > 100:
        return await ctx.send("❌ Term too long (max 100 characters)")
    
    url = "https://api.urbandictionary.com/v0/define"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"term": term}, timeout=10) as resp:
                if resp.status != 200:
                    return await ctx.send(f"❌ API returned error {resp.status}")
                data = await resp.json()
    except asyncio.TimeoutError:
        return await ctx.send("❌ Request timed out")
    except Exception as e:
        logger.error(f"Urban Dictionary error: {e}")
        return await ctx.send("❌ An error occurred")
    
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
    
@bot.command(name="quote")
@commands.cooldown(1, 3, commands.BucketType.user)
async def quote_command(ctx, *, keyword: str = None):
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
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = load_quotes_from_db()
    matches = [q for q in quotes if keyword.lower() in q.lower()]
    if not matches:
        await ctx.send(f"🔍 No quotes found containing "{keyword}."")
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

@bot.command(name="daily")
@commands.cooldown(1, 5, commands.BucketType.user)
async def daily_command(ctx):
    if ctx.author.guild_permissions.administrator or any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles):
        if daily_quote_of_the_day:
            embed = discord.Embed(
                title="🌅 Blessings to Apeiron",
                description=f"📜 {daily_quote_of_the_day}",
                color=discord.Color.gold()
            )
            embed.set_footer(text="🕊️ Daily Quote Recall")
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="listquotes")
async def list_quotes(ctx):
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

@bot.command(name="stats")
async def stats_command(ctx):
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

@bot.command(name="commands")
async def commands_command(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return

    commands_list = [
        "`.quote [keyword]` - Get a random quote or search by keyword",
        "`.addquote <quote>` - Add a new quote (Role required)",
        "`.editquote <keyword>` - Edit an existing quote (Role required)",
        "`.delquote <keyword>` - Delete a quote (Admin only)",
        "`.daily` - Show today's quote",
        "`.listquotes` - DM all quotes (Admin only)",
        "`.stats` - Show bot stats (Admin only)",
        "`.blessing` - Send a Blessings message to channels",
        "`.rev` - Reverse image search (Google Lens)",
        "`.location <city>` - Set your timezone location",
        "`.time [@user]` - Check time for user",
        "`.ud <term>` - Urban Dictionary lookup",
        "`.commands` - Show this command list"
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

# ---- REVERSE IMAGE SEARCH ----
@bot.command(name="rev")
@commands.cooldown(1, 10, commands.BucketType.user)
async def reverse_command(ctx):
    """Reverse search the most relevant image in chat using Google Lens (via SerpApi)."""
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

        # Format results with embeds
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

# ---- LOCATION COMMAND ----
@bot.command(name="location")
async def location_command(ctx, *, args: str):
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

# ---- TIME COMMAND ----
@bot.command(name="time")
async def time_command(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    timezone_name, city = get_user_timezone(member.id)
    if not timezone_name or not city:
        await ctx.send(f"❌ {member.display_name} has not set their location yet. Use `.location <city>`.")
        return
    try:
        now = datetime.now(ZoneInfo(timezone_name))
        time_str = now.strftime("%-I:%M %p").lower()  # 12-hour format with am/pm
        await ctx.send(f"{time_str} in {city}")
    except Exception as e:
        logger.error(f"Error getting time: {e}")
        await ctx.send(f"❌ Error getting time: {e}")

# ---- UTIL CMDS ----

@bot.command(name="dbcheck")
async def db_check(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    exists = os.path.exists(DB_FILE)
    size = os.path.getsize(DB_FILE) if exists else 0
    await ctx.send(f"🗄️ DB file: {DB_FILE}\nExists: {exists}\nSize: {size} bytes")

@bot.command(name="showquotes")
async def show_quotes(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    quotes = load_quotes_from_db()
    sample = quotes[-3:] if len(quotes) >= 3 else quotes
    await ctx.send(f"Loaded {len(quotes)} quotes.\nLast 3:\n" + "\n".join(sample))
    
@bot.command(name="delquote")
async def delete_quote(ctx, *, keyword: str):
    """Delete a quote by keyword with confirmation."""
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, quote FROM quotes WHERE quote LIKE ?", (f"%{keyword}%",))
            results = c.fetchall()
    except Exception as e:
        logger.error(f"Error searching quotes: {e}")
        return await ctx.send("❌ Database error")

    if not results:
        return await ctx.send(f"🔍 No quotes found containing "{keyword}."")

    if len(results) > 1:
        formatted = "\n".join(f"{i+1}. {r[1][:80]}..." if len(r[1]) > 80 else f"{i+1}. {r[1]}" for i, r in enumerate(results))
        await ctx.send(
            f"⚠️ Multiple quotes found containing "{keyword}."\n{formatted}\n"
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

    # Ask for typed confirmation
    await ctx.send(f"🗑️ Delete this quote?\n"{quote_text}"\nType `yes` to confirm.")

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
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        await ctx.send(f"✅ Deleted quote:\n"{quote_text}"")
    except Exception as e:
        logger.error(f"Error deleting quote: {e}")
        await ctx.send("❌ Error deleting quote")
    
@bot.command(name="dbcheckwrite")
async def db_check_write(ctx, *, quote_text: str = "test write"):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("🚫 Peasant Detected")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote_text,))
        await ctx.send(f"✅ Successfully wrote "{quote_text}" to {DB_FILE}")
    except Exception as e:
        logger.error(f"DB write error: {e}")
        await ctx.send(f"❌ Write failed: {e}")

@bot.command(name="fixdb")
async def fix_db(ctx):
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

# ---- DAILY AUTO QUOTE ----
@tasks.loop(minutes=1)
async def daily_quote():
    global daily_quote_of_the_day
    main_channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None
    if not main_channel and not test_channel:
        logger.warning("No valid channels found for daily quote.")
        return

    try:
        now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
        current_time = now_pt.strftime("%H:%M")

        # Morning (10 AM PT)
        if current_time == "10:00":
            quotes = load_quotes_from_db()
            if quotes:
                daily_quote_of_the_day = random.choice(quotes)
                embed = discord.Embed(
                    title="🌅 Blessings to Apeiron",
                    description=f"📜 {daily_quote_of_the_day}",
                    color=discord.Color.gold()
                )
                embed.set_footer(text="🕊️ Quote")
                for ch in [main_channel, test_channel]:
                    if ch:
                        await ch.send(embed=embed)
                logger.info("✅ Sent 10AM quote")

        # Evening (6 PM PT)
        elif current_time == "18:00" and daily_quote_of_the_day:
            embed = discord.Embed(
                description=f"📜 {daily_quote_of_the_day}",
                color=discord.Color.dark_gold()
            )
            embed.set_footer(text="🌇 Quote")
            for ch in [main_channel, test_channel]:
                if ch:
                    await ch.send(embed=embed)
            logger.info("✅ Sent 6PM quote")
    except Exception as e:
        logger.error(f"Error in daily_quote task: {e}")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    logger.info("⏳ Daily quote task started")

# ---- RUN BOT ----
if __name__ == "__main__":
    bot.run(TOKEN)
