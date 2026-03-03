"""
Tarot Cog - Tarot card reading system
Commands: tc (tarot card)
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import time
import random
from datetime import datetime
from database import get_guild_tarot_deck, set_guild_tarot_deck, get_balance, update_balance
import tarot
import rws
import manara
import economy

logger = logging.getLogger(__name__)

# Usage tracking for cooldown/reinforcement
user_usage = {}


class TarotCog(commands.Cog):
    tarot_group = app_commands.Group(name="tarot", description="Tarot card reading system")

    def __init__(self, bot):
        self.bot = bot

    async def _handle_draw(self, target: discord.abc.Messageable, author: discord.Member, guild: discord.Guild):
        """Unified logic for prefix and slash draws."""
        deck_setting = await get_guild_tarot_deck(guild.id)
        deck_name_clean = str(deck_setting).lower().strip() if deck_setting else "thoth"

        if deck_name_clean == "rws":
            deck_module = rws
        elif deck_name_clean == "manara":
            deck_module = manara
        else:
            deck_module = tarot

        async def execute_draw():
            card_key = deck_module.draw_card()
            await deck_module.send_tarot_card(target, card_key=card_key)

        user_id = author.id
        now = time.time()
        today = datetime.utcnow().date()

        if author.guild_permissions.administrator:
            await execute_draw()
            return

        balance = await get_balance(user_id)
        if balance < 1:
            msg = "❌ The spirits demand tribute. You're flat. (Need 1 💎)"
            if isinstance(target, discord.Interaction):
                await target.response.send_message(msg, ephemeral=True)
            else:
                await target.reply(msg, mention_author=False)
            return

        await update_balance(user_id, -1)

        if user_id not in user_usage or user_usage[user_id]["day"] != today:
            user_usage[user_id] = {
                "day": today,
                "count": 0,
                "last_used": 0,
                "next_cooldown": None,
            }

        user_data = user_usage[user_id]

        if user_data["count"] < 2:
            user_data["count"] += 1
            await execute_draw()
            return

        if user_data["next_cooldown"] is None:
            user_data["next_cooldown"] = random.triangular(16, 60, 33)

        cooldown = user_data["next_cooldown"]
        time_since_last = now - user_data["last_used"]

        if time_since_last < cooldown:
            messages = [
                "Rest...", "Patience...", "The abyss awaits...",
                "You will wait...", "Not on my watch...", "The void beckons...",
            ]
            msg = random.choice(messages)
            if isinstance(target, discord.Interaction):
                await target.response.send_message(msg, ephemeral=True)
            else:
                await target.send(msg)
            return

        user_data["last_used"] = now
        user_data["count"] += 1
        user_data["next_cooldown"] = None

        await execute_draw()

    @commands.command(name="tc")
    async def tarot_card(self, ctx, action: str = None, deck_name: str = None):
        """Tarot card command (.tc for draw, .tc set <deck> for config)"""
        if action and action.lower() == "set":
            if not ctx.author.guild_permissions.administrator:
                return await ctx.reply("🚫 Peasant Detected. Begone!", mention_author=False)

            if not deck_name:
                return await ctx.reply("❌ Specify its name: `thoth`, `rws`, or `manara`.", mention_author=False)

            deck_name = deck_name.lower()
            valid_decks = {
                "thoth": "thoth", "aleister": "thoth",
                "rws": "rws", "rider": "rws", "waite": "rws",
                "manara": "manara", "milo": "manara", "erotic": "manara"
            }
            
            final_deck = valid_decks.get(deck_name)
            if not final_deck:
                return await ctx.reply(f"❌ Unknown deck `{deck_name}`. The spirits only know `thoth`, `rws` or `manara`.", mention_author=False)

            await set_guild_tarot_deck(ctx.guild.id, final_deck)
            await ctx.send(f"🌑 The deck has been swapped to **{final_deck.upper()}**. The cards never lie.")
            return

        await self._handle_draw(ctx, ctx.author, ctx.guild)

    @tarot_group.command(name="draw", description="Draw a random tarot card from the current deck")
    async def slash_draw(self, interaction: discord.Interaction):
        await self._handle_draw(interaction, interaction.user, interaction.guild)

    @tarot_group.command(name="config", description="[ADMIN] Set the default tarot deck for the server")
    @app_commands.describe(deck="The card deck to use")
    @app_commands.choices(deck=[
        app_commands.Choice(name="Thoth (Aleister Crowley)", value="thoth"),
        app_commands.Choice(name="Rider-Waite-Smith (Classic)", value="rws"),
        app_commands.Choice(name="Manara (Erotic)", value="manara")
    ])
    @app_commands.default_permissions(administrator=True)
    async def slash_config(self, interaction: discord.Interaction, deck: app_commands.Choice[str]):
        await set_guild_tarot_deck(interaction.guild_id, deck.value)
        await interaction.response.send_message(f"🌑 The deck has been swapped to **{deck.value.upper()}**. The cards never lie.")


async def setup(bot):
    await bot.add_cog(TarotCog(bot))
