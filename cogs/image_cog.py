import discord
from discord.ext import commands
import io
import time
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
                return await ctx.reply(f"❌ You lack the tokens to manifest this. (Cost: {cost})", mention_author=False)
            
            # Deduct cost
            await update_balance(user_id, -cost)

        # 2. Manifesting message
        loading_msg = await ctx.send("🌑 **Manifesting...** The spirits are painting your vision.")
        
        # 3. Call API
        try:
            image_bytes = await pollinations_generate_image(prompt)
            
            if not image_bytes:
                # Refund on failure
                if not ctx.author.guild_permissions.administrator:
                    await update_balance(user_id, cost)
                await loading_msg.edit(content="❌ **The vision collapsed.** Try again later. (Refunded)")
                return

            # 4. Prepare File
            file = discord.File(io.BytesIO(image_bytes), filename="manifestation.png")
            
            # 5. Send Result
            embed = discord.Embed(
                title="🔮 Manifestation Complete",
                description=f"**Vision**: {prompt}",
                color=discord.Color.dark_purple()
            )
            embed.set_image(url="attachment://manifestation.png")
            embed.set_footer(text=f"Requested by {ctx.author.display_name} | {cost} Tokens sacrificed")
            
            await loading_msg.delete()
            await ctx.send(embed=embed, file=file)

        except Exception as e:
            logger.error(f"Error in .img command: {e}", exc_info=True)
            if not ctx.author.guild_permissions.administrator:
                await update_balance(user_id, cost)
            await loading_msg.edit(content="❌ **The ritual failed.** Check the logs. (Refunded)")

async def setup(bot):
    await bot.add_cog(ImageCog(bot))
