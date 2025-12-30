"""
Economy Cog - Handles all economy-related commands
Commands: balance, send, buy, inventory, use, baladd, balremove
"""

import discord
from discord.ext import commands
import logging
import economy
from database import get_balance, update_balance, atomic_purchase, get_user_inventory, remove_item_from_inventory, add_active_effect, get_active_effect
from items import ITEM_REGISTRY, ITEM_ALIASES
import database

logger = logging.getLogger(__name__)


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.command(name="buy")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy_command(self, ctx, item_name: str = None):
        """View the shop menu (via DM) or purchase an item."""

        if item_name is None:
            embed = discord.Embed(
                title="Apeiron Shop",
                description="Spend your tokens and observe the effects.",
                color=discord.Color.purple(),
            )

            for item, data in ITEM_REGISTRY.items():
                price = f"{data['cost']} 💎"
                embed.add_field(
                    name=f"{item.replace('_', ' ').title()} — {price}",
                    value=f"*{data.get('feedback', 'No description.')}*",
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
            return await ctx.send(
                f"❌ '{item_name}' not available. Type `.buy` to see the menu."
            )

        item_data = ITEM_REGISTRY[official_name]
        cost = item_data["cost"]

        success = await self.bot.loop.run_in_executor(
            None, atomic_purchase, ctx.author.id, official_name, cost
        )

        if success:
            await ctx.send(
                f"✅ **{ctx.author.display_name}** bought a **{official_name.replace('_', ' ').title()}** for {cost} 💎!"
            )
        else:
            balance = await self.bot.loop.run_in_executor(None, get_balance, ctx.author.id)
            await ctx.send(f"❌ Declined. You need {cost} 💎 but only have {balance} 💎.")

    @commands.command(name="inventory", aliases=["inv"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def inventory_command(self, ctx):
        """DMs the user their current items."""
        inventory = await self.bot.loop.run_in_executor(None, get_user_inventory, ctx.author.id)

        if not inventory:
            return await ctx.send(f"{ctx.author.mention}, your inventory is empty.")

        msg = "🎒 **Your Inventory:**\n"
        for item, qty in inventory.items():
            msg += f"• **{item.replace('_', ' ').title()}**: x{qty}\n"

        try:
            await ctx.author.send(msg)
            await ctx.send(f"Inventory sent to DMs {ctx.author.mention}")
        except discord.Forbidden:
            await ctx.send(
                f"⚠️ {ctx.author.mention}, your DMs are closed. Here is your inventory:\n{msg}"
            )

    @commands.command(name="use")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def use_command(self, ctx, item_input: str = None, target: discord.Member = None, *, message: str = None):
        """
        Uses an item.
        Usage: .use muzzle @user (Curses) OR .use kush (Consumables) OR .use global <message> (Broadcast)
        """

        if not item_input:
            embed = discord.Embed(title="🎒 Item Usage Guide", color=discord.Color.blue())
            embed.add_field(
                name="Curses (Target @User)",
                value="`.use muzzle @user`\n`.use uwu @user`",
                inline=False,
            )
            embed.add_field(name="Consumables (Self)", value="`.use kush`", inline=False)
            embed.add_field(name="Broadcast", value="`.use global <message>`", inline=False)
            embed.add_field(
                name="Info", value="Check your `.inv` to see what you own.", inline=False
            )
            return await ctx.send(embed=embed)

        item_input = item_input.strip('"').strip("'")
        official_name = ITEM_ALIASES.get(item_input.lower())
        item_info = ITEM_REGISTRY.get(official_name)

        if not official_name or not item_info:
            return await ctx.send(f"❌ '{item_input}' is not a valid item.")

        inventory = await self.bot.loop.run_in_executor(
            None, database.get_user_inventory, ctx.author.id
        )
        if inventory.get(official_name, 0) <= 0:
            return await ctx.send(
                f"❌ You don't have any **{official_name.replace('_', ' ').title()}**s!"
            )

        item_type = item_info.get("type")

        if item_type == "fun":
            await self.bot.loop.run_in_executor(
                None, database.remove_item_from_inventory, ctx.author.id, official_name
            )
            return await ctx.send(f"🌿 {ctx.author.mention}: {item_info['feedback']}")

        if item_type == "curse":
            if target is None:
                return await ctx.send(
                    f"❌ You must mention someone to use **{official_name}** on! Example: `.use {official_name} @user`"
                )

            if target.guild_permissions.administrator or target.bot:
                return await ctx.send(
                    f"❌ {target.display_name} is immune to your nonsense."
                )

            existing_effect = await self.bot.loop.run_in_executor(
                None, database.get_active_effect, target.id
            )
            if existing_effect:
                return await ctx.send(
                    f"❌ {target.display_name} is already suffering from an active curse."
                )

            target_inv = await self.bot.loop.run_in_executor(
                None, database.get_user_inventory, target.id
            )
            if target_inv.get("echo_ward", 0) > 0:
                await self.bot.loop.run_in_executor(
                    None, database.remove_item_from_inventory, target.id, "echo_ward"
                )
                await self.bot.loop.run_in_executor(
                    None, database.remove_item_from_inventory, ctx.author.id, official_name
                )
                return await ctx.send(
                    f"🛡️ **WARD TRIGGERED!** {target.mention}'s Echo Ward blocked {ctx.author.mention}'s curse!"
                )

            duration = item_info.get("duration_sec", 600)
            await self.bot.loop.run_in_executor(
                None, database.add_active_effect, target.id, official_name, duration
            )
            await self.bot.loop.run_in_executor(
                None, database.remove_item_from_inventory, ctx.author.id, official_name
            )
            await ctx.send(
                f"👹 **HEX APPLIED!** {item_info['feedback']}\nTarget: {target.mention}"
            )

        elif item_type == "defense":
            await ctx.send(
                "🛡️ This item is passive! It stays in your inventory and blocks the next curse automatically."
            )

        elif item_type == "broadcast":
            # Handle global transmission
            if not message:
                # Try to get message from target parameter if it's a string
                if target and isinstance(target, str):
                    message = str(target)
                else:
                    return await ctx.send(
                        f"❌ You must provide a message! Usage: `.use global <your message>`"
                    )

            # Remove item from inventory
            await self.bot.loop.run_in_executor(
                None, database.remove_item_from_inventory, ctx.author.id, official_name
            )

            # Send the global transmission
            transmission_text = f"📡 **APEIRON TRANSMISSION BY {ctx.author.mention}**\n@everyone\n\n{message}"
            await ctx.send(transmission_text)
            await ctx.send(item_info['feedback'])


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
