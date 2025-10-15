import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import sqlite3
from io import BytesIO

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is missing!")

CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"
ROLE_ADD_QUOTE = "Caporegime"

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

def update_quote_in_db(qid, new_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE quotes SET text = ? WHERE id = ?", (new_text, qid))
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
        if ctx.author.guild_permissions.administrator or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles):
            quote = random.choice(QUOTES)
            embed = discord.Embed(title="📜 Quote", description=quote, color=discord.Color.gold())
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant Detected")
    else:
        matches = [q for q in QUOTES if keyword.lower() in q.lower()]
        if matches:
            for match in matches:
                embed = discord.Embed(description=f"📜 {match}", color=discord.Color.gold())
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"🔍 No quotes found containing “{keyword}.”")

@bot.command(name="addquote")
async def add_quote_command(ctx, *, quote_text: str):
    global QUOTES
    if ctx.author.guild_permissions.administrator or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles):
        add_quote_to_db(quote_text)
        QUOTES.append(quote_text)
        embed = discord.Embed(title="✅ Quote Added", description=quote_text, color=discord.Color.green())
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("🚫 Peasant Detected")

@bot.command(name="daily")
async def daily_command(ctx):
    if ctx.author.guild_permissions.administrator or any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles):
        if daily_quote_of_the_day:
            embed = discord.Embed(title="🌅 Blessings to Apeiron", description=daily_quote_of_the_day, color=discord.Color.gold())
            embed.set_footer(text="🕊️ Daily Quote Recall")
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 Peasant Detected")

# ---- EDIT QUOTE ----
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

    embed = discord.Embed(title="📝 Found Quotes", color=discord.Color.blue())
    for i, (qid, text) in enumerate(results, start=1):
        embed.add_field(name=f"{i}", value=text, inline=False)
    embed.set_footer(text="Reply with the number of the quote to edit, or 'cancel'.")
    await ctx.send(embed=embed)

    def check(m): return m.author == ctx.author and m.channel == ctx.channel

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
    update_quote_in_db(quote_id, new_text)
    conn.close()

    # Update in-memory
    global QUOTES
    QUOTES = load_quotes_from_db()

    embed = discord.Embed(title="✅ Quote Updated", description=new_text, color=discord.Color.green())
    embed.set_footer(text=f"Edited by {ctx.author.display_name}")
    await ctx.send(embed=embed)

# ---- LIST QUOTES (admin only, DM) ----
@bot.command(name="listquotes")
async def list_quotes(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 Only admins can use this command.")
        return

    global QUOTES
    file_content = "\n".join(QUOTES)
    file_buffer = BytesIO(file_content.encode('utf-8'))
    discord_file = discord.File(fp=file_buffer, filename="quotes.txt")

    try:
        await ctx.author.send("📄 Here are all the quotes:", file=discord_file)
        await ctx.send("✅ Quotes sent to your DMs!")
    except discord.Forbidden:
        await ctx.send("⚠️ Unable to send DM. Please allow DMs from this server.")

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

    if current_time == "10:00":
        daily_quote_of_the_day = random.choice(QUOTES)
        embed = discord.Embed(title="🌅 Blessings to Apeiron", description=daily_quote_of_the_day, color=discord.Color.gold())
        embed.set_footer(text="🕊️ Quote")
        if main_channel: await main_channel.send(embed=embed)
        if test_channel: await test_channel.send(embed=embed)
        print("✅ Sent 10AM quote")

    elif current_time == "18:00" and daily_quote_of_the_day:
        embed = discord.Embed(description=daily_quote_of_the_day, color=discord.Color.dark_gold())
        embed.set_footer(text="🌇 Quote")
        if main_channel: await main_channel.send(embed=embed)
        if test_channel: await test_channel.send(embed=embed)
        print("✅ Sent 6PM quote")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")

bot.run(TOKEN)
