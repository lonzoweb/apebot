"""
Games Cog - Game commands
Commands: dice, pull, torture
"""

import discord
from discord.ext import commands
import logging
import random
import asyncio
import time
from database import get_balance, update_balance
import economy
import torture

logger = logging.getLogger(__name__)

# Dice emoji mapping
DICE_EMOJIS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}

# Tracking
user_dice_usage = {}
user_pull_usage = {}


class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_ceelo_score(self, dice):
        """Calculate Cee-lo score"""
        d = sorted(dice)
        if d == [4, 5, 6]:
            return 4, 0
        if d == [1, 2, 3]:
            return 1, 0
        if d[0] == d[1] == d[2]:
            return 3, d[0]
        if d[0] == d[1]:
            return 2, d[2]
        if d[1] == d[2]:
            return 2, d[0]
        if d[0] == d[2]:
            return 2, d[1]
        return 0, 0

    @commands.command(name="dice")
    async def dice_command(self, ctx, bet: str = None):
        """Cee-lo dice game - bet tokens"""
        
        # Handle help command
        if bet and bet.lower() == "help":
            help_embed = discord.Embed(
                title="🎲 Cee-Lo Dice Rules",
                description="Street dice - you vs me",
                color=discord.Color.gold()
            )
            help_embed.add_field(
                name="How to Play",
                value="`.dice <amount>` or `.dice all` to bet\n"
                      "Roll 3 dice until you get a valid combo",
                inline=False
            )
            help_embed.add_field(
                name="Winning Combos",
                value="**4-5-6** = Auto win (1.5x payout)\n"
                      "**Trips** = Auto win (2x payout)\n"
                      "**Point** = Higher point wins (1x payout)",
                inline=False
            )
            help_embed.add_field(
                name="Losing Combos",
                value="**1-2-3** = Auto loss\n"
                      "**Lower point** = Loss",
                inline=False
            )
            help_embed.add_field(
                name="Push",
                value="Tie, money back",
                inline=False
            )
            return await ctx.send(embed=help_embed)
        
        user_id = ctx.author.id
        balance = await self.bot.loop.run_in_executor(None, get_balance, user_id)

        if bet == "all":
            bet_amt = balance
        else:
            try:
                bet_amt = int(bet)
            except (ValueError, TypeError):
                return await ctx.send(
                    '`Usage: .dice <amount> or .dice all`\n"Put some dough on the floor."'
                )

        if bet_amt <= 0:
            return await ctx.send("Enter a real bet.")
        if balance < bet_amt:
            return await ctx.send(
                f"❌ Broke. Balance: {economy.format_balance(balance)}"
            )

        if not ctx.author.guild_permissions.administrator:
            now = time.time()
            if user_id not in user_dice_usage:
                user_dice_usage[user_id] = {
                    "timestamps": [],
                    "last_used": 0,
                    "next_cooldown": None,
                }
            u_data = user_dice_usage[user_id]
            u_data["timestamps"] = [t for t in u_data["timestamps"] if now - t < 180]

            if len(u_data["timestamps"]) >= 15:
                if u_data["next_cooldown"] is None:
                    u_data["next_cooldown"] = random.triangular(8, 30, 15)
                if now - u_data["last_used"] < u_data["next_cooldown"]:
                    return await ctx.send("The alley is hot, wait a minute...")
                u_data["next_cooldown"] = None
            u_data["last_used"] = now
            u_data["timestamps"].append(now)

        await self.execute_dice(ctx, bet_amt)

    async def execute_dice(self, ctx, bet):
        """Execute dice game logic"""
        msg = await ctx.send(
            f"🎰 **{ctx.author.display_name}** is shaking the bones for {economy.format_balance(bet)}..."
        )
        await asyncio.sleep(1.2)

        player_rank, player_point = 0, 0
        player_dice = []

        while player_rank == 0:
            player_dice = [random.randint(1, 6) for _ in range(3)]
            player_rank, player_point = self.get_ceelo_score(player_dice)
            d_str = f"{DICE_EMOJIS[player_dice[0]]} {DICE_EMOJIS[player_dice[1]]} {DICE_EMOJIS[player_dice[2]]}"
            if player_rank == 0:
                await msg.edit(content=f"🎲  **{d_str}**\n*Bounced. Rollin' again...*")
                await asyncio.sleep(0.8)

        if player_rank == 4:
            return await self.finalize_dice(
                ctx, msg, player_dice, "4-5-6! CLEAN SWEEP.", int(bet * 1.5), bet
            )
        if player_rank == 1:
            return await self.finalize_dice(
                ctx, msg, player_dice, "1-2-3... You got got mane.", -bet, bet
            )
        if player_rank == 3:
            return await self.finalize_dice(
                ctx, msg, player_dice, f"TRIPS [{player_point}]!", int(bet * 2), bet
            )

        d_str = f"{DICE_EMOJIS[player_dice[0]]} {DICE_EMOJIS[player_dice[1]]} {DICE_EMOJIS[player_dice[2]]}"
        await msg.edit(
            content=f"🎲  **{d_str}**\n*Your point is {player_point}. I'm rolling...*"
        )
        await asyncio.sleep(1.5)

        bot_rank, bot_point = 0, 0
        bot_dice = []
        while bot_rank == 0:
            bot_dice = [random.randint(1, 6) for _ in range(3)]
            bot_rank, bot_point = self.get_ceelo_score(bot_dice)

        win, draw = False, False
        if bot_rank == 4:
            win = False
        elif bot_rank == 1:
            win = True
        elif bot_rank == 3:
            if player_rank == 3 and player_point > bot_point:
                win = True
            else:
                win = False
        elif bot_rank == 2:
            if player_rank == 3 or player_point > bot_point:
                win = True
            elif player_point < bot_point:
                win = False
            else:
                draw = True

        bot_d_str = f"{DICE_EMOJIS[bot_dice[0]]} {DICE_EMOJIS[bot_dice[1]]} {DICE_EMOJIS[bot_dice[2]]}"
        bot_status = f"I rolled {bot_d_str}"

        if draw:
            await self.finalize_dice(
                ctx, msg, player_dice, f"{bot_status} | Push.", 0, bet
            )
        elif win:
            await self.finalize_dice(
                ctx, msg, player_dice, f"{bot_status} | You win.", bet, bet
            )
        else:
            await self.finalize_dice(
                ctx, msg, player_dice, f"{bot_status} | I win.", -bet, bet
            )

    async def finalize_dice(self, ctx, msg, dice, status_text, winnings, bet):
        """Finalize dice game and update balance"""
        await ctx.bot.loop.run_in_executor(
            None, update_balance, ctx.author.id, winnings
        )

        d_str = (
            f"{DICE_EMOJIS[dice[0]]}  {DICE_EMOJIS[dice[1]]}  {DICE_EMOJIS[dice[2]]}"
        )

        if winnings > 0:
            result_header = f"### ✅ +{economy.format_balance(winnings)}"
        elif winnings < 0:
            result_header = f"### ❌ -{economy.format_balance(abs(winnings))}"
        else:
            result_header = f"### 🤝 PUSH (Money Back)"

        final_output = (
            f"🎲  **{d_str}**\n"
            f"*{status_text}*\n\n"
            f"{result_header}\n"
            f"{ctx.author.mention}"
        )
        await msg.edit(content=final_output)

    @commands.command(name="pull")
    async def pull_command(self, ctx):
        """Slot machine with dark occult casino theme"""

        user_id = ctx.author.id
        now = time.time()

        if ctx.author.guild_permissions.administrator:
            await self.execute_pull(ctx)
            return

        if user_id not in user_pull_usage:
            user_pull_usage[user_id] = {
                "timestamps": [],
                "last_used": 0,
                "next_cooldown": None,
            }

        user_data = user_pull_usage[user_id]
        user_data["timestamps"] = [t for t in user_data["timestamps"] if now - t < 180]

        if len(user_data["timestamps"]) < 20:
            user_data["timestamps"].append(now)
            await self.execute_pull(ctx)
            return

        if user_data["next_cooldown"] is None:
            user_data["next_cooldown"] = random.triangular(8, 30, 15)

        cooldown = user_data["next_cooldown"]
        time_since_last = now - user_data["last_used"]

        if time_since_last < cooldown:
            messages = [
                "Rest...",
                "Patience...",
                "The abyss awaits...",
                "You will wait...",
                "Not on my watch...",
                "The void beckons...",
            ]
            await ctx.send(random.choice(messages))
            return

        user_data["last_used"] = now
        user_data["timestamps"].append(now)
        user_data["next_cooldown"] = None

        await self.execute_pull(ctx)

    async def execute_pull(self, ctx):
        """Execute the slot machine pull"""

        await asyncio.sleep(1)

        symbols = {
            "common": ["🏴‍☠️", "🗝️", "🗡️", "🃏", "🪦"],
            "medium": ["🔱", "🦇", "⭐"],
            "rare": ["💎", "👑", "<:emoji_name:1427107096670900226>"],
        }

        weighted_pool = (
            symbols["common"] * 10 + symbols["medium"] * 4 + symbols["rare"] * 1
        )

        msg = await ctx.send("🎲 | 🎲 | 🎲")

        delays = [0.12, 0.15, 0.18, 0.22, 0.28, 0.33]

        for d in delays:
            await asyncio.sleep(d)
            spin = [random.choice(list(weighted_pool)) for _ in range(3)]
            await msg.edit(content=f"{spin[0]} | {spin[1]} | {spin[2]}")

        roll = random.random()

        if roll < 0.01:
            symbol = random.choice(symbols["rare"])
            result = [symbol, symbol, symbol]
        elif roll < 0.085:
            pool = symbols["common"] + symbols["medium"]
            symbol = random.choice(pool)
            result = [symbol, symbol, symbol]
        elif roll < 0.235:
            symbol = random.choice(weighted_pool)
            other = random.choice([s for s in weighted_pool if s != symbol])
            pattern = random.choice(
                [
                    [symbol, symbol, other],
                    [symbol, other, symbol],
                    [other, symbol, symbol],
                ]
            )
            result = pattern
        elif roll < 0.46:
            symbol = random.choice(weighted_pool)
            near = random.choice([s for s in weighted_pool if s != symbol])
            pattern = random.choice([[symbol, symbol, near], [near, symbol, symbol]])
            result = pattern
        else:
            result = random.sample(weighted_pool, 3)

        r1, r2, r3 = result
        winnings = 0

        if r1 == r2 == r3:
            if r1 in symbols["rare"]:
                winnings = 100
                final_msg = (
                    f"{r1} | {r2} | {r3}\n**JACKPOT!** {r1}\n{ctx.author.mention}"
                )
            else:
                winnings = 20
                medium_msgs = ["**Hit!**", "**Score!**", "**Got em!**", "**Connect!**"]
                final_msg = f"{r1} | {r2} | {r3}\n{random.choice(medium_msgs)} {r1}\n{ctx.author.mention}"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            winnings = 5
            winning_symbol = r1 if r1 == r2 else (r2 if r2 == r3 else r1)
            small_msgs = ["Push.", "Match.", "Pair.", "Almost."]
            final_msg = f"{r1} | {r2} | {r3}\n{random.choice(small_msgs)} {winning_symbol}\n{ctx.author.mention}"
        else:
            winnings = 0
            insults = [
                "Pathetic.",
                "Trash.",
                "Garbage.",
                "Awful.",
                "Weak.",
                "Embarrassing.",
                "Yikes.",
                "Oof.",
                "Cringe.",
                "Terrible.",
                "Horrendous.",
                "Tragic.",
                "Broke.",
                "Washed.",
                "Cooked.",
                "Mid.",
                "Kys.",
                "Loser.",
                "It's over.",
            ]
            final_msg = (
                f"{r1} | {r2} | {r3}\n{random.choice(insults)}\n{ctx.author.mention}"
            )

        if winnings > 0:
            await ctx.bot.loop.run_in_executor(
                None, update_balance, ctx.author.id, winnings
            )

            formatted_winnings = economy.format_balance(winnings)
            final_msg += f"\n\nYou received {formatted_winnings}!"

        await asyncio.sleep(0.3)
        await msg.edit(content=final_msg)

    @commands.command(name="torture")
    async def torture_command(self, ctx):
        """Display a random historical torture method"""

        torture_cooldowns = getattr(self.bot, "torture_cooldowns", {})
        user_id = ctx.author.id
        current_time = time.time()

        if user_id in torture_cooldowns:
            time_since_last = current_time - torture_cooldowns[user_id]
            if time_since_last < 15:
                return

        torture_cooldowns[user_id] = current_time
        self.bot.torture_cooldowns = torture_cooldowns

        method = torture.get_random_torture_method()

        embed = discord.Embed(
            title=f"🩸 Torture Method: {method['name']}",
            description=method["description"],
            color=discord.Color.dark_red(),
        )

        embed.add_field(name="Origin", value=method["origin"], inline=True)
        embed.add_field(name="Era", value=method["era"], inline=True)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GamesCog(bot))
