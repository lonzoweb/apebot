# --- economy.py ---
import discord
import logging
from database import get_balance, update_balance, transfer_tokens

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

# Define your currency unit and symbol
CURRENCY_NAME = "Tokens"
CURRENCY_SYMBOL = "💎"

# ============================================================
# UTILITIES
# ============================================================


def format_balance(balance: int) -> str:
    """Formats the balance nicely with the symbol and commas."""
    return f"{balance:,} {CURRENCY_SYMBOL}"


# ============================================================
# ECONOMY COMMAND LOGIC
# ============================================================


async def handle_balance_command(ctx, member: discord.Member = None):
    """
    Handles the .balance command.
    Checks self balance if member is None, otherwise checks member's balance (Admin check is done in main.py).
    """
    target = member if member else ctx.author

    # We use asyncio.to_thread for database reads to prevent blocking the main loop
    balance = await ctx.bot.loop.run_in_executor(None, get_balance, target.id)

    if target == ctx.author:
        message = f"{ctx.author.mention}, your current balance is **{format_balance(balance)}**."
    else:
        message = f"**{target.display_name}**'s current balance is **{format_balance(balance)}**."

    await ctx.send(message)


async def handle_send_command(ctx, member: discord.Member, amount: int):
    """Handles the .send @user <amount> command."""

    if member.bot:
        return await ctx.send("You cannot send tokens to a bot.")
    if member.id == ctx.author.id:
        return await ctx.send("You cannot send tokens to yourself.")
    if amount <= 0:
        return await ctx.send("Amount must be positive.")

    sender_id = ctx.author.id
    recipient_id = member.id

    # Run atomic transfer in a separate thread
    success = await ctx.bot.loop.run_in_executor(
        None, transfer_tokens, sender_id, recipient_id, amount
    )

    if success:
        # Fetch new balance in the thread
        sender_new_balance = await ctx.bot.loop.run_in_executor(
            None, get_balance, sender_id
        )
        await ctx.send(
            f"✅ **{format_balance(amount)}** transferred from {ctx.author.mention} to {member.mention}. "
            f"Your new balance is {format_balance(sender_new_balance)}."
        )
    else:
        # Fetch current balance in the thread
        current_balance = await ctx.bot.loop.run_in_executor(
            None, get_balance, sender_id
        )
        await ctx.send(
            f"❌ Transaction declined. You only have {format_balance(current_balance)}."
        )


async def handle_admin_modify_command(
    ctx, member: discord.Member, amount: int, operation: str
):
    """Handles .baladd and .balremove commands."""

    # Admin check is done in main.py before this function is called.

    if amount <= 0:
        return await ctx.send("❌ Amount must be positive.")

    # Determine the final amount to be passed to update_balance
    final_amount = amount if operation == "add" else -amount

    # Get initial balance
    initial_balance = await ctx.bot.loop.run_in_executor(None, get_balance, member.id)

    # Run update in a separate thread
    await ctx.bot.loop.run_in_executor(None, update_balance, member.id, final_amount)

    # Get final balance
    final_balance = await ctx.bot.loop.run_in_executor(None, get_balance, member.id)

    action = "added to" if final_amount > 0 else "removed from"

    await ctx.send(
        f"👑 Successfully {format_balance(abs(final_amount))} {action} {member.mention}'s account. "
        f"New balance: **{format_balance(final_balance)}** (Change: {format_balance(initial_balance - final_balance)})"
    )
