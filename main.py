import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta, timezone
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

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"  # role for using .daily
ROLE_ADD_QUOTE = "Caporegime"  # Only this role or admin can add quotes

QUOTES_FILE = "quotes.txt"
POST_HOUR = 17  # 10 AM PT currently
# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

daily_quote_of_the_day = None
QUOTES = []

# ---- Quote cleaning helpers ----
QUOTE_EDGE_CHARS = ('"', "'", "“", "”", "‘", "’")

def clean_quote_text(s: str) -> str:
    """Trim whitespace and strip any surrounding or trailing quote-like characters."""
    if s is None:
        return s
    s = s.strip()
    # Strip leading quote chars
    while s and s[0] in QUOTE_EDGE_CHARS:
        s = s[1:].lstrip()
    # Strip trailing quote chars (even after dash or punctuation)
    while s and s[-1] in QUOTE_EDGE_CHARS + (' ',):
        s = s[:-1].rstrip()
    return s

# ---- Load & Save Quotes ----
def load_quotes():
    global QUOTES
    QUOTES = []
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                clean = clean_quote_text(line)
                if clean:
                    QUOTES.append(clean)
    else:
        print("⚠️ No quotes file found. Starting with an empty database.")

def save_quote(quote):
    """Append a cleaned quote to file (and keep in memory)."""
    clean = clean_quote_text(quote)
    if not clean:
        return
    QUOTES.append(clean)
    with open(QUOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{clean}\n")

# ---- Helper ----
async def send_random_quote(channel):
    global daily_quote_of_the_day
    daily_quote_of_the_day = random.choice(QUOTES)
    await channel.send(f"📜 {daily_quote_of_the_day}")

# ---- EVENTS ----
@bot.event
async def on_ready():
    load_quotes()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- COMMANDS ----
@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    if keyword is None:
        if (ctx.author.guild_permissions.administrator or
            any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)):
            quote = random.choice(QUOTES)
            formatted_quote = "\n".join(line.strip() for line in quote.splitlines())
            embed = discord.Embed(
                title="📜 Quote",
                description=formatted_quote,
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in QUOTES if keyword.lower() in q.lower()]
        if matches:
            for match in matches:
                formatted_match = "\n".join(line.strip() for line in match.splitlines())
                embed = discord.Embed(
                    description=f"📜 {formatted_match}",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"🔍 No quotes found containing “{keyword}.”")

@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    if ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles):
        # Support multi-line quotes
        lines = quote_text.splitlines()
        cleaned_lines = [clean_quote_text(line) for line in lines if clean_quote_text(line)]
        cleaned_quote = "\n".join(cleaned_lines)

        if not cleaned_quote:
            await ctx.send("🚫 Quote is empty or invalid.")
            return

        # Save cleaned quote
        QUOTES.append(cleaned_quote)
        with open(QUOTES_FILE, "a", encoding="utf-8") as f:
            f.write(cleaned_quote + "\n")

        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"“{cleaned_quote}”",
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
            formatted_quote = "\n".join(line.strip() for line in daily_quote_of_the_day.splitlines())
            embed = discord.Embed(
                title="🌅 Blessings to Apeiron",
                description=f"📜 {formatted_quote}",
                color=discord.Color.gold()
            )
            embed.set_footer(text="🕊️ Daily Quote Recall")
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="normalizequotes")
async def normalize_quotes_command(ctx):
    if ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles):
        if not os.path.exists(QUOTES_FILE):
            await ctx.send("⚠️ No quotes file to normalize.")
            return
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            lines = [clean_quote_text(line) for line in f]
        cleaned = [l for l in lines if l]
        with open(QUOTES_FILE, "w", encoding="utf-8") as f:
            for q in cleaned:
                f.write(q + "\n")
        load_quotes()
        await ctx.send(f"🔁 Normalized quotes file. {len(cleaned)} quotes saved.")
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
        formatted_quote = "\n".join(line.strip() for line in daily_quote_of_the_day.splitlines())
        embed = discord.Embed(
            title="🌅 Blessings to Apeiron",
            description=f"\n📜 {formatted_quote}\n",
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
        formatted_quote = "\n".join(line.strip() for line in daily_quote_of_the_day.splitlines())
        embed = discord.Embed(
            description=f"\n📜 {formatted_quote}\n",
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
