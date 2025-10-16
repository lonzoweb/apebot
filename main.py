import discord
from discord.ext import commands, tasks
import random
import sqlite3
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import os

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID", CHANNEL_ID))
DB_FILE = os.getenv("DB_FILE", "/app/data/quotes.db")  # persistent storage on Railway
AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
ROLE_ADD_QUOTE = "Caporegime"
ADMIN_ROLE = "Patrizio"
# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)

QUOTES = []
daily_quote_of_the_day = None
last_sent_day = {"morning": None, "evening": None}


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


def load_quotes():
    global QUOTES
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text FROM quotes")
    QUOTES = [row[0].strip() for row in c.fetchall()]
    conn.close()


def add_quote_to_db(quote_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO quotes (text) VALUES (?)", (quote_text.strip(),))
        conn.commit()
    finally:
        conn.close()


def update_quote_in_db(old_text, new_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE quotes SET text = ? WHERE text = ?", (new_text.strip(), old_text.strip()))
    conn.commit()
    conn.close()


# ---- UTIL ----
async def send_quote_embed(channel, title, quote, color):
    embed = discord.Embed(title=title, description=f"📜 {quote}", color=color)
    embed.set_footer(text="🕊️ Quote")
    await channel.send(embed=embed)


# ---- COMMANDS ----
@bot.command(name="quote")
async def quote_command(ctx, *, keyword: str = None):
    if not QUOTES:
        load_quotes()

    if keyword is None:
        if ctx.author.guild_permissions.administrator or any(r.name in AUTHORIZED_ROLES for r in ctx.author.roles):
            quote = random.choice(QUOTES)
            embed = discord.Embed(title="📜 Quote", description=quote, color=discord.Color.gold())
            await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Peasant detected.")
    else:
        matches = [q for q in QUOTES if keyword.lower() in q.lower()]
        if matches:
            for match in matches[:5]:
                embed = discord.Embed(title="📜 Matching Quote", description=match, color=discord.Color.gold())
                await ctx.send(embed=embed)
        else:
            await ctx.send("No matches found.")


@bot.command(name="addquote")
async def addquote_command(ctx, *, quote: str):
    if not (ctx.author.guild_permissions.administrator or any(r.name == ROLE_ADD_QUOTE for r in ctx.author.roles)):
        await ctx.send("🚫 You lack permission to add quotes.")
        return
    add_quote_to_db(quote)
    load_quotes()
    await ctx.send(f"✅ Quote added: {quote}")


@bot.command(name="editquote")
async def editquote_command(ctx, *, keyword: str):
    matches = [q for q in QUOTES if keyword.lower() in q.lower()]
    if not matches:
        await ctx.send("No matching quotes found.")
        return

    if len(matches) > 1:
        msg = "\n".join([f"{i+1}. {q}" for i, q in enumerate(matches[:5])])
        await ctx.send(f"Multiple matches found:\n```{msg}```\nReply with the number to edit.")
        try:
            reply = await bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=30
            )
            idx = int(reply.content.strip()) - 1
            if idx < 0 or idx >= len(matches):
                await ctx.send("Invalid selection.")
                return
            target = matches[idx]
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timeout.")
            return
    else:
        target = matches[0]

    await ctx.send(f"Editing quote:\n```{target}```\nSend the updated version:")

    try:
        reply = await bot.wait_for(
            "message",
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
            timeout=120
        )
        new_quote = reply.content.strip()
        update_quote_in_db(target, new_quote)
        load_quotes()
        await ctx.send(f"✅ Quote updated:\n```{new_quote}```")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Timeout.")


@bot.command(name="listquotes")
async def listquotes_command(ctx):
    if not (ctx.author.guild_permissions.administrator or any(r.name == ADMIN_ROLE for r in ctx.author.roles)):
        await ctx.send("🚫 You lack permission to list quotes.")
        return

    file_path = "/tmp/quotes_export.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        for quote in QUOTES:
            f.write(f"{quote}\n")

    await ctx.author.send(file=discord.File(file_path))
    await ctx.send("📨 Sent the quotes list to your DMs.")


# ---- DAILY QUOTES ----
@tasks.loop(minutes=1)
async def daily_quote():
    global daily_quote_of_the_day, last_sent_day

    channel = bot.get_channel(CHANNEL_ID)
    test_channel = bot.get_channel(TEST_CHANNEL_ID)
    if not channel:
        print("⚠️ Channel not found.")
        return

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    date_str = now.strftime("%Y-%m-%d")
    hour = now.hour

    # 10 AM Morning Quote
    if hour >= 10 and last_sent_day["morning"] != date_str:
        daily_quote_of_the_day = random.choice(QUOTES)
        await send_quote_embed(channel, "🌅 Blessings to Apeiron", daily_quote_of_the_day, discord.Color.gold())
        await send_quote_embed(test_channel, "🌅 Blessings to Apeiron", daily_quote_of_the_day, discord.Color.gold())
        last_sent_day["morning"] = date_str
        print("✅ Sent morning quote")

    # 6 PM Evening Quote
    if hour >= 18 and last_sent_day["evening"] != date_str:
        if daily_quote_of_the_day:
            await send_quote_embed(channel, "", daily_quote_of_the_day, discord.Color.dark_gold())
            await send_quote_embed(test_channel, "", daily_quote_of_the_day, discord.Color.dark_gold())
            last_sent_day["evening"] = date_str
            print("✅ Sent evening quote")


@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    load_quotes()
    print("⏳ Waiting for next scheduled quote...")


# ---- AUTO-RELOAD QUOTES ----
@tasks.loop(minutes=15)
async def auto_reload_quotes():
    load_quotes()
    print("🔄 Quotes reloaded.")


# ---- EVENTS ----
@bot.event
async def on_ready():
    init_db()
    load_quotes()
    daily_quote.start()
    auto_reload_quotes.start()
    print(f"✅ Logged in as {bot.user}")


# ---- RUN ----
bot.run(TOKEN)
