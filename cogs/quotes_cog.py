"""
Quotes Cog - Handles all quote-related commands
Commands: quote, addquote, editquote, delquote, listquotes, daily
"""

import discord
from discord.ext import commands
import logging
import random
import asyncio
from database import (
    load_quotes_from_db,
    add_quote_to_db,
    update_quote_in_db,
    search_quotes_by_keyword,
    delete_quote_by_id,
)
from config import AUTHORIZED_ROLES, ROLE_ADD_QUOTE, DAILY_COMMAND_ROLE
import tasks

logger = logging.getLogger(__name__)


class QuotesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quote")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def quote_command(self, ctx, *, keyword: str = None):
        """Get a random quote or search by keyword"""
        quotes = await load_quotes_from_db()
        if not quotes:
            await ctx.send("⚠️ No quotes available.")
            return

        if keyword is None:
            if ctx.author.guild_permissions.administrator or any(
                role.name in AUTHORIZED_ROLES for role in ctx.author.roles
            ):
                quote = random.choice(quotes)
                embed = discord.Embed(
                    title="📜 Quote", description=quote, color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("🚫 Peasant Detected")
        else:
            matches = [q for q in quotes if keyword.lower() in q.lower()]
            if matches:
                for match in matches[:5]:
                    embed = discord.Embed(
                        description=f"📜 {match}", color=discord.Color.gold()
                    )
                    await ctx.send(embed=embed)
                if len(matches) > 5:
                    await ctx.send(
                        f"📊 Showing 5 of {len(matches)} matches. Be more specific!"
                    )
            else:
                await ctx.send(f"🔍 No quotes found containing '{keyword}'")

    @commands.command(name="addquote")
    async def add_quote_command(self, ctx, *, quote_text: str):
        """Add a new quote (Role required)"""
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
        ):
            return await ctx.send("🚫 Peasant Detected")

        if len(quote_text) > 2000:
            return await ctx.send("❌ Quote too long (max 2000 characters)")

        try:
            await add_quote_to_db(quote_text)
            embed = discord.Embed(
                title="✅ Quote Added",
                description=f"{quote_text}",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Added by {ctx.author.display_name}")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error adding quote: {e}")
            await ctx.send("❌ Error adding quote")

    @commands.command(name="editquote")
    async def edit_quote_command(self, ctx, *, keyword: str):
        """Edit an existing quote (Role required)"""
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
        ):
            await ctx.send("🚫 Peasant Detected")
            return

        quotes = await load_quotes_from_db()
        matches = [q for q in quotes if keyword.lower() in q.lower()]
        if not matches:
            await ctx.send(f"🔍 No quotes found containing '{keyword}'")
            return

        description = "\n".join(
            f"{i+1}. {q[:100]}..." if len(q) > 100 else f"{i+1}. {q}"
            for i, q in enumerate(matches)
        )
        embed = discord.Embed(
            title="Select a quote to edit (reply with number or 'cancel')",
            description=description,
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            if msg.content.lower() == "cancel":
                return await ctx.send("❌ Edit cancelled.")

            if not msg.content.isdigit() or not (1 <= int(msg.content) <= len(matches)):
                return await ctx.send("❌ Invalid selection. Edit cancelled.")

            index = int(msg.content) - 1
            old_quote = matches[index]

            await ctx.send(f"✏️ Enter the new version of the quote (or 'cancel'):")
            new_msg = await self.bot.wait_for("message", check=check, timeout=120)

            if new_msg.content.lower() == "cancel":
                return await ctx.send("❌ Edit cancelled.")

            new_quote = new_msg.content.strip()
            if len(new_quote) > 2000:
                return await ctx.send("❌ Quote too long (max 2000 characters)")

            await update_quote_in_db(old_quote, new_quote)
            await ctx.send(f"✅ Quote updated.")
        except asyncio.TimeoutError:
            await ctx.send("⌛ Timeout. Edit cancelled.")

    @commands.command(name="delquote")
    async def delete_quote(self, ctx, *, keyword: str):
        """Delete a quote by keyword (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        results = await search_quotes_by_keyword(keyword)
        if not results:
            return await ctx.send(f"🔍 No quotes found containing '{keyword}'")

        if len(results) > 1:
            formatted = "\n".join(
                f"{i+1}. {r[1][:80]}..." if len(r[1]) > 80 else f"{i+1}. {r[1]}"
                for i, r in enumerate(results)
            )
            await ctx.send(
                f"⚠️ Multiple quotes found containing '{keyword}'.\n{formatted}\n"
                f"Type the number (1–{len(results)}), or `cancel`."
            )

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reply = await self.bot.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                return await ctx.send("⌛ Timed out. No quotes deleted.")

            if reply.content.lower() == "cancel":
                return await ctx.send("❎ Cancelled.")

            if not reply.content.isdigit() or not (1 <= int(reply.content) <= len(results)):
                return await ctx.send("❌ Invalid selection. Cancelled.")

            quote_id, quote_text = results[int(reply.content) - 1]
        else:
            quote_id, quote_text = results[0]

        await ctx.send(f'🗑️ Delete this quote?\n"{quote_text}"\nType `yes` to confirm.')

        def check_confirm(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            confirm = await self.bot.wait_for("message", timeout=30.0, check=check_confirm)
        except asyncio.TimeoutError:
            return await ctx.send("⌛ Timed out. Quote not deleted.")

        if confirm.content.lower() != "yes":
            return await ctx.send("❎ Cancelled.")

        try:
            await delete_quote_by_id(quote_id)
            await ctx.send(f'✅ Deleted quote:\n"{quote_text}"')
        except Exception as e:
            logger.error(f"Error deleting quote: {e}")
            await ctx.send("❌ Error deleting quote")

    @commands.command(name="listquotes")
    async def list_quotes(self, ctx):
        """DM all quotes (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("🚫 Peasant Detected")
            return
        quotes = await load_quotes_from_db()
        if not quotes:
            await ctx.send("⚠️ No quotes available.")
            return

        quote_text = "\n\n".join(f"{i+1}. {q}" for i, q in enumerate(quotes))
        chunks = [quote_text[i : i + 1900] for i in range(0, len(quote_text), 1900)]

        try:
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=(
                        f"📜 All Quotes (Part {i+1}/{len(chunks)})"
                        if len(chunks) > 1
                        else "📜 All Quotes"
                    ),
                    description=chunk,
                    color=discord.Color.blue(),
                )
                await ctx.author.send(embed=embed)
            await ctx.send("📬 Quotes sent to your DM!")
        except discord.Forbidden:
            await ctx.send("⚠️ Cannot DM you. Check privacy settings.")

    @commands.command(name="daily")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily_command(self, ctx):
        """Show today's quote"""
        if ctx.author.guild_permissions.administrator or any(
            role.name == DAILY_COMMAND_ROLE for role in ctx.author.roles
        ):
            daily_quote = tasks.get_daily_quote()
            if daily_quote:
                embed = discord.Embed(
                    title="🌅 Blessings to Apeiron",
                    description=f"📜 {daily_quote}",
                    color=discord.Color.gold(),
                )
                embed.set_footer(text="🕊️ Daily Quote Recall")
                await ctx.send(embed=embed)
            else:
                await ctx.send("⚠️ The daily quote has not been generated yet today.")
        else:
            await ctx.send("🚫 Peasant Detected")


async def setup(bot):
    await bot.add_cog(QuotesCog(bot))
