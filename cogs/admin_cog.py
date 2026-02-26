import discord
from discord.ext import commands
from database import (
    is_economy_on, set_economy_status, set_yap_level, get_yap_level,
    get_top_balances, cap_all_balances, clear_user_inventory
)

class AdminCog(commands.Cog):
    """Admin-only commands for system control."""
    
    def __init__(self, bot):
        self.bot = bot
        self.cleanse_votes = {}  # {target_id: {voter_id: timestamp}}

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
    async def pink_command(self, ctx, member: discord.Member):
        """Votes to assign the Masochist role to a user. Requires 7 votes in 48h."""
        from database import update_pink_vote, get_active_pink_vote_count, add_masochist_role_removal
        from config import MASOCHIST_ROLE_ID, VOTE_THRESHOLD, ROLE_DURATION_SECONDS
        import time

        if member.id == ctx.author.id:
            return await ctx.reply("❌ You can't vote for yourself... unless you're into that?", mention_author=False)
        if member.bot:
            return await ctx.reply("❌ Bots are immune to this torture.", mention_author=False)

        masochist_role = ctx.guild.get_role(MASOCHIST_ROLE_ID)
        if not masochist_role:
            return await ctx.send(f"❌ Error: The Masochist role ({MASOCHIST_ROLE_ID}) was not found.")

        # Hierarchy Checks
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("🛑 I need `Manage Roles` permission.")
        if ctx.guild.me.top_role.position <= masochist_role.position:
            return await ctx.send("🛑 My role must be higher than the Masochist role.")

        if masochist_role in member.roles:
            return await ctx.reply(f"❌ {member.display_name} already has the role.", mention_author=False)

        await update_pink_vote(str(member.id), str(ctx.author.id))
        vote_count = await get_active_pink_vote_count(str(member.id))

        if vote_count >= VOTE_THRESHOLD:
            try:
                await member.add_roles(masochist_role, reason=f"Reached {VOTE_THRESHOLD} pink votes.")
                removal_time = time.time() + ROLE_DURATION_SECONDS
                await add_masochist_role_removal(str(member.id), removal_time)
                await ctx.send(f"🎉 **PAYMENT DUE!** {member.mention} reached **{VOTE_THRESHOLD} votes** and is now pink for 2 days")
            except discord.Forbidden:
                await ctx.send("❌ permission error while assigning role.")
        else:
            needed = VOTE_THRESHOLD - vote_count
            await ctx.send(f"{member.display_name} has **{vote_count}/{VOTE_THRESHOLD}** pink votes. **{needed} more** needed to pink name this fool")

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

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
