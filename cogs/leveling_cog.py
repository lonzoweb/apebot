import discord
from discord.ext import commands
from discord import app_commands
import time
import random
import math
import logging
import json
import io
from database import (
    get_user_xp_data, update_user_xp, get_level_settings, 
    get_level_multipliers, get_reward_roles, get_top_levels,
    set_level_setting, set_reward_role, set_level_multiplier
)

logger = logging.getLogger(__name__)

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {} # user_id -> last_xp_time
        self.bot.loop.create_task(self.initialize_settings())

    async def initialize_settings(self):
        """Populate default Polaris settings if empty."""
        settings = await get_level_settings()
        if not settings:
            defaults = {
                "c3": "1",
                "c2": "50",
                "c1": "100",
                "rounding": "100",
                "xp_min": "15",
                "xp_max": "25",
                "cooldown": "60"
            }
            for k, v in defaults.items():
                await set_level_setting(k, v)
            logger.info("Initialized default Leveling settings (Polaris).")

    def calculate_xp_for_level(self, level, settings):
        """
        Polaris Cubic Formula: 
        Requirement = round((c3 * L^3 + c2 * L^2 + c1 * L) / rounding) * rounding
        """
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        rounding = int(settings.get("rounding", 100))
        
        if level <= 0: return 0
        
        val = (c3 * (level**3)) + (c2 * (level**2)) + (c1 * level)
        return round(val / rounding) * rounding

    async def get_multiplied_xp(self, message, base_xp):
        multipliers = await get_level_multipliers()
        final_multiplier = 1.0
        
        # Role multipliers
        for role in message.author.roles:
            if str(role.id) in multipliers:
                final_multiplier = max(final_multiplier, float(multipliers[str(role.id)]))
        
        # Channel multipliers
        if str(message.channel.id) in multipliers:
            final_multiplier = max(final_multiplier, float(multipliers[str(message.channel.id)]))
            
        return int(base_xp * final_multiplier)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # XP Cooldown (Default 60s)
        settings = await get_level_settings()
        cooldown = int(settings.get("cooldown", 60))
        
        now = time.time()
        user_data = await get_user_xp_data(message.author.id)
        last_xp_time = user_data["last_xp_time"]
        
        if now - last_xp_time < cooldown:
            return

        # XP Gain (Default 15-25)
        xp_min = int(settings.get("xp_min", 15))
        xp_max = int(settings.get("xp_max", 25))
        base_xp = random.randint(xp_min, xp_max)
        
        xp_gain = await self.get_multiplied_xp(message, base_xp)
        
        new_xp = user_data["xp"] + xp_gain
        current_level = user_data["level"]
        
        # Check level up
        next_level_req = self.calculate_xp_for_level(current_level + 1, settings)
        
        leveled_up = False
        while new_xp >= next_level_req:
            current_level += 1
            leveled_up = True
            next_level_req = self.calculate_xp_for_level(current_level + 1, settings)

        await update_user_xp(message.author.id, new_xp, current_level, now)

        if leveled_up:
            await self.handle_level_up(message, current_level)

    async def handle_level_up(self, message, new_level):
        # 1. Notify User
        embed = discord.Embed(
            title="✨ LEVEL UP!",
            description=f"{message.author.mention}, you've ascended to **Level {new_level}**!",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed)
        
        # 2. Reward Roles
        rewards = await get_reward_roles()
        role_id = rewards.get(new_level)
        if role_id:
            role = message.guild.get_role(int(role_id))
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role, reason=f"Level {new_level} Reward")
                except discord.Forbidden:
                    logger.warning(f"Failed to add reward role {role.name} to {message.author.name}")

    @app_commands.command(name="rank", description="Check your current level and XP")
    @app_commands.describe(member="The member to check")
    async def rank_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        data = await get_user_xp_data(target.id)
        settings = await get_level_settings()
        
        current_xp = data["xp"]
        current_level = data["level"]
        xp_next = self.calculate_xp_for_level(current_level + 1, settings)
        xp_prev = self.calculate_xp_for_level(current_level, settings)
        
        # XP in current level
        level_xp = current_xp - xp_prev
        req_xp = xp_next - xp_prev
        
        percentage = min(100, int((level_xp / req_xp) * 100)) if req_xp > 0 else 100
        
        embed = discord.Embed(title=f"Rank: {target.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Total XP", value=f"{current_xp:,}", inline=True)
        embed.add_field(name="Progress", value=f"{level_xp:,} / {req_xp:,} XP ({percentage}%)", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the highest level users")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        top_users = await get_top_levels(10)
        
        if not top_users:
            return await interaction.response.send_message("The halls are empty. No one has claimed any XP yet.")

        lines = []
        for i, (user_id, xp, level) in enumerate(top_users, 1):
            user = self.bot.get_user(int(user_id))
            name = user.name if user else f"User {user_id}"
            lines.append(f"**{i}. {name}** — Lvl {level} ({xp:,} XP)")
            
        embed = discord.Embed(
            title="🏆 GLOBAL LEADERBOARD",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    # ──────────────────────────────────────────────────────────────────────────
    # ADMIN COMMANDS
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="level_edit", description="[ADMIN] Manually adjust a member's XP or Level")
    @app_commands.describe(member="Member to edit", xp="Set exact XP", level="Set exact Level")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_edit(self, interaction: discord.Interaction, member: discord.Member, xp: int = None, level: int = None):
        if xp is None and level is None:
            return await interaction.response.send_message("Please provide either XP or Level to update.", ephemeral=True)
            
        data = await get_user_xp_data(member.id)
        new_xp = xp if xp is not None else data["xp"]
        new_level = level if level is not None else data["level"]
        
        await update_user_xp(member.id, new_xp, new_level, data["last_xp_time"])
        await interaction.response.send_message(f"✅ Updated {member.mention}: Level **{new_level}**, XP **{new_xp:,}**", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
