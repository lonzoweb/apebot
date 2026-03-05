import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
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
    get_cached_roles, init_db, get_cached_channels,
    get_user_rank, get_rank_card_prefs, set_rank_card_prefs,
)
import rank_card as rc

logger = logging.getLogger(__name__)

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}  # user_id -> last_xp_time
        self.profile_sync_times = {}  # user_id -> last_sync_time
        self._rank_cooldowns = {}  # user_id -> last /rank card time

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

        # Pre-fetch rank card fonts in background (non-blocking)
        import threading
        threading.Thread(target=rc.prefetch_fonts, daemon=True).start()
        
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

    # ──────────────────────────────────────────────────────────────────────────
    # /rank  — unified command
    # ──────────────────────────────────────────────────────────────────────────
    async def _build_and_send_card(self, interaction: discord.Interaction, member: discord.Member, invoker_id: int, display_name: str):
        """Shared helper: gathers data, renders Pillow image, sends it."""
        settings = await get_level_settings()
        is_ephemeral = settings.get("rank_force_hidden") == "1"

        # Check if interaction already responded
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=is_ephemeral)

        data = await get_user_xp_data(member.id)
        await sync_user_profile(member.id, member.display_name, str(member.display_avatar.url))

        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r  = int(settings.get("rounding", 100))

        current_level = calculate_level_for_xp(data["xp"], c3, c2, c1, r)

        def xp_for(L):
            val = c3 * (L**3) + c2 * (L**2) + c1 * L
            return round(val / r) * r if r > 0 else val

        xp_start     = xp_for(current_level)
        xp_next      = xp_for(current_level + 1)
        progress_xp  = data["xp"] - xp_start
        needed_xp    = xp_next - xp_start
        percentage   = min(100.0, max(0.0, (progress_xp / needed_xp) * 100)) if needed_xp > 0 else 100.0

        server_rank = await get_user_rank(member.id)

        from database import get_balance
        balance = await get_balance(member.id)

        # Get prefs for the invoker (themes are personal)
        prefs = await get_rank_card_prefs(invoker_id)

        # Calculate member days
        member_days = 0
        if member.joined_at:
            delta = __import__("datetime").datetime.now(member.joined_at.tzinfo) - member.joined_at
            member_days = max(0, delta.days)

        avatar_bytes = None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as sess:
                async with sess.get(str(member.display_avatar.with_size(256).url)) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()
        except Exception:
            pass

        # Average XP for msgs_left estimate
        xp_min = float(settings.get("xp_min", 15))
        xp_max = float(settings.get("xp_max", 25))
        avg_xp = (xp_min + xp_max) / 2

        loop = asyncio.get_event_loop()
        img_buf = await loop.run_in_executor(
            None, rc.build_rank_card,
            display_name, current_level, server_rank, balance,
            data["xp"], progress_xp, needed_xp, percentage,
            avatar_bytes, prefs["font"], prefs["theme"],
            member_days, avg_xp
        )

        await interaction.followup.send(
            file=discord.File(img_buf, filename="rank.png"),
            ephemeral=is_ephemeral,
        )

    @app_commands.command(name="rank", description="View your rank card or customize appearance")
    @app_commands.describe(
        member="User to check (defaults to yourself)",
        font="Update your rank card font style",
        theme="Update your rank card colour theme",
        display="Switch between showing your Discord username or server nickname",
    )
    async def rank_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
        font: Literal["Avenger", "Disney", "Chalice", "Truckin", "StarWars", "Pokemon"] = None,
        theme: Literal["matrix", "cyberpunk", "vampire", "ghost", "obsidian", "aurora", "crimson", "void"] = None,
        display: Literal["username", "nickname"] = None,
    ):
        invoker_id = interaction.user.id
        target = member or interaction.user

        # 10-second cooldown when viewing own card (and not just updating font/theme/display)
        if target.id == invoker_id and not (font or theme or display):
            now  = time.time()
            last = self._rank_cooldowns.get(invoker_id, 0)
            if now - last < 10:
                return await interaction.response.send_message(
                    f"⏳ Slow down. Try again in **{int(10 - (now - last))}s**.", ephemeral=True
                )
            self._rank_cooldowns[invoker_id] = now

        settings = await get_level_settings()
        if settings.get("rank_enabled", "1") == "0" and target == interaction.user:
            return await interaction.response.send_message("❌ Rank cards are disabled on this server.", ephemeral=True)

        # Handle font/theme/display updates
        if font or theme or display:
            await set_rank_card_prefs(invoker_id, font=font, theme=theme, display_type=display)
            # Notify but then proceed to show the card
            update_msg = "✅ Preferences updated! Showing your updated card:"
            if not interaction.response.is_done():
                await interaction.response.send_message(update_msg, ephemeral=True)
            else:
                await interaction.followup.send(update_msg, ephemeral=True)

        # Fetch prefs for the target (we use THEIR display preference, but INVOKER'S theme if viewing own?)
        # Actually, let's use the target's preference for name, but invoker's theme for the card frame?
        # Usually, rank cards show the target's custom style.
        target_prefs = await get_rank_card_prefs(target.id)
        
        # Determine name to display based on target's preference
        if target_prefs["display_type"] == "nickname":
            display_name = target.nick or target.display_name
        else:
            display_name = target.name

        await self._build_and_send_card(interaction, target, invoker_id, display_name)



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
    @app_commands.default_permissions(administrator=True)
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
