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
from database import get_balance, update_balance, add_active_effect, is_economy_on, get_user_inventory, remove_item_from_inventory
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
        self.active_roulette = []  # Global queue
        self.roulette_spinning = False # Execution lock (the actual spin)
        self.roulette_timer_active = False # Timer lock (the 25s count)
        self.roulette_start_time = 0 # When the first person joined

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
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The underground casinos are closed while the economy is disabled.", mention_author=False)
        
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
        
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The underground casinos are closed while the economy is disabled.", mention_author=False)

        user_id = ctx.author.id
        balance = await get_balance(user_id)

        if bet == "all":
            bet_amt = balance
        else:
            try:
                bet_amt = int(bet)
            except (ValueError, TypeError):
                return await ctx.reply( # Changed to ctx.reply
                    '`Usage: .dice <amount> or .dice all`\n"Put some dough on the floor."', mention_author=False
                )

        if bet_amt <= 0:
            return await ctx.reply("❌ Enter a real bet.", mention_author=False)

        if balance < bet_amt:
            return await ctx.reply(f"❌ You're flat. Need **{economy.format_balance(bet_amt)}**.", mention_author=False)

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
        await update_balance(ctx.author.id, winnings)

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
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: Slot machines are powered off. Economy is disabled.", mention_author=False)

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

        if now - user_data["last_used"] < 1.5:
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

        if len(user_data["timestamps"]) < 6:
            user_data["last_used"] = now
            user_data["timestamps"].append(now)
            await self.execute_pull(ctx)
            return

        if user_data["next_cooldown"] is None:
            user_data["next_cooldown"] = random.triangular(8, 22, 15)

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
            await update_balance(ctx.author.id, winnings)

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


    @commands.command(name="roulette")
    async def roulette_command(self, ctx):
        """Join the Russian Roulette queue (20 buyout)"""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The chamber is locked while the economy is disabled.", mention_author=False)
        user_id = ctx.author.id
        now = time.time()
        
        # 1. Check if a game is already spinning
        if self.roulette_spinning:
            return await ctx.reply("🚨 **HOLD UP.** The gun is already at someone's head. Wait for the shot.", mention_author=False)
            
        # 2. Prune expired queue members (1 hour limit) and refund them
        expired = [p for p in self.active_roulette if now - p['time'] >= 3600]
        if expired:
            for p in expired:
                await update_balance(p['id'], 20)
            self.active_roulette = [p for p in self.active_roulette if now - p['time'] < 3600]
            
        queue = self.active_roulette
        
        # 1.5 Set start time if first joiner
        if not queue:
            self.roulette_start_time = now
            self.roulette_spinning = False
            
        # 3. Check if user is already in queue
        if any(p['id'] == user_id for p in queue):
            return await ctx.reply(f"❌ {ctx.author.mention}, you're already in the chamber! Wait for more players.", mention_author=False)
            
        # 4. Check if Max Players reached
        if len(queue) >= 6:
            return await ctx.reply(f"❌ The chamber is full! Wait for this round to end.", mention_author=False)

        # 5. Deduct buy-in and join
        buy_in = 20
        balance = await get_balance(user_id)
        if balance < buy_in:
            return await ctx.reply(f"❌ You're flat. Need {economy.format_balance(buy_in)} to buy in.", mention_author=False)
            
        await update_balance(user_id, -buy_in)
        queue.append({'id': user_id, 'time': now})
        
        # 6. Check for Game Start
        if len(queue) >= 3 and not self.roulette_timer_active:
            self.roulette_timer_active = True # Lock to prevent multiple timer tasks
            
            elapsed = time.time() - self.roulette_start_time
            remaining = 25 - elapsed
            
            if remaining > 0:
                await ctx.send(f"🔫 **{ctx.author.display_name}** has joined! [{len(queue)}/6]\n🚨 **CHAMBER MINIMUM REACHED.** Wait for the clock or more fodder...")
                await asyncio.sleep(remaining)
            # Time's up message removed

            # 7. Start Game!
            self.roulette_spinning = True
            self.roulette_timer_active = False
            
            await ctx.send("🚨 **SPINNING THE CYLINDER...** 🚨")
            await asyncio.sleep(2.5)
            
            # Choose loser
            player_ids = [p['id'] for p in self.active_roulette]
            loser_id = random.choice(player_ids)
            winners = [uid for uid in player_ids if uid != loser_id]
            
            # Prep mentions
            loser_member = self.bot.get_user(loser_id)
            loser_mention = loser_member.mention if loser_member else f"<@{loser_id}>"

            # 8. Check for Wards and Apply Penalty (Ward Twist)
            warded_players = []
            for uid in player_ids:
                inv = await get_user_inventory(uid)
                if inv.get("echo_ward", 0) > 0 or inv.get("echo_ward_max", 0) > 0:
                    warded_players.append(uid)
            
            penalty_msg = f"🎀 {loser_mention} is **uwuud** for **5 minutes**."
            
            if loser_id in warded_players:
                # Twist: If ALL players are warded, one still gets hit
                if len(warded_players) == len(player_ids):
                    penalty_msg = f"🛡️ **WARD NULLIFIED.** You all tried to hide behind glass? The spirits laugh. {loser_mention} is hit anyway."
                    await add_active_effect(loser_id, "uwu", 300)
                else:
                    # Normal block - consume ward
                    inv = await get_user_inventory(loser_id)
                    ward_to_remove = "echo_ward_max" if inv.get("echo_ward_max", 0) > 0 else "echo_ward"
                    await remove_item_from_inventory(loser_id, ward_to_remove)
                    penalty_msg = f"🛡️ **WARD CONSUMED.** {loser_mention} was hit, but their ward shattered the curse."
            else:
                await add_active_effect(loser_id, "uwu", 300)

            # Payout (60 tokens each)
            payout = 60
            for win_id in winners:
                await update_balance(win_id, payout)
            
            # Announcement Mentions
            winners_mentions = []
            for uid in winners:
                m = self.bot.get_user(uid)
                winners_mentions.append(m.display_name if m else f"User#{str(uid)[:4]}")
                
            embed = discord.Embed(
                title="💀💀💀 WHO GOT GOT?",
                color=discord.Color.red()
            )
            embed.description = f"**CLICK... CLICK... CLICK... BANG!**\n\n{loser_mention} took the bullet. Hold that L 😵"
            embed.add_field(name="Outcome", value=f"{penalty_msg}\n💰 The winners receive a **{economy.format_balance(payout)}** reward!", inline=False)
            embed.add_field(name="Survivors (+60 tokens)", value=", ".join(winners_mentions), inline=False)
            
            await ctx.send(embed=embed)
            
            # Clear queue and lock
            self.active_roulette.clear()
            self.roulette_spinning = False
        else:
            # Not enough players yet
            players_needed = 3 - len(queue)
            elapsed = time.time() - self.roulette_start_time
            remaining = 25 - elapsed
            
            if players_needed > 0:
                await ctx.send(f"🔫 **{ctx.author.display_name}** has queued for roulette! [{len(queue)}/6]\nNeed **{players_needed}** more to start.")
            else:
                # Timer already running, just info
                await ctx.send(f"🔫 **{ctx.author.display_name}** has joined the chamber! [{len(queue)}/6]\nWaiting for the clock or more fodder...")



    @commands.command(name="lick", aliases=["hit_a_lick", "rob"])
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def lick_command(self, ctx, target: discord.Member = None):
        """Hit a lick on a user or a random non-mod. (Cost: 357 tokens)"""
        try:
            logger.info(f"Lick triggered by {ctx.author.name}")
            if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
                return await ctx.reply("🌑 **System Notice**: The streets are too hot. Economy is disabled.", mention_author=False)

            cost = 357
            min_steal = cost - 50
            max_steal = cost + 300

            balance = await get_balance(ctx.author.id)
            if balance < cost:
                return await ctx.reply(f"❌ You aren't geared up for a lick. Need {economy.format_balance(cost)}.", mention_author=False)

            # 1. Deduct cost
            logger.info("Deducting cost...")
            await update_balance(ctx.author.id, -cost)

            # 2. Assign or Find target
            logger.info("Finding target...")
            if not target and ctx.message.reference:
                # Check if it's a reply to another message
                ref_msg = ctx.message.reference.resolved
                if isinstance(ref_msg, discord.Message):
                    target = ref_msg.author

            if target:
                # Validate manual target
                if target.bot:
                    await update_balance(ctx.author.id, cost)
                    return await ctx.reply("❌ You can't rob a machine.", mention_author=False)
                if target.guild_permissions.administrator:
                    await update_balance(ctx.author.id, cost)
                    return await ctx.reply("❌ You tried to rob a mod? Are you suicidal?", mention_author=False)
                if target.id == ctx.author.id:
                    await update_balance(ctx.author.id, cost)
                    return await ctx.reply("❌ Stop robbing yourself, clown.", mention_author=False)
                
                target_bal = await get_balance(target.id)
                if target_bal < min_steal:
                    await update_balance(ctx.author.id, cost)
                    return await ctx.reply(f"❌ {target.display_name} is too broke to be worth the heat. (Min {min_steal} tokens)", mention_author=False)
            else:
                # Find random target
                logger.info("Scouring the streets for victims...")
                exclude = [ctx.author.id, self.bot.user.id]
                victim_ids = await get_potential_victims(exclude)
                
                potential_victims = []
                for vid in victim_ids:
                    m = ctx.guild.get_member(int(vid))
                    if not m: continue
                    if m.bot or m.guild_permissions.administrator: continue
                    
                    # Need to check if they have enough for MIN_STEAL specifically
                    bal = await get_balance(int(vid))
                    if bal >= min_steal:
                        potential_victims.append(m)

                if not potential_victims:
                    await update_balance(ctx.author.id, cost) # Refund
                    return await ctx.reply("❌ The streets are empty tonight. No licks to hit. (Refunded)", mention_author=False)

                target = random.choice(potential_victims)

            # 3. Announcement
            logger.info(f"Target found: {target.display_name}. Sending announcement.")
            await ctx.send(f"🌑 **{ctx.author.display_name}** is hitting a lick on {target.mention}!\n🚨 {target.mention}, you have **20 seconds** to spook them! (Type anything in chat)")

            # 4. Wait for response
            def check(m):
                return m.author.id == target.id and m.channel.id == ctx.channel.id

            try:
                await self.bot.wait_for('message', timeout=20.0, check=check)
                # Spooked!
                logger.info("Target spooked the thief.")
                await ctx.send(f"🚔 **SPOOKED!** {target.mention} spotted the thief and made a scene. **{ctx.author.display_name}** ran off, losing the gear fee.")
            except asyncio.TimeoutError:
                # Robbery success (100% chance if no response)
                logger.info("Target silence. Robbing now.")
                rob_amount = random.randint(min_steal, max_steal)
                target_bal = await get_balance(target.id)
                actual_steal = min(rob_amount, target_bal)
                
                await update_balance(target.id, -actual_steal)
                await update_balance(ctx.author.id, actual_steal)
                
                await ctx.send(f"💰 **LICK SUCCESSFUL.** {ctx.author.mention} robbed **{economy.format_balance(actual_steal)}** from {target.mention}. Total silence.")
        
        except Exception as e:
            logger.error(f"Error in lick_command: {e}", exc_info=True)
            await ctx.send("❌ An internal error occurred. Administrators have been notified.")

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
