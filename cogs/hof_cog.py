"""
Hall of Fame Cog — Starboard-style feature for apebot
Slash commands:  /hall <subcommand>       (admin config + leaderboard)
Context menu:    "Add to Hall of Fame"    (right-click any message, admin)
Prefix commands: .hall random | .hall @user
"""

import json
import time
import logging
import random
import re
import discord
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
from database import get_db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────

async def _get_settings(guild_id: int) -> dict:
    gid = str(guild_id)
    async with get_db() as conn:
        async with conn.execute(
            "SELECT channel_id, threshold, emojis, autostar_channels, "
            "ignored_channels, locked_messages, trashed_messages, blacklisted_users "
            "FROM hof_settings WHERE guild_id = ?", (gid,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return {
            "channel_id": None, "threshold": 3,
            "emojis": ["⭐"],
            "autostar_channels": [], "ignored_channels": [],
            "locked_messages": [], "trashed_messages": [],
            "blacklisted_users": [],
        }
    return {
        "channel_id": row[0],
        "threshold":  row[1],
        "emojis":            json.loads(row[2]),
        "autostar_channels": json.loads(row[3]),
        "ignored_channels":  json.loads(row[4]),
        "locked_messages":   json.loads(row[5]),
        "trashed_messages":  json.loads(row[6]),
        "blacklisted_users": json.loads(row[7]) if len(row) > 7 else [],
    }


async def _set_settings(guild_id: int, **fields):
    gid = str(guild_id)
    s = await _get_settings(guild_id)
    for k, v in fields.items():
        s[k] = v
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO hof_settings
                (guild_id, channel_id, threshold, emojis, autostar_channels,
                 ignored_channels, locked_messages, trashed_messages, blacklisted_users)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id         = excluded.channel_id,
                threshold          = excluded.threshold,
                emojis             = excluded.emojis,
                autostar_channels  = excluded.autostar_channels,
                ignored_channels   = excluded.ignored_channels,
                locked_messages    = excluded.locked_messages,
                trashed_messages   = excluded.trashed_messages,
                blacklisted_users  = excluded.blacklisted_users
            """,
            (gid,
             s["channel_id"], s["threshold"],
             json.dumps(s["emojis"]),
             json.dumps(s["autostar_channels"]),
             json.dumps(s["ignored_channels"]),
             json.dumps(s["locked_messages"]),
             json.dumps(s["trashed_messages"]),
             json.dumps(s["blacklisted_users"])),
        )


async def _get_entry(msg_id: int):
    async with get_db() as conn:
        async with conn.execute(
            "SELECT orig_message_id, orig_channel_id, author_id, hof_message_id, "
            "star_count, content, image_url, jump_url, voice_url, trigger_emoji FROM hof_entries WHERE orig_message_id = ?",
            (str(msg_id),)
        ) as cur:
            return await cur.fetchone()


async def _upsert_entry(orig_msg_id, orig_ch_id, author_id, hof_msg_id,
                        star_count, content, image_url, jump_url, voice_url=None, trigger_emoji=None):
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO hof_entries
                (orig_message_id, orig_channel_id, author_id, hof_message_id,
                 star_count, content, image_url, jump_url, voice_url, trigger_emoji, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(orig_message_id) DO UPDATE SET
                hof_message_id = excluded.hof_message_id,
                star_count     = excluded.star_count,
                content        = excluded.content,
                image_url      = excluded.image_url,
                voice_url      = excluded.voice_url,
                trigger_emoji  = COALESCE(hof_entries.trigger_emoji, excluded.trigger_emoji)
            """,
            (str(orig_msg_id), str(orig_ch_id), str(author_id),
             str(hof_msg_id) if hof_msg_id else None,
             star_count, content, image_url, jump_url, voice_url, trigger_emoji, time.time())
        )


# ─────────────────────────────────────────────────────────────
# EMBED BUILDER
# ─────────────────────────────────────────────────────────────

def _extract_image(message: discord.Message) -> str | None:
    for att in message.attachments:
        if att.content_type and att.content_type.startswith("image/"):
            return att.url
    for emb in message.embeds:
        if emb.image and emb.image.url:
            return emb.image.url
        if emb.thumbnail and emb.thumbnail.url:
            return emb.thumbnail.url
    m = re.search(r"https?://\S+\.(?:png|jpg|jpeg|gif|webp)", message.content or "", re.I)
    return m.group(0) if m else None


def _extract_voice(message: discord.Message) -> str | None:
    """Return the URL of the first audio/video attachment (covers Discord voice notes)."""
    for att in message.attachments:
        ct = att.content_type or ""
        if ct.startswith("audio/") or ct.startswith("video/"):
            return att.url
    return None


def _count_by_emoji_from_reactions(message: discord.Message, tracked: list) -> dict:
    return {str(r.emoji): r.count for r in message.reactions if str(r.emoji) in tracked}


async def _build_hof_data(
    message: discord.Message,
    emoji_counts: dict,
    jump_url: str,
    trigger_emoji: str = None,
) -> tuple[str, discord.Embed]:
    """
    Final Layout:
    [emoji] [count] in [#channel](jump_url)
    [Gold Embed Box]
      [Author avatar] AuthorName
      *Replying to @user: content...*
      Original message text
      🎙️ [Voice Note]
      [Attached image]
    """
    # 1. Plain Text Header (above embed)
    if trigger_emoji:
        count = emoji_counts.get(trigger_emoji, 1)
        content_header = f"{trigger_emoji} **{count}** in [#{(message.channel.name or 'channel')}]({jump_url})"
    else:
        content_header = f"in [#{(message.channel.name or 'channel')}]({jump_url})"

    # 2. Reply Context
    reply_text = ""
    if message.reference and message.reference.message_id:
        try:
            # Try to fetch from cache first if possible, but fetch is safer
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            snippet = ref_msg.content[:150] + ("..." if len(ref_msg.content) > 150 else "")
            reply_text = f"⤷ *Replying to {ref_msg.author.mention}:* {snippet}\n\n"
        except Exception:
            # If we can't find it (deleted etc), just skip context
            pass

    # 3. Voice note line (Discord voice messages are audio attachments)
    voice_url = _extract_voice(message)
    voice_line = f"\n\n🎙️ [Voice Note]({voice_url})" if voice_url else ""

    # 4. Embed Box - Always Gold
    base_text = f"{reply_text}{message.content[:3800]}" if (message.content or reply_text) else ""
    description = (base_text + voice_line).strip() or None

    embed = discord.Embed(
        description=description,
        color=0xFFD700,
        timestamp=message.created_at,
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url,
    )

    image_url = _extract_image(message)
    if image_url:
        embed.set_image(url=image_url)

    return content_header, embed


# ─────────────────────────────────────────────────────────────
# CORE LOGIC — post / update / remove HOF entry
# ─────────────────────────────────────────────────────────────

async def _post_or_update_hof(
    bot: commands.Bot,
    guild: discord.Guild,
    message: discord.Message,
    emoji_counts: dict,
    s: dict,
    trigger_emoji: str = None,
):
    """Post or update the HOF embed."""
    hof_ch = guild.get_channel(int(s["channel_id"]))
    if not hof_ch:
        return

    entry          = await _get_entry(message.id)
    jump_url       = message.jump_url
    content, embed = await _build_hof_data(message, emoji_counts, jump_url, trigger_emoji=trigger_emoji)

    hof_msg = None
    if entry and entry[3]:
        try:
            hof_msg = await hof_ch.fetch_message(int(entry[3]))
            await hof_msg.edit(content=content, embed=embed)
        except discord.NotFound:
            hof_msg = None

    if hof_msg is None:
        hof_msg = await hof_ch.send(content=content, embed=embed)
        # Bot self-reacts ONLY with the trigger emoji
        if trigger_emoji:
            try:
                await hof_msg.add_reaction(trigger_emoji)
            except Exception:
                pass

    total = sum(emoji_counts.values()) if emoji_counts else 0
    await _upsert_entry(
        message.id, message.channel.id, message.author.id,
        hof_msg.id, total,
        message.content, _extract_image(message), jump_url,
        voice_url=_extract_voice(message),
        trigger_emoji=trigger_emoji
    )

    # ── AUTO-QUOTE: add short text-only HoF entries to quote drops DB ──
    if (
        message.content
        and len(message.content.strip()) <= 25
        and not message.attachments
        and not message.embeds
    ):
        try:
            from database import add_quote_drop
            await add_quote_drop(message.content.strip(), str(message.author.id))
            logger.info(f"📜 Auto-quoted HoF entry: \"{message.content.strip()}\"")
        except Exception as e:
            logger.warning(f"Auto-quote failed: {e}")


# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────

class _jump_view(discord.ui.View):
    """A simple View with a single 'Jump to message' link button."""
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Jump to message", url=url, style=discord.ButtonStyle.link))


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class HofCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.locks = {} # msg_id -> Lock
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(hours=24)
    async def cleanup_task(self):
        """Purge non-HOF entries older than 30 days and prune stale locks."""
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        async with get_db() as conn:
            await conn.execute(
                "DELETE FROM hof_entries WHERE hof_message_id IS NULL AND created_at < ?",
                (thirty_days_ago,)
            )
            await conn.commit()
        # Prune reaction locks — if dict gets large, clear it entirely
        if len(self.locks) > 500:
            self.locks.clear()
        logger.info("🧹 Cleaned up old Hall of Fame rejects.")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # ── REACTION HANDLING ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload)

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        # Serialization: ensure one reaction at a time per message to prevent race induction
        lock = self.locks.setdefault(payload.message_id, asyncio.Lock())
        
        async with lock:
            s = await _get_settings(payload.guild_id)
            if not s["channel_id"]:
                return

            # Check blacklist (voter)
            if str(payload.user_id) in s.get("blacklisted_users", []):
                return
            if str(payload.emoji) not in s["emojis"]:
                return
            if str(payload.channel_id) == s["channel_id"]:
                return  # Ignore reactions on HOF channel itself
            if str(payload.channel_id) in s["ignored_channels"]:
                return
            if str(payload.message_id) in s["trashed_messages"]:
                return

            guild   = self.bot.get_guild(payload.guild_id)
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                return
            try:
                message = await channel.fetch_message(payload.message_id)
            except Exception:
                return

            # Check blacklist (author)
            if str(message.author.id) in s.get("blacklisted_users", []):
                return

            emoji_counts = _count_by_emoji_from_reactions(message, s["emojis"])
            max_count = max(emoji_counts.values()) if emoji_counts else 0
            is_locked = str(payload.message_id) in s["locked_messages"]

            entry = await _get_entry(payload.message_id)
            persistent_trigger = entry[9] if entry else None

            if max_count >= s["threshold"]:
                # Use persistent trigger if available, else current reaction
                trigger = persistent_trigger or str(payload.emoji)
                await _post_or_update_hof(self.bot, guild, message, emoji_counts, s, trigger_emoji=trigger)
                # Cleanup lock after completion (optional, but keep it for threshold transitions)
            else:
                if entry and entry[3] and not is_locked:
                    hof_ch = guild.get_channel(int(s["channel_id"]))
                    if hof_ch:
                        try:
                            await (await hof_ch.fetch_message(int(entry[3]))).delete()
                        except discord.NotFound:
                            pass
                    await _upsert_entry(
                        message.id, channel.id, message.author.id,
                        None, max_count,
                        message.content, _extract_image(message), message.jump_url,
                        voice_url=_extract_voice(message),
                        trigger_emoji=persistent_trigger
                    )
                elif max_count > 0:
                    # Always populate entries with at least 1 reaction to support "lost hall"
                    await _upsert_entry(
                        message.id, channel.id, message.author.id,
                        None, max_count,
                        message.content, _extract_image(message), message.jump_url,
                        voice_url=_extract_voice(message),
                        trigger_emoji=persistent_trigger or str(payload.emoji)
                    )

    # ── AUTO-STAR ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        s = await _get_settings(message.guild.id)
        if str(message.channel.id) not in s["autostar_channels"]:
            return
        for emoji in s["emojis"]:
            try:
                await message.add_reaction(emoji)
            except Exception:
                pass

    # ── PREFIX BROWSE (.hall random | .hall @user) ────────────

    @commands.command(name="hall", aliases=["hof"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def hall_command(self, ctx, *, arg: str = None):
        """Browse Hall of Fame. Usage: .hall random | .hall @user | .hall lost"""
        async with ctx.channel.typing():
            async with get_db() as conn:
                if arg == "lost":
                    # Pull a random message with 2+ stars that isn't in the HOF
                    async with conn.execute(
                        "SELECT author_id, star_count, content, image_url, jump_url, voice_url "
                        "FROM hof_entries "
                        "WHERE hof_message_id IS NULL AND star_count >= 2 "
                        "ORDER BY RANDOM() LIMIT 1"
                    ) as cur:
                        row = await cur.fetchone()
                    
                    if not row:
                        return await ctx.reply("❌ No 'lost' entries found yet.", mention_author=False)
                    
                    author_id, star_count, content, image_url, jump_url, voice_url = row
                    s = await _get_settings(ctx.guild.id)
                    emoji = s["emojis"][0] if s["emojis"] else "⭐"
                    author = ctx.guild.get_member(int(author_id)) or await self.bot.fetch_user(int(author_id))

                    embed = discord.Embed(
                        description=content[:4090] if content else "*[no text]*",
                        color=0x808080,
                    )
                    embed.set_author(name=getattr(author, "display_name", str(author)), icon_url=author.display_avatar.url)
                    if image_url:
                        embed.set_image(url=image_url)
                    embed.set_footer(text=f"{emoji} {star_count} — no cigar")
                    return await ctx.send(embed=embed, view=_jump_view(jump_url) if jump_url else None)

                elif arg and ctx.message.mentions:
                    uid = str(ctx.message.mentions[0].id)
                    async with conn.execute(
                        "SELECT author_id, hof_message_id, star_count, content, image_url, jump_url, voice_url "
                        "FROM hof_entries WHERE author_id = ? AND hof_message_id IS NOT NULL "
                        "ORDER BY RANDOM() LIMIT 1", (uid,)
                    ) as cur:
                        row = await cur.fetchone()
                    if not row:
                        m = ctx.message.mentions[0]
                        return await ctx.reply(
                            f"❌ No Hall of Fame entries found for **{m.display_name}**.",
                            mention_author=False
                        )
                else:
                    async with conn.execute(
                        "SELECT author_id, hof_message_id, star_count, content, image_url, jump_url, voice_url "
                        "FROM hof_entries WHERE hof_message_id IS NOT NULL "
                        "ORDER BY RANDOM() LIMIT 1"
                    ) as cur:
                        row = await cur.fetchone()
                    if not row:
                        return await ctx.reply(
                            "❌ The Hall of Fame is empty — start reacting to messages!",
                            mention_author=False
                        )

            author_id, hof_msg_id, star_count, content, image_url, jump_url, voice_url = row
            author = ctx.guild.get_member(int(author_id)) or await self.bot.fetch_user(int(author_id))

            voice_line = f"\n\n🎙️ [Voice Note]({voice_url})" if voice_url else ""
            description = (content[:4090] if content else "") + voice_line
            embed = discord.Embed(
                description=description.strip() or "*[no text]*",
                color=0xFFD700,
            )
            embed.set_author(
                name=getattr(author, "display_name", str(author)),
                icon_url=author.display_avatar.url,
            )
            if image_url:
                embed.set_image(url=image_url)
            embed.set_footer(text=f"⭐ {star_count} total reactions")
            await ctx.send(embed=embed, view=_jump_view(jump_url) if jump_url else None)

    @hall_command.error
    async def hall_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return

    # ── SLASH COMMAND GROUP ───────────────────────────────────

    hall_group = app_commands.Group(
        name="hall",
        description="Hall of Fame — configure and view the starboard system",
    )

    @hall_group.command(name="setup", description="Set the #hall-of-fame channel")
    @app_commands.describe(channel="Channel where starred messages appear")
    @app_commands.default_permissions(administrator=True)
    async def slash_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await _set_settings(interaction.guild_id, channel_id=str(channel.id))
        await interaction.response.send_message(
            f"✅ Hall of Fame channel set to {channel.mention}.", ephemeral=True
        )

    @hall_group.command(name="threshold", description="Set how many reactions a message needs")
    @app_commands.describe(count="Reactions required (default: 3)")
    @app_commands.default_permissions(administrator=True)
    async def slash_threshold(self, interaction: discord.Interaction, count: int):
        if count < 1:
            return await interaction.response.send_message("❌ Must be at least 1.", ephemeral=True)
        await _set_settings(interaction.guild_id, threshold=count)
        await interaction.response.send_message(f"✅ Threshold set to **{count}**.", ephemeral=True)

    @hall_group.command(name="emojis", description="Set which emojis are tracked (space-separated)")
    @app_commands.describe(emojis="e.g.  ⭐ 🔥 💯")
    @app_commands.default_permissions(administrator=True)
    async def slash_emojis(self, interaction: discord.Interaction, emojis: str):
        parsed = emojis.strip().split()
        if not parsed:
            return await interaction.response.send_message("❌ Provide at least one emoji.", ephemeral=True)
        await _set_settings(interaction.guild_id, emojis=parsed)
        await interaction.response.send_message(
            f"✅ Tracking: {'  '.join(parsed)}", ephemeral=True
        )

    @hall_group.command(name="ignore", description="Exclude a channel from the Hall of Fame")
    @app_commands.describe(channel="Channel to ignore")
    @app_commands.default_permissions(administrator=True)
    async def slash_ignore(self, interaction: discord.Interaction, channel: discord.TextChannel):
        s = await _get_settings(interaction.guild_id)
        ignored = s["ignored_channels"]
        if str(channel.id) not in ignored:
            ignored.append(str(channel.id))
        await _set_settings(interaction.guild_id, ignored_channels=ignored)
        await interaction.response.send_message(f"✅ {channel.mention} ignored.", ephemeral=True)

    @hall_group.command(name="unignore", description="Re-allow a previously ignored channel")
    @app_commands.describe(channel="Channel to unignore")
    @app_commands.default_permissions(administrator=True)
    async def slash_unignore(self, interaction: discord.Interaction, channel: discord.TextChannel):
        s = await _get_settings(interaction.guild_id)
        ignored = [c for c in s["ignored_channels"] if c != str(channel.id)]
        await _set_settings(interaction.guild_id, ignored_channels=ignored)
        await interaction.response.send_message(f"✅ {channel.mention} unignored.", ephemeral=True)

    @hall_group.command(name="autostar", description="Toggle auto-react in a channel")
    @app_commands.describe(channel="Channel to toggle")
    @app_commands.default_permissions(administrator=True)
    async def slash_autostar(self, interaction: discord.Interaction, channel: discord.TextChannel):
        s = await _get_settings(interaction.guild_id)
        asc = s["autostar_channels"]
        cid = str(channel.id)
        if cid in asc:
            asc.remove(cid)
            msg = f"✅ Auto-star **off** for {channel.mention}."
        else:
            asc.append(cid)
            msg = f"✅ Auto-star **on** for {channel.mention}."
        await _set_settings(interaction.guild_id, autostar_channels=asc)
        await interaction.response.send_message(msg, ephemeral=True)

    @hall_group.command(name="lock", description="Freeze a HOF entry (won't be removed if stars drop)")
    @app_commands.describe(message_link="Right-click a message → Copy Message Link")
    @app_commands.default_permissions(administrator=True)
    async def slash_lock(self, interaction: discord.Interaction, message_link: str):
        msg_id = _parse_message_id(message_link)
        if not msg_id:
            return await interaction.response.send_message("❌ Invalid message link.", ephemeral=True)
        s = await _get_settings(interaction.guild_id)
        locked = s["locked_messages"]
        if msg_id not in locked:
            locked.append(msg_id)
        await _set_settings(interaction.guild_id, locked_messages=locked)
        await interaction.response.send_message("🔒 Entry locked.", ephemeral=True)

    @hall_group.command(name="trash", description="Remove from HOF and permanently blacklist the message")
    @app_commands.describe(message_link="Right-click a message → Copy Message Link")
    @app_commands.default_permissions(administrator=True)
    async def slash_trash(self, interaction: discord.Interaction, message_link: str):
        msg_id = _parse_message_id(message_link)
        if not msg_id:
            return await interaction.response.send_message("❌ Invalid message link.", ephemeral=True)
        s = await _get_settings(interaction.guild_id)
        trashed = s["trashed_messages"]
        if msg_id not in trashed:
            trashed.append(msg_id)
        await _set_settings(interaction.guild_id, trashed_messages=trashed)

        entry = await _get_entry(int(msg_id))
        if entry and entry[3] and s["channel_id"]:
            hof_ch = interaction.guild.get_channel(int(s["channel_id"]))
            if hof_ch:
                try:
                    await (await hof_ch.fetch_message(int(entry[3]))).delete()
                except discord.NotFound:
                    pass
            await _upsert_entry(int(msg_id), entry[1], entry[2], None, entry[4], entry[5], entry[6], entry[7], voice_url=entry[8] if len(entry) > 8 else None)

        await interaction.response.send_message("🗑️ Removed and blacklisted.", ephemeral=True)

    @hall_group.command(name="settings", description="Show current Hall of Fame configuration")
    @app_commands.default_permissions(administrator=True)
    async def slash_settings(self, interaction: discord.Interaction):
        s = await _get_settings(interaction.guild_id)
        hof_ch  = f"<#{s['channel_id']}>" if s["channel_id"] else "❌ Not set"
        emojis  = "  ".join(s["emojis"]) if s["emojis"] else "None"
        autostr = ", ".join(f"<#{c}>" for c in s["autostar_channels"]) or "None"
        ignored = ", ".join(f"<#{c}>" for c in s["ignored_channels"]) or "None"
        embed = discord.Embed(title="🏆 Hall of Fame Settings", color=0xFFD700)
        embed.add_field(name="Channel",   value=hof_ch,              inline=True)
        embed.add_field(name="Threshold", value=str(s["threshold"]), inline=True)
        embed.add_field(name="Emojis",    value=emojis,              inline=True)
        embed.add_field(name="Auto-star", value=autostr,             inline=False)
        embed.add_field(name="Ignored",   value=ignored,             inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @hall_group.command(name="leaderboard", description="Top users by cumulative Hall of Fame reactions")
    @app_commands.describe(limit="How many users to show (default 15)")
    async def slash_leaderboard(self, interaction: discord.Interaction, limit: int = 15):
        limit = max(1, min(limit, 25))

        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT author_id, SUM(star_count) as total
                FROM hof_entries
                WHERE hof_message_id IS NOT NULL
                GROUP BY author_id
                ORDER BY total DESC
                LIMIT ?
                """,
                (limit,)
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "❌ No Hall of Fame entries yet.", ephemeral=True
            )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (author_id, total) in enumerate(rows):
            member = interaction.guild.get_member(int(author_id))
            name   = member.display_name if member else f"User {author_id}"
            prefix = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{prefix}  **{name}** — {total:,} reactions")

        embed = discord.Embed(
            title="🏆 Hall of Fame Leaderboard",
            description="\n".join(lines),
            color=0xFFD700,
        )
        embed.set_footer(text="Cumulative reactions across all tracked emojis")
        await interaction.response.send_message(embed=embed)

    @hall_group.command(name="export", description="Export the Hall of Fame as a CSV file")
    @app_commands.default_permissions(administrator=True)
    async def slash_export(self, interaction: discord.Interaction):
        """Generate a CSV of every HOF entry — author, content, reactions, media URL, jump link."""
        import csv
        import io
        from datetime import datetime, timezone

        await interaction.response.defer(ephemeral=True)

        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT e.orig_message_id, e.author_id, e.star_count,
                       e.content, e.image_url, e.jump_url, e.created_at
                FROM hof_entries e
                WHERE e.hof_message_id IS NOT NULL
                ORDER BY e.star_count DESC
                """
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await interaction.followup.send("❌ No Hall of Fame entries to export.", ephemeral=True)

        # Resolve display names
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "rank", "author", "author_id", "reactions",
            "message", "media_url", "jump_url", "date_added"
        ])

        for rank, (msg_id, author_id, star_count, content, image_url, jump_url, created_at) in enumerate(rows, 1):
            member = interaction.guild.get_member(int(author_id))
            author_name = member.display_name if member else f"User {author_id}"
            date_str = datetime.fromtimestamp(created_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if created_at else ""
            writer.writerow([
                rank,
                author_name,
                author_id,
                star_count,
                (content or "").replace("\n", " "),
                image_url or "",
                jump_url or "",
                date_str,
            ])

        output.seek(0)
        filename = f"hall_of_fame_{interaction.guild.name.replace(' ', '_')}.csv"
        file = discord.File(fp=io.BytesIO(output.getvalue().encode("utf-8")), filename=filename)

        await interaction.followup.send(
            f"📥 **Hall of Fame Export** — {len(rows)} entries",
            file=file,
            ephemeral=True,
        )
    @hall_group.command(name="random", description="Show a random entry from the Hall of Fame")
    async def slash_random(self, interaction: discord.Interaction):
        async with get_db() as conn:
            async with conn.execute(
                "SELECT author_id, star_count, content, image_url, jump_url, voice_url "
                "FROM hof_entries "
                "WHERE hof_message_id IS NOT NULL AND star_count > 0 "
                "ORDER BY RANDOM() LIMIT 1"
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return await interaction.response.send_message("❌ The Hall of Fame is empty.", ephemeral=True)

        await self._send_hof_embed(interaction, row)

    @hall_group.command(name="lost", description="Show a random Hall of Fame reject message")
    async def slash_lost(self, interaction: discord.Interaction):
        async with get_db() as conn:
            async with conn.execute(
                "SELECT author_id, star_count, content, image_url, jump_url "
                "FROM hof_entries "
                "WHERE hof_message_id IS NULL AND star_count >= 2 "
                "ORDER BY RANDOM() LIMIT 1"
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ No lost entries found yet.", ephemeral=True
            )

        s = await _get_settings(interaction.guild_id)
        emoji = s["emojis"][0] if s["emojis"] else "⭐"

        author_id, star_count, content, image_url, jump_url = row
        member = interaction.guild.get_member(int(author_id))
        if member is None:
            try:
                member = await self.bot.fetch_user(int(author_id))
            except Exception:
                member = None

        embed = discord.Embed(
            description=content[:4090] if content else "*[no text]*",
            color=0x808080,
        )
        if member:
            embed.set_author(name=getattr(member, "display_name", str(member)), icon_url=member.display_avatar.url)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text=f"{emoji} {star_count} — no cigar")

        view = _jump_view(jump_url) if jump_url else None
        await interaction.response.send_message(embed=embed, view=view)

    async def _send_hof_embed(self, interaction: discord.Interaction, row):
        """Shared helper to build and send a gold HOF embed from a DB row."""
        s = await _get_settings(interaction.guild_id)
        emoji = s["emojis"][0] if s["emojis"] else "⭐"

        author_id, star_count, content, image_url, jump_url, voice_url = row
        member = interaction.guild.get_member(int(author_id))
        if member is None:
            try:
                member = await self.bot.fetch_user(int(author_id))
            except Exception:
                member = None

        voice_line = f"\n\n🎙️ [Voice Note]({voice_url})" if voice_url else ""
        description = (content[:4090] if content else "") + voice_line
        embed = discord.Embed(
            description=description.strip() or "*[no text]*",
            color=0xFFD700,
        )
        if member:
            embed.set_author(name=getattr(member, "display_name", str(member)), icon_url=member.display_avatar.url)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text=f"{emoji} {star_count}")

        view = _jump_view(jump_url) if jump_url else None
        await interaction.response.send_message(embed=embed, view=view)

    @hall_group.command(name="search", description="Search the Hall of Fame by keyword")
    @app_commands.describe(query="Keywords to search for")
    async def slash_search(self, interaction: discord.Interaction, query: str):
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT jump_url, content 
                FROM hof_entries 
                WHERE hof_message_id IS NOT NULL AND content LIKE ? 
                LIMIT 5
                """,
                (f"%{query}%",)
            ) as cur:
                rows = await cur.fetchall()
        
        if not rows:
            return await interaction.response.send_message(f"🔍 No entries found for `{query}`.", ephemeral=True)
        
        links = [f"• {row[0]}" for row in rows]
        await interaction.response.send_message(f"🔍 **Search Results for `{query}`:**\n" + "\n".join(links))

    @hall_group.command(name="stats", description="Show Hall of Fame statistics for a user")
    @app_commands.describe(user="The user to check stats for")
    @app_commands.default_permissions(administrator=True)
    async def slash_stats(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        async with get_db() as conn:
            async with conn.execute(
                """
                SELECT COUNT(*), SUM(star_count) 
                FROM hof_entries 
                WHERE author_id = ? AND hof_message_id IS NOT NULL
                """,
                (str(target.id),)
            ) as cur:
                row = await cur.fetchone()
        
        count = row[0] if row else 0
        stars = row[1] if row and row[1] else 0
        
        embed = discord.Embed(
            title=f"📊 HOF Stats: {target.display_name}",
            color=0xFFD700
        )
        embed.add_field(name="🏛️ Inductions", value=f"`{count}`", inline=True)
        embed.add_field(name="✨ Total Reactions", value=f"`{stars}`", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)


    @hall_group.command(name="sync", description="[ADMIN] Manually scan and induct a message by its link")
    @app_commands.describe(link="The link to the Discord message")
    @app_commands.default_permissions(administrator=True)
    async def slash_sync_msg(self, interaction: discord.Interaction, link: str):
        msg_id = _parse_message_id(link)
        if not msg_id:
            return await interaction.response.send_message("❌ Invalid message link.", ephemeral=True)
        
        # We need to fetch the message. Usually links are guild/channel/message
        # Format: https://discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
        parts = link.split("/")
        if len(parts) < 3:
             return await interaction.response.send_message("❌ Invalid link format.", ephemeral=True)
        
        try:
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                channel = await interaction.guild.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Error fetching message: {e}", ephemeral=True)

        await _force_to_hof(interaction, message)



# ─────────────────────────────────────────────────────────────
# CONTEXT MENU — right-click "Add to Hall of Fame"
# ─────────────────────────────────────────────────────────────

async def _force_to_hof(interaction: discord.Interaction, message: discord.Message):
    """Right-click context menu: force any message into the Hall of Fame."""
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("🚫 Admins only.", ephemeral=True)

    s = await _get_settings(interaction.guild_id)
    if not s["channel_id"]:
        return await interaction.response.send_message(
            "❌ Hall of Fame channel not set. Use `/hall setup` first.", ephemeral=True
        )

    if str(message.channel.id) == s["channel_id"]:
        return await interaction.response.send_message(
            "❌ Can't add a HOF message to itself.", ephemeral=True
        )

    # Allow forced adds even if trashed — remove from trash first
    trashed = s["trashed_messages"]
    if str(message.id) in trashed:
        trashed.remove(str(message.id))
        await _set_settings(interaction.guild_id, trashed_messages=trashed)

    # Build emoji counts from existing reactions (if any); empty dict if none
    emoji_counts = {}
    for r in message.reactions:
        if str(r.emoji) in s["emojis"]:
            emoji_counts[str(r.emoji)] = r.count

    # Choose a random emoji for the header/self-react if forced
    trigger = random.choice(s["emojis"]) if s["emojis"] else None
    await _force_post_to_hof(interaction.client, interaction.guild, message, emoji_counts, s, trigger)

    await interaction.response.send_message(
        f"✅ Message by **{message.author.display_name}** added to the Hall of Fame.", ephemeral=True
    )


async def _force_post_to_hof(bot, guild, message, emoji_counts, s, trigger_emoji):
    """Same as _post_or_update_hof but always posts regardless of threshold."""
    hof_ch = guild.get_channel(int(s["channel_id"]))
    if not hof_ch:
        return

    entry          = await _get_entry(message.id)
    jump_url       = message.jump_url
    content, embed = await _build_hof_data(message, emoji_counts, jump_url, trigger_emoji=trigger_emoji)

    hof_msg = None
    if entry and entry[3]:
        try:
            hof_msg = await hof_ch.fetch_message(int(entry[3]))
            await hof_msg.edit(content=content, embed=embed)
        except discord.NotFound:
            hof_msg = None

    if hof_msg is None:
        hof_msg = await hof_ch.send(content=content, embed=embed)
        if trigger_emoji:
            try:
                await hof_msg.add_reaction(trigger_emoji)
            except Exception:
                pass

    total = sum(emoji_counts.values()) if emoji_counts else 0
    await _upsert_entry(
        message.id, message.channel.id, message.author.id,
        hof_msg.id, total,
        message.content, _extract_image(message), jump_url,
        voice_url=_extract_voice(message),
        trigger_emoji=trigger_emoji
    )


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _parse_message_id(link: str) -> str | None:
    m = re.search(r"/(\d+)$", link.strip())
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────

@app_commands.context_menu(name="Add to Hall of Fame")
@app_commands.default_permissions(administrator=True)
async def force_to_hof_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Right-click context menu: force any message into the Hall of Fame."""
    await _force_to_hof(interaction, message)


@app_commands.context_menu(name="Trash from Hall of Fame")
@app_commands.default_permissions(administrator=True)
async def trash_from_hof_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Right-click context menu: remove a message from the Hall of Fame and blacklist it."""
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("🚫 Admins only.", ephemeral=True)

    s = await _get_settings(interaction.guild_id)
    msg_id = str(message.id)

    trashed = s["trashed_messages"]
    if msg_id not in trashed:
        trashed.append(msg_id)
    await _set_settings(interaction.guild_id, trashed_messages=trashed)

    entry = await _get_entry(message.id)
    if entry and entry[3] and s["channel_id"]:
        hof_ch = interaction.guild.get_channel(int(s["channel_id"]))
        if hof_ch:
            try:
                await (await hof_ch.fetch_message(int(entry[3]))).delete()
            except discord.NotFound:
                pass
        await _upsert_entry(message.id, entry[1], entry[2], None, entry[4], entry[5], entry[6], entry[7], voice_url=entry[8] if len(entry) > 8 else None)

    await interaction.response.send_message(
        f"🗑️ **{message.author.display_name}'s** message removed from the Hall of Fame and blacklisted.",
        ephemeral=True,
    )


async def setup(bot: commands.Bot):
    cog = HofCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(force_to_hof_context_menu)
    bot.tree.add_command(trash_from_hof_context_menu)
