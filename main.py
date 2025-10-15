import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
import sqlite3
from dotenv import load_dotenv

# ==== CONFIG ====
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"  # role for using .daily
ROLE_ADD_QUOTE = "Caporegime"    # Only this role or admin can add quotes

DB_FILE = "quotes.db"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None
QUOTES = []

# ---- DB Helpers ----
def init_db():
    """Initialize the DB if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def load_quotes_from_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes")
    quotes = [row[0] for row in c.fetchall()]
    conn.close()
    return quotes

def add_quote_to_db(text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO quotes (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    global QUOTES
    QUOTES = load_quotes_from_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- COMMANDS ----
@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    global QUOTES
    if keyword is None:
        # Random quote
        if ctx.author.guild_permissions.administrator or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles):
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
        # Keyword search
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
    global QUOTES
    if ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles):
        add_quote_to_db(quote_text)
        QUOTES.append(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=quote_text,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="daily")
async def daily_command(ctx):
    if ctx.author.guild_permissions.administrator or any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles):
        if daily_quote_of_the_day:
            embed = discord.Embed(
                title="🌅 Blessings to Apeiron",
                description=daily_quote_of_the_day,
                color=discord.Color.gold()
            )
            embed.set_footer(text="🕊️ Daily Quote Recall")
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 Peasant Detected")

# ---- EDIT QUOTE COMMAND ----
@bot.command(name="editquote")
async def edit_quote(ctx, *, keyword: str):
    if not (ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        await ctx.send("🚫 Peasant Detected")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, text FROM quotes WHERE text LIKE ?", (f"%{keyword}%",))
    results = c.fetchall()

    if not results:
        await ctx.send(f"🔍 No quotes found containing “{keyword}.”")
        conn.close()
        return

    # Show matches in an embed
    embed = discord.Embed(title="📝 Found Quotes", color=discord.Color.blue())
    for i, (qid, text) in enumerate(results, start=1):
        embed.add_field(name=f"{i}", value=text, inline=False)
    embed.set_footer(text="Reply with the number of the quote to edit, or 'cancel'.")
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        reply = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Edit cancelled.")
        conn.close()
        return

    if reply.content.lower() == 'cancel':
        await ctx.send("❌ Edit cancelled.")
        conn.close()
        return

    try:
        choice = int(reply.content)
        if not (1 <= choice <= len(results)):
            raise ValueError
    except ValueError:
        await ctx.send("🚫 Invalid selection. Edit cancelled.")
        conn.close()
        return

    quote_id = results[choice-1][0]
    await ctx.send("✏️ Send the edited quote text:")

    try:
        new_msg = await bot.wait_for('message', check=check, timeout=300)
    except asyncio.TimeoutError:
        await ctx.send("⌛ Timeout. Edit cancelled.")
        conn.close()
        return

    new_text = new_msg.content.strip()
    c.execute("UPDATE quotes SET text = ? WHERE id = ?", (new_text, quote_id))
    conn.commit()
    conn.close()

    # Update in-memory quotes
    global QUOTES
    QUOTES = load_quotes_from_db()

    embed = discord.Embed(
        title="✅ Quote Updated",
        description=new_text,
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Edited by {ctx.author.display_name}")
    await ctx.send(embed=embed)

# ---- DAILY AUTO QUOTE ----
@tasks.loop(minutes=1)
async def daily_quote():
    global daily_quote_of_the_day

    main_channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None

    if not main_channel and not test_channel:
        print("⚠️ No valid channel found.")
        return

    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
    current_time = now_pt.strftime("%H:%M")

    # Morning (10 AM PT)
    if current_time == "10:00":
        daily_quote_of_the_day = random.choice(QUOTES)
        embed = discord.Embed(
            title="🌅 Blessings to Apeiron",
            description=daily_quote_of_the_day,
            color=discord.Color.gold()
        )
        embed.set_footer(text="🕊️ Quote")
        if main_channel:
            await main_channel.send(embed=embed)
        if test_channel:
            await test_channel.send(embed=embed)
        print("✅ Sent 10AM quote")

    # Evening (6 PM PT)
    elif current_time == "18:00" and daily_quote_of_the_day:
        embed = discord.Embed(
            description=daily_quote_of_the_day,
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="🌇 Quote")
        if main_channel:
            await main_channel.send(embed=embed)
        if test_channel:
            await test_channel.send(embed=embed)
        print("✅ Sent 6PM quote")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")

bot.run(TOKEN)
