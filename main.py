import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta
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
DAILY_COMMAND_ROLE = "Patrizio"
ROLE_ADD_QUOTE = "Caporegime"
DB_FILE = os.getenv("DB_FILE", "/app/data/quotes.db")

# ==== BOT SETUP ====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None


# ---- DATABASE ----
def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
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


def get_all_quotes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes")
    quotes = [row[0] for row in c.fetchall()]
    conn.close()
    return quotes


def add_quote_to_db(quote):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO quotes (text) VALUES (?)", (quote,))
    conn.commit()
    conn.close()


# ---- HELPERS ----
async def send_daily_quote(channel, is_morning=True):
    global daily_quote_of_the_day
    quotes = get_all_quotes()
    if not quotes:
        await channel.send("⚠️ No quotes in database.")
        return

    if is_morning:
        daily_quote_of_the_day = random.choice(quotes)
        embed = discord.Embed(
            title="🌅 Blessings to Apeiron",
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.gold()
        )
        embed.set_footer(text="🕊️ Morning Quote")
    else:
        embed = discord.Embed(
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="🌇 Evening Quote")

    await channel.send(embed=embed)


# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote_loop.start()


# ---- COMMANDS ----
@bot.command(name="daily")
async def daily_command(ctx):
    """Manually repeat today's quote."""
    if (ctx.author.guild_permissions.administrator or
        any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles)):
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


@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    quotes = get_all_quotes()
    if not quotes:
        await ctx.send("⚠️ No quotes in the database.")
        return

    if keyword is None:
        if (ctx.author.guild_permissions.administrator or
            any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)):
            quote = random.choice(quotes)
            embed = discord.Embed(title="📜 Quote", description=quote, color=discord.Color.gold())
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in quotes if keyword.lower() in q.lower()]
        if matches:
            for match in matches:
                embed = discord.Embed(description=f"📜 {match}", color=discord.Color.gold())
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"🔍 No quotes found containing “{keyword}.”")


@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    if (ctx.author.guild_permissions.administrator or
        any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)):
        add_quote_to_db(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"“{quote_text}”",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")


@bot.command(name="stats")
async def stats_command(ctx):
    """Show quote and schedule stats (admin only)."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Peasant Detected")
        return

    quotes = get_all_quotes()
    authors = set()
    for q in quotes:
        if "–" in q:
            authors.add(q.split("–")[-1].strip())

    embed = discord.Embed(title="📊 Apeiron Bot Stats", color=discord.Color.blurple())
    embed.add_field(name="Total Quotes", value=str(len(quotes)), inline=True)
    embed.add_field(name="Unique Authors", value=str(len(authors)), inline=True)
    embed.add_field(name="Last Daily Quote", value=daily_quote_of_the_day or "None yet", inline=False)
    embed.add_field(name="Next Schedules", value="10:00 AM PT & 6:00 PM PT", inline=False)
    await ctx.send(embed=embed)


# ---- DAILY AUTO QUOTE ----
@tasks.loop(minutes=1)
async def daily_quote_loop():
    global daily_quote_of_the_day
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%H:%M")

    main_channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None
    targets = [c for c in [main_channel, test_channel] if c]

    if not targets:
        print("⚠️ No valid channels found.")
        return

    if now_pt == "10:00":
        for ch in targets:
            await send_daily_quote(ch, is_morning=True)
        print("✅ Sent 10AM quote")

    elif now_pt == "18:00" and daily_quote_of_the_day:
        for ch in targets:
            await send_daily_quote(ch, is_morning=False)
        print("✅ Sent 6PM quote")


@daily_quote_loop.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")


bot.run(TOKEN)
