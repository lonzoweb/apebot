"""
Reaction Battle System
Tracks reactions on messages during timed battles between two users
"""

import discord
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

# Global battle state (in-memory)
active_battle = None
battle_data = None

BATTLE_DURATION = 600  # 5 minutes in seconds

# ============================================================
# BATTLE DATA STRUCTURE
# ============================================================


class Battle:
    def __init__(self, user1, user2, channel):
        self.user1 = user1
        self.user2 = user2
        self.channel = channel
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=BATTLE_DURATION)
        self.user1_reactions = defaultdict(int)  # {emoji: count}
        self.user2_reactions = defaultdict(int)
        self.message_authors = {}  # {message_id: user_id} to track who sent what

    def is_expired(self):
        """Check if battle has expired"""
        return datetime.now() >= self.end_time

    def time_remaining(self):
        """Get remaining time in seconds"""
        remaining = (self.end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))

    def add_message(self, message_id, user_id):
        """Track a message sent during battle"""
        self.message_authors[message_id] = user_id

    def add_reaction(self, message_id, emoji, reactor_id):
        """Add a reaction to the battle count"""
        # Check if message is from one of the battlers
        if message_id not in self.message_authors:
            return False

        message_author = self.message_authors[message_id]

        # Can't react to own message
        if reactor_id == message_author:
            return False

        # Add reaction to appropriate user's count
        if message_author == self.user1.id:
            self.user1_reactions[str(emoji)] += 1
            return True
        elif message_author == self.user2.id:
            self.user2_reactions[str(emoji)] += 1
            return True

        return False

    def get_total_reactions(self, user_id):
        """Get total reaction count for a user"""
        if user_id == self.user1.id:
            return sum(self.user1_reactions.values())
        elif user_id == self.user2.id:
            return sum(self.user2_reactions.values())
        return 0

    def get_winner(self):
        """Determine winner (or tie)"""
        user1_total = self.get_total_reactions(self.user1.id)
        user2_total = self.get_total_reactions(self.user2.id)

        if user1_total > user2_total:
            return self.user1, user1_total, user2_total
        elif user2_total > user1_total:
            return self.user2, user2_total, user1_total
        else:
            return None, user1_total, user2_total  # Tie


# ============================================================
# BATTLE EVENT HANDLERS
# ============================================================


async def on_message_during_battle(message):
    """Track messages sent during active battle"""
    global active_battle, battle_data

    if not active_battle or not battle_data:
        return

    # Only track messages from the battlers
    if message.author.id in [battle_data.user1.id, battle_data.user2.id]:
        battle_data.add_message(message.id, message.author.id)


async def on_reaction_during_battle(payload):
    """Track reactions added during active battle"""
    global active_battle, battle_data

    if not active_battle or not battle_data:
        return

    # Add reaction to battle count
    battle_data.add_reaction(payload.message_id, payload.emoji, payload.user_id)


# ============================================================
# BATTLE RESULTS
# ============================================================


def format_reactions(reaction_dict, limit=10):
    """Format reaction dict as emoji count pairs"""
    if not reaction_dict:
        return "No reactions"

    # Sort by count, take top reactions
    sorted_reactions = sorted(reaction_dict.items(), key=lambda x: x[1], reverse=True)[
        :limit
    ]

    return "  ".join([f"{emoji} {count}" for emoji, count in sorted_reactions])


async def end_battle_and_announce():
    """End the battle and announce results"""
    global active_battle, battle_data

    if not active_battle or not battle_data:
        return

    winner, winner_count, loser_count = battle_data.get_winner()

    # Build results embed
    embed = discord.Embed(title="⚔️ AND THE WINNER IS", color=discord.Color.red())

    if winner:
        # Someone won
        loser = battle_data.user1 if winner == battle_data.user2 else battle_data.user2

        embed.add_field(
            name=f"🏆 {winner.display_name}",
            value=f"**{winner_count} reactions**\nRatiod Niqqa",
            inline=False,
        )

        # Winner's reactions
        winner_reactions = (
            battle_data.user1_reactions
            if winner == battle_data.user1
            else battle_data.user2_reactions
        )
        embed.add_field(
            name=f"{winner.display_name}:",
            value=format_reactions(winner_reactions),
            inline=False,
        )

        # Loser's reactions
        loser_reactions = (
            battle_data.user2_reactions
            if winner == battle_data.user1
            else battle_data.user1_reactions
        )
        embed.add_field(
            name=f"{loser.display_name}:",
            value=format_reactions(loser_reactions),
            inline=False,
        )
    else:
        # Tie
        embed.add_field(
            name="🤝 It's a Tie!",
            value=f"Both vamps earned **{winner_count} reactions**",
            inline=False,
        )

        # Both users' reactions
        embed.add_field(
            name=f"{battle_data.user1.display_name} reactions:",
            value=format_reactions(battle_data.user1_reactions),
            inline=False,
        )

        embed.add_field(
            name=f"{battle_data.user2.display_name} reactions:",
            value=format_reactions(battle_data.user2_reactions),
            inline=False,
        )

    await battle_data.channel.send(embed=embed)

    # Clear battle state
    active_battle = None
    battle_data = None


# ============================================================
# AUTO-END TIMER
# ============================================================


async def battle_timer():
    """Background task to auto-end battle after 5 minutes"""
    global active_battle, battle_data

    await asyncio.sleep(BATTLE_DURATION)

    # Check if battle is still active
    if active_battle and battle_data:
        await end_battle_and_announce()


# ============================================================
# COMMAND HANDLERS
# ============================================================


async def start_battle(ctx, user1: discord.Member, user2: discord.Member):
    """Start a new battle"""
    global active_battle, battle_data

    # Check if battle already active
    if active_battle:
        return await ctx.send(
            "⚠️ There's a battle underway! Use `.battle stop` to end it first."
        )

    # Validate users
    if user1 == user2:
        return await ctx.send("❌ A warrior cannot battle themselves!")

    if user1.bot or user2.bot:
        return await ctx.send("❌ Bots cannot participate in battles!")

    # Create battle
    battle_data = Battle(user1, user2, ctx.channel)
    active_battle = True

    # Announce battle
    embed = discord.Embed(
        title="⚔️ FIGHT",
        description=f"{user1.mention} vs {user2.mention}!\n\nReact to their messages to vote.\n⏰",
        color=discord.Color.orange(),
    )
    await ctx.send(embed=embed)

    # Start timer
    asyncio.create_task(battle_timer())


async def stop_battle(ctx):
    """Manually end the current battle"""
    global active_battle, battle_data

    if not active_battle:
        return await ctx.send("⚠️ No battle is currently active.")

    await end_battle_and_announce()
