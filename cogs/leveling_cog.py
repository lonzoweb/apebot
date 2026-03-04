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
    update_user_xp, get_user_xp_data, get_top_levels, 
    get_level_settings, get_level_multipliers, get_reward_roles,
    sync_user_profile, calculate_level_for_xp,
    set_level_setting, sync_server_roles, sync_server_channels,
    get_cached_roles, init_db, get_cached_channels
)

logger = logging.getLogger(__name__)

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {} # user_id -> last_xp_time
        self.profile_sync_times = {} # user_id -> last_sync_time
        
        # Performance Cache
        self.cache = {
            "settings": {},
            "multipliers": {},
            "rewards": [],
            "last_refresh": 0
        }
        
        self.bot.loop.create_task(self.initialize_settings())

    async def initialize_settings(self):
        """Populate default Polaris settings and notification templates if empty."""
        settings = await get_level_settings()
        defaults = {
            "c3": "1", "c2": "50", "c1": "100", "rounding": "100",
            "xp_min": "15", "xp_max": "25", "cooldown": "60",
            # Message Settings
            "lvl_msg_enabled": "1",
            "lvl_msg_template": "Bravo [[DISPLAYNAME]], you've advanced to level [[LEVEL]] in [[SERVER]]!",
            "lvl_msg_channel": "dm",
            "lvl_msg_embed": "1",
            "lvl_msg_interval": "1",
            "lvl_msg_reward_only": "0",
            "lvl_msg_interval_stop": "0",
            # Reward Sync Settings
            "reward_sync_mode": "levelup",
            "reward_manual_sync": "0",
            "reward_sync_warning": "1",
            "reward_exclude_enabled": "0",
            "reward_exclude_roles": "",
            # Rank Card Settings
            "rank_enabled": "1",
            "rank_hide_cooldown": "0",
            "rank_hide_multipliers": "0",
            "rank_force_hidden": "0",
            "rank_relative_xp": "1",
        }
        for k, v in defaults.items():
            if k not in settings:
                await set_level_setting(k, v)
        logger.info("Initialized Leveling settings.")
        
        # Initial cache populate
        await self.refresh_cache_now()
        
        # Start background tasks
        self.bot.loop.create_task(self.role_sync_task())
        self.bot.loop.create_task(self.profile_sync_task())
        self.bot.loop.create_task(self.cache_refresh_task())

    async def refresh_cache_now(self):
        """Forces an absolute refresh of the memory cache."""
        try:
            self.cache["settings"] = await get_level_settings()
            self.cache["multipliers"] = await get_level_multipliers()
            self.cache["rewards"] = await get_reward_roles()
            self.cache["last_refresh"] = time.time()
            logger.debug("Leveling Cache Refreshed.")
        except Exception as e:
            logger.error(f"Failed to refresh leveling cache: {e}")

    async def cache_refresh_task(self):
        """Periodically refresh the settings cache to stay in sync with Dashboard."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(300) # Every 5 minutes
            await self.refresh_cache_now()

    async def role_sync_task(self):
        """Periodically sync server roles to cache for the dashboard."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    await self._sync_guild_roles(guild)
                logger.info("Synced server roles to cache.")
            except Exception as e:
                logger.error(f"Error syncing roles: {e}")
            await asyncio.sleep(3600) # Sync every hour

    async def _sync_guild_roles(self, guild):
        roles_data = []
        for role in guild.roles:
            if role.is_default(): continue
            roles_data.append((
                str(role.id), 
                role.name, 
                f"#{role.color.value:06x}" if role.color.value != 0 else "inherit", 
                role.position
            ))
        await sync_server_roles(roles_data)
        
        channels_data = []
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
                channels_data.append((
                    str(channel.id),
                    channel.name,
                    str(channel.type)
                ))
        await sync_server_channels(channels_data)

    async def profile_sync_task(self):
        """Perform a full member profile sweep on startup and every 24h."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    logger.info(f"Starting full profile sync for {guild.name}...")
                    count = 0
                    for member in guild.members:
                        if member.bot: continue
                        await sync_user_profile(
                            member.id, 
                            member.display_name, 
                            str(member.display_avatar.url)
                        )
                        count += 1
                    logger.info(f"Synced {count} member profiles for {guild.name}.")
            except Exception as e:
                logger.error(f"Error in profile sync task: {e}")
            await asyncio.sleep(86400) # Every 24 hours

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

        settings = self.cache["settings"]
        data = await get_user_xp_data(message.author.id)
        
        # XP Cooldown Check
        cooldown = data.get("last_xp_time", 0)
        cd_setting = float(settings.get("cooldown", 60))
        if cooldown and (time.time() - cooldown) < cd_setting:
            return

        # Base XP calculation
        xp_min = float(settings.get("xp_min", 15))
        xp_max = float(settings.get("xp_max", 25))
        base_xp = random.randint(int(xp_min), int(xp_max))
        
        # Multiplier check
        final_multiplier = 1.0
        multipliers = self.cache["multipliers"]
        for target_id, mult in multipliers.items():
            if message.channel.id == int(target_id):
                final_multiplier *= mult
            elif any(role.id == int(target_id) for role in message.author.roles):
                final_multiplier *= mult
                
        added_xp = int(base_xp * final_multiplier)
        new_xp = data["xp"] + added_xp
        
        # Level calculation
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        rounding = int(settings.get("rounding", 100))

        new_level = calculate_level_for_xp(new_xp, c3, c2, c1, rounding)
        
        if new_level > data["level"]:
            await self.handle_level_up(message, new_level, settings)
            
        await update_user_xp(message.author.id, new_xp, new_level, int(time.time()))
        
        # OPTIMIZED: Sync profile ONLY once every 12 hours or if missing
        last_sync = self.profile_sync_times.get(message.author.id, 0)
        if (time.time() - last_sync) > 43200: # 12 Hours
            await sync_user_profile(
                message.author.id, 
                message.author.display_name, 
                str(message.author.display_avatar.url)
            )
            self.profile_sync_times[message.author.id] = time.time()

    async def apply_reward_roles(self, member, level, settings, rewards):
        """Core logic for syncing reward roles for a member at given level. Returns True if a new role was granted."""
        earned_reward = False
        
        # Get excluded role IDs if the feature is enabled
        excluded_ids = set()
        if settings.get("reward_exclude_enabled") == "1":
            raw = settings.get("reward_exclude_roles", "")
            excluded_ids = {rid.strip() for rid in raw.split(",") if rid.strip()}
        
        new_reward = next((r for r in rewards if r["level"] == level), None)
        
        if new_reward:
            role = member.guild.get_role(int(new_reward["role_id"]))
            if role and str(role.id) not in excluded_ids:
                try:
                    if role not in member.roles:
                        await member.add_roles(role, reason=f"Level {level} Reward")
                        earned_reward = True
                    
                    # Remove old reward roles if stacking is disabled
                    if not new_reward["stack_role"]:
                        to_remove = []
                        for r in rewards:
                            if r["level"] < level:
                                old_role = member.guild.get_role(int(r["role_id"]))
                                if old_role and old_role in member.roles and str(old_role.id) not in excluded_ids:
                                    to_remove.append(old_role)
                        if to_remove:
                            await member.remove_roles(*to_remove, reason="Level Role Replacement")
                except discord.Forbidden:
                    logger.warning(f"Forbidden: Cannot manage roles for {member}")
        
        return earned_reward

    async def handle_level_up(self, message, new_level, settings):
        rewards = self.cache["rewards"]
        
        # 1. Reward Roles — obey sync mode setting
        sync_mode = settings.get("reward_sync_mode", "levelup")
        earned_reward = False
        if sync_mode in ("levelup", "always"):
            earned_reward = await self.apply_reward_roles(message.author, new_level, settings, rewards)

        # 2. Notification Logic
        if settings.get("lvl_msg_enabled") != "1":
            return

        # Filtering
        interval = int(settings.get("lvl_msg_interval", 1))
        stop_at = int(settings.get("lvl_msg_interval_stop", 0))
        reward_only = settings.get("lvl_msg_reward_only") == "1"

        should_notify = True
        if reward_only and not earned_reward:
            should_notify = False
        elif interval > 1:
            if stop_at > 0 and new_level > stop_at:
                should_notify = True # All levels after stop_at
            elif new_level % interval != 0:
                should_notify = False

        if not should_notify:
            return

        # Prepare message
        template = settings.get("lvl_msg_template", "Level up!")
        content = template.replace("[[DISPLAYNAME]]", message.author.display_name)\
                          .replace("[[LEVEL]]", str(new_level))\
                          .replace("[[SERVER]]", message.guild.name)

        target = settings.get("lvl_msg_channel", "dm")
        is_embed = settings.get("lvl_msg_embed") == "1"

        msg_kwargs = {}
        if is_embed:
            embed = discord.Embed(title="✨ Level Up!", description=content, color=discord.Color.gold())
            embed.set_thumbnail(url=message.author.display_avatar.url)
            msg_kwargs["embed"] = embed
        else:
            msg_kwargs["content"] = content

        try:
            if target == "dm":
                await message.author.send(**msg_kwargs)
            else:
                channel = message.guild.get_channel(int(target))
                if channel:
                    await channel.send(**msg_kwargs)
                else:
                    await message.channel.send(**msg_kwargs)
        except Exception:
            pass # Silently fail if DMs closed

    @app_commands.command(name="rank", description="Check your current level and XP")
    async def rank_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        settings = await get_level_settings()

        # --- Setting: rank_enabled ---
        if settings.get("rank_enabled", "1") == "0" and member == interaction.user:
            return await interaction.response.send_message("❌ Rank cards are disabled on this server.", ephemeral=True)

        is_ephemeral = settings.get("rank_force_hidden") == "1"
        hide_cooldown = settings.get("rank_hide_cooldown") == "1"
        hide_mults = settings.get("rank_hide_multipliers") == "1"
        relative_xp = settings.get("rank_relative_xp", "1") != "0"

        data = await get_user_xp_data(member.id)
        
        # Sync profile on rank check
        await sync_user_profile(member.id, member.display_name, str(member.display_avatar.url))
        
        # Formula variables
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r = int(settings.get("rounding", 100))
        
        # Ensure level is correct (Recalculate in case of 0 from import)
        current_level = calculate_level_for_xp(data["xp"], c3, c2, c1, r)
        
        # XP for current level start and next level start
        def get_xp_for_l(L):
            val = (c3 * (L**3) + c2 * (L**2) + c1 * L)
            return round(val / r) * r if r > 0 else val

        xp_current_start = get_xp_for_l(current_level)
        xp_next_start = get_xp_for_l(current_level + 1)
        
        progress_xp = data["xp"] - xp_current_start
        needed_xp = xp_next_start - xp_current_start
        remaining_xp = xp_next_start - data["xp"]
        
        percentage = min(100, max(0, (progress_xp / needed_xp) * 100)) if needed_xp > 0 else 100
        
        # Multipliers
        user_multiplier = 1.0
        active_mults = []
        multipliers = await get_level_multipliers()
        if not hide_mults:
            for target_id, mult in multipliers.items():
                matched_role = next((r for r in member.roles if r.id == int(target_id)), None)
                if matched_role:
                    user_multiplier *= mult
                    active_mults.append(f"{mult}x ({matched_role.name})")
                elif interaction.channel.id == int(target_id):
                    ch = interaction.guild.get_channel(int(target_id))
                    ch_name = f"#{ch.name}" if ch else target_id
                    user_multiplier *= mult
                    active_mults.append(f"{mult}x ({ch_name})")
        else:
            # Still need user_multiplier for accuracy, just don't surface the labels
            for target_id, mult in multipliers.items():
                if any(r.id == int(target_id) for r in member.roles):
                    user_multiplier *= mult
                elif interaction.channel.id == int(target_id):
                    user_multiplier *= mult

        # Cooldown
        last_xp = data.get("last_xp_time", 0)
        time_since = time.time() - last_xp
        cd_val = float(settings.get("cooldown", 60))
        cooldown_status = "None!" if time_since >= cd_val else f"{int(cd_val - time_since)}s"

        # Messages to go
        xp_min_setting = float(settings.get("xp_min", 15))
        xp_max_setting = float(settings.get("xp_max", 25))
        avg_xp = (xp_min_setting + xp_max_setting) / 2 * user_multiplier
        msg_min = int(remaining_xp / (xp_max_setting * user_multiplier)) if (xp_max_setting * user_multiplier) > 0 else 0
        msg_max = int(remaining_xp / (xp_min_setting * user_multiplier)) if (xp_min_setting * user_multiplier) > 0 else 0
        
        # Progress Bar — use ▓/░ at width 30 for crisp Discord rendering
        bar_len = 28
        filled = int((percentage / 100) * bar_len)
        bar = "▓" * filled + "░" * (bar_len - filled)

        cd_display = f"{int(cd_val - time_since)}s" if time_since < cd_val else "0s"
        line1_parts = [f"Lv. {current_level}", f"{int(remaining_xp):,} xp to level up"]
        if not hide_cooldown:
            line1_parts.append(f"{cd_display} cooldown")
        if active_mults and not hide_mults:
            line1_parts.append(', '.join(active_mults))

        embed = discord.Embed(
            description=(
                f"{' — '.join(line1_parts)}\n"
                f"`{bar}` **({percentage:.1f}%)**\n"
                f"{msg_min}–{msg_max} messages to go!"
            ),
            color=member.color if member.color.value else discord.Color.from_rgb(99, 102, 241)
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=is_ephemeral)

    @app_commands.command(name="rolesync", description="Sync your level reward roles")
    async def rolesync(self, interaction: discord.Interaction):
        settings = await get_level_settings()
        if settings.get("reward_manual_sync") != "1":
            return await interaction.response.send_message("❌ Manual role syncing is disabled on this server.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        data = await get_user_xp_data(member.id)

        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r_val = int(settings.get("rounding", 100))
        current_level = calculate_level_for_xp(data["xp"], c3, c2, c1, r_val)

        rewards_list = await get_reward_roles()
        member_role_ids = {str(r.id) for r in member.roles}

        synced = 0
        for reward in rewards_list:
            if reward["level"] <= current_level and str(reward["role_id"]) not in member_role_ids:
                role = member.guild.get_role(int(reward["role_id"]))
                if role:
                    try:
                        await member.add_roles(role, reason="Manual /rolesync")
                        synced += 1
                    except discord.Forbidden:
                        pass

        if synced:
            await interaction.followup.send(f"✅ Synced! Added {synced} missing reward role(s).", ephemeral=True)
        else:
            await interaction.followup.send("✅ Your roles are already up to date!", ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the top 25 users")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        top_users = await get_top_levels(25)
        
        if not top_users:
            return await interaction.response.send_message("The leaderboard is empty!")

        description = ""
        for i, (user_id, xp, level, username, avatar_url) in enumerate(top_users, 1):
            name = username or f"User {user_id}"
            
            # Medal emojis for top 3
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`#{i}`"
            description += f"{medal} **{name}** • Lvl {level} ({xp:,} XP)\n"

        embed = discord.Embed(
            title="✨ Global Leaderboard (Top 25)",
            description=description,
            color=discord.Color.blue()
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

    @app_commands.command(name="level_sync", description="Force sync all members and roles to the dashboard cache")
    @app_commands.default_permissions(administrator=True)
    async def level_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            # Sync Roles
            for guild in self.bot.guilds:
                await self._sync_guild_roles(guild)
            
            # Sync Members
            count = 0
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.bot: continue
                    await sync_user_profile(member.id, member.display_name, str(member.display_avatar.url))
                    count += 1
            
            await interaction.followup.send(f"✅ Sync complete! Cached {count} members and updated server roles.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
