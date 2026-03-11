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
            daily_quote = await tasks.get_daily_quote_async()
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


    @commands.command(name="pv", aliases=["pickquote"])
    @commands.has_permissions(administrator=True)
    async def pickquote_command(self, ctx, choice: str = None):
        """[Admin] Pick tomorrow's quote via reaction. Usage: .pv | .pv revote"""

        choice_lower = (choice or "").strip().lower()

        # --- REVOKE: regenerate 3 fresh candidates and re-post to #emperor ---
        if choice_lower == "revote":
            try:
                all_quotes = await load_quotes_from_db()
                today = await tasks.get_daily_quote_async()
                pool = [q for q in all_quotes if q != today]
                if not pool:
                    return await ctx.reply("❌ Not enough quotes in the pool to pick from.", mention_author=False)

                candidates = random.sample(pool, min(3, len(pool)))
                await tasks._set_pending_quotes(candidates)
                await tasks._set_tomorrow_quote(None)
                self.bot.pending_quotes = candidates
                self.bot.tomorrow_quote = None

                # Re-post to #emperor with reactions
                NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]
                pick_embed = discord.Embed(
                    title="🔄 Tomorrow's Quote — New Vote",
                    description="\n\n".join(f"{NUMBER_EMOJIS[i]} {q}" for i, q in enumerate(candidates)),
                    color=discord.Color.blurple(),
                )
                emperor_channel = discord.utils.get(ctx.guild.text_channels, name="emperor")
                target_channel = emperor_channel or ctx.channel
                
                msg = await target_channel.send(embed=pick_embed)
                for emoji in NUMBER_EMOJIS[:len(candidates)]:
                    await msg.add_reaction(emoji)
                
                # Save msg ID for the listener
                from tasks import PV_MSG_ID_KEY
                from database import set_setting
                await set_setting(PV_MSG_ID_KEY, str(msg.id))

                if emperor_channel and target_channel != ctx.channel:
                    await ctx.reply(f"✅ New vote posted in {emperor_channel.mention}.", mention_author=False)

            except Exception as e:
                logger.error(f"Error in pv revote: {e}")
                await ctx.reply("❌ Error generating new candidates.", mention_author=False)
            return

        # --- VOTE: load pending candidates and post reaction vote ---
        candidates = await tasks._get_pending_quotes()
        if not candidates:
            candidates = getattr(self.bot, "pending_quotes", [])

        if not candidates:
            return await ctx.reply(
                "❌ No candidates loaded. Use `.pv revote` to generate a fresh set.",
                mention_author=False
            )

        await self._post_candidate_vote(ctx, candidates, title="📋 Tomorrow's Quote — React to Vote")

    async def _post_candidate_vote(self, ctx, candidates: list, title: str):
        """Post a reaction-voteable embed to #emperor (or current channel) and wait for admin pick."""
        NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]
        emojis = NUMBER_EMOJIS[:len(candidates)]

        lines = "\n\n".join(f"{emojis[i]} {q}" for i, q in enumerate(candidates))
        pick_embed = discord.Embed(
            title=title,
            description=lines,
            color=discord.Color.blurple(),
        )
        pick_embed.set_footer(text="React below to choose tomorrow's quote")

        guild = ctx.guild
        emperor_channel = discord.utils.get(guild.text_channels, name="emperor") if guild else None
        target_channel = emperor_channel or ctx.channel

        vote_msg = await target_channel.send(embed=pick_embed)
        for emoji in emojis:
            await vote_msg.add_reaction(emoji)

        if emperor_channel and target_channel != ctx.channel:
            await ctx.reply(f"✅ Vote posted in {emperor_channel.mention}. React to pick.", mention_author=False)

        # Wait for a reaction from the command author
        def check(reaction, user):
            return (
                user.id == ctx.author.id
                and reaction.message.id == vote_msg.id
                and str(reaction.emoji) in emojis
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=300.0, check=check)
            idx = emojis.index(str(reaction.emoji))
            picked = candidates[idx]
        except asyncio.TimeoutError:
            await target_channel.send("⌛ No pick made — vote timed out. Use `.pv` to try again.")
            return

        await tasks._set_tomorrow_quote(picked)
        await tasks._set_pending_quotes([])
        self.bot.tomorrow_quote = picked
        self.bot.pending_quotes = []

        embed = discord.Embed(
            title="✅ Tomorrow's Quote — Locked In",
            description=f"📜 {picked}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Chosen by {ctx.author.display_name} · Posts at 10am & 6pm tomorrow")
        await target_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Listen for 1, 2, 3 reactions on the current PV message."""
        if payload.user_id == self.bot.user.id:
            return
        
        from database import get_setting
        from tasks import PV_MSG_ID_KEY
        pv_msg_id = await get_setting(PV_MSG_ID_KEY)
        if not pv_msg_id or str(payload.message_id) != pv_msg_id:
            return

        # Check if user is an admin
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or not member.guild_permissions.administrator:
            return

        # Check if emoji is 1, 2, or 3
        NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]
        emoji_str = str(payload.emoji)
        if emoji_str not in NUMBER_EMOJIS:
            return

        # Lock it in
        candidates = await tasks._get_pending_quotes()
        if not candidates:
            return

        idx = NUMBER_EMOJIS.index(emoji_str)
        if idx >= len(candidates):
            return
        
        picked = candidates[idx]
        await tasks._set_tomorrow_quote(picked)
        await tasks._set_pending_quotes([])
        self.bot.tomorrow_quote = picked
        self.bot.pending_quotes = []
        # Clear PV message ID so we don't double-trigger
        from database import set_setting
        await set_setting(PV_MSG_ID_KEY, "")

        # Notify
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            embed = discord.Embed(
                title="✅ Tomorrow's Quote — Locked In",
                description=f"📜 {picked}",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Chosen by {member.display_name} via reaction")
            await channel.send(embed=embed)

    # ── =quote REPLY LISTENER ─────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle =quote (reply-based quote saving) and bot ping quote drops."""
        if message.author.bot or not message.guild:
            return

        content = message.content.strip()

        # --- =quote: save the replied-to message as a quote ---
        if content.lower() == "=quote" and message.reference and message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if not ref_msg.content or len(ref_msg.content) > 2000:
                    return await message.reply("❌ That message can't be quoted.", mention_author=False)
                
                quote_text = ref_msg.content.strip()
                await add_quote_to_db(quote_text)
                await message.reply(f"📜 Quote added: *\"{quote_text[:100]}{'...' if len(quote_text) > 100 else ''}\"*", mention_author=False)
            except Exception as e:
                logger.error(f"Error in =quote: {e}")
            return

        # --- Bot ping: 40% chance to drop a random quote ---
        if self.bot.user in message.mentions:
            if random.random() < 0.40:
                try:
                    from database import get_db
                    async with get_db() as conn:
                        async with conn.execute("SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1") as cur:
                            row = await cur.fetchone()
                    if row:
                        await message.reply(f"📜 *\"{row[0]}\"*", mention_author=False)
                except Exception as e:
                    logger.error(f"Error in ping quote: {e}")

    # ── QUOTE DROP LOOP ───────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self, '_quote_drop_started'):
            self._quote_drop_started = True
            self.bot.loop.create_task(self._quote_drop_loop())

    async def _quote_drop_loop(self):
        """Background task that drops random quotes to #forum based on quotes_per_day setting."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                from database import get_setting
                per_day = await get_setting("quotes_per_day", "0")
                per_day = int(per_day)
                
                if per_day <= 0:
                    await asyncio.sleep(300)  # Check again in 5 minutes
                    continue
                
                # Calculate interval: spread drops evenly across 24 hours
                interval = (24 * 3600) / per_day
                # Add some randomness (±25%)
                jitter = interval * 0.25
                wait_time = interval + random.uniform(-jitter, jitter)
                wait_time = max(wait_time, 60)  # At least 1 minute between drops
                
                await asyncio.sleep(wait_time)
                
                # Find #forum channel and drop a random quote
                for guild in self.bot.guilds:
                    channel = discord.utils.get(guild.text_channels, name="forum")
                    if channel:
                        from database import get_db
                        async with get_db() as conn:
                            async with conn.execute("SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1") as cur:
                                row = await cur.fetchone()
                        if row:
                            await channel.send(f"📜 *\"{row[0]}\"*")
                            logger.info(f"📜 Quote drop: {row[0][:60]}...")
                        break
                        
            except Exception as e:
                logger.error(f"Error in quote drop loop: {e}", exc_info=True)
                await asyncio.sleep(300)


async def setup(bot):
    await bot.add_cog(QuotesCog(bot))
