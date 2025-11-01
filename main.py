import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import sqlite3
import time
import aiohttp

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
    # Try original query
    timezone_name, city = await try_lookup(query)
    if timezone_name:
        return timezone_name, city

    # Fallback 1: remove numbers (likely ZIP)
    import re
    query_no_numbers = re.sub(r"\d+", "", query).strip()
    if query_no_numbers != query:
        timezone_name, city = await try_lookup(query_no_numbers)
        if timezone_name:
            return timezone_name, city

    # Fallback 2: just first word (maybe city only)
    first_word = query.split()[0]
    if first_word.lower() != query.lower():
        timezone_name, city = await try_lookup(first_word)
        if timezone_name:
            return timezone_name, city

    # Nothing found
    return None, None

async def try_lookup(query):
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

# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- COMMANDS ----

# ---- QUOTES & EXISTING COMMANDS ----
# ... Keep all your existing commands here (ud, quote, addquote, editquote, daily, listquotes, stats, blessing, commands) ...
# (The code remains exactly as you pasted it earlier)

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
            await ctx.send("🚫 Peasant Detected")
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

# ---- DAILY AUTO QUOTE ----
# Keep your existing daily_quote task as is

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
