"""
Admin Cog - Admin commands and system management
Commands: pink, gr, qd, blessing, cleanse, hierarchy, archive, debug, db* commands
"""

import discord
from discord.ext import commands
import logging
import asyncio
import time
import os
import shutil
import sqlite3
from datetime import datetime

from database import (
    update_pink_vote,
    get_active_pink_vote_count,
    add_masochist_role_removal,
    get_db,
    load_quotes_from_db,
    get_active_effect,
    remove_active_effect,
)
from config import (
    ROLE_ADD_QUOTE,
    CHANNEL_ID,
    TEST_CHANNEL_ID,
    DB_FILE,
    AUTHORIZED_ROLES,
)
from helpers import get_forum_channel
import hierarchy

logger = logging.getLogger(__name__)

# Constants
MASOCHIST_ROLE_ID = 1167184822129664113
VOTE_THRESHOLD = 7
ROLE_DURATION_SECONDS = 48 * 3600  # 2 days

# Role aliases
ROLE_ALIASES = {
    "niggapass": "1168965931918176297",
    "trial": "1444477594698514594",
    "masochist": "1167184822129664113",
    "hoe": "1168293630570676354",
    "vip": "1234567890123456793",
}


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pink")
    async def pink_command(self, ctx, member: discord.Member):
        """Votes to assign the Masochist role to a user. Requires 7 votes in 48h."""

        if member.id == ctx.author.id:
            return await ctx.reply(
                "❌ You can't vote for yourself... unless you're into that?",
                mention_author=False,
            )
        if member.bot:
            return await ctx.reply(
                "❌ Bots are immune to this torture.", mention_author=False
            )

        masochist_role = ctx.guild.get_role(MASOCHIST_ROLE_ID)
        if not masochist_role:
            return await ctx.send(
                f"❌ Error: The configured role ID ({MASOCHIST_ROLE_ID}) was not found on this server."
            )

        bot_member = ctx.guild.me

        if not bot_member.guild_permissions.manage_roles:
            return await ctx.send(
                "🛑 **SETUP ERROR:** I do not have the **`Manage Roles`** permission. "
                "I cannot assign or remove the Masochist role until this is fixed."
            )

        if bot_member.top_role.position <= masochist_role.position:
            return await ctx.send(
                f"🛑 **HIERARCHY ERROR:** My highest role (`{bot_member.top_role.name}`) is not positioned above "
                f"the target role (`{masochist_role.name}`). "
                "Please move my role higher than the Masochist role in the server settings."
            )

        if masochist_role in member.roles:
            return await ctx.reply(
                f"❌ {member.display_name} already has the {masochist_role.name} role.",
                mention_author=False,
            )

        voted_id_str = str(member.id)
        voter_id_str = str(ctx.author.id)

        await update_pink_vote(voted_id_str, voter_id_str)

        vote_count = await get_active_pink_vote_count(voted_id_str)

        if vote_count >= VOTE_THRESHOLD:
            try:
                await member.add_roles(
                    masochist_role, reason="Reached 7 pink votes in 48 hours."
                )

                removal_time = time.time() + ROLE_DURATION_SECONDS
                await add_masochist_role_removal(voted_id_str, removal_time)

                await ctx.send(
                    f"🎉 **PAYMENT DUE!** {member.mention} has reached **{VOTE_THRESHOLD} pink votes** in 48 hours and has been assigned the **{masochist_role.name}** role for 2 days!"
                )

            except discord.Forbidden:
                await ctx.send(
                    "❌ Internal Error: Failed to assign role due to unexpected permissions issue."
                )

        else:
            needed = VOTE_THRESHOLD - vote_count
            await ctx.send(
                f"{member.display_name} now has **{vote_count}/{VOTE_THRESHOLD}** pink votes. "
                f"**{needed} more** needed to pink name this fool"
            )

    @pink_command.error
    async def pink_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Please mention a user to vote for, {ctx.author.mention}. Usage: `.pink @UserMention`"
            )
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ I could not find that user in the server. Please try again with a proper mention."
            )
            return
        else:
            raise error

    @commands.command(name="gr")
    async def give_role_command(self, ctx, member: discord.Member = None, role_alias: str = None):
        """Give a role to a user using an alias (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        if not member or not role_alias:
            available = ", ".join(f"`{alias}`" for alias in ROLE_ALIASES.keys())
            return await ctx.send(
                f"❌ Usage: `.gr @user <role_alias>`\nAvailable aliases: {available}"
            )

        role_alias = role_alias.lower()

        if role_alias not in ROLE_ALIASES:
            available = ", ".join(f"`{alias}`" for alias in ROLE_ALIASES.keys())
            return await ctx.send(
                f"❌ Unknown role alias: `{role_alias}`\nAvailable aliases: {available}"
            )

        role_id = ROLE_ALIASES[role_alias]
        role = ctx.guild.get_role(int(role_id))

        if not role:
            return await ctx.send(
                f"❌ Role not found. Please check the role ID for `{role_alias}` in the configuration."
            )

        try:
            if role in member.roles:
                await member.remove_roles(role)
                embed = discord.Embed(
                    title="🗑️ Role Removed",
                    description=f"{member.mention} no longer has the **{role.name}** role.",
                    color=discord.Color.orange(),
                )
                embed.set_footer(text=f"Removed by {ctx.author.display_name}")
                await ctx.send(embed=embed)
            else:
                await member.add_roles(role)
                embed = discord.Embed(
                    title="✅ Role Granted",
                    description=f"{member.mention} has been given the **{role.name}** role.",
                    color=discord.Color.green(),
                )
                embed.set_footer(text=f"Given by {ctx.author.display_name}")
                await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this role.")
        except Exception as e:
            logger.error(f"Error managing role: {e}")
            await ctx.send(f"❌ Error managing role: {type(e).__name__}")

    @commands.command(name="qd")
    async def quick_delete_command(self, ctx, *, message: str = None):
        """Quick delete - deletes your message after 1 second"""
        await asyncio.sleep(1)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command(name="blessing")
    async def blessing_command(self, ctx):
        """Send a Blessings message to channels (Role required)"""
        if not (
            ctx.author.guild_permissions.administrator
            or any(role.name == ROLE_ADD_QUOTE for role in ctx.author.roles)
        ):
            await ctx.send("🚫 Peasant Detected")
            return

        embed = discord.Embed(
            title="",
            description="**<a:3bluefire:1332813616696524914> Blessings to Apeiron <a:3bluefire:1332813616696524914>**",
            color=discord.Color.gold(),
        )
        main_channel = self.bot.get_channel(CHANNEL_ID)
        test_channel = self.bot.get_channel(TEST_CHANNEL_ID) if TEST_CHANNEL_ID else None
        targets = [c for c in [main_channel, test_channel] if c]
        if not targets:
            await ctx.send("⚠️ No valid channels to send the blessing.")
            return

        for ch in targets:
            await ch.send(embed=embed)
        await ctx.send("✅ Blessings sent to channels.")

    @commands.command(name="cleanse")
    async def cleanse_command(self, ctx, member: discord.Member = None):
        """[MOD] Remove all active hexes from a user. Usage: .cleanse @user"""
        
        # Permission check
        if not any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles):
            return await ctx.reply(
                "❌ You don't have permission to use this command.", 
                mention_author=False
            )
        
        # Argument validation
        if member is None:
            return await ctx.reply(
                "❌ Please mention a user to cleanse. Usage: `.cleanse @user`",
                mention_author=False
            )
        
        # Check for active effects
        try:
            effect_data = await get_active_effect(member.id)
            
            if effect_data is None:
                return await ctx.reply(
                    f"✨ {member.mention} has no active hexes.",
                    mention_author=False
                )
            
            effect_name, expiration_time = effect_data
            
            # Remove the effect
            await remove_active_effect(member.id)
            
            # Send success embed
            embed = discord.Embed(
                title="🌟 Hex Cleansed",
                description=f"Removed **{effect_name}** from {member.mention}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Cleansed by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            logger.info(f"Cleanse: {ctx.author} removed {effect_name} from {member}")
            
        except Exception as e:
            logger.error(f"Error in cleanse command: {e}", exc_info=True)
            await ctx.reply(
                "❌ An error occurred while cleansing. Check logs.",
                mention_author=False
            )

    @commands.command(name="hierarchy")
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def hierarchy_command(self, ctx, *, args: str = None):
        """Fallen angel and demon hierarchy system"""
        from config import AUTHORIZED_ROLES

        if args is None:
            if not (
                ctx.author.guild_permissions.administrator
                or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)
            ):
                return await ctx.send(
                    "🚫 Peasant Detected - Full hierarchy chart is restricted to authorized roles."
                )

            await hierarchy.send_hierarchy_chart(ctx)
            return

        args_lower = args.lower().strip()

        if args_lower.startswith("list"):
            if not (
                ctx.author.guild_permissions.administrator
                or any(role.name in AUTHORIZED_ROLES for role in ctx.author.roles)
            ):
                return await ctx.send(
                    "🚫 Peasant Detected - Hierarchy list is restricted to authorized roles."
                )

            parts = args.split()
            page = 1
            if len(parts) > 1 and parts[1].isdigit():
                page = int(parts[1])

            await hierarchy.send_entity_list(ctx, page)
            return

        if args_lower == "random":
            entity_key = hierarchy.get_random_entity()
            await hierarchy.send_entity_details(ctx, entity_key)
            return

        if args_lower.startswith("search "):
            keyword = args[7:].strip()
            if not keyword:
                return await ctx.send(
                    "❌ Please provide a search keyword. Usage: `.hierarchy search [keyword]`"
                )

            results = hierarchy.search_hierarchy(keyword)
            await hierarchy.send_search_results(ctx, results)
            return

        entity_key = args_lower.replace(" ", "_").replace("-", "_")

        if entity_key in hierarchy.HIERARCHY_DB:
            await hierarchy.send_entity_details(ctx, entity_key)
        else:
            results = hierarchy.search_hierarchy(args)
            if results:
                for key, entity in results:
                    if entity["name"].lower() == args_lower:
                        await hierarchy.send_entity_details(ctx, key)
                        return

                await hierarchy.send_search_results(ctx, results)
            else:
                await ctx.send(
                    f"❌ No entity found matching '{args}'. Try `.hierarchy search {args}` or `.hierarchy random`"
                )

    @commands.command(name="archive")
    async def archive_forum(self, ctx, which: str = None):
        """Archive forum channels and create fresh replacements (Admin only)"""

        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        valid_options = ["forum", "forum-livi", "both"]
        if which not in valid_options:
            return await ctx.send(
                "⚠️ Usage:\n"
                "`.archive forum` - Archive #forum\n"
                "`.archive forum-livi` - Archive #forum-livi\n"
                "`.archive both` - Archive both channels"
            )

        guild = ctx.guild
        channels_to_archive = []

        if which == "both":
            channels_to_archive = ["forum", "forum-livi"]
        else:
            channels_to_archive = [which]

        for channel_name in channels_to_archive:
            try:
                old_channel = get_forum_channel(guild, channel_name)

                if not old_channel:
                    await ctx.send(f"⚠️ Channel `#{channel_name}` not found. Skipping...")
                    continue

                category = old_channel.category
                position = old_channel.position

                now = datetime.now()
                archive_name = f"{channel_name}-{now.strftime('%b-%Y').lower()}"

                await old_channel.edit(name=archive_name)

                ARCHIVE_CATEGORY_ID = 1439078260402159626
                archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)

                if archive_category:
                    await old_channel.edit(
                        category=archive_category,
                        sync_permissions=True,
                    )
                    await ctx.send(
                        f"📦 Channel `#{channel_name}` archived as `#{archive_name}` and moved to archive category"
                    )

                new_channel = await guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    position=position,
                    overwrites=old_channel.overwrites,
                    topic=old_channel.topic,
                    slowmode_delay=old_channel.slowmode_delay,
                    nsfw=old_channel.nsfw,
                )

                await new_channel.send(
                    f"✨ **#{channel_name} channel created!** The old channel has been archived."
                )

                logger.info(
                    f"{channel_name} archived by {ctx.author} - Old: {old_channel.id}, New: {new_channel.id}"
                )

            except Exception as e:
                logger.error(f"Error archiving {channel_name}: {e}")
                await ctx.send(f"❌ Error archiving `#{channel_name}`: {e}")

        await ctx.send("✅ Archived")

    @commands.command(name="debug")
    @commands.has_permissions(administrator=True)
    async def toggle_debug(self, ctx, state: str = None):
        """Toggle debug mode on/off. When on, only admins can use commands."""
        DEBUG_MODE = getattr(self.bot, 'DEBUG_MODE', False)

        if state is None:
            await ctx.send(
                f"🔧 Debug mode is currently **{'ON' if DEBUG_MODE else 'OFF'}**."
            )
            return

        state = state.lower()
        if state in ["on", "true", "enable"]:
            self.bot.DEBUG_MODE = True
            await ctx.send(
                "🧰 Debug mode **enabled** — only administrators can use commands."
            )
        elif state in ["off", "false", "disable"]:
            self.bot.DEBUG_MODE = False
            await ctx.send("✅ Debug mode **disabled** — all users can use commands again.")
        else:
            await ctx.send("Usage: `.debug on` or `.debug off`")

    # Database commands
    @commands.command(name="dbcheck")
    async def db_check(self, ctx):
        """Check database status (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        exists = os.path.exists(DB_FILE)
        size = os.path.getsize(DB_FILE) if exists else 0

        try:
            async with get_db() as conn:
                async with conn.execute("SELECT COUNT(*) FROM quotes") as cursor:
                    quote_count = (await cursor.fetchone())[0]

                async with conn.execute("SELECT COUNT(*) FROM activity_hourly") as cursor:
                    activity_count = (await cursor.fetchone())[0]

                async with conn.execute("SELECT COUNT(*) FROM user_timezones") as cursor:
                    tz_count = (await cursor.fetchone())[0]

                await ctx.send(
                    f"🗄️ **Database Status**\n"
                    f"File: `{DB_FILE}`\n"
                    f"Size: {size:,} bytes\n"
                    f"Quotes: {quote_count}\n"
                    f"Activity Records: {activity_count}\n"
                    f"Timezones: {tz_count}"
                )
        except Exception as e:
            await ctx.send(f"❌ Database error: {e}")

    @commands.command(name="dbintegrity")
    async def db_integrity(self, ctx):
        """Check database integrity (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        try:
            async with get_db() as conn:
                async with conn.execute("PRAGMA integrity_check") as cursor:
                    result = (await cursor.fetchone())[0]

                if result == "ok":
                    await ctx.send("✅ Database integrity check passed!")
                else:
                    await ctx.send(f"⚠️ Database integrity issues: {result}")
        except Exception as e:
            await ctx.send(f"❌ Error checking integrity: {e}")

    @commands.command(name="testactivity")
    async def test_activity(self, ctx):
        """Test activity logging manually"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        from activity import activity_buffer, log_activity_in_memory
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        hour = now.strftime("%H")

        log_activity_in_memory(str(ctx.author.id), hour)
        log_activity_in_memory(str(ctx.author.id), hour)
        log_activity_in_memory("999999999", hour)

        total_hourly = sum(activity_buffer["hourly"].values())
        total_users = sum(activity_buffer["users"].values())

        await ctx.send(
            f"✅ Added 3 test messages to buffer\n"
            f"Buffer hourly: {dict(activity_buffer['hourly'])}\n"
            f"Buffer users: {dict(activity_buffer['users'])}\n"
            f"Total hourly count: {total_hourly}\n"
            f"Total user count: {total_users}"
        )

    @commands.command(name="showquotes")
    async def show_quotes(self, ctx):
        """Show sample quotes (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")
        quotes = await load_quotes_from_db()
        sample = quotes[-3:] if len(quotes) >= 3 else quotes
        await ctx.send(f"Loaded {len(quotes)} quotes.\nLast 3:\n" + "\n".join(sample))

    @commands.command(name="dbcheckwrite")
    async def db_check_write(self, ctx, *, quote_text: str = "test write"):
        """Test database write (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")
        try:
            async with get_db() as conn:
                await conn.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote_text,))
            await ctx.send(f'✅ Successfully wrote "{quote_text}" to {DB_FILE}')
        except Exception as e:
            logger.error(f"DB write error: {e}")
            await ctx.send(f"❌ Write failed: {e}")

    @commands.command(name="flushactivity")
    async def flush_activity_manual(self, ctx):
        """Manually flush activity to database"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        try:
            from activity import flush_activity_to_db

            await flush_activity_to_db()
            await ctx.send("✅ Activity flushed to database!")
        except Exception as e:
            logger.error(f"Error flushing: {e}")
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="fixdb")
    async def fix_db(self, ctx):
        """Reinitialize database with backup (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        if os.path.exists(DB_FILE):
            backup_path = f"{DB_FILE}.bak"
            shutil.copy2(DB_FILE, backup_path)
            await ctx.send(f"📦 Backed up old DB to {backup_path}")

        try:
            async with get_db() as conn:
                await conn.execute("DROP TABLE IF EXISTS quotes")
                await conn.execute(
                    "CREATE TABLE quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, quote TEXT UNIQUE)"
                )
            await ctx.send(f"✅ Reinitialized quotes table at {DB_FILE}")
        except Exception as e:
            logger.error(f"Error fixing DB: {e}")
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="mergequotes")
    async def merge_quotes(self, ctx):
        """Merge quotes from backup (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("🚫 Peasant Detected")

        old_db = f"{DB_FILE}.bak"
        if not os.path.exists(old_db):
            return await ctx.send("❌ No backup file found to merge.")

        try:
            import aiosqlite
            async with aiosqlite.connect(DB_FILE) as conn_new:
                async with aiosqlite.connect(old_db) as conn_old:
                    async with conn_old.execute("SELECT quote FROM quotes") as cursor_old:
                        rows = await cursor_old.fetchall()
                        count = 0
                        for (quote,) in rows:
                            try:
                                await conn_new.execute(
                                    "INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (quote,)
                                )
                                count += 1
                            except Exception:
                                pass
                        await conn_new.commit()
            await ctx.send(f"✅ Merged {count} quotes from backup into the new database.")
        except Exception as e:
            logger.error(f"Error merging: {e}")
            await ctx.send(f"❌ Error merging: {e}")
        finally:
            conn_old.close()
            conn_new.close()


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
