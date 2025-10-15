import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
import sqlite3

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"  # role for using .daily
ROLE_ADD_QUOTE = "Caporegime"  # Only this role or admin can add quotes

# Path to SQLite DB
os.makedirs("/app/data", exist_ok=True)
DB_FILE = "/app/data/quotes.db"

# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None


# ---- DATABASE ----
def init_db():
    """Initialize database and create table if it doesn't exist."""
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
    """Load all quotes from database into a Python list."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes")
    rows = c.fetchall()
    conn.close()
    # Clean quotes before returning
    return [row[0].strip().strip('"').rstrip(',') for row in rows]


def add_quote_to_db(quote_text):
    """Add a quote to the database after cleaning."""
    cleaned = quote_text.strip().strip('"').rstrip(',')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO quotes (text) VALUES (?)", (cleaned,))
    conn.commit()
    conn.close()
    return cleaned


# ---- EVENTS ----
@bot.event
async def on_ready():
    global QUOTES
    init_db()
    QUOTES = load_quotes_from_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()


# ---- COMMANDS ----
@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    if keyword is None:
        # Random quote requires authorized role
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
        # Search quotes by keyword
        matches = [q for q in QUOTES if keyword.lower() in q.lower()]
        if matches:
            for match in matches:
                embed = discord.Embed(
                    description=match,
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"🔍 No quotes found containing “{keyword}.”")


@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    if (ctx.author.guild_permissions.administrator or
        any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        cleaned = add_quote_to_db(quote_text)
        # Reload quotes list in memory
        global QUOTES
        QUOTES = load_quotes_from_db()

        embed = discord.Embed(
            title="✅ Quote Added",
            description=cleaned,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")


@bot.command(name="daily")
async def daily_command(ctx):
    if (ctx.author.guild_permissions.administrator or
        any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles)):
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
