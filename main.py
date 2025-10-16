import discord
from discord.ext import commands, tasks
import random
import asyncio
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import os

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None

DB_FILE = os.getenv("DB_FILE", "/data/quotes.db")  # Persistent path for Railway
AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"
ROLE_ADD_QUOTE = "Caporegime"
# =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None
last_reload_time = None

# ---- Database ----
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def fetch_all_quotes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes")
    rows = [row[0] for row in c.fetchall()]
    conn.close()
    return rows

def add_quote_to_db(text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO quotes (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def search_quotes(keyword):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes WHERE text LIKE ?", (f"%{keyword}%",))
    results = [row[0] for row in c.fetchall()]
    conn.close()
    return results

def update_quote(old_text, new_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE quotes SET text = ? WHERE text = ?", (new_text, old_text))
    conn.commit()
    conn.close()

# ---- Helper ----
def clean_quote(quote):
    quote = quote.strip()
    if quote.startswith('"') and quote.endswith('"'):
        quote = quote[1:-1]
    if quote.endswith('",'):
        quote = quote[:-2]
    return quote.strip()

# ---- Reload Quotes Cache ----
def reload_quotes():
    global QUOTES, last_reload_time
    QUOTES = [clean_quote(q) for q in fetch_all_quotes()]
    last_reload_time = datetime.now(ZoneInfo("America/Los_Angeles"))

# ---- Events ----
@bot.event
async def on_ready():
    init_db()
    reload_quotes()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- Commands ----
@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    if keyword is None:
        if not QUOTES:
            await ctx.send("⚠️ No quotes found in the database.")
            return
        if (ctx.author.guild_permissions.administrator or
            any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)):
            quote = random.choice(QUOTES)
            embed = discord.Embed(
                title="📜 Quote",
                description=quote,
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in QUOTES if keyword.lower() in q.lower()]
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
    if (ctx.author.guild_permissions.administrator or
        any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        quote_text = clean_quote(quote_text)
        add_quote_to_db(quote_text)
        reload_quotes()
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"“{quote_text}”",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="editquote")
async def edit_quote_command(ctx, *, keyword: str):
    matches = search_quotes(keyword)
    if not matches:
        await ctx.send(f"🔍 No quotes found containing “{keyword}.”")
        return

    if len(matches) > 1:
        await ctx.send(f"Found {len(matches)} quotes. Please refine your keyword.")
        return

    old_quote = matches[0]
    await ctx.send(f"✏️ Editing this quote:\n> {old_quote}\n\nPlease reply with the new version.")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        new_quote = clean_quote(msg.content)
        update_quote(old_quote, new_quote)
        reload_quotes()
        await ctx.send("✅ Quote updated successfully.")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Edit timed out.")

@bot.command(name="listquotes")
async def list_quotes_command(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = fetch_all_quotes()
    if not quotes:
        await ctx.send("⚠️ No quotes found in the database.")
        return

    chunks = []
    current_chunk = ""
    for q in quotes:
        line = f"• {q}\n"
        if len(current_chunk) + len(line) > 1900:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line
    if current_chunk:
        chunks.append(current_chunk)

    try:
        await ctx.author.send("📜 **Full Quote List:**")
        for i, chunk in enumerate(chunks):
            await ctx.author.send(chunk)
        await ctx.send("✅ Sent the full quote list to your DMs.")
        print(f"📤 Sent quote list to {ctx.author}")
    except discord.Forbidden:
        await ctx.send("❌ Unable to send DM. Please enable DMs from server members.")

@bot.command(name="reloadquotes")
async def reload_quotes_command(ctx):
    if ctx.author.guild_permissions.administrator:
        reload_quotes()
        await ctx.send("🔄 Quotes reloaded from database.")
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="stats")
async def stats_command(ctx):
    total_quotes = len(QUOTES)
    embed = discord.Embed(
        title="📊 Bot Stats",
        description=(
            f"**Quotes Loaded:** {total_quotes}\n"
            f"**Last Reload:** {last_reload_time.strftime('%Y-%m-%d %H:%M:%S') if last_reload_time else 'Never'}"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# ---- Daily Auto Post ----
@tasks.loop(minutes=1)
async def daily_quote():
    global daily_quote_of_the_day

    main_channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None

    now_pt = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%H:%M")

    # 10AM PT
    if now_pt == "10:00":
        daily_quote_of_the_day = random.choice(QUOTES)
        embed = discord.Embed(
            title="🌅 Blessings to Apeiron",
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.gold()
        )
        if main_channel: await main_channel.send(embed=embed)
        if test_channel: await test_channel.send(embed=embed)
        print("✅ Sent 10AM quote")

    # 6PM PT
    elif now_pt == "18:00" and daily_quote_of_the_day:
        embed = discord.Embed(
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.dark_gold()
        )
        if main_channel: await main_channel.send(embed=embed)
        if test_channel: await test_channel.send(embed=embed)
        print("✅ Sent 6PM quote")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")

bot.run(TOKEN)