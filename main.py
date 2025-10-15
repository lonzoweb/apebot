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
                color=discord.Color.
