import discord
from discord.ext import commands, tasks
import random
import asyncio
import os

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)
POST_HOUR = int(os.getenv("POST_HOUR", 17))
AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]

QUOTES = [
    "When I get a bitch, I get a bitch. – Pretty Tony",
    "Be a sucker for a bitch and she'll suck your dick. I know he loves her, I don't doubt him. She pulled out his money, said ‘I love things about him’. – Too $hort",
    "‘Cause I'm the miggida miggida miggida mac daddy. The miggida miggida miggida mac. 'Cause I'm the miggida miggida miggida mac daddy. The miggida miggida miggida mac. – Kris",
    "Put your faith in your sword and your sword in the Pole. – Tony Curtis",
    "My style is all that and a big bag of chips with the dip. So fuck all that sensuous shit. – Ray Keith",
    "I bomb atomically. Socrates philosophies and hypotheses can’t define how I be dropping these mockeries. – Inspectah Deck",
    "You've got to know when to hold 'em. Know when to fold 'em. Know when to walk away. Know when to run. – Kenny Rogers",
    "What you gonna do, when morons come for you? – Terry Hall",
    "I’ll bash in you c l i t just until you get w e t. – Buskin",
    "Well, I've fucked a sheep. And I've fucked a goat. I've had my cock right down its throat. So what! So what! So what? So what? You boring little cunt! – Animal",
    "R.I.P. Rest in peace. Pussy get a coffin then dem soon get da wreath, me bawl. – Mad Cobra",
    "I’ve got hoes in different area codes. – Nate Dogg",
    "You know, all bitches are the same, just like my hoes. I keep em' broke. Wake up one morning with some money, they subject to go crazy, y'know. I keep ‘em lookin’ good, pretty and all that, but no dough. – Pretty Tony",
    "It’s better to have no whore than a piece of a whore. – Sweet Jones",
    "By the dark webs, her nape caught in his bill. – Yeats",
    "You think a crackhead payin’ you back, shit forget it. – Biggie Smalls",
    "With shimmering blue from the bowl in Circe's hall. Their brown eyes blacken, and the blue drop hue. – Crane",
    "Weak, like clock radio speakers. – GZA",
    "Ignorant kinds, I free ‘em. – Pharoahe Monch",
    "Limb by limb we gon cut em down. – Cutty Ranks",
    "Cattle and fat sheep can all be had for the raiding, tripods all for the trading, and tawny-headed stallions. But a man’s life breath cannot come back again. – Achilles",
    "A man can have sex with animals such as sheep, cows, camels and so on. However, he should kill the animal after he has his orgasm. He should not sell the meat to the people in his own village, but selling the meat to a neighboring village is reasonable. – Ayatollah Khomeini"
]
# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

async def send_random_quote(channel):
    quote = random.choice(QUOTES)
    await channel.send(f"{quote}")

@bot.command(name="quote")
async def manual_quote(ctx):
    if (ctx.author.guild_permissions.administrator or
        any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)):
        await send_random_quote(ctx.channel)
    else:
        await ctx.send("🚫 Peasant Detected")

@tasks.loop(hours=24)
async def daily_quote():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await send_random_quote(channel)
    else:
        print("⚠️ Channel not found.")

@daily_quote.before_loop
async def before_daily_quote():
    await bot.wait_until_ready()
    now = discord.utils.utcnow().replace(tzinfo=None)
    target = now.replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)
    if target < now:
        target = target.replace(day=now.day + 1)
    wait_time = (target - now).total_seconds()
    print(f"⏳ Waiting {wait_time/3600:.2f} hours until first daily quote.")
    await asyncio.sleep(wait_time)

bot.run(TOKEN)
