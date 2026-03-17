import discord
from discord.ext import commands
import io
import time
import asyncio
import logging
from api import google_generate_image
from database import get_balance, update_balance, is_economy_on, get_channel_assigns

logger = logging.getLogger(__name__)

class ImageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _report_error(self, ctx, prompt, error_msg):
        """Send detailed error report to the configured error channel."""
        try:
            config = await get_channel_assigns()
            error_channel_id = config.get("error")
            if not error_channel_id:
                return

            error_channel = self.bot.get_channel(int(error_channel_id))
            if not error_channel:
                return

            embed = discord.Embed(
                title="⚠️ Image Generation Failure",
                description=f"**User**: {ctx.author.mention} ({ctx.author.id})\n"
                            f"**Prompt**: `{prompt}`\n"
                            f"**Error**: ```{error_msg}```",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="System Error Reporting")
            await error_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send detailed error report: {e}")

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
        
        # 3. Get Image Bytes
        try:
            await asyncio.sleep(2.5) # Optics: The spirits need a moment
            image_bytes, error_msg = await google_generate_image(prompt)
            
            if not image_bytes:
                # Refund on failure
                if not ctx.author.guild_permissions.administrator:
                    await update_balance(user_id, cost)
                await status_msg.edit(content=f"❌ **Error**: {error_msg or 'Try again later.'} (Refunded)")
                return

            # 4. Prepare File & Embed
            file = discord.File(io.BytesIO(image_bytes), filename="vision.png")
            embed = discord.Embed(
                description=f"**Vision**: {prompt}",
                color=discord.Color.dark_purple()
            )
            embed.set_image(url="attachment://vision.png")
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            
            # 5. Edit Original Message with Attachment
            await status_msg.edit(content=f"🌑 **Finished {prompt}:**", embed=embed, attachments=[file])

        except Exception as e:
            err_str = str(e)
            logger.error(f"Error in .img command: {err_str}", exc_info=True)
            
            # Detailed reporting to error channel
            await self._report_error(ctx, prompt or "None", err_str)
            
            if not ctx.author.guild_permissions.administrator:
                await update_balance(user_id, cost)
            await status_msg.edit(content=f"❌ **The gen failed.** Error details sent to spirits. (Refunded)")

    @commands.Cog.listener()

async def setup(bot):
    await bot.add_cog(ImageCog(bot))
