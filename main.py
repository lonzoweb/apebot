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

# ---- Load & Save Quotes ----
def load_quotes():
    global QUOTES
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            QUOTES = [line.strip() for line in f if line.strip()]
    else:
        QUOTES = []
        print("⚠️ No quotes file found. Starting with an empty database.")

def save_quote(quote):
    with open(QUOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{quote}\n")

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
        # No keyword -> random quote (requires role)
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
        QUOTES.append(quote_text)
        save_quote(quote_text)
        embed = discord.Embed(
            title="✅ Quote Added",
            description=f"“{quote_text}”",
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
                description=f"📜 {daily_quote_of_the_day}",
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

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Channel not found.")
        return

    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
    current_time = now_pt.strftime("%H:%M")

    # Morning (10 AM PT)
    if current_time == "10:00":
        daily_quote_of_the_day = random.choice(QUOTES)

        embed = discord.Embed(
            title="🌅 Blessings to Apeiron",
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.gold()
        )
        embed.set_footer(text="🕊️ Quote")
        await channel.send(embed=embed)

        print("✅ Sent 10AM quote")

    # Evening (6 PM PT)
    elif current_time == "18:00" and daily_quote_of_the_day:
        embed = discord.Embed(
            description=f"📜 {daily_quote_of_the_day}",
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="🌇 Quote")
        await channel.send(embed=embed)

        print("✅ Sent 6PM quote")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    print("⏳ Waiting for the next scheduled quote...")



bot.run(TOKEN)
