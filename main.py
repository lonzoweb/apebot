import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # Python 3.9+
import os

# ==== CONFIG ====
TOKEN = os.getenv("DISCORD_TOKEN")
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo"]
DAILY_COMMAND_ROLE = "Patrizio"  # role for using .daily
QUOTES = [
    "When I get a bitch, I get a bitch. – Pretty Tony",
    "Be a sucker for a bitch and she'll suck your dick. I know he loves her, I don't doubt him. She pulled out his money, said ‘I love things about him’. – Too $hort",
    "‘Cause I'm the miggida miggida miggida mac daddy. The miggida miggida miggida mac. 'Cause I'm the miggida miggida miggida mac daddy. The miggida miggida miggida mac. – Kris",
    "Put your faith in your sword and your sword in the Pole. – Tony Curtis",
    "My style is all that and a big bag of chips with the dip. So fuck all that sensuous shit. – Ray Keith",
    "I bomb atomically. Socrates philosophies and hypotheses can’t define how I be dropping these mockeries. – Inspectah Deck",
    "You've got to know when to hold 'em. Know when to fold 'em. Know when to walk away. Know when to run. – Kenny Rogers",
    "What you gonna do, when morons come for you? – Terry Hall",
    "I’ll bash in you clit just until you get wet. – Buskin",
    "Well, I've fucked a sheep. And I've fucked a goat. I've had my cock right down its throat. So what! So what! So what? So what? You boring little cunt! – Animal",
    "R.I.P. Rest in peace. Pussy get a coffin then dem soon get da wreath, me bawl. – Mad Cobra",
    "I’ve got hoes in different area codes. – Nate Dogg",
    "You know, all bitches are the same, just like my hoes. I keep em' broke. Wake up one morning with some money, they subject to go crazy, y'know. I keep ‘em lookin’ good, pretty and all that, but no dough. – Pretty Tony",
    "It’s better to have no whore than a piece of a whore. – Sweet Jones",
    "By the dark webs, her nape caught in his bill. – Yeats",
    "You think a crackhead payin’ you back, shit forget it. – Biggie Smalls",
    "With shimmering blue from the bowl in Circe's hall. Their brown eyes blacken, and the blue drop hue. – Crane",
    "Weak, like clock radio speakers. – GZA",
    "You should never have time on your hands. It's like having your hands on your cock. - Titan",
    "Ignorant kinds, I free ‘em. – Pharoahe Monch",
    "He proves by algebra that Hamlet's grandson is Shakespeare's grandfather and that he himself is the ghost of his own father. - Mulligan",
    "All them no like da funny man, putcha gunz up ‘na air. - Masta Simon",
    "But there is neither East nor West, Border, nor Breed, nor Birth, When two strong men stand face to face, though they come from the ends of the earth! - Kipling",
    "Limb by limb we gon cut em down. – Cutty Ranks",
    "Knocking niggas out the box, daily. Yo weekly, monthly and yearly. Until them dumb motherfuckers see clearly - Ice Cube",
    "No problem can be solved from the same level of consciousness that created it. - Einstein",
    "To reflect that each one who enters imagines himself to be the first to enter whereas he is always the last term of a preceding series even if the first term of a succeeding one, each imagining himself to be first, last, only and alone whereas he is neither first nor last nor only nor alone in a series originating in and repeated to infinity. - Poldy",
    "There ain’t no such thing as halfway crooks. - Mobb Deep",
    "Cattle and fat sheep can all be had for the raiding, tripods all for the trading, and tawny-headed stallions. But a man’s life breath cannot come back again. – Achilles",
    "A man can have sex with animals such as sheep, cows, camels and so on. However, he should kill the animal after he has his orgasm. He should not sell the meat to the people in his own village, but selling the meat to a neighboring village is reasonable. – Ayatollah Khomeini"
]

POST_HOUR = 17  # 10 AM California PDT (UTC-7) right now
# =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

# Store the daily quote so .daily can access it
daily_quote_of_the_day = None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    daily_quote.start()

# ---- Helper Function ----
async def send_random_quote(channel):
    global daily_quote_of_the_day
    daily_quote_of_the_day = random.choice(QUOTES)
    await channel.send(f"{daily_quote_of_the_day}")

# ---- Manual Command ----
@bot.command(name="quote")
async def manual_quote(ctx):
    if (ctx.author.guild_permissions.administrator or
        any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)):
        # Manual quote is separate, still random
        quote = random.choice(QUOTES)
        await ctx.send(f"📜 **Quote:** {quote}")
    else:
        await ctx.send("🚫 Peasant Detected")

# ---- Daily Command ----
@bot.command(name="daily")
async def daily_command(ctx):
    if (ctx.author.guild_permissions.administrator or
        any(role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles)):
        if daily_quote_of_the_day:
            await ctx.send(f"{daily_quote_of_the_day}")
        else:
            await ctx.send("⚠️ The daily quote has not been generated yet today.")
    else:
        await ctx.send("🚫 You don’t have permission to use this command.")

# ---- Daily Automatic Quote ----
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

    now_utc = datetime.now(timezone.utc)
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))

    # Next post hour in PT
    target_pt = now_pt.replace(hour=10, minute=0, second=0, microsecond=0)
    if target_pt < now_pt:
        target_pt += timedelta(days=1)

    # Convert to UTC for sleep
    target_utc = target_pt.astimezone(ZoneInfo("UTC"))
    wait_seconds = (target_utc - now_utc).total_seconds()
    print(f"⏳ Waiting {wait_seconds/3600:.2f} hours until first daily quote.")
    await asyncio.sleep(wait_seconds)

bot.run(TOKEN)
