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
            return await ctx.reply("⚠️ The scrolls are empty.", mention_author=False)

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
                await ctx.reply("🚫 Peasant Detected. Begone!", mention_author=False)
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
                await ctx.reply(f"🔍 Found nothing containing '{keyword}'.", mention_author=False)

    @commands.command(name="addquote")
    async def add_quote_command(self, ctx, *, quote_text: str):
        """Add a new quote (Role required)"""
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
        ):
            return await ctx.reply("🚫 Peasant Detected. Begone!", mention_author=False)

        if len(quote_text) > 2000:
            return await ctx.reply("❌ Too long. Keep it under 2000 characters.", mention_author=False)

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
            await ctx.reply("❌ Error etching the scroll.", mention_author=False)

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
            return await ctx.reply(f"🔍 No quotes found matching '{keyword}'. Is it a ghost?", mention_author=False)

        description = "\n".join(
            f"{i+1}. {q[:100]}..." if len(q) > 100 else f"{i+1}. {q}"
            for i, q in enumerate(matches)
        )
        embed = discord.Embed(
            title="📜 RECALL SELECTION (Reply with number or 'cancel')",
            description=description,
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            if msg.content.lower() == "cancel":
                return await ctx.reply("❌ Edit aborted. The past remains.", mention_author=False)

            if not msg.content.isdigit() or not (1 <= int(msg.content) <= len(matches)):
                return await ctx.reply("❌ Invalid choice. The spirits are confused. Aborted.", mention_author=False)

            index = int(msg.content) - 1
            old_quote = matches[index]

            await ctx.send(f"✏️ Etch the new path (or type 'cancel'):")
            new_msg = await self.bot.wait_for("message", check=check, timeout=120)

            if new_msg.content.lower() == "cancel":
                return await ctx.send("❌ Edit cancelled.")

            new_quote = new_msg.content.strip()
            if len(new_quote) > 2000:
                return await ctx.send("❌ Quote too long (max 2000 characters)")

            await update_quote_in_db(old_quote, new_quote)
            await ctx.send(f"✅ Quote updated.")
        except asyncio.TimeoutError:
            await ctx.reply("⌛ The sands have run out. Aborted.", mention_author=False)

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
                f"⚠️ Too many matches for '{keyword}'. Conflicting scrolls found.\n{formatted}\n"
                f"Pick a number (1–{len(results)}), or `cancel`."
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

    @commands.command(name="dailyquote", aliases=["dq", "qotd"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dailyquote_command(self, ctx):
        """Show today's curated quote"""
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
            await ctx.reply("🚫 Peasant Detected. Begone!", mention_author=False)


    @commands.command(name="pickquote")
    @commands.has_permissions(administrator=True)
    async def pickquote_command(self, ctx, choice: str = None):
        """[Admin] Pick tomorrow's quote from the 3 evening candidates. Usage: .pickquote <1|2|3|random>"""
        candidates = getattr(self.bot, "pending_quotes", [])
        if not candidates:
            return await ctx.reply(
                "❌ No candidates available yet. They appear in #emperor after the 6pm daily quote.",
                mention_author=False
            )

        if choice is None:
            return await ctx.reply(
                "Usage: `.pickquote <1 | 2 | 3 | random>`", mention_author=False
            )

        choice = choice.strip().lower()
        if choice == "random":
            picked = random.choice(candidates)
        elif choice in ("1", "2", "3") and int(choice) <= len(candidates):
            picked = candidates[int(choice) - 1]
        else:
            return await ctx.reply(
                "❌ Invalid choice. Use `1`, `2`, `3`, or `random`.", mention_author=False
            )

        self.bot.tomorrow_quote = picked
        self.bot.pending_quotes = []  # Clear so it can't be re-picked

        embed = discord.Embed(
            title="✅ Tomorrow's Quote — Locked In",
            description=f"📜 {picked}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Chosen by {ctx.author.display_name} · Posts at 10am & 6pm tomorrow")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QuotesCog(bot))
