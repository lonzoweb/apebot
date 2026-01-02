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

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
