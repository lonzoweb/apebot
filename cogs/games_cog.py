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
from database import (
    get_balance, update_balance, add_active_effect, is_economy_on,
    get_user_inventory, remove_item_from_inventory, get_blood_moon_multiplier,
    get_potential_victims, is_reaping_active, add_reaping_tithe, get_active_effect,
    get_reaping_state, end_reaping, transfer_tokens, get_setting
)
from helpers import has_authorized_role
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
        self.roulette_event = asyncio.Event()
        self.roulette_task = None

        self.active_cut = []
        self.cut_spinning = False
        self.cut_timer_active = False
        self.cut_start_time = 0
        self.cut_event = asyncio.Event()
        self.cut_task = None

        self.active_fades = {}  # challenger_id -> {target_id, time}

    async def process_reaping(self, ctx):
        """Handle Reaping lifecycle: End if expired, else tax user."""
        state = await get_reaping_state()
        if not state: 
            return

        active, pool, games_count, expires_at = state
        now = time.time()
        user_id = ctx.author.id

    async def apply_minigame_penalty(self, user_id, mention):
        """Standardized 5m UwU penalty with ward protection check."""
        target_inv = await get_user_inventory(user_id)
        has_ward = False
        ward_used = None
        
        if target_inv.get("echo_seal", 0) > 0:
            has_ward = True
            ward_used = "echo_seal"
        elif target_inv.get("reversal_ward", 0) > 0:
            has_ward = True
            ward_used = "reversal_ward"
        elif target_inv.get("echo_ward", 0) > 0:
            has_ward = True
            ward_used = "echo_ward"

        if has_ward:
            await remove_item_from_inventory(user_id, ward_used)
            duration = 100
            await add_active_effect(user_id, "uwu", duration)
            return f"🛡️ **WARD SHATTERED.** {mention}'s protection absorbed most of the blast. (uwu for 1m 40s)"
        else:
            duration = 300
            await add_active_effect(user_id, "uwu", duration)
            return f"🎀 {mention} took the full shot. **uwu for 5m** applied."

        # 1. Check Expiration
        if active and expires_at and now >= expires_at:
            winner_count, payout_per_person, burned = await end_reaping()
            
            if winner_count > 0:
                formatted_payout = economy.format_balance(payout_per_person)
                formatted_burned = economy.format_balance(burned)
                await ctx.send(
                    f"🌾 **THE HARVEST IS COMPLETE.**\n"
                    f"The gathered souls have been judged.\n\n"
                    f"👥 **Participants:** {winner_count}\n"
                    f"💰 **Payout:** {formatted_payout} each\n"
                    f"🔥 **Burned:** {formatted_burned}"
                )
            else:
                await ctx.send("🌾 **The Harvest Ends.** No souls were claimed.")
            return

        # 2. Apply Tax if Active
        # 2. Apply Tax if Active
        if active:
            # Always increment game count for the event progression
            await add_reaping_tithe(user_id, 0) # Helper needs to support 0 amount just for increment
            
            # Now calculate tax separately 
            bal = await get_balance(user_id)
            tithe = 0
            if bal > 0:
                tithe = int(bal * 0.04)
                if tithe > 0:
                    await update_balance(user_id, -tithe)
                    # We already incremented game count, so just add to pool?
                    # Actually add_reaping_tithe increments game count.
                    # We should probably split the helper or just call it once with the amount.
            
            # Let's fix this properly. 
            # We want to increment games_count + 1 ALWAYS.
            # We want to add tithe to pool IF tithe > 0.
            
            # Refactored Logic:
            tithe = 0
            if bal > 0:
                tithe = int(bal * 0.04)
            
            if tithe > 0:
                await update_balance(user_id, -tithe)
            
            # Update DB state (Game +1, Pool + tithe)
            await add_reaping_tithe(user_id, tithe)
            
            # Batch Announcement (Every 4 games)
            # games_count in 'state' is the OLD count. 
            # add_reaping_tithe made it games_count + 1.
            current_games = games_count + 1
            
            if current_games % 4 == 0:
                 new_pool = pool + tithe
                 await ctx.send(f"🌾 **Harvest:** {current_games} sacrifices made. Pool: {economy.format_balance(new_pool)}")

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

        # Check for Mod Advantage (Insider Item)
        mod_advantage = False
        inventory = await get_user_inventory(ctx.author.id)
        if inventory.get("insider", 0) > 0:
            mod_advantage = True
            logger.info(f"MOD ADVANTAGE: Insider item detected for {ctx.author}. Advantage active.")

        player_rank, player_point = 0, 0
        player_dice = []

        while player_rank == 0:
            player_dice = [random.randint(1, 6) for _ in range(3)]
            player_rank, player_point = self.get_ceelo_score(player_dice)

            # Mod Advantage: Reroll 1-2-3 (instant loss) or low points (1, 2)
            if mod_advantage:
                if player_rank == 1:
                    logger.info(f"MOD ADVANTAGE: Avoided 1-2-3 for {ctx.author}")
                    player_rank = 0
                    continue
                if player_rank == 2 and player_point <= 2:
                    logger.info(f"MOD ADVANTAGE: Rerolling low point {player_point} for {ctx.author}")
                    player_rank = 0
                    continue

            d_str = f"{DICE_EMOJIS[player_dice[0]]}  {DICE_EMOJIS[player_dice[1]]}  {DICE_EMOJIS[player_dice[2]]}"
            if player_rank == 0:
                await msg.edit(content=f"🎲 Your roll\n{d_str}\nBounced. Rollin' again...")
                await asyncio.sleep(0.8)

        if player_rank == 4:
            return await self.finalize_dice(
                ctx, msg, player_dice, "4-5-6! CLEAN SWEEP.", int(bet * 1.5), bet, bot_dice=None
            )
        if player_rank == 1:
            return await self.finalize_dice(
                ctx, msg, player_dice, "1-2-3... You got got mane.", -bet, bet, bot_dice=None
            )
        if player_rank == 3:
            return await self.finalize_dice(
                ctx, msg, player_dice, f"TRIPS [{player_point}]!", int(bet * 2), bet, bot_dice=None
            )

        d_str = f"{DICE_EMOJIS[player_dice[0]]}  {DICE_EMOJIS[player_dice[1]]}  {DICE_EMOJIS[player_dice[2]]}"
        await msg.edit(
            content=f"🎲 Your roll\n{d_str}\nYour point is {player_point}. I'm rolling..."
        )
        await asyncio.sleep(1.5)

        bot_rank, bot_point = 0, 0
        bot_dice = []
        while bot_rank == 0:
            # 🏠 CASINO LOGIC: High Roller Edge
            # 1. 15% chance for bot to force 4-5-6 (Auto-Win)
            # 2. 10% chance for player to force 1-2-3 (Auto-Loss) - Added per user request
            roll = random.random()
            if bet > 1400:
                if roll < 0.15 and not mod_advantage:
                    bot_dice = [4, 5, 6]
                    logger.info(f"HOUSE EDGE (BOT WIN) TRIGGERED: High bet of {bet} detected. Bot forced 4-5-6.")
                elif roll < 0.25 and not mod_advantage: # 0.15 + 0.10 = 0.25
                    # CRITICAL: We need to override the PLAYER'S dice here, but dice is passed in.
                    # Instead, we force the BOT to win by checking this roll in the main loop logic.
                    # Or, easier: Force bot to roll higher than player if this roll hits.
                    bot_dice = [4, 5, 6] # Same outcome: player loses
                    logger.info(f"HOUSE EDGE (PLAYER LOSS) TRIGGERED: High bet of {bet} detected. Bot forced 4-5-6.")
                else:
                    bot_dice = [random.randint(1, 6) for _ in range(3)]
            else:
                bot_dice = [random.randint(1, 6) for _ in range(3)]
            
            bot_rank, bot_point = self.get_ceelo_score(bot_dice)

        win, draw = False, False
        win_reason = "You win."  # Default
        
        if bot_rank == 4:
            win = False
        elif bot_rank == 1:
            win = True
            win_reason = "You win."  # Bot rolled 1-2-3
        elif bot_rank == 3:
            if player_rank == 3 and player_point > bot_point:
                win = True
                win_reason = "You win."  # Higher trips
            else:
                win = False
        elif bot_rank == 2:
            if player_rank == 3:
                win = True
                win_reason = "You win."  # Trips beats point
            elif player_point > bot_point:
                win = True
                win_reason = f"Win, High {player_point}"  # Beat bot's point
            elif player_point < bot_point:
                win = False
            else:
                draw = True

        if draw:
            await self.finalize_dice(
                ctx, msg, player_dice, "Push.", 0, bet, bot_dice=bot_dice
            )
        elif win:
            await self.finalize_dice(
                ctx, msg, player_dice, win_reason, bet, bet, bot_dice=bot_dice
            )
        else:
            await self.finalize_dice(
                ctx, msg, player_dice, "I win.", -bet, bet, bot_dice=bot_dice
            )

    async def finalize_dice(self, ctx, msg, dice, status_text, winnings, bet, bot_dice=None):
        """Finalize dice game and update balance"""
        await update_balance(ctx.author.id, winnings)

        # 🌾 THE REAPING TAX
        # 🌾 THE REAPING Logic
        await self.process_reaping(ctx)

        player_d_str = f"{DICE_EMOJIS[dice[0]]}  {DICE_EMOJIS[dice[1]]}  {DICE_EMOJIS[dice[2]]}"

        if winnings > 0:
            result_header = f"### ✅ +{economy.format_balance(winnings)}"
        elif winnings < 0:
            result_header = f"### ❌ -{economy.format_balance(abs(winnings))}"
        else:
            result_header = f"### 🤝 PUSH (Money Back)"

        # Build output based on whether we have a bot roll
        if bot_dice:
            bot_d_str = f"{DICE_EMOJIS[bot_dice[0]]}  {DICE_EMOJIS[bot_dice[1]]}  {DICE_EMOJIS[bot_dice[2]]}"
            final_output = (
                f"🎲 Your roll\n"
                f"{player_d_str}\n"
                f"━━━━━━━━\n"
                f"{bot_d_str}\n"
                f"{status_text}\n\n"
                f"{result_header}\n"
                f"{ctx.author.mention}"
            )
        else:
            # Special cases (4-5-6, 1-2-3, trips) - no bot roll
            final_output = (
                f"🎲 Your roll\n"
                f"{player_d_str}\n"
                f"{status_text}\n\n"
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

        if len(user_data["timestamps"]) < 11:
            user_data["last_used"] = now
            user_data["timestamps"].append(now)
            await self.execute_pull(ctx)
            return

        if user_data["next_cooldown"] is None:
            user_data["next_cooldown"] = random.triangular(5, 15, 10)

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

            # 🌾 THE REAPING Logic
            await self.process_reaping(ctx)

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
        
        if self.roulette_spinning:
            return await ctx.reply("🚨 **HOLD UP.** The gun is already at someone's head. Wait for the shot.", mention_author=False)
            
        # Prune expired queue members (1 hour limit) and refund them
        expired = [p for p in self.active_roulette if now - p['time'] >= 3600]
        if expired:
            for p in expired:
                await update_balance(p['id'], 20)
            self.active_roulette = [p for p in self.active_roulette if now - p['time'] < 3600]
            
        queue = self.active_roulette
        
        if any(p['id'] == user_id for p in queue):
            return await ctx.reply(f"❌ {ctx.author.mention}, you're already in the chamber!", mention_author=False)
            
        if len(queue) >= 6:
            return await ctx.reply(f"❌ The chamber is full! Wait for this round to end.", mention_author=False)

        buy_in = 20
        balance = await get_balance(user_id)
        if balance < buy_in:
            return await ctx.reply(f"❌ You're flat. Need {economy.format_balance(buy_in)} to buy in.", mention_author=False)
            
        await update_balance(user_id, -buy_in)
        await self.process_reaping(ctx)

        # RE-CHECK: Make sure they didn't slip in while we were awaiting balance/reaping
        if any(p['id'] == user_id for p in self.active_roulette):
            await update_balance(user_id, buy_in) # Refund
            return await ctx.reply("❌ Caught a glitch in the chamber. You're already in. (Refunded)", mention_author=False)

        queue.append({'id': user_id, 'time': now})
        
        # FIXED: Use synchronized timer_active check instead of exact length 1
        if not self.roulette_timer_active:
            self.roulette_start_time = now
            self.roulette_event.clear()
            self.roulette_timer_active = True
            # Start the background timer task
            self.roulette_task = asyncio.create_task(self.roulette_timer_loop(ctx))
            await ctx.send(f"🔫 **{ctx.author.display_name}** has entered the chamber! [{len(queue)}/6]\n🚨 **THE CLOCK IS TICKING.** 25 seconds to join.")
        elif len(queue) == 6:
            # Instant start
            self.roulette_event.set()
            await ctx.send(f"🔫 **{ctx.author.display_name}** joined! [6/6]\n⚠️ **CHAMBER FULL.** Starting immediately...")
        else:
            elapsed = now - self.roulette_start_time
            remaining = max(0, 25 - int(elapsed))
            await ctx.send(f"🔫 **{ctx.author.display_name}** joined! [{len(queue)}/6]\n(Starts in {remaining}s or at 6 players)")

    async def roulette_timer_loop(self, ctx):
        """Background task for roulette countdown."""
        try:
            # Wait 25s OR until event set (6 players)
            try:
                await asyncio.wait_for(self.roulette_event.wait(), timeout=25.0)
            except asyncio.TimeoutError:
                pass 

            # Wait for minimum 3 players if timer expired with fewer
            if len(self.active_roulette) < 3:
                await ctx.send("⏳ **NOT ENOUGH FODDER.** Waiting for at least 3 souls to begin the game...")
                while len(self.active_roulette) < 3:
                    await asyncio.sleep(1)

            await self.execute_roulette(ctx)
        except Exception as e:
            logger.error(f"Roulette timer loop error: {e}")
        finally:
            self.roulette_timer_active = False
            self.roulette_task = None

    async def execute_roulette(self, ctx):
        """Perform the actual roulette resolution."""
        self.roulette_spinning = True
        try:
            await ctx.send("🚨 **SPINNING THE CYLINDER...** 🚨")
            await asyncio.sleep(2.5)
            
            player_ids = [p['id'] for p in self.active_roulette]
            loser_id = random.choice(player_ids)
            winners = [uid for uid in player_ids if uid != loser_id]
            
            loser_member = self.bot.get_user(loser_id)
            loser_mention = loser_member.mention if loser_member else f"<@{loser_id}>"

            penalty_msg = await self.apply_minigame_penalty(loser_id, loser_mention)

            payout = 60
            for win_id in winners:
                await update_balance(win_id, payout)
            
            winners_mentions = []
            for uid in winners:
                m = self.bot.get_user(uid)
                winners_mentions.append(m.display_name if m else f"User#{str(uid)[:4]}")
                
            embed = discord.Embed(title="💀💀💀 WHO GOT GOT?", color=discord.Color.red())
            embed.description = f"**CLICK... CLICK... CLICK... BANG!**\n\n{loser_mention} took the bullet. Hold that L 😵\n\n"
            
            outcome_lines = []
            for uid in player_ids:
                m = self.bot.get_user(uid)
                name = m.display_name if m else f"User#{str(uid)[:4]}"
                if uid == loser_id:
                    outcome_lines.append(f"💀 **{name}**: (-20)")
                else:
                    outcome_lines.append(f"🔫 **{name}**: (+60)")
            
            embed.description += "\n".join(outcome_lines)
            embed.add_field(name="Outcome", value=penalty_msg, inline=False)
            
            await ctx.send(embed=embed)

        finally:
            self.active_roulette.clear()
            self.roulette_spinning = False

    @commands.command(name="cut")
    async def cut_command(self, ctx):
        """High-stakes card draw (15% balance ante). Min 3, Max 6 players."""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The deck is sealed while the economy is disabled.", mention_author=False)
        
        user_id = ctx.author.id
        now = time.time()
        
        if self.cut_spinning:
            return await ctx.reply("🃏 **PATIENCE.** The dealer is already flipping cards.", mention_author=False)
            
        # Prune expired queue members (1 hour limit)
        expired = [p for p in self.active_cut if now - p['time'] >= 3600]
        if expired:
            for p in expired:
                await update_balance(p['id'], p['ante'])
            self.active_cut = [p for p in self.active_cut if now - p['time'] < 3600]

        queue = self.active_cut
        
        # Prune expired queue members (1 hour limit)
        expired = [p for p in queue if now - p['time'] >= 3600]
        if expired:
            for p in expired:
                await update_balance(p['id'], p.get('ante', 0))
            self.active_cut = [p for p in queue if now - p['time'] < 3600]
            queue = self.active_cut
        if any(p['id'] == user_id for p in queue):
            return await ctx.reply(f"❌ {ctx.author.mention}, you've already bought into this cut!", mention_author=False)
            
        if len(queue) >= 6:
            return await ctx.reply(f"❌ The table is full! Wait for the reveal.", mention_author=False)

        balance = await get_balance(user_id)
        ante = int(balance * 0.15)
        
        if balance < 100 or ante < 15:
            return await ctx.reply(f"❌ You're too broke for this table. Need at least 100 tokens.", mention_author=False)
            
        await update_balance(user_id, -ante)
        await self.process_reaping(ctx)

        # RE-CHECK: Make sure they didn't slip in while we were awaiting balance/reaping
        if any(p['id'] == user_id for p in self.active_cut):
            await update_balance(user_id, ante) # Refund
            return await ctx.reply(f"❌ Caught a glitch at the table. You're already in. (Refunded)", mention_author=False)

        queue.append({'id': user_id, 'display_name': ctx.author.display_name, 'mention': ctx.author.mention, 'ante': ante, 'time': now})
        
        if not self.cut_timer_active:
            self.cut_start_time = now
            self.cut_event.clear()
            self.cut_timer_active = True
            # Start the background timer task
            self.cut_task = asyncio.create_task(self.cut_timer_loop(ctx))
            await ctx.send(f"🃏 **{ctx.author.display_name}** tossed **{economy.format_balance(ante)}** into the pot! [{len(queue)}/6]\n🚨 **THE CLOCK IS TICKING.** 25 seconds to join.")
        elif len(queue) == 6:
            # Instant start
            self.cut_event.set()
            await ctx.send(f"🃏 **{ctx.author.display_name}** joined! [6/6]\n⚠️ **TABLE FULL.** Dealing immediately...")
        else:
            elapsed = now - self.cut_start_time
            remaining = max(0, 25 - int(elapsed))
            await ctx.send(f"🃏 **{ctx.author.display_name}** tossed **{economy.format_balance(ante)}** in! [{len(queue)}/6]\n(Starts in {remaining}s or at 6 players)")

    async def cut_timer_loop(self, ctx):
        """Background task for cut countdown."""
        try:
            # Wait 25s OR until event set (6 players)
            try:
                await asyncio.wait_for(self.cut_event.wait(), timeout=25.0)
            except asyncio.TimeoutError:
                pass 

            # Wait for minimum 3 players if timer expired with fewer
            if len(self.active_cut) < 3:
                await ctx.send("⏳ **NOT ENOUGH FODDER.** Waiting for at least 3 souls to begin the cut...")
                while len(self.active_cut) < 3:
                    await asyncio.sleep(1)

            await self.execute_cut(ctx)
        except Exception as e:
            logger.error(f"Cut timer loop error: {e}")
        finally:
            self.cut_timer_active = False
            self.cut_task = None

    async def execute_cut(self, ctx):
        """Perform the actual cut resolution."""
        self.cut_spinning = True
        try:
            await ctx.send("🌑 **SHUFFLING THE COLD DECK...** 🃏")
            await asyncio.sleep(2.5)
            
            # 1. Deck Generation
            suits = ["♣️", "♦️", "❤️", "♠️"]
            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
            deck = []
            for r_idx, r in enumerate(ranks):
                for s_idx, s in enumerate(suits):
                    deck.append({'label': f"**{r}** {s}", 'score': r_idx * 10 + s_idx})
            
            # 2. Draw for each player
            random.shuffle(deck)
            results = []
            total_pot = 0
            for i, p in enumerate(self.active_cut):
                card = deck.pop()
                results.append({**p, 'card': card})
                total_pot += p['ante']
            
            # 3. Determine Winner and Loser
            results.sort(key=lambda x: x['card']['score'], reverse=True)
            winner = results[0]
            loser = results[-1]
            others = results[1:-1]
            
            # 4. Payouts
            # 60% of total pot to King, 40% split among survivors
            king_share = int(total_pot * 0.60)
            survivor_total_share = int(total_pot * 0.40)
            
            await update_balance(winner['id'], king_share)
            
            survivor_payout = 0
            if others:
                survivor_payout = int(survivor_total_share / len(others))
                for s in others:
                    await update_balance(s['id'], survivor_payout)

            # 5. Loser Penalty
            penalty_msg = await self.apply_minigame_penalty(loser['id'], loser['mention'])

            # 6. Final Optics
            lines = []
            for r in results:
                if r == winner:
                    prefix = "👑"
                    payout = king_share
                    # Show Total Payout as primary, Profit as secondary
                    profit = payout - r['ante']
                    change = f"**{economy.format_balance(payout)}** ({'+' if profit >= 0 else ''}{economy.format_balance(profit)} net)"
                elif r == loser:
                    prefix = "💀"
                    change = f"**0** (-{economy.format_balance(r['ante'])} net)"
                else:
                    prefix = "🃏"
                    payout = survivor_payout
                    profit = payout - r['ante']
                    change = f"**{economy.format_balance(payout)}** ({'+' if profit >= 0 else ''}{economy.format_balance(profit)} net)"
                
                lines.append(f"{prefix} **{r['display_name']}**: {r['card']['label']} — {change}")
            
            embed = discord.Embed(
                title="🃏 THE CUT: RESULTS",
                description="\n".join(lines),
                color=discord.Color.dark_purple()
            )
            embed.set_footer(text=f"Total Pot: {economy.format_balance(total_pot)}")
            
            embed.add_field(name="Judgment", value=penalty_msg, inline=False)
            
            await ctx.send(embed=embed)

        finally:
            # Reset
            self.active_cut.clear()
            self.cut_spinning = False


    @commands.command(name="jugg")
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

            # 🌒 Blood Moon Check
            if await get_blood_moon_multiplier() > 1:
                return await ctx.reply("🩸 **THE BLOOD MOON IS UP.** Robbery is forbidden while the spirits feast.", mention_author=False)

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

            else:
                # Find random target
                logger.info("Scouring the streets for victims...")
                exclude = [ctx.author.id, self.bot.user.id]
                
                # Database now allows anyone with at least 1 token
                victim_ids = await get_potential_victims(exclude, min_balance=1)

                
                potential_victims = []
                for vid in victim_ids:
                    m = ctx.guild.get_member(int(vid))
                    if not m: continue
                    if m.bot or m.guild_permissions.administrator: continue
                    potential_victims.append(m)

                if not potential_victims:
                    await update_balance(ctx.author.id, cost) # Refund
                    return await ctx.reply(f"❌ The streets are empty tonight. No licks to hit. (Refunded)", mention_author=False)


                target = random.choice(potential_victims)

            # 3. Announcement
            # Check for Night Vision
            nv_expiry = await get_active_effect(target.id, "night_vision")
            if nv_expiry and nv_expiry > time.time():
                 logger.info(f"Lick blocked by Night Vision on {target.display_name}")
                 await update_balance(ctx.author.id, cost) # Refund
                 return await ctx.reply(f"🌙 **Theft Blocked.** {target.mention} is shrouded in Night Vision. You can't see them to rob them. (Refunded)", mention_author=False)

            logger.info(f"Target found: {target.display_name}. Sending announcement.")
            await ctx.send(f"🌑 **{ctx.author.display_name}** is hitting a lick on {target.mention}!\n🚨 {target.mention}, you have **18 seconds** to spook them! (Type anything in chat)")

            # 4. Wait for response (but ignore if they're cursed)
            async def check(m):
                if m.author.id != target.id or m.channel.id != ctx.channel.id:
                    return False
                # Check if target has active uwu or muzzle - they can't defend if cursed
                uwu_effect = await get_active_effect(target.id, "uwu")
                muzzle_effect = await get_active_effect(target.id, "muzzle")
                current_time = time.time()
                
                # If they have active uwu or muzzle, ignore their defense attempt
                if (uwu_effect and uwu_effect > current_time) or (muzzle_effect and muzzle_effect > current_time):
                    return False
                return True

            try:
                await self.bot.wait_for('message', timeout=18.0, check=check)
                # Spooked!
                logger.info("Target spooked the thief.")
                await ctx.send(f"🚔 **SPOOKED!** {target.mention} spotted the thief and made a scene. **{ctx.author.display_name}** ran off, losing the gear fee.")
            except asyncio.TimeoutError:
                # Robbery success (100% chance if no response)
                logger.info("Target silence. Checking for wards...")
                target_inv = await get_user_inventory(target.id)

                # 0. Echo Seal Check (Multi-charge 50% block)
                if target_inv.get("echo_seal", 0) > 0:
                    await remove_item_from_inventory(target.id, "echo_seal")
                    
                    # Block 50% of the theft
                    steal_amt = random.randint(min_steal, max_steal)
                    blocked_amt = steal_amt // 2  # 50% blocked
                    stolen_amt = steal_amt - blocked_amt
                    
                    target_bal = await get_balance(target.id)
                    actual_stolen = min(stolen_amt, target_bal)
                    
                    await update_balance(target.id, -actual_stolen)
                    await update_balance(ctx.author.id, actual_stolen)
                    
                    return await ctx.send(
                        f"🪞 **ECHO SEAL INTERCEPTED!** {target.mention}'s obsidian barrier blocked 50% of the theft. "
                        f"**{ctx.author.display_name}** only got **{economy.format_balance(actual_stolen)}** (blocked {economy.format_balance(blocked_amt)})."
                    )

                # 1. Reversal Ward Check (Single-use 50% Reflection)
                if target_inv.get("reversal_ward", 0) > 0:
                    await remove_item_from_inventory(target.id, "reversal_ward")
                    
                    # Reflect 50% back to thief, victim keeps 50%
                    steal_amt = random.randint(min_steal, max_steal)
                    reflected_amt = steal_amt // 2  # 50% reflected
                    kept_amt = steal_amt - reflected_amt  # 50% kept by victim
                    
                    thief_bal = await get_balance(ctx.author.id)
                    actual_reflect = min(reflected_amt, thief_bal)
                    
                    await update_balance(ctx.author.id, -actual_reflect)
                    await update_balance(target.id, actual_reflect)
                    
                    return await ctx.send(
                        f"🔮 **REVERSAL WARD SHATTERED!** {target.mention}'s protection reflected 50% back. "
                        f"**{ctx.author.display_name}** lost **{economy.format_balance(actual_reflect)}** to the shadows."
                    )
                
                # 2. Standard Echo Ward Check (50% block)
                if target_inv.get("echo_ward", 0) > 0:
                    await remove_item_from_inventory(target.id, "echo_ward")
                    
                    # Block 50% of the theft
                    steal_amt = random.randint(min_steal, max_steal)
                    blocked_amt = steal_amt // 2  # 50% blocked
                    stolen_amt = steal_amt - blocked_amt
                    
                    target_bal = await get_balance(target.id)
                    actual_stolen = min(stolen_amt, target_bal)
                    
                    await update_balance(target.id, -actual_stolen)
                    await update_balance(ctx.author.id, actual_stolen)
                    
                    return await ctx.send(
                        f"🛡️ **ECHO WARD SHATTERED.** {target.mention} was protected by a glass barrier. "
                        f"Only **{economy.format_balance(actual_stolen)}** stolen (blocked {economy.format_balance(blocked_amt)})."
                    )

                # 3. Successful Lick - Dual Tier Returns
                tier_roll = random.random()
                target_bal = await get_balance(target.id) # Fresh check after 18s wait
                
                if tier_roll < 0.30:
                    # THE BIG SCORE (30% chance)
                    logger.info("BIG SCORE rolled.")
                    # Range: cost+1 to full balance (or at least cost+2)
                    rob_amount = random.randint(cost + 1, max(cost + 2, target_bal))
                    flavor_prefix = "💸 **JACKPOT!** A clean sweep of the safe."
                else:
                    # STANDARD RETURN (70% chance)
                    logger.info("Standard return rolled.")
                    rob_amount = random.randint(350, 450)
                    flavor_prefix = "💰 **LICK SUCCESSFUL.**"

                actual_steal = min(rob_amount, target_bal)
                
                if actual_steal <= 0:
                    # THE BUST
                    await ctx.send(
                        f"🚔 **BUST.** {ctx.author.mention} cornered {target.mention} only to find their pockets were completely empty. "
                        f"The thief slinks away, losing the gear fee for nothing."
                    )
                    return
                
                # CRITICAL: Use transfer_tokens to ENSURE zero-inflation (No multipliers)
                # and to link the deduction directly to the reward.
                await transfer_tokens(target.id, ctx.author.id, actual_steal)
                
                if actual_steal < 100:
                    flavor = f"📉 **SLOPPY WORK.** {ctx.author.mention} only managed to scrape **{economy.format_balance(actual_steal)}** from {target.mention}. Hardly worth the effort."
                else:
                    flavor = f"{flavor_prefix} {ctx.author.mention} robbed **{economy.format_balance(actual_steal)}** from {target.mention}. Total silence."
                
                await ctx.send(flavor)
        
        except Exception as e:
            logger.error(f"Error in lick_command: {e}", exc_info=True)
            await ctx.send("❌ An internal error occurred. Administrators have been notified.")

    @commands.command(name="fade")
    async def fade_command(self, ctx, target: discord.Member = None):
        """1v1 Street Fade. Catch one for 30 tokens."""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: Fades are forbidden. Economy is disabled.", mention_author=False)

        user_id = ctx.author.id
        now = time.time()
        buy_in = 30

        # Check if user is accepting a fade
        challenger_id = None
        for cid, data in self.active_fades.items():
            if data['target_id'] == user_id and (now - data['time']) < 300:
                # Potential acceptance
                if target is None or target.id == int(cid):
                    challenger_id = int(cid)
                    break

        if challenger_id:
            # EXECUTE FADE
            challenger = ctx.guild.get_member(challenger_id)
            if not challenger:
                del self.active_fades[str(challenger_id)]
                return await ctx.reply("❌ Wtf", mention_author=False)

            # Check balances
            if await get_balance(user_id) < buy_in:
                return await ctx.reply(f"❌ You can't afford the fade anyone, {buy_in} tokens", mention_author=False)
            if await get_balance(challenger_id) < buy_in:
                return await ctx.reply(f"❌ They can't afford to fade you.", mention_author=False)

            # Deduct and clear
            await update_balance(user_id, -buy_in)
            await update_balance(challenger_id, -buy_in)
            del self.active_fades[str(challenger_id)]

            await self.execute_fade(ctx, challenger, ctx.author)
            return

        # Check if initiating a new fade
        if target is None:
            return await ctx.reply("❌ Usage: `.fade @user`", mention_author=False)

        if target.id == user_id:
            return await ctx.reply("❌ You can't fade your own shadow.", mention_author=False)
        
        if target.bot:
            return await ctx.reply("❌ Bots have no blood to spill.", mention_author=False)

        if await get_balance(user_id) < buy_in:
            return await ctx.reply(f"❌ You're too broke for a fade. (Need {buy_in} tokens)", mention_author=False)

        # Record challenge
        self.active_fades[str(user_id)] = {'target_id': target.id, 'time': now}
        await ctx.send(f"⚔️ **FADE!** {ctx.author.mention} wants to run the fade with {target.mention}\n💡 {target.display_name}, type `.fade @{ctx.author.display_name}` to accept. (Expires in 5m)")

    async def execute_fade(self, ctx, p1, p2):
        """Perform the actual 1v1 dice battle."""
        msg = await ctx.send(f"⚔️ **STREET FADE: {p1.display_name} vs {p2.display_name}**\nWho's getting murked?")
        await asyncio.sleep(2)

        # Check for Packing Heat (Gun Item) - Stealth Advantage
        p1_inv = await get_user_inventory(p1.id)
        p2_inv = await get_user_inventory(p2.id)
        p1_has_gun = p1_inv.get("gun", 0) > 0
        p2_has_gun = p2_inv.get("gun", 0) > 0

        p1_roll, p2_roll = 0, 0
        while p1_roll == p2_roll:
            if p1_has_gun and not p2_has_gun:
                p1_roll = random.randint(60, 100)
                p2_roll = random.randint(1, 59)
            elif p2_has_gun and not p1_has_gun:
                p2_roll = random.randint(60, 100)
                p1_roll = random.randint(1, 59)
            else:
                p1_roll = random.randint(1, 100)
                p2_roll = random.randint(1, 100)

        winner = p1 if p1_roll > p2_roll else p2
        loser = p2 if p1_roll > p2_roll else p1
        win_roll = max(p1_roll, p2_roll)
        loss_roll = min(p1_roll, p2_roll)

        # Rewards (Pot 60 + 100 bonus)
        payout = 160
        await update_balance(winner.id, payout)

        # Penalty
        await add_active_effect(loser.id, "uwu", 60)

        outcomes = [
            f"🦷  {loser.mention} got they teeth busted in and uwud, do better 🎀",
            f"🚑  {loser.mention} got their jaw broken and uwud, do better 🎀",
            f"🚑  {loser.mention} getting a black eye and an uwud, graped 🎀",
            f"🚑  {loser.mention} got curbstomped and uwud, do better 🎀",
            f"👊  {loser.mention} got MURKED NIGGA, hold this uwu, 🎀",
            f"🚑  {loser.mention} is bleeding out and uwud, tragic kid 🎀"
        ]
        outcome = random.choice(outcomes)

        desc = (
            f"✅ **{winner.display_name}**: {win_roll} | ❌ **{loser.display_name}**: {loss_roll}\n\n"
            f"**{winner.display_name} took the W**\n"
            f"{outcome}"
        )

        embed = discord.Embed(
            title="⚔️ FADED",
            description=desc,
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"💰 {winner.display_name} secured {economy.format_balance(payout)}")
        
        # Record stats
        from database import record_fade_result
        await record_fade_result(winner.id, won=True)
        await record_fade_result(loser.id, won=False)
        
        await msg.edit(content=None, embed=embed)

    @commands.command(name="fadestats")
    async def fadestats_command(self, ctx, member: discord.Member = None):
        """View fade win/loss statistics. Usage: .fadestats [@user]"""
        target = member or ctx.author
        
        from database import get_fade_stats
        stats = await get_fade_stats(target.id)
        
        wins = stats["wins"]
        losses = stats["losses"]
        total = wins + losses
        
        if total == 0:
            return await ctx.send(f"📊 {target.display_name} hasn't participated in any fades yet.")
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        embed = discord.Embed(
            title=f"⚔️ {target.display_name}'s Fade Stats",
            color=discord.Color.gold()
        )
        embed.add_field(name="Wins", value=f"✅ {wins}", inline=True)
        embed.add_field(name="Losses", value=f"❌ {losses}", inline=True)
        embed.add_field(name="Win Rate", value=f"📈 {win_rate:.1f}%", inline=True)
        embed.set_footer(text=f"Total Fades: {total}")
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GamesCog(bot))
