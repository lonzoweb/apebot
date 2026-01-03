"""
Economy Cog - Handles all economy-related commands
Commands: balance, send, buy, inventory, use, baladd, balremove
"""

import discord
from discord.ext import commands
import logging
import asyncio
import random
import economy
from database import (
    get_balance, update_balance, atomic_purchase, get_user_inventory, 
    remove_item_from_inventory, add_active_effect, get_active_effect, 
    set_balance, get_potential_victims, get_global_cooldown, 
    set_global_cooldown, is_economy_on, can_claim_daily, record_daily_claim
)
from exceptions import InsufficientTokens, InsufficientInventory, ActiveCurseError, ItemNotFoundError
from items import ITEM_REGISTRY, ITEM_ALIASES
import database

logger = logging.getLogger(__name__)


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_storm = {}  # channel_id -> message_count_remaining
        self.active_potato = {} # channel_id -> {holder_id, expires_at, task}
        self.active_feasts = {} # channel_id -> {attacker_id, active_users, victim_counts, task}

    @commands.command(name="balance", aliases=["bal", "tokens"])
    async def balance_command(self, ctx, member: discord.Member = None):
        """
        Shows your current token balance.
        Admins can check another user's balance: .balance @user
        """
        if (
            member
            and member.id != ctx.author.id
            and not ctx.author.guild_permissions.administrator
        ):
            return await ctx.send(
                "🚫 You can only check your own balance or an admin can check others."
            )

        await economy.handle_balance_command(ctx, member)

    @commands.command(name="send")
    async def send_command(self, ctx, member: discord.Member, amount: int):
        """Transfer tokens to another user. Usage: .send @user <amount>"""
        await economy.handle_send_command(ctx, member, amount)

    @commands.command(name="baladd")
    @commands.has_permissions(administrator=True)
    async def adminadd_command(self, ctx, member: discord.Member, amount: int):
        """[ADMIN] Manually add tokens to a user. Usage: .baladd @user <amount>"""
        await economy.handle_admin_modify_command(ctx, member, amount, operation="add")

    @commands.command(name="balremove")
    @commands.has_permissions(administrator=True)
    async def adminremove_command(self, ctx, member: discord.Member, amount: int):
        """[ADMIN] Manually remove tokens from a user. Usage: .balremove @user <amount>"""
        await economy.handle_admin_modify_command(ctx, member, amount, operation="remove")

    @commands.command(name="baledit")
    @commands.has_permissions(administrator=True)
    async def baledit_command(self, ctx, member: discord.Member, new_balance: int):
        """[ADMIN] Set a user's balance to an exact amount. Usage: .baledit @user <amount>"""
        await economy.handle_baledit_command(ctx, member, new_balance)

    @commands.command(name="buy", aliases=["shop"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy_command(self, ctx, item_name: str = None):
        """View the shop menu (via DM) or purchase an item."""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The spirits have locked the exchange. Economy is currently disabled.", mention_author=False)

        if item_name is None:
            embed = discord.Embed(
                title="🎰 APEIRON EXCHANGE",
                description="Spend your tokens and observe the fallout.",
                color=discord.Color.gold(),
            )

            # Sort items by cost (ascending)
            sorted_items = sorted(ITEM_REGISTRY.items(), key=lambda x: x[1]["cost"])

            for item, data in sorted_items:
                price = f"{data['cost']} 💎"
                if data.get('shop_desc'):
                    desc = data['shop_desc']
                else:
                    desc = data.get('feedback', 'No description.')
                    
                embed.add_field(
                    name=f"{item.replace('_', ' ').title()} — {price}",
                    value=f"*{desc}*",
                    inline=False,
                )

            try:
                await ctx.author.send(embed=embed)
                await ctx.send(f"Menu sent to DMs {ctx.author.mention}")
            except discord.Forbidden:
                await ctx.send(f"❌ {ctx.author.mention}, Please open your DMs.")
            return

        official_name = ITEM_ALIASES.get(item_name.lower())
        if not official_name:
            return await ctx.reply(
                f"❌ '{item_name}' isn't on the shelf. Type `.buy` to see the menu.", mention_author=False
            )

        item_data = ITEM_REGISTRY[official_name]
        cost = item_data["cost"]

        # Special handling for wards - limit to one in inventory
        if item_data.get("type") == "defense":
            inventory = await get_user_inventory(ctx.author.id)
            if inventory.get("echo_ward", 0) > 0 or inventory.get("echo_ward_max", 0) > 0:
                return await ctx.reply(
                    "❌ You already have a ward in your stash. You can't handle another.", mention_author=False
                )

        # Special handling for npass - check if user already has role
        if official_name == "npass":
            role_id = item_data.get("role_id")
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role and role in ctx.author.roles:
                    return await ctx.send(
                        f"❌ You already have the **Npass** role! No need to buy it again."
                    )

        try:
            await atomic_purchase(ctx.author.id, official_name, cost)
            await ctx.send(
                f"💰 **{ctx.author.display_name}** grabbed a **{official_name.replace('_', ' ').title()}** for {cost} 💎. Pleasure doing business."
            )
        except InsufficientTokens as e:
            await ctx.reply(f"❌ Transaction declined. You're flat. Need {e.required} 💎.", mention_author=False)

    @commands.command(name="inventory", aliases=["inv"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def inventory_command(self, ctx):
        """DMs the user their current items."""
        inventory = await get_user_inventory(ctx.author.id)

        if not inventory:
            return await ctx.send(f"{ctx.author.mention}, your inventory is empty.")

        msg = "🎒 **Your Inventory:**\n"
        for item, qty in inventory.items():
            msg += f"• **{item.replace('_', ' ').title()}**: x{qty}\n"

        try:
            await ctx.author.send(msg)
            await ctx.send(f"💰 Inventory sent to DMs {ctx.author.mention}")
        except discord.Forbidden:
            await ctx.reply(
                f"⚠️ DMs are locked. Here's your stash:\n{msg}", mention_author=False
            )

    @commands.command(name="use")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def use_command(self, ctx, item_input: str = None, target: discord.Member = None, *, message: str = None):
        """
        Uses an item.
        Usage: .use muzzle @user (Curses) OR .use kush (Consumables) OR .use global <message> (Broadcast)
        """
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: Artifacts are inert while the economy is disabled.", mention_author=False)

        if not item_input:
            embed = discord.Embed(title="🎒 Item Usage Guide", color=discord.Color.blue())
            embed.add_field(
                name="Curses (Target @User)",
                value="`.use muzzle @user`\n`.use uwu @user`",
                inline=False,
            )
            embed.add_field(name="Consumables (Self)", value="`.use kush`\n`.use npass`", inline=False)
            embed.add_field(name="Broadcast", value="`.use everyone <message>`", inline=False)
            embed.add_field(
                name="Info", value="Check your `.inv` to see what you own.", inline=False
            )
            return await ctx.send(embed=embed)

        item_input = item_input.strip('"').strip("'")
        official_name = ITEM_ALIASES.get(item_input.lower())
        item_info = ITEM_REGISTRY.get(official_name)

        if not official_name or not item_info:
            return await ctx.reply(f"❌ '{item_input}' isn't in your stash. Check `.inv`.", mention_author=False)

        try:
            inventory = await get_user_inventory(ctx.author.id)
            if inventory.get(official_name, 0) <= 0:
                raise InsufficientInventory(official_name)

            item_type = item_info.get("type")

            if item_type == "fun":
                await remove_item_from_inventory(ctx.author.id, official_name)
                return await ctx.send(f"🌿 {ctx.author.mention}: {item_info['feedback']}")

            if item_type == "curse":
                if target is None:
                    return await ctx.reply(
                        f"❌ Who you aiming at? Mention a target. Example: `.use {official_name} @user`", mention_author=False
                    )

                if target.guild_permissions.administrator or target.bot:
                    return await ctx.send(
                        f"❌ {target.display_name} is immune to your nonsense."
                    )

                existing_effect = await get_active_effect(target.id)
                if existing_effect:
                    return await ctx.send(
                        f"❌ {target.display_name} is already suffering from an active curse."
                    )

                target_inv = await get_user_inventory(target.id)
                
                # 1. Check for Echo Ward Max (Reflection)
                if target_inv.get("echo_ward_max", 0) > 0:
                    await remove_item_from_inventory(target.id, "echo_ward_max")
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    
                    # Reflect! Apply effect to the sender (ctx.author)
                    duration = item_info.get("duration_sec", 600)
                    await add_active_effect(ctx.author.id, official_name, duration)
                    
                    return await ctx.send(
                        f"🔮 **REFLECTED!** {target.mention}'s Echo Ward Max bounced the curse back! {ctx.author.mention} is hit with **{official_name}**!"
                    )

                # 2. Check for Standard Echo Ward (Blocking)
                if target_inv.get("echo_ward", 0) > 0:
                    await remove_item_from_inventory(target.id, "echo_ward")
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    return await ctx.send(
                        f"🛡️ **WARD TRIGGERED!** {target.mention}'s Echo Ward blocked {ctx.author.mention}'s curse!"
                    )

                duration = item_info.get("duration_sec", 600)
                await add_active_effect(target.id, official_name, duration)
                await remove_item_from_inventory(ctx.author.id, official_name)
                await ctx.send(
                    f"👹 **HEX APPLIED!** {item_info['feedback']}\nTarget: {target.mention}"
                )

            elif item_type == "defense":
                await ctx.send(
                    "🛡️ This item is passive! It stays in your inventory and blocks the next curse automatically."
                )

            elif item_type == "role_grant":
                role_id = item_info.get("role_id")
                if not role_id:
                    return await ctx.send("❌ Item configuration error.")

                role = ctx.guild.get_role(role_id)
                if not role:
                    return await ctx.send("❌ Role not found on this server.")

                if role in ctx.author.roles:
                    return await ctx.send(f"❌ You already have the {role.name} role!")

                try:
                    await ctx.author.add_roles(role)
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(f"✅ {item_info['feedback']}")
                except discord.Forbidden:
                    await ctx.send("❌ Bot lacks permission to grant roles.")

            elif item_type == "broadcast":
                # Check Global Cooldown
                if official_name == "ping_everyone":
                    cooldown = await get_global_cooldown("ping_everyone")
                    now = asyncio.get_event_loop().time()
                    # get_global_cooldown returns epoch time, but database.py uses time.time()
                    # However, time.time() and loop.time() are different. 
                    # Let's fix database.py to use time.time() consistently or loop.time()
                    # Actually database.py uses time.time() so let's stick to that.
                    import time as pytime
                    now = pytime.time()
                    if cooldown > now:
                        remaining_sec = int(cooldown - now)
                        hours = remaining_sec // 3600
                        minutes = (remaining_sec % 3600) // 60
                        return await ctx.reply(
                            f"⌛ **PING ON COOLDOWN.** The spirits are resting. Try again in **{hours}h {minutes}m**.",
                            mention_author=False
                        )

                # Remove item from inventory
                await remove_item_from_inventory(ctx.author.id, official_name)

                # Handle message extraction for broadcast
                if not message:
                    if target and isinstance(target, str):
                        message = str(target)
                    else:
                        return await ctx.reply(
                            f"❌ You must provide a message! Usage: `.use everyone <your message>`",
                            mention_author=False
                        )

                # Set Global Cooldown
                if official_name == "ping_everyone":
                    await set_global_cooldown("ping_everyone", 86400)

                # Send the ping
                transmission_text = f"📡 **from {ctx.author.mention}**\n@everyone\n\n{message}"
                await ctx.send(transmission_text)
                await ctx.send(item_info['feedback'])

            elif item_type == "event":
                if official_name == "storm":
                    if ctx.channel.id in self.active_storm:
                        return await ctx.send("❌ A Token Storm is already active in this channel!")
                    
                    self.active_storm[ctx.channel.id] = {'remaining': 10, 'participants': set()}
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(item_info['feedback'])

                elif official_name == "hot_potato":
                    if ctx.channel.id in self.active_potato:
                        return await ctx.send("❌ A Hot Potato is already active in this channel!")
                    
                    if target is None:
                        return await ctx.send("❌ You must target someone to start the Hot Potato! `.use potato @user`")
                    
                    if target.guild_permissions.administrator or target.bot:
                        return await ctx.send(f"❌ {target.display_name} won't play your games.")

                    # Start the event
                    duration = 180 # 3 minutes (shortened)
                    
                    # Potato logic: muzzle whoever is holding it at the end
                    async def potato_timer(channel_id):
                        await asyncio.sleep(duration)
                        if channel_id in self.active_potato:
                            p = self.active_potato[channel_id]
                            loser_id = p['holder_id']
                            del self.active_potato[channel_id]
                            
                            # Apply Muzzle (30 mins)
                            await add_active_effect(loser_id, "muzzle", 1800)
                            
                            chan = self.bot.get_channel(channel_id)
                            if chan:
                                await chan.send(f"💥 **BOOM!** The potato exploded in <@!{loser_id}>'s hands! They are now muzzled for 30 minutes. 🤐")

                    task = asyncio.create_task(potato_timer(ctx.channel.id))
                    self.active_potato[ctx.channel.id] = {
                        'holder_id': target.id,
                        'task': task
                    }

                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(f"{item_info['feedback']}\nTarget: {target.mention}")

                elif official_name == "feast":
                    if ctx.channel.id in self.active_feasts:
                        return await ctx.send("❌ A Feast is already occurring in this channel!")
                    
                    # 4-5 minutes duration
                    duration = random.randint(240, 300)
                    
                    self.active_feasts[ctx.channel.id] = {
                        'attacker_id': ctx.author.id,
                        'active_users': {str(ctx.author.id)}, # Attacker is active
                        'victim_counts': {}, # user_id -> count (max 2)
                        'task': None
                    }

                    # Start Feast Loop
                    async def feast_loop(channel_id, attacker_id, total_duration):
                        try:
                            start_time = asyncio.get_event_loop().time()
                            attacker = self.bot.get_user(attacker_id)
                            chan = self.bot.get_channel(channel_id) # Define once

                            while asyncio.get_event_loop().time() - start_time < total_duration:
                                # Wait random interval (30-45s) to get ~7-8 rounds
                                await asyncio.sleep(random.randint(30, 45))
                                
                                if channel_id not in self.active_feasts:
                                    break
                                
                                feast = self.active_feasts[channel_id]
                                # Get potential victims (exclude attacker and the bot)
                                exclude = [attacker_id, self.bot.user.id]
                                victims = await get_potential_victims(exclude)
                                
                                if not victims:
                                    continue
                                    
                                target_id = random.choice(victims)
                                # Discord IDs from DB are strings
                                target_member = self.bot.get_user(int(target_id))
                                
                                # Check if target is "active" (blocked)
                                if str(target_id) in feast['active_users']:
                                    if chan:
                                        victim_member = target_member if target_member else f"<@{target_id}>"
                                        await chan.send(f"🛡️ **{victim_member.display_name if isinstance(victim_member, discord.Member) else victim_member}** BLOCKED the attack! No snacks here.")
                                    continue
                                    
                                # Check if target has been eaten 2 times
                                if feast['victim_counts'].get(target_id, 0) >= 2:
                                    continue
                                    
                                # Successful Eat (15-75 range aimed at ~330 total steal)
                                amount = random.randint(15, 75)
                                current_bal = await get_balance(int(target_id))
                                if current_bal <= 0:
                                    continue
                                    
                                actual_steal = min(amount, current_bal)
                                await update_balance(int(target_id), -actual_steal)
                                await update_balance(attacker_id, actual_steal)
                                
                                feast['victim_counts'][target_id] = feast['victim_counts'].get(target_id, 0) + 1
                                
                                if chan:
                                    victim_mention = target_member.mention if target_member else f"<@{target_id}>"
                                    await chan.send(f"🍗 **{attacker.display_name}** ate **{actual_steal} tokens** from {victim_mention}. Delicious.")

                            # Cleanup on natural finish
                            if chan:
                                await chan.send("🌅 **The Feast has concluded. The sun rises...**")

                        except Exception as e:
                            logger.error(f"Feast error: {e}")
                        finally:
                            # Force cleanup
                            if channel_id in self.active_feasts:
                                del self.active_feasts[channel_id]

                    task = asyncio.create_task(feast_loop(ctx.channel.id, ctx.author.id, duration))
                    self.active_feasts[ctx.channel.id]['task'] = task
                    
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(item_info['feedback'])

        except InsufficientInventory:
            await ctx.send(f"❌ You don't have any **{official_name.replace('_', ' ').title()}**s!")
        except Exception as e:
            logger.error(f"Error using item {official_name}: {e}")
            await ctx.send("❌ An unexpected error occurred.")


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        user_id = message.author.id

        # 🌧️ Handle Token Storm
        if channel_id in self.active_storm:
            storm = self.active_storm[channel_id]
            if storm['remaining'] > 0 and user_id not in storm['participants']:
                storm['remaining'] -= 1
                storm['participants'].add(user_id)
                bonus = 50
                await update_balance(user_id, bonus)
                await message.channel.send(f"⛈️ **{message.author.display_name}** grabbed a shard! **+50 tokens**")
                
                if storm['remaining'] == 0:
                    del self.active_storm[channel_id]
                    await message.channel.send("☀️ **The Token Storm has ended.**")

        # 🥔 Handle Hot Potato
        if channel_id in self.active_potato:
            potato = self.active_potato[channel_id]
            # If the speaker isn't the current holder, transfer it!
            if user_id != potato['holder_id']:
                old_holder_id = potato['holder_id']
                potato['holder_id'] = user_id
                
                # Award Passer's Fee (15 tokens)
                await update_balance(old_holder_id, 15)
                
                # Feedback
                await message.channel.send(f"⚡ **PASSED!** {message.author.mention} takes the heat! (+15 tokens) 🥔🔥")

        # 🍗 Handle Feast In-Channel Activity (Blocking mechanism)
        if channel_id in self.active_feasts:
            self.active_feasts[channel_id]['active_users'].add(str(user_id))



    @commands.command(name="beg", aliases=["claim", "daily"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def beg_command(self, ctx):
        """Claim your daily 88 tokens."""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The treasury is sealed. Economy is disabled.", mention_author=False)

        if await can_claim_daily(ctx.author.id, "beg"):
            await update_balance(ctx.author.id, 88)
            await record_daily_claim(ctx.author.id, "beg")
            await ctx.reply("🌑 You held your hand out. Someone dropped **88 tokens** in your palm. Don't spend it all in one crackhouse.", mention_author=False)
        else:
            await ctx.reply("❌ You've already bled the streets dry today. Come back tomorrow.", mention_author=False)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
