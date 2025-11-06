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
from bs4 import BeautifulSoup
import urllib.parse
import tempfile


# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
OPENCAGE_KEY = os.getenv("OPENCAGE_KEY")
if not OPENCAGE_KEY:
    raise ValueError("OPENCAGE_KEY environment variable is missing!")
    
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
bot_start_time = time.time()

# ---- DATABASE ----

def init_db():
    conn = sqlite3.connect(DB_FILE)
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
    conn.commit()
    conn.close()

def load_quotes_from_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT quote FROM quotes")
    quotes = [row[0] for row in c.fetchall()]
    conn.close()
    return quotes

def add_quote_to_db(quote):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,))
    conn.commit()
    conn.close()

def update_quote_in_db(old_quote, new_quote):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE quotes SET quote = ? WHERE quote = ?", (new_quote, old_quote))
    conn.commit()
    conn.close()

def get_user_timezone(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT timezone, city FROM user_timezones WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def set_user_timezone(user_id, timezone_str, city):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_timezones (user_id, timezone, city) VALUES (?, ?, ?)",
              (str(user_id), timezone_str, city))
    conn.commit()
    conn.close()

# ---- HELPER ----

# ---- reverse ----
# ---- helpers.py ----
import aiohttp
from bs4 import BeautifulSoup
import tempfile
import os
from urllib.parse import quote_plus

async def yandex_fetch_similar(image_url, limit=3):
    """
    Uploads the image to Yandex and fetches the top `limit` visually similar images.
    Returns list of dicts: {'title', 'domain', 'link'}
    """
    results = []

    # Download the image to a temp file
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status != 200:
                return {"results": [], "search_page": ""}
            img_bytes = await resp.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('upfile', open(tmp_path, 'rb'), filename=os.path.basename(tmp_path))
            # Upload image
            async with session.post("https://yandex.com/images/search?rpt=imageview", data=form) as resp:
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # Grab first few "similar images" cards
        # These are often in <div class="CbirSimilar-Item"> or similar classes
        similar_items = soup.select("a.CbirSimilar-Item") or soup.select("a.serp-item__link")

        for item in similar_items[:limit]:
            link = item.get("href")
            title = item.get("title") or "No title"
            domain = link.split("/")[2] if link and link.startswith("http") else "Unknown"
            results.append({"title": title, "domain": domain, "link": link})

        search_page = f"https://yandex.com/images/search?rpt=imageview&url={quote_plus(image_url)}"

        return {"results": results, "search_page": search_page}

    finally:
        os.remove(tmp_path)


# ---- other ----

async def send_random_quote(channel, blessing=False):
    global daily_quote_of_the_day
    quotes = load_quotes_from_db()
    if not quotes:
        print("⚠️ No quotes in DB")
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
    url = f"https://api.opencagedata.com/geocode/v1/json?q={query}&key={OPENCAGE_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
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
            if embed.thumbnail:
                return embed.thumbnail.url
            if embed.image:
                return embed.image.url

    return None

# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- COMMANDS ----

import aiohttp

@bot.command(name="ud")
async def urban_command(ctx, *, term: str):
    url = f"https://api.urbandictionary.com/v0/define?term={term}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
    if not data.get("list"):
        await ctx.send(f"No definition found for **{term}**.")
        return
    first = data["list"][0]
    definition = first["definition"]
    example   = first.get("example", "")
    embed = discord.Embed(
        title=f"Definition of {term}",
        description=f"{definition}\n\n*Example: {example}*",
        color=discord.Color.dark_purple()
    )
    await ctx.send(embed=embed)
    
@bot.command(name="quote")
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
            for match in matches:
                embed = discord.Embed(
                    description=f"📜 {match}",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"🔍 No quotes found containing “{keyword}.”")

