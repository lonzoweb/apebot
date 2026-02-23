"""
Economy Cog - Handles all economy-related commands
Commands: balance, send, buy, inventory, use, baladd, balremove
"""

import discord
from discord.ext import commands
import logging
import asyncio
import random
import time
import economy
from collections import defaultdict
from database import (
    get_balance, update_balance, atomic_purchase, get_user_inventory, 
    remove_item_from_inventory, add_active_effect, get_active_effect, 
    get_all_active_effects, set_balance, get_potential_victims, 
    get_global_cooldown, set_global_cooldown, is_economy_on, 
    can_claim_daily, record_daily_claim, set_blood_moon, start_reaping, 
    is_reaping_active, can_claim_shard, record_shard_claim
)
from activity import get_recent_active_users
from exceptions import InsufficientTokens, InsufficientInventory, ActiveCurseError, ItemNotFoundError
from items import ITEM_REGISTRY, ITEM_ALIASES
from helpers import has_authorized_role
import database
import shutil
import os

logger = logging.getLogger(__name__)



# ============================================================
# SILENCER VIEW
# ============================================================

class SilencerView(discord.ui.View):
    NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    def __init__(self, initiator, active_users, bot, cog):
        # We don't use View timeout for the vote itself anymore, we use asyncio.sleep
        super().__init__(timeout=120) 
        self.initiator = initiator
        self.active_users = active_users[:10]
        self.bot = bot
        self.cog = cog
        self.message = None

    async def start(self, ctx):
        try:
            lines = [f"{self.NUMBERS[i]} **{m.display_name}**" for i, m in enumerate(self.active_users)]
            
            embed = discord.Embed(
                title="🤐 Silencer",
                description=f"{self.initiator.mention} has bought a Silencer.\n\n**Targets:**\n" + "\n".join(lines) + 
                            "\n\nReact with the number to cast your vote.\n**Duration**: 30s",
                color=discord.Color.dark_grey()
            )
            embed.set_footer(text="Min 2 total votes required.")
            
            self.message = await ctx.send(embed=embed, view=self)
            
            # Add reactions
            for i in range(len(self.active_users)):
                await self.message.add_reaction(self.NUMBERS[i])
            
            # Use asyncio.sleep for reliable timing
            await asyncio.sleep(30)
            
            # Resolve
            await self.resolve_and_finish()
            
        except Exception as e:
            logger.error(f"Error in Silencer start/loop: {e}", exc_info=True)
            if self.message:
                try:
                    await self.message.delete()
                except:
                    pass
                await self.message.channel.send("❌ **THE RITUAL FAILED.** The silencer was interrupted by a void leak.")

    async def resolve_and_finish(self):
        try:
            results = await self.resolve_vote()
            
            # Delete original message
            if self.message:
                try:
                    await self.message.delete()
                except:
                    pass
            
            # Send result as new message
            if results:
                if isinstance(results, discord.Embed):
                    await self.message.channel.send(embed=results)
                else:
                    await self.message.channel.send(content=results)
            else:
                 await self.message.channel.send("🗳️ The ritual yielded no conclusion.")

        except Exception as e:
            logger.error(f"Error resolving Silencer: {e}", exc_info=True)
            try:
                await self.message.channel.send("❌ The ritual failed to resolve.")
            except:
                pass
        finally:
            self.stop()

    async def resolve_vote(self):
        if not self.active_users:
            return discord.Embed(title="🗳️ VOTE CANCELLED", description="No souls were present to be silenced.", color=discord.Color.light_grey())

        try:
            msg = await self.message.channel.fetch_message(self.message.id)
        except discord.NotFound:
            return None
        
        # 1. Tally all reactions
        vote_counts = [0] * len(self.active_users)
        recent_active = await get_recent_active_users(50)
        active_ids = {str(u[0]) for u in recent_active} # Ensure strings
        
        total_valid_votes = 0
        
        for i in range(len(self.active_users)):
            reaction = discord.utils.get(msg.reactions, emoji=self.NUMBERS[i])
            if reaction:
                async for user in reaction.users():
                    if user.bot or user.id == self.initiator.id:
                        continue
                    if str(user.id) in active_ids:
                        vote_counts[i] += 1
                        total_valid_votes += 1

        if total_valid_votes < 2:
            return discord.Embed(
                title="🗳️ VOTE CANCELLED", 
                description="Not enough participants emerged from the shadows.", 
                color=discord.Color.light_grey()
            )

        # Determine winner
        max_votes = max(vote_counts)
        winners_indices = [i for i, count in enumerate(vote_counts) if count == max_votes and count > 0]
        
        if not winners_indices:
            return discord.Embed(title="🗳️ VOTE FAILED", description="The ritual yielded no conclusion.", color=discord.Color.light_grey())

        # If tie, pick random
        winner_idx = random.choice(winners_indices)
        target = self.active_users[winner_idx]
        
        await add_active_effect(target.id, "muzzle", 1200)
        
        return discord.Embed(
            title="🤐 SILENCED",
            description=f"The shades have spoken. **{target.display_name}** silenced for 20 minutes.\n\n**Votes:** {max_votes}",
            color=discord.Color.dark_purple()
        )


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

    @commands.command(name="send", aliases=["gift", "give", "transfer"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def send_command(self, ctx, member: discord.Member, *, content: str):
        """Transfer tokens or items to another user. Usage: .send @user <amount/item>"""
        content = content.strip()
        
        # Try numeric (tokens) - extract first number and ignore trailing text
        words = content.split()
        if words:
            try:
                amount = int(words[0])
                return await economy.handle_send_command(ctx, member, amount)
            except ValueError:
                pass
        
        # Not a number, try gifting item
        return await economy.handle_gift_command(ctx, member, content)

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

    @commands.command(name="backup_economy")
    @commands.has_permissions(administrator=True)
    async def backup_economy_command(self, ctx):
        """[ADMIN] Create a backup of the database file."""
        from config import DB_FILE
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_file = f"{DB_FILE}.{timestamp}.bak"
        try:
            shutil.copy2(DB_FILE, backup_file)
            await ctx.send(f"✅ Database backed up to `{os.path.basename(backup_file)}`")
        except Exception as e:
            await ctx.send(f"❌ Backup failed: {e}")

    @commands.command(name="reset_economy")
    @commands.has_permissions(administrator=True)
    async def reset_economy_command(self, ctx):
        """[ADMIN] Reset the entire economy (balances and inventories)."""
        await ctx.send("🚨 **WARNING**: This will wipe ALL balances and inventories. Are you absolutely sure? Type `CONFIRM RESET` to proceed.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM RESET"

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
            await reset_economy_data()
            await ctx.send("🔥 **ECONOMY WIPED.** All balances and inventories have been reset to zero.")
        except asyncio.TimeoutError:
            await ctx.send("⌛ Reset cancelled. The treasury remains intact.")

    @commands.command(name="invremove")
    async def invremove_command(self, ctx, member: discord.Member, item: str, quantity: int = 1):
        """[MOD] Remove items from a user's inventory. Usage: .invremove @user <item> [quantity]"""
        if not has_authorized_role(ctx.author):
            return await ctx.reply("❌ This command is restricted to moderators.", mention_author=False)
        
        # Parse item name
        official_name = ITEM_ALIASES.get(item.strip().lower())
        if not official_name:
            return await ctx.reply(f"❌ '{item}' is not a valid item.", mention_author=False)
        
        if quantity <= 0:
            return await ctx.reply("❌ Quantity must be positive.", mention_author=False)
        
        # Get current inventory
        from database import get_user_inventory, update_inventory
        inv = await get_user_inventory(member.id)
        current_qty = inv.get(official_name, 0)
        
        if current_qty <= 0:
            return await ctx.reply(f"❌ {member.display_name} doesn't have any **{official_name.replace('_', ' ').title()}**.", mention_author=False)
        
        # Calculate new quantity
        new_qty = max(0, current_qty - quantity)
        removed = current_qty - new_qty
        
        # Update inventory
        await update_inventory(member.id, official_name, new_qty)
        
        item_display = official_name.replace('_', ' ').title()
        if new_qty == 0:
            await ctx.send(f"🗑️ Removed all **{removed}x {item_display}** from {member.mention}'s inventory.")
        else:
            await ctx.send(f"🗑️ Removed **{removed}x {item_display}** from {member.mention}. ({new_qty} remaining)")

    @commands.command(name="buy", aliases=["shop"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy_command(self, ctx, *, item_name: str = None):
        """View the shop menu (via DM) or purchase an item."""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The spirits have locked the exchange. Economy is currently disabled.", mention_author=False)

        # Channel Restriction: Only forum-livi
        if ctx.channel.name != "forum-livi" and not ctx.author.guild_permissions.administrator:
            return

        if item_name is None or (item_name.lower() == "hidden" and has_authorized_role(ctx.author)):
            embed = discord.Embed(
                title="🎰 APEIRON EXCHANGE",
                description="Spend your tokens and observe the fallout.",
                color=discord.Color.gold(),
            )

            # Sort items by cost (ascending)
            sorted_items = sorted(ITEM_REGISTRY.items(), key=lambda x: x[1]["cost"])

            # 1. Show Standard Items
            for item, data in sorted_items:
                if data.get('hidden'):
                    continue
                    
                price = f"{data['cost']} 💎"
                max_uses = data.get('max_uses')
                if max_uses and max_uses > 1:
                    price += f" ({max_uses} charges)"
                desc = data.get('shop_desc', data.get('feedback', 'No description.'))
                embed.add_field(
                    name=f"{item.replace('_', ' ').title()} — {price}",
                    value=f"*{desc}*",
                    inline=False,
                )

            # 2. Show Hidden Items for Mods
            if has_authorized_role(ctx.author):
                hidden_items = [i for i in sorted_items if i[1].get('hidden')]
                if hidden_items:
                    embed.add_field(name="──────────────", value="**🌑 THE HIDDEN EXCHANGE**", inline=False)
                    for item, data in hidden_items:
                        price = f"{data['cost']} 💎"
                        max_uses = data.get('max_uses')
                        if max_uses and max_uses > 1:
                            price += f" ({max_uses} charges)"
                        desc = data.get('shop_desc', data.get('feedback', 'No description.'))
                        embed.add_field(
                            name=f"👁️ {item.replace('_', ' ').title()} — {price}",
                            value=f"*{desc}*",
                            inline=False,
                        )

            try:
                await ctx.author.send(embed=embed)
                await ctx.send(f"Menu sent to DMs {ctx.author.mention}")
            except discord.Forbidden:
                await ctx.send(f"❌ {ctx.author.mention}, Please open your DMs.")
            return

        if item_name.lower() == "hidden":
             return await ctx.reply("🌑 You're not ready for the hidden menu, peasant.", mention_author=False)

        # Smart Parsing Strategy (Consistent with .use)
        # 1. Try exact match first
        # 2. Try partial match (longest prefix)
        
        args = item_name # Alias for readability
        item_input_clean = args.strip('"').strip("'").lower()
        official_name = ITEM_ALIASES.get(item_input_clean)
        
        if not official_name:
            words = args.split()
            # Try 3 words, then 2, then 1
            for i in range(min(3, len(words)), 0, -1):
                potential_name = " ".join(words[:i]).strip('"').strip("'").lower()
                if potential_name in ITEM_ALIASES:
                    official_name = ITEM_ALIASES[potential_name]
                    break
        
        if not official_name:
             # Fallback check first word
             if words and words[0].lower() in ITEM_ALIASES:
                 official_name = ITEM_ALIASES[words[0].lower()]

        if not official_name:
            return await ctx.reply(
                f"❌ '{item_name}' isn't on the shelf. Type `.buy` to see the menu.", mention_author=False
            )

        item_data = ITEM_REGISTRY[official_name]
        cost = item_data["cost"]

        # Special handling for wards - limit to one in inventory
        if item_data.get("type") == "defense":
            inventory = await get_user_inventory(ctx.author.id)
            if inventory.get("echo_ward", 0) > 0 or inventory.get("reversal_ward", 0) > 0 or inventory.get("echo_seal", 0) > 0:
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

        # Restriction Check
        if item_data.get("restricted") and not ctx.author.guild_permissions.administrator:
            return await ctx.reply(
                "❌ **ACCESS DENIED.** This relic is reserved for the Architect roles.", mention_author=False
            )

        try:
            # Check if item has max_uses defined, otherwise default to 1
            qty = item_data.get("max_uses", 1)
            await atomic_purchase(ctx.author.id, official_name, cost, qty)
            
            payout_msg = f"💰 **{ctx.author.display_name}** grabbed a **{official_name.replace('_', ' ').title()}** for {cost} 💎."
            
            await ctx.send(f"{payout_msg} Pleasure doing business.")
        except InsufficientTokens as e:
            await ctx.reply(f"❌ Transaction declined. You're flat. Need {e.required} 💎.", mention_author=False)

    @buy_command.error
    async def buy_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return # Silently ignore
        # If you want to log other errors, do it here. Or let global handler take them.
        pass

    @commands.command(name="inventory", aliases=["inv"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def inventory_command(self, ctx):
        """DMs the user their current items."""
        # Channel Restriction: Only forum-livi
        if ctx.channel.name != "forum-livi" and not ctx.author.guild_permissions.administrator:
            return

        inventory = await get_user_inventory(ctx.author.id)

        if not inventory:
            return await ctx.send(f"{ctx.author.mention}, your inventory is empty.")

        msg = "🎒 **Your Inventory:**\n"
        for item, qty in inventory.items():
            item_display = item.replace('_', ' ').title()
            item_data = ITEM_REGISTRY.get(item, {})
            max_uses = item_data.get("max_uses")
            
            # Show usage count for items with max_uses
            if max_uses and max_uses > 1:
                msg += f"• **{item_display}**: {qty}/{max_uses} uses\n"
            else:
                msg += f"• **{item_display}**: x{qty}\n"

        try:
            await ctx.author.send(msg)
            await ctx.send(f"💰 Inventory sent to DMs {ctx.author.mention}")
        except discord.Forbidden:
            await ctx.reply(
                f"⚠️ DMs are locked. Here's your stash:\n{msg}", mention_author=False
            )

    @commands.command(name="use")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def use_command(self, ctx, *, args: str = None):
        """
        Uses an item. Supports multi-word names (e.g. .use night vision).
        Usage: .use muzzle @user | .use night vision | .use everyone <msg>
        """
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: Artifacts are inert while the economy is disabled.", mention_author=False)

        if not args:
            embed = discord.Embed(title="🎒 Item Usage Guide", color=discord.Color.blue())
            embed.add_field(
                name="Curses (Target @User)",
                value="`.use muzzle @user`\n`.use uwu @user`",
                inline=False,
            )
            embed.add_field(name="Consumables (Self)", value="`.use night vision`\n`.use kush`", inline=False)
            embed.add_field(name="Broadcast", value="`.use everyone <message>`", inline=False)
            return await ctx.send(embed=embed)

        # Basic Parsing Strategy:
        # 1. Split args into words
        # 2. Try to match longest possible alias from the start
        # 3. Remainder is target/message
        
        words = args.split()
        official_name = None
        target_str = ""
        
        # Try 3 words, then 2, then 1
        for i in range(min(3, len(words)), 0, -1):
            potential_name = " ".join(words[:i]).strip('"').strip("'").lower()
            if potential_name in ITEM_ALIASES:
                official_name = ITEM_ALIASES[potential_name]
                target_str = " ".join(words[i:])
                break
        
        if not official_name:
             # Fallback: maybe first word is alias
             potential = words[0].lower()
             if potential in ITEM_ALIASES:
                 official_name = ITEM_ALIASES[potential]
                 target_str = " ".join(words[1:])
        
        item_info = ITEM_REGISTRY.get(official_name)

        if not official_name or not item_info:
            return await ctx.reply(f"❌ '{args}' isn't in your stash. Check `.inv`.", mention_author=False)
            
        # Parse Target if needed
        target = None
        message = None
        
        if target_str:
            if item_info.get("type") == "broadcast":
                message = target_str
            else:
                try:
                    target = await commands.MemberConverter().convert(ctx, target_str)
                except commands.BadArgument:
                    # Maybe it's not a target, just extra junk, ignore if not needed
                     pass

        try:
            is_admin = ctx.author.guild_permissions.administrator
            inventory = await get_user_inventory(ctx.author.id)
            if not is_admin and inventory.get(official_name, 0) <= 0:
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

                effects = await get_all_active_effects(target.id)
                if any(e[0] in ["muzzle", "uwu"] for e in effects):
                    return await ctx.send(
                        f"❌ {target.display_name} is already suffering from an active curse."
                    )

                target_inv = await get_user_inventory(target.id)
                
                # 0. Check for Echo Seal (Multi-charge Blocking)
                if target_inv.get("echo_seal", 0) > 0:
                    await remove_item_from_inventory(target.id, "echo_seal")
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    
                    return await ctx.send(
                        f"🪞 **ECHO SEAL TRIGGERED!** {target.mention}'s obsidian barrier blocked {ctx.author.mention}'s curse!"
                    )

                # 1. Check for Reversal Ward (Reflection)
                if target_inv.get("reversal_ward", 0) > 0:
                    await remove_item_from_inventory(target.id, "reversal_ward")
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    
                    # Reflect! Apply effect to the sender (ctx.author)
                    duration = item_info.get("duration_sec", 600)
                    await add_active_effect(ctx.author.id, official_name, duration)
                    
                    return await ctx.send(
                        f"🔮 **REFLECTED!** {target.mention}'s Reversal Ward bounced the curse back! {ctx.author.mention} is hit with **{official_name}**!"
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

            elif item_type == "protection":
                # Night Vision logic
                if official_name == "night_vision":
                    # Check 10h cooldown (36000 seconds)
                    cooldown_key = f"nv_{ctx.author.id}"
                    expires_at = await get_global_cooldown(cooldown_key)
                    
                    if expires_at and expires_at > time.time():
                        remaining = expires_at - time.time()
                        hours = int(remaining // 3600)
                        minutes = int((remaining % 3600) // 60)
                        return await ctx.reply(
                            f"⏳ **PATIENCE.** The shadows need time to gather. You can engage Night Vision again in `{hours}h {minutes}m`.",
                            mention_author=False
                        )
                    
                    # Apply effect
                    duration = item_info.get("duration_sec", 18000) # 5 hours
                    await add_active_effect(ctx.author.id, official_name, duration)
                    
                    # Set 10h cooldown (36000 sec)
                    await set_global_cooldown(cooldown_key, 36000)
                    
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    # Public announcement
                    return await ctx.send(f"{item_info['feedback']}")

            elif item_type == "event":
                # Handle The Reaping
                if official_name == "reaping":
                    if await is_reaping_active():
                        return await ctx.send("🌾 **Wait.** The harvest is already underway.")
                    
                    await start_reaping()
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    return await ctx.send(item_info["feedback"])
                
                elif official_name == "storm":
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
                    duration = 180 # 3 minutes
                    
                    # Potato logic: muzzle whoever is holding it at the end
                    async def potato_timer(channel_id):
                        await asyncio.sleep(duration)
                        if channel_id in self.active_potato:
                            p = self.active_potato[channel_id]
                            loser_id = p['holder_id']
                            del self.active_potato[channel_id]
                            
                            # Muzzle the loser
                            try:
                                await add_active_effect(loser_id, "muzzle", 600)
                                await ctx.send(f"💥 **BOOM!** The potato exploded on <@{loser_id}>! They are now muzzled.")
                            except Exception as e:
                                logger.error(f"Failed to muzzle potato loser: {e}")

                    self.active_potato[ctx.channel.id] = {
                        'holder_id': target.id,
                        'expires_at': time.time() + duration,
                        'task': self.bot.loop.create_task(potato_timer(ctx.channel.id))
                    }
                    
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(f"🥔🔥 **HOT POTATO!** {ctx.author.mention} tossed it to {target.mention}!")

                elif official_name == "blood_altar":
                    await set_blood_moon(3600) # 1 hour persistent
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(item_info['feedback'])

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
                                all_victims = await get_potential_victims(exclude)
                                
                                if not all_victims:
                                    continue
                                    
                                # Priority 1: Idle users (not in active_users)
                                eligible = [v for v in all_victims if str(v) not in feast['active_users']]
                                # Priority 2: Anyone else if needed
                                if not eligible:
                                    eligible = all_victims
                                    
                                victim_id = int(random.choice(eligible))
                                victim = self.bot.get_user(victim_id)
                                
                                # Use mention fallback if user not in cache (common for idle users)
                                victim_mention = f"<@{victim_id}>"
                                victim_name = victim.display_name if victim else f"User#{str(victim_id)[:4]}"
                                
                                # Direct Steal for Feast: 5% of balance
                                victim_bal = await get_balance(victim_id)
                                if victim_bal <= 10:
                                    continue
                                    
                                steal_amount = int(victim_bal * 0.05)
                                # CAP: Limit steal to 2,500 tokens per round to prevent whale-drain
                                if steal_amount > 2500: steal_amount = 2500
                                if steal_amount < 5: steal_amount = 5
                                
                                if steal_amount > 0:
                                    await update_balance(victim_id, -steal_amount)
                                    await update_balance(attacker_id, steal_amount)
                                    
                                    if chan:
                                        # Use the fallback name/mention to avoid None errors
                                        await chan.send(f"🍗 **{attacker.display_name if attacker else 'Thief'}** ate **{steal_amount} tokens** from {victim_mention}. Delicious.")
                                
                        except Exception as e:
                            logger.error(f"Feast error: {e}")
                        finally:
                           if channel_id in self.active_feasts:
                               del self.active_feasts[channel_id]
                               if chan: await chan.send("🍗 **THE FEAST ENDS.** Satiated.")

                    task = self.bot.loop.create_task(feast_loop(ctx.channel.id, ctx.author.id, duration))
                    self.active_feasts[ctx.channel.id]['task'] = task
                    
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    await ctx.send(item_info['feedback'])

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

            elif item_type == "buff":
                # Buffs like Luck Curse (Self or Target?) 
                # User said send it to others, then they use it.
                duration = item_info.get("duration_sec", 86400) # Default 24h
                await add_active_effect(ctx.author.id, official_name, duration)
                await remove_item_from_inventory(ctx.author.id, official_name)
                await ctx.send(item_info['feedback'])

            elif official_name == "silencer":
                # 20 min global cooldown
                if not is_admin:
                    cooldown = await get_global_cooldown("silencer")
                    now = time.time()
                    if cooldown > now:
                        rem = int(cooldown - now)
                        return await ctx.reply(f"⏳ **GLITCH IN THE SHADOWS.** The Silencer needs `{rem // 60}m {rem % 60}s` to recharge.", mention_author=False)

                # Get active users (last 5 mins)
                active_users_data = await get_recent_active_users(15) # get a few more to filter
                
                # Fetch Member objects for them (excluding initiator and admins)
                active_members = []
                for uid_str, _ in active_users_data:
                    member = ctx.guild.get_member(int(uid_str))
                    if member and not member.bot and not member.guild_permissions.administrator and member.id != ctx.author.id:
                        active_members.append(member)
                
                if not active_members:
                    return await ctx.reply("🌑 **DARKNESS IS EMPTY.** There are no valid souls to silence in the current shadows.", mention_author=False)

                if len(active_members) < 2 and not is_admin: # requires at least 2 candidates or 2 participants? 
                    # User said "requires min 3 active users to initiate". 
                    # If author is excluded from targets, we need 2 more active users.
                    # active_users_data includes author.
                    # Let's count total active users
                    total_active = sum(1 for uid_str, _ in active_users_data if ctx.guild.get_member(int(uid_str)) and not ctx.guild.get_member(int(uid_str)).bot)
                    if total_active < 3:
                        return await ctx.reply("🌑 **DARKNESS IS TOO STAGNANT.** At least 3 active souls are required to initiate a silence.", mention_author=False)

                if not is_admin:
                    await remove_item_from_inventory(ctx.author.id, official_name)
                    # Set 20 min cooldown
                    await set_global_cooldown("silencer", 1200)

                view = SilencerView(ctx.author, active_members[:10], self.bot, self)
                await view.start(ctx)

        except InsufficientInventory:
            await ctx.send(f"❌ You don't have any **{official_name.replace('_', ' ').title()}**s!")
        except Exception as e:
            logger.error(f"Error using item {official_name}: {e}")


    @use_command.error
    async def use_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return # Silently ignore
        # Propagate other errors? Or log them?
        # The main command has a try/except, but this catches stuff before that (like cooldowns/converters)
        # Given usage so far, letting others propagate (or be ignored if not critical) is fine.
        # But if we don't handle them, they might print to console. 
        # Let's just pass for Cooldowns.
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        user_id = message.author.id

        # 💎 Re-entry Shard Reward
        if await can_claim_shard(user_id):
            await record_shard_claim(user_id)
            bonus = 50
            await update_balance(user_id, bonus)
            try:
                await message.channel.send(
                    f"💎 **{message.author.display_name}** re-entered the shadows! **+50 tokens**",
                    delete_after=15
                )
            except discord.Forbidden:
                pass

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
                
                # Feedback (Using display_name to avoid rate limits/spam)
                await message.channel.send(f"⚡ **PASSED!** **{message.author.display_name}** takes the heat! (+15 tokens) 🥔🔥")

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
