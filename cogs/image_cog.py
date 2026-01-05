import discord
from discord.ext import commands
import io
import time
import asyncio
import logging
from api import pollinations_generate_image
from database import get_balance, update_balance, is_economy_on

logger = logging.getLogger(__name__)

class ImageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="img")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def img_command(self, ctx, *, prompt: str = None):
        """Generate an AI image (Cost: 50 Tokens)"""
        if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🌑 **System Notice**: The visual portal is sealed. Economy is disabled.", mention_author=False)

        if not prompt:
            return await ctx.reply("🌑 **Prompt required.** What do you wish to manifest?", mention_author=False)

        # 1. Economy Check
        user_id = ctx.author.id
        cost = 50
        
        if not ctx.author.guild_permissions.administrator:
            bal = await get_balance(user_id)
            if bal < cost:
                return await ctx.reply(f"❌ (Cost: {cost})", mention_author=False)
            
            # Deduct cost
            await update_balance(user_id, -cost)

        # 2. Status message
        status_msg = await ctx.send(f"🌑 **Generating {prompt}...**")
        
        # 3. Get Image URL & Simulated delay for "optics"
        try:
            await asyncio.sleep(2.5) # The spirits need a moment to focus
            image_url = await pollinations_generate_image(prompt)
            
            if not image_url:
                # Refund on failure
                if not ctx.author.guild_permissions.administrator:
                    await update_balance(user_id, cost)
                await status_msg.edit(content="❌ **The vision collapsed.** Try again later. (Refunded)")
                return

            # 4. Prepare Embed
            embed = discord.Embed(
                description=f"**Vision**: {prompt}",
                color=discord.Color.dark_purple()
            )
            embed.set_image(url=image_url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name} | {cost} Tokens sacrificed")
            
            # 5. Edit Original Message
            await status_msg.edit(content=f"🌑 **Completed {prompt}:**", embed=embed)

        except Exception as e:
            logger.error(f"Error in .img command: {e}", exc_info=True)
            if not ctx.author.guild_permissions.administrator:
                await update_balance(user_id, cost)
            await loading_msg.edit(content="❌ **The ritual failed.** Check the logs. (Refunded)")

async def setup(bot):
    await bot.add_cog(ImageCog(bot))