@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    if ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles):
        add_quote_to_db(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"{quote_text}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="editquote")
async def edit_quote_command(ctx, *, keyword: str):
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = load_quotes_from_db()
    matches = [q for q in quotes if keyword.lower() in q.lower()]
    if not matches:
        await ctx.send(f"🔍 No quotes found containing “{keyword}.”")
        return

    # Display matches with numbering
    description = "\n".join(f"{i+1}. {q}" for i, q in enumerate(matches))
    embed = discord.Embed(
        title="Select a quote to edit (reply with number)",
        description=description,
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= len(matches)

    try:
        msg = await bot.wait_for('message', check=check, timeout=60)
        index = int(msg.content) - 1
        old_quote = matches[index]

        await ctx.send(f"✏️ Enter the new version of the quote:")
        new_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=120)
        new_quote = new_msg.content.strip()
        update_quote_in_db(old_quote, new_quote)
        await ctx.send(f"✅ Quote updated.")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Edit cancelled.")

@bot.command(name="daily")
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
    embed = discord.Embed(
        title="📜 All Quotes",
        description="\n".join(quotes),
        color=discord.Color.blue()
    )
    try:
        await ctx.author.send(embed=embed)
        await ctx.send("📬 Quotes sent to your DM!")
    except discord.Forbidden:
        await ctx.send("⚠️ Cannot DM you. Check privacy settings.")

@bot.command(name="stats")
async def stats_command(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return
    uptime_seconds = int(time.time() - bot_start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    embed = discord.Embed(
        title="📊 Bot Stats",
        description=f"Uptime: {hours}h {minutes}m {seconds}s",
        color=discord.Color.teal()
    )
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
        ".quote [keyword] - Get a random quote or search by keyword",
        ".addquote <quote> - Add a new quote (Role required)",
        ".editquote <keyword> - Edit an existing quote (Role required)",
        ".daily - Show today's quote",
        ".listquotes - DM all quotes (Admin only)",
        ".stats - Show bot stats (Admin only)",
        ".blessing - Send a Blessings message to channels",
        ".commands - Show this command list"
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

# ---- reverse command ----

@bot.command(name="rev")
async def reverse_command(ctx):
    async with ctx.typing():
        # Try reply first
        image_url = None
        if ctx.message.reference:
            try:
                replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                image_url = await extract_image(replied)
            except:
                pass

        # Scan last 20 messages if no reply
        if not image_url:
            async for msg in ctx.channel.history(limit=20):
                image_url = await extract_image(msg)
                if image_url:
                    break

        if not image_url:
            return await ctx.reply("⚠️ No image found in the last 20 messages.")

        # Perform Yandex similar images search
        data = await yandex_fetch_similar(image_url, limit=3)

        if not data["results"]:
            return await ctx.reply("❌ No similar images found.")

        text = "**🔍 Top Similar Images (Yandex)**\n\n"
        for i, r in enumerate(data["results"], start=1):
            text += f"**{i}.** `{r['title']}`\n🌍 {r['domain']}\n🔗 <{r['link']}>\n\n"

        text += f"📸 Full search → <{data['search_page']}>"

        await ctx.reply(text)

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
        return m.author == ctx.author and m.content.lower() in ["yes", "no"]

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
        await ctx.send(f"❌ Error getting time: {e}")

# ---- UTIL CMDS ----

@bot.command(name="dbcheck")
async def db_check(ctx):
    import os
    exists = os.path.exists(DB_FILE)
    size = os.path.getsize(DB_FILE) if exists else 0
    await ctx.send(f"🗄️ DB file: {DB_FILE}\nExists: {exists}\nSize: {size} bytes")

@bot.command(name="showquotes")
async def show_quotes(ctx):
    quotes = load_quotes_from_db()
    await ctx.send(f"Loaded {len(quotes)} quotes.\nExample:\n{quotes[-3:]}")
    
@bot.command(name="delquote")
async def delete_quote(ctx, *, keyword: str):
    """Delete a quote by keyword with confirmation."""
    import asyncio
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, quote FROM quotes WHERE quote LIKE ?", (f"%{keyword}%",))
    results = c.fetchall()
    conn.close()

    if not results:
        await ctx.send(f"🔍 No quotes found containing “{keyword}.”")
        return

    if len(results) > 1:
        formatted = "\n".join(f"{i+1}. {r[1][:80]}" for i, r in enumerate(results))
        await ctx.send(
            f"⚠️ Multiple quotes found containing “{keyword}.”\n"
            f"Type the number of the one you want to delete (1–{len(results)}), or `cancel`."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            reply = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⌛ Timed out. No quotes deleted.")
            return

        if reply.content.lower() == "cancel":
            await ctx.send("❎ Cancelled.")
            return

        if not reply.content.isdigit() or not (1 <= int(reply.content) <= len(results)):
            await ctx.send("❌ Invalid selection. Cancelled.")
            return

        quote_id, quote_text = results[int(reply.content) - 1]
    else:
        quote_id, quote_text = results[0]

    # Ask for typed confirmation
    await ctx.send(f"🗑️ Delete this quote?\n“{quote_text}”\nType `yes` to confirm.")

    def check_confirm(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        confirm = await bot.wait_for("message", timeout=30.0, check=check_confirm)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timed out. Quote not deleted.")
        return

    if confirm.content.lower() != "yes":
        await ctx.send("❎ Cancelled.")
        return

    # Delete confirmed
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()

    await ctx.send(f"✅ Deleted quote:\n“{quote_text}”")
    
@bot.command(name="dbcheckwrite")
async def db_check_write(ctx, *, quote_text: str = "test write"):
    import sqlite3, os
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote_text,))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ Successfully wrote “{quote_text}” to {DB_FILE}")
    except Exception as e:
        await ctx.send(f"❌ Write failed: {e}")

@bot.command(name="fixdb")
async def fix_db(ctx):
    import shutil
    if os.path.exists(DB_FILE):
        backup_path = f"{DB_FILE}.bak"
        shutil.copy2(DB_FILE, backup_path)
        await ctx.send(f"📦 Backed up old DB to {backup_path}")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS quotes")
    c.execute("CREATE TABLE quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)")
    conn.commit()
    conn.close()
    await ctx.send(f"✅ Reinitialized quotes table at {DB_FILE}")

@bot.command(name="mergequotes")
async def merge_quotes(ctx):
    import sqlite3, os, shutil
    old_db = f"{DB_FILE}.bak"
    if not os.path.exists(old_db):
        await ctx.send("❌ No backup file found to merge.")
        return

    conn_new = sqlite3.connect(DB_FILE)
    conn_old = sqlite3.connect(old_db)
    c_new = conn_new.cursor()
    c_old = conn_old.cursor()

    try:
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
        print("⚠️ No valid channels found for daily quote.")
        return

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
            print("✅ Sent 10AM quote")

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
        print("✅ Sent 6PM quote")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")

bot.run(TOKEN)
