import discord
from discord.ext import commands
from database import is_economy_on, set_economy_status

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

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
