# --- economy.py ---
import discord
import logging
from database import get_balance, update_balance, transfer_tokens, set_balance
from exceptions import InsufficientTokens

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

    # Directly await the async database function
    balance = await get_balance(target.id)

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

    try:
        # Directly await the async transfer function
        await transfer_tokens(sender_id, recipient_id, amount)
        # Don't reveal balance in public chat
        await ctx.send(
            f"✅ **{format_balance(amount)}** transferred from {ctx.author.mention} to {member.mention}"
        )
    except InsufficientTokens:
        await ctx.send(
            f"❌ Transaction declined. Insufficient balance."
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

    # Directly await the async update function
    await update_balance(member.id, final_amount)

    # Silent confirmation - don't reveal balance
    action = "added to" if final_amount > 0 else "removed from"
    await ctx.send(f"✅ Tokens {action} {member.mention}")


async def handle_baledit_command(ctx, member: discord.Member, new_balance: int):
    """Handles .baledit command - sets exact balance."""

    # Admin check is done in the cog before this function is called.

    if new_balance < 0:
        return await ctx.send("❌ Balance cannot be negative.")

    # Directly await the async set function
    await set_balance(member.id, new_balance)

    # Silent confirmation - don't reveal balance
    await ctx.send(f"✅ Balance updated for {member.mention}")
