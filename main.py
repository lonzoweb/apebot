import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
import sqlite3
import time

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
    c.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT UNIQUE
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

# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- COMMANDS ----
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
        description="<a:3bluefire:1332813616696524914> Blessings to Apeiron <a:3bluefire:1332813616696524914>",
        color=discord.Color.Purple()
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
