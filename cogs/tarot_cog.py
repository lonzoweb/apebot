"""
Tarot Cog - Tarot card reading system
Commands: tc (tarot card)
"""

import discord
from discord.ext import commands
import logging
import time
import random
from datetime import datetime
from database import get_guild_tarot_deck, set_guild_tarot_deck, get_balance, update_balance
import tarot
import rws
import economy

logger = logging.getLogger(__name__)

# Usage tracking for cooldown/reinforcement
user_usage = {}


class TarotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tc")
    async def tarot_card(self, ctx, action: str = None, deck_name: str = None):
        """Tarot card command

        Usage:
        .tc                    - Draw a random card from current deck
        .tc set <deck_name>    - Set the deck (admin only)
        """

        if action and action.lower() == "set":
            if not ctx.author.guild_permissions.administrator:
                return await ctx.send("🚫 Peasant Detected")

            if not deck_name:
                return await ctx.send("❌ Please specify a deck name: `thoth` or `rws`")

            deck_name = deck_name.lower()

            if deck_name not in ["thoth", "rws"]:
                return await ctx.send(
                    f"❌ Unknown deck `{deck_name}`\nAvailable decks: `thoth`, `rws`"
                )

            await set_guild_tarot_deck(ctx.guild.id, deck_name)

            deck_full_name = (
                "Aleister Crowley Thoth Tarot"
                if deck_name == "thoth"
                else "Rider-Waite-Smith Tarot"
            )
            await ctx.send(f"✅ Deck set to **{deck_full_name}**")
            return

        # Draw Card Logic
        deck_setting = await get_guild_tarot_deck(ctx.guild.id)
        deck_name_clean = str(deck_setting).lower().strip() if deck_setting else "thoth"

        if deck_name_clean == "rws":
            deck_module = rws
        else:
            deck_module = tarot

        async def execute_draw():
            card_key = deck_module.draw_card()
            await deck_module.send_tarot_card(ctx, card_key=card_key)

        user_id = ctx.author.id
        now = time.time()
        today = datetime.utcnow().date()

        if ctx.author.guild_permissions.administrator:
            await execute_draw()
            return

        balance = await get_balance(user_id)
        if balance < 1:
            return await ctx.send(f"❌ Insufficient balance. You need {economy.format_balance(1)} to draw a card.")

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
                "Rest...",
                "Patience...",
                "The abyss awaits...",
                "You will wait...",
                "Not on my watch...",
                "The void beckons...",
            ]
            await ctx.send(random.choice(messages))
            return

        user_data["last_used"] = now
        user_data["count"] += 1
        user_data["next_cooldown"] = None

        await execute_draw()


async def setup(bot):
    await bot.add_cog(TarotCog(bot))
