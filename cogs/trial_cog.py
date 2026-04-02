import discord
from discord.ext import commands
import time
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import database
from config import MOD_CHANNEL_ID

logger = logging.getLogger(__name__)

TRIAL_ROLE_ID = 1444477594698514594
TRIAL_DURATION_DAYS = 4

class TrialCog(commands.Cog):
    """Trial system for monitoring new members."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trial")
    @commands.has_permissions(administrator=True)
    async def trial_command(self, ctx, member: discord.Member):
        """Place a member under trial. Gives them the TRIAL role for 4 days."""
        trial_role = ctx.guild.get_role(TRIAL_ROLE_ID)
        if not trial_role:
            return await ctx.reply(f"❌ Error: Trial role ({TRIAL_ROLE_ID}) not found.", mention_author=False)

        # Hierarchy check
        if ctx.guild.me.top_role.position <= trial_role.position:
            return await ctx.reply("❌ Error: My role must be higher than the Trial role to assign it.", mention_author=False)

        if trial_role in member.roles:
            return await ctx.reply(f"❌ {member.display_name} is already under trial.", mention_author=False)

        # Start trial (4 days)
        start_time = time.time()
        end_time = start_time + (TRIAL_DURATION_DAYS * 24 * 60 * 60)

        await database.add_trial(str(member.id), str(ctx.guild.id), start_time, end_time)
        
        try:
            await member.add_roles(trial_role, reason=f"Trial started by {ctx.author.display_name}")
            await ctx.send(f"{member.mention} granted 4 day trial")
        except discord.Forbidden:
            return await ctx.reply("❌ Permission error: Could not assign the Trial role.", mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reactions on trial decision embeds in admin log."""
        if payload.user_id == self.bot.user.id:
            return

        # Simple check for relevant emojis
        # 🎓 (Graduate), ⏳ (Extend), 🥾 (Kick)
        REACTION_MAP = {
            "🎓": "graduated",
            "⏳": "extended",
            "🥾": "kicked"
        }

        emoji_str = str(payload.emoji)
        if emoji_str not in REACTION_MAP:
            return

        # Check if the message is a trial decision message
        # We need to check the database
        async with database.get_db() as conn:
            async with conn.execute(
                "SELECT user_id, guild_id, status FROM trials WHERE message_id = ?", (str(payload.message_id),)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return

        target_user_id, guild_id, status = row
        if status != "pending":
            return # Already handled

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or not member.guild_permissions.administrator:
            return # Only admins can decide

        action = REACTION_MAP[emoji_str]
        target_member = guild.get_member(int(target_user_id))
        
        admin_log_ch = guild.get_channel(int(MOD_CHANNEL_ID))
        if not admin_log_ch:
            return

        try:
            msg = await admin_log_ch.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if action == "graduated":
            await database.update_trial_status(target_user_id, guild_id, "graduated")
            trial_role = guild.get_role(TRIAL_ROLE_ID)
            if target_member:
                if trial_role and trial_role in target_member.roles:
                    await target_member.remove_roles(trial_role, reason="Trial graduated.")
                await admin_log_ch.send(f"🎓 **Trial Result**: {target_member.mention} has **GRADUATED**! (Decision by {member.display_name})")
            else:
                await admin_log_ch.send(f"🎓 **Trial Result**: User `{target_user_id}` (not found in server) marked as **GRADUATED**. (Decision by {member.display_name})")
            
            # Update embed to show result
            embed = msg.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "🎓 Trial Graduated"
            embed.set_footer(text=f"Decision by {member.display_name}")
            await msg.edit(embed=embed)
            await msg.clear_reactions()

        elif action == "extended":
            # Extend for another 4 days
            new_end_time = time.time() + (TRIAL_DURATION_DAYS * 24 * 60 * 60)
            await database.update_trial_end_time(target_user_id, guild_id, new_end_time)
            
            if target_member:
                await admin_log_ch.send(f"⏳ **Trial Result**: {target_member.mention}'s trial has been **EXTENDED** for another {TRIAL_DURATION_DAYS} days. (Decision by {member.display_name})")
            else:
                await admin_log_ch.send(f"⏳ **Trial Result**: User `{target_user_id}` (not found in server) trial **EXTENDED**. (Decision by {member.display_name})")
            
            # Update embed to show extension
            embed = msg.embeds[0]
            embed.color = discord.Color.blue()
            embed.title = "⏳ Trial Extended"
            embed.description += f"\n\n**Update**: Extended by {member.display_name}. Notification will reappear in {TRIAL_DURATION_DAYS} days."
            embed.set_footer(text=f"Extended by {member.display_name}")
            await msg.edit(embed=embed)
            await msg.clear_reactions()

        elif action == "kicked":
            await database.update_trial_status(target_user_id, guild_id, "kicked")
            
            main_channel = discord.utils.get(guild.text_channels, name="forum") # Hardcoded for now per instructions
            
            if target_member:
                try:
                    await target_member.kick(reason=f"Trial expired/failed. Action by {member.display_name}")
                    await admin_log_ch.send(f"🥾 **Trial Result**: {target_member.display_name} has been **KICKED** (Trial Expired). (Action by {member.display_name})")
                    if main_channel:
                        await main_channel.send(f"🥾 Kicked {target_member.mention}, trial expired. They didn't make the cut.")
                except discord.Forbidden:
                    await admin_log_ch.send(f"❌ Error: Could not kick {target_member.mention} due to permissions.")
            else:
                await admin_log_ch.send(f"🥾 **Trial Result**: User `{target_user_id}` (not found) marked as **KICKED**. (Action by {member.display_name})")

            # Update embed
            embed = msg.embeds[0]
            embed.color = discord.Color.red()
            embed.title = "🥾 Trial Terminated / Kicked"
            embed.set_footer(text=f"Action by {member.display_name}")
            await msg.edit(embed=embed)
            await msg.clear_reactions()

async def setup(bot):
    await bot.add_cog(TrialCog(bot))
