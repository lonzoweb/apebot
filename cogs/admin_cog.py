import discord
from discord.ext import commands
from database import is_economy_on, set_economy_status

class AdminCog(commands.Cog):
    """Admin-only commands for system control."""
    
    def __init__(self, bot):
        self.bot = bot

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
