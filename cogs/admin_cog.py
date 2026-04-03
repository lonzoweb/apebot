import discord
from discord import app_commands
from discord.ext import commands, tasks
from database import (
    is_economy_on, set_economy_status, set_yap_level, get_yap_level,
    get_top_balances, cap_all_balances, clear_user_inventory
)
import logging
from main import remove_muzzle_role

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    """Admin-only commands for system control."""
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanse_votes = {}  # {target_id: {voter_id: timestamp}}
        self._dynamic_color_commands = set()
        self.color_refresh_loop.start()

    def cog_unload(self):
        self.color_refresh_loop.cancel()

    async def sync_color_commands(self):
        """
        Dynamically registers or unregisters .{color} commands based on the database.
        """
        from database import get_color_role_configs
        configs = await get_color_role_configs()
        current_db_colors = {entry["name"].lower().strip() for entry in configs}

        # 1. Remove commands that are no longer in the DB
        to_remove = self._dynamic_color_commands - current_db_colors
        for color in to_remove:
            self.bot.remove_command(color)
            self._dynamic_color_commands.remove(color)
            logger.info(f"🎨 Removed dynamic color command: .{color}")

        # 2. Add new commands from the DB
        for color in current_db_colors:
            # Skip if it's already registered either statically or dynamically
            if self.bot.get_command(color):
                continue

            # Dynamically create and add the command
            async def _color_cmd(ctx, member: discord.Member, now: str = "", _color=color):
                await self._handle_color_vote(ctx, _color, member, now)

            cmd = commands.Command(
                _color_cmd,
                name=color,
                help=f"Votes to assign the {color} role to a user. Admins can add 'now' to bypass."
            )
            self.bot.add_command(cmd)
            self._dynamic_color_commands.add(color)
            logger.info(f"🎨 Registered new dynamic color command: .{color}")

    @tasks.loop(seconds=10)
    async def color_refresh_loop(self):
        """Checks for the manual trigger flag 'trigger_refresh_colors' set by the dashboard."""
        from database import get_setting, set_setting
        try:
            flag = await get_setting("trigger_refresh_colors", "0", use_cache=False)
            if flag == "1":
                await self.sync_color_commands()
                await set_setting("trigger_refresh_colors", "0")
                logger.info("🎨 Color role commands refreshed via dashboard trigger.")
        except Exception as e:
            logger.error(f"Error in color_refresh_loop: {e}")

    @color_refresh_loop.before_loop
    async def before_color_refresh(self):
        await self.bot.wait_until_ready()

    @commands.command(name="economy")
    @commands.has_permissions(administrator=True)
    async def economy_toggle(self, ctx, status: str = None):
        """Enable or disable the global economy (.economy on/off)"""
        if status is None:
            current = await is_economy_on()
            state = "ENABLED" if current else "DISABLED"
            return await ctx.reply(f"🌑 System report: Economy is currently **{state}**.", mention_author=False)
        
        status = status.lower()
        if status in ["on", "enable", "true"]:
            await set_economy_status(True)
            await ctx.reply("🌑 **System Update**: Global economy has been **ENABLED**.", mention_author=False)
        elif status in ["off", "disable", "false"]:
            await set_economy_status(False)
            await ctx.reply("🌑 **System Update**: Global economy has been **DISABLED**.", mention_author=False)
        else:
            await ctx.reply("❌ Invalid status. Use `on` or `off`.", mention_author=False)

    @commands.command(name="pink")
    async def pink_command(self, ctx, member: discord.Member, now: str = ""):
        """Votes to assign the pink role to a user. Admins can add 'now' to bypass."""
        await self._handle_color_vote(ctx, "pink", member, now)

    @commands.command(name="green")
    async def green_command(self, ctx, member: discord.Member, now: str = ""):
        """Votes to assign the green role to a user. Admins can add 'now' to bypass."""
        await self._handle_color_vote(ctx, "green", member, now)


    async def cog_command_error(self, ctx, error):
        """Cog-specific error handler for syntax guidance."""
        if isinstance(error, commands.MissingRequiredArgument):
            # If it's a dynamic color command (or pink/green)
            from database import get_color_role_configs
            configs = await get_color_role_configs()
            color_names = [c["name"].lower() for c in configs] + ["pink", "green"]
            
            if ctx.command.name in color_names:
                return await ctx.reply(f"❌ Incorrect syntax. Use: `.{ctx.command.name} <user> [now]`", mention_author=False)
        
        # Fallback to global handler or just ignore if not handled here
        pass

    async def _handle_color_vote(self, ctx, color_name: str, member: discord.Member, now: str = ""):
        """Generalized logic for colour role voting system."""
        from database import (
            update_color_vote, 
            get_active_color_vote_count, 
            add_color_role_expiration, 
            get_color_role_config,
            has_color_voted
        )
        import time
        import discord

        config = await get_color_role_config(color_name)
        if not config or not config["role_id"]:
            return await ctx.send(f"❌ The `.{color_name}` role system is not configured in the dashboard.")

        try:
            role_id = int(config["role_id"])
        except ValueError:
            return await ctx.send(f"❌ Invalid Role ID configured for `.{color_name}`.")
            
        threshold = config["vote_threshold"]
        duration_days = config["duration_days"]

        if member.id == ctx.author.id:
            return await ctx.reply("❌ You can't vote for yourself... unless you're into that?", mention_author=False)
        if member.bot:
            return await ctx.reply("❌ Bots are immune to this torture.", mention_author=False)

        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send(f"❌ Error: The configured role ({role_id}) was not found on this server.")

        # Hierarchy Checks
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("🛑 I need `Manage Roles` permission.")
        if ctx.guild.me.top_role.position <= role.position:
            return await ctx.send(f"🛑 My role must be higher than the target role ({role.name}).")

        if role in member.roles:
            return await ctx.reply(f"❌ {member.display_name} already has the {color_name} role.", mention_author=False)

        # Format duration string for later use
        dur_str = f"{duration_days} days" if duration_days != 1 else "1 day"
        if duration_days < 1:
            dur_str = f"{duration_days * 24:.1f} hours"

        # ADMIN INSTANT BYPASS
        if now.lower() == "now" and ctx.author.guild_permissions.administrator:
            try:
                await member.add_roles(role, reason=f"Manual Admin assignment by {ctx.author}.")
                removal_time = time.time() + (duration_days * 86400)
                await add_color_role_expiration(str(member.id), str(role_id), color_name, removal_time)
                return await ctx.send(f"⚖️ **ADMIN DECREE!** {member.mention} has been manually assigned the {color_name} role for {dur_str}.")
            except discord.Forbidden:
                return await ctx.send("❌ Permission error while assigning role.")

        # Duplicate vote check (48h window)
        already_voted = await has_color_voted(color_name, str(member.id), str(ctx.author.id))
        if already_voted:
            return await ctx.reply(f"❌ You already voted to {color_name} {member.display_name}! Your vote fades after 48 hours.", mention_author=False)

        await update_color_vote(color_name, str(member.id), str(ctx.author.id))
        vote_count = await get_active_color_vote_count(color_name, str(member.id))

        if vote_count >= threshold:
            try:
                await member.add_roles(role, reason=f"Reached {threshold} {color_name} votes.")
                removal_time = time.time() + (duration_days * 86400)
                await add_color_role_expiration(str(member.id), str(role_id), color_name, removal_time)
                await ctx.send(f"🎉 **PAYMENT DUE!** {member.mention} reached **{threshold} votes** and is now {color_name} for {dur_str}!")
            except discord.Forbidden:
                await ctx.send("❌ Permission error while assigning role.")
        else:
            needed = threshold - vote_count
            await ctx.send(f"{member.display_name} has **{vote_count}/{threshold}** {color_name} votes. **{needed} more** needed to {color_name} name this fool")

    @commands.command(name="cleanse")
    async def cleanse_command(self, ctx, member: discord.Member):
        """Remove all active effects from a user. Admins can cleanse instantly, others need 4 votes."""
        from database import get_all_active_effects, remove_active_effect
        import time
        
        if member.bot:
            return await ctx.reply("❌ Bots don't have active effects.", mention_author=False)
        
        # Check if target has any active effects
        effects = await get_all_active_effects(member.id)
        if not effects:
            return await ctx.reply(f"✨ {member.display_name} has no active effects to cleanse.", mention_author=False)
        
        # Admin instant cleanse
        if ctx.author.guild_permissions.administrator:
            await remove_active_effect(member.id)
            await remove_muzzle_role(member)
            effect_names = ", ".join([e[0] for e in effects])
            return await ctx.send(f"✨ **CLEANSED!** {member.mention} has been purified. Removed: {effect_names}")
        
        # Democratic voting system for non-admins
        target_id = member.id
        voter_id = ctx.author.id
        
        # Can't vote for yourself
        if voter_id == target_id:
            return await ctx.reply("❌ You can't vote to cleanse yourself.", mention_author=False)
        
        # Initialize vote tracking for this target
        if target_id not in self.cleanse_votes:
            self.cleanse_votes[target_id] = {}
        
        # Clean up old votes (older than 1 hour)
        current_time = time.time()
        self.cleanse_votes[target_id] = {
            vid: timestamp for vid, timestamp in self.cleanse_votes[target_id].items()
            if current_time - timestamp < 3600
        }
        
        # Check if user already voted
        if voter_id in self.cleanse_votes[target_id]:
            return await ctx.reply("❌ You've already voted to cleanse this user.", mention_author=False)
        
        # Add this vote
        self.cleanse_votes[target_id][voter_id] = current_time
        vote_count = len(self.cleanse_votes[target_id])
        
        # Check if we have enough votes
        if vote_count >= 4:
            await remove_active_effect(member.id)
            await remove_muzzle_role(member)
            effect_names = ", ".join([e[0] for e in effects])
            self.cleanse_votes[target_id] = {}  # Clear votes
            return await ctx.send(f"✨ **DEMOCRATIC CLEANSE!** {member.mention} reached **4 votes** and has been purified. Removed: {effect_names}")
        else:
            needed = 4 - vote_count
            return await ctx.send(f"🗳️ {member.display_name} has **{vote_count}/4** cleanse votes. **{needed} more** needed to purify.")

    @commands.command(name="gr")
    @commands.has_permissions(administrator=True)
    async def give_role_command(self, ctx, member: discord.Member, role_alias: str):
        """Give/Remove a role via alias (Admin only). Aliases: niggapass, trial, masochist, hoe, vip"""
        from config import ROLE_ALIASES
        
        alias = role_alias.lower()
        if alias not in ROLE_ALIASES:
            available = ", ".join(f"`{a}`" for a in ROLE_ALIASES.keys())
            return await ctx.send(f"❌ Unknown alias. Available: {available}")

        role_id = ROLE_ALIASES[alias]
        role = ctx.guild.get_role(role_id)
        
        if not role:
            return await ctx.send(f"❌ Role ID `{role_id}` not found on this server.")

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await ctx.send(f"🗑️ **{member.display_name}** no longer has the **{role.name}** role.")
            else:
                await member.add_roles(role)
                await ctx.send(f"✅ **{member.display_name}** has been given the **{role.name}** role.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this role.")

    @commands.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_system_setting(self, ctx, setting_name: str = None, value: str = None):
        """Set a system level setting (e.g., .set yap low/high)"""
        if not setting_name or not value:
            return await ctx.reply("❌ Usage: `.set <setting> <value>`. Example: `.set yap low`", mention_author=False)

        setting_name = setting_name.lower()
        value = value.lower()

        await ctx.reply(f"❌ Unknown setting: `{setting_name}`.", mention_author=False)

    @commands.command(name="top20")
    @commands.has_permissions(administrator=True)
    async def top20_command(self, ctx):
        """[ADMIN] Show the top 20 users by balance."""
        top_users = await get_top_balances(20)
        if not top_users:
            return await ctx.send("🌑 The treasury is currently empty.")

        embed = discord.Embed(
            title="💎 TOP 20 TREASURY",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        
        lines = []
        for i, (uid, bal) in enumerate(top_users, 1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User#{uid[:5]}"
            lines.append(f"**{i}.** {name}: `{bal:,} 💎`")
        
        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @commands.command(name="max")
    @commands.has_permissions(administrator=True)
    async def max_balance_command(self, ctx, amount: int):
        """[ADMIN] Cap all user balances to a specific amount. Usage: .max <amount>"""
        if amount < 0:
            return await ctx.send("❌ Amount must be positive.")

        await ctx.send(f"🚨 **WARNING**: This will cap ALL balances over `{amount:,}` down to `{amount:,}`. Type `CONFIRM CAP` to proceed.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM CAP"

        try:
            import asyncio
            await self.bot.wait_for("message", check=check, timeout=30.0)
            await cap_all_balances(amount)
            await ctx.send(f"⚖️ **BALANCES CAPPED.** All users over `{amount:,} 💎` have been reset to the ceiling.")
        except asyncio.TimeoutError:
            await ctx.send("⌛ Cap cancelled.")

    @commands.command(name="clearinv")
    @commands.has_permissions(administrator=True)
    async def clearinv_command(self, ctx, member: discord.Member):
        """[ADMIN] Wipe a user's entire inventory. Usage: .clearinv @user"""
        await ctx.send(f"🚨 **WARNING**: This will wipe ALL items from {member.mention}'s inventory. Type `CONFIRM CLEAR` to proceed.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM CLEAR"

        try:
            import asyncio
            await self.bot.wait_for("message", check=check, timeout=30.0)
            await clear_user_inventory(member.id)
            await ctx.send(f"🗑️ **INVENTORY WIPED.** {member.mention} is now empty-handed.")
        except asyncio.TimeoutError:
            await ctx.send("⌛ Clear cancelled.")

    @commands.command(name="help")
    @commands.has_permissions(administrator=True)
    async def admin_help_command(self, ctx):
        """[ADMIN] Displays channel-specific command guide."""
        embed = discord.Embed(
            title="🗺️ APEIRON COMMAND MAP",
            description="Guide for public command channel affinity.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏛️ #forum",
            value="`.beg` / `.daily` / `.bal` / `.send` / `.key` / `.tc` / `.gem` / `.moon` / `.w` / `.time` / `.8ball` / `.location` / `.roulette` ",
            inline=False
        )
        
        embed.add_field(
            name="🎰 #forum-livi (Economy & Games)",
            value="`.buy` / `.shop` / `.inventory` / `.bt` / `.dice` / `.pull` / `.fade` / `.torture` / `.use` / `.silencer` / `.pink` / `.cleanse` / `.rev` / `.lp` / `.crypto` / `.gifs` / `.flip` / `.roll` / `.rev` ",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Admin Only (Anywhere)",
            value="`.top20` / `.max` / `.clearinv` / `.clean` / `.economy` / `.baladd` / `.balremove` / `.baledit` / `.reset_economy` / `.backup_economy` / `.invremove` / `.gr` / `.set` / `.help` / `.stats` ",
            inline=False
        )
        
        embed.set_footer(text="Administrators are exempt from channel locks.")
        await ctx.send(embed=embed)

    @commands.command(name="clean")
    @commands.has_permissions(administrator=True)
    async def clean_bot_messages(self, ctx, limit: int = 50):
        """[ADMIN] Deletes the last N bot messages and the messages that prompted them."""
        if limit <= 0:
            return await ctx.reply("❌ Limit must be positive.", mention_author=False)
        if limit > 100:
            limit = 100 # Safety cap

        # Status message
        status_msg = await ctx.send(f"🧹 **Cleaning {limit} interactions from chat...** requested by **{ctx.author.display_name}**")

        await ctx.message.delete() # Delete the .clean command itself first

        to_delete = []
        bot_found = 0
        
        # We search through a larger window to find the requested number of bot messages
        async for msg in ctx.channel.history(limit=limit * 4):
            # Don't delete the status message we just sent
            if msg.id == status_msg.id:
                continue
                
            if bot_found >= limit:
                break
            
            if msg.author.id == self.bot.user.id:
                to_delete.append(msg)
                bot_found += 1
                
                # Look for the "prompt" message
                if msg.reference and msg.reference.message_id:
                    try:
                        ref_msg = await ctx.channel.fetch_message(msg.reference.message_id)
                        if ref_msg and ref_msg not in to_delete:
                            to_delete.append(ref_msg)
                    except:
                        pass
                else:
                    try:
                        async for prev_msg in ctx.channel.history(limit=1, before=msg):
                            if prev_msg.author.id != self.bot.user.id and prev_msg not in to_delete:
                                to_delete.append(prev_msg)
                    except:
                        pass

        if to_delete:
            unique_to_delete = list(set(to_delete))
            
            # Divide into chunks of 100 for bulk_delete
            for i in range(0, len(unique_to_delete), 100):
                chunk = unique_to_delete[i:i + 100]
                await ctx.channel.delete_messages(chunk)
            
            await status_msg.edit(content=f"✅ **Successfully cleaned {bot_found} interactions from chat.** requested by **{ctx.author.display_name}**")
        else:
            await status_msg.edit(content=f"🌑 **No bot messages found to prune.** requested by **{ctx.author.display_name}**")


    @app_commands.command(name="purge", description="[ADMIN] Modern cleanup for bot messages and prompts")
    @app_commands.describe(limit="Number of bot interactions to remove (max 50)")
    @app_commands.default_permissions(administrator=True)
    async def slash_purge(self, interaction: discord.Interaction, limit: int = 15):
        limit = max(1, min(limit, 50))
        
        # Defer because fetching history can take time
        await interaction.response.defer(ephemeral=True)

        to_delete = []
        bot_found = 0
        
        async for msg in interaction.channel.history(limit=limit * 4):
            if bot_found >= limit:
                break
            
            if msg.author.id == self.bot.user.id:
                to_delete.append(msg)
                bot_found += 1
                
                # Check for prompt
                if msg.reference and msg.reference.message_id:
                    try:
                        ref_msg = await interaction.channel.fetch_message(msg.reference.message_id)
                        if ref_msg and ref_msg not in to_delete:
                            to_delete.append(ref_msg)
                    except:
                        pass
                else:
                    try:
                        async for prev_msg in interaction.channel.history(limit=1, before=msg):
                            if prev_msg.author.id != self.bot.user.id and prev_msg not in to_delete:
                                to_delete.append(prev_msg)
                    except:
                        pass

        if to_delete:
            unique_to_delete = list(set(to_delete))
            # Delete in chunks
            for i in range(0, len(unique_to_delete), 100):
                chunk = unique_to_delete[i:i + 100]
                await interaction.channel.delete_messages(chunk)
            
            await interaction.followup.send(f"✅ Successfully purged **{bot_found}** interactions.")
        else:
            await interaction.followup.send("🌑 No recent bot messages found to purge.")


    @commands.command(name="num")
    @commands.has_permissions(administrator=True)
    async def numerology_today(self, ctx):
        """[ADMIN] Post today's numerology reading embed."""
        import numerology as num_engine
        import database
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
        embed = await num_engine.get_embed(today, database, label="Daily Numerology Reading 🌅")
        await ctx.send(embed=embed)

    @commands.command(name="num2")
    @commands.has_permissions(administrator=True)
    async def numerology_tomorrow(self, ctx):
        """[ADMIN] Post tomorrow's numerology reading embed (preview)."""
        import numerology as num_engine
        import database
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        tomorrow = datetime.now(ZoneInfo("America/Los_Angeles")).date() + timedelta(days=1)
        embed = await num_engine.get_embed(tomorrow, database, label="Tomorrow's Numerology Preview 🌙")
        await ctx.send(embed=embed)


async def setup(bot):
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    await cog.sync_color_commands()
