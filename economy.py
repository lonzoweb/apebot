# --- economy.py ---
import discord
import logging
from database import (
    get_balance, update_balance, transfer_tokens, set_balance, is_economy_on,
    transfer_item
)
from exceptions import InsufficientTokens
from items import ITEM_ALIASES, ITEM_REGISTRY

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
        message = f"💰 {ctx.author.mention}, you're holding: **{format_balance(balance)}**"
    else:
        message = f"💰 **{target.display_name}** is holding: **{format_balance(balance)}**"

    await ctx.send(message)


async def handle_send_command(ctx, member: discord.Member, amount: int):
    """Handles the .send @user <amount> command."""
    from helpers import has_authorized_role
    
    if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("🌑 **System Notice**: Token flow is currently frozen by the administration.", mention_author=False)

    is_authorized = has_authorized_role(ctx.author)
    
    if member.bot:
        return await ctx.reply("❌ Bots don't need your charity.", mention_author=False)
    
    # Mods can send to themselves
    if member.id == ctx.author.id and not is_authorized:
        return await ctx.reply("❌ You can't send tokens to yourself, clown.", mention_author=False)
    
    if amount <= 0:
        return await ctx.reply("❌ Enter a real amount.", mention_author=False)

    sender_id = ctx.author.id
    recipient_id = member.id

    try:
        # Mods bypass balance check - directly add tokens if authorized
        if is_authorized:
            from database import update_balance
            await update_balance(recipient_id, amount)
            await ctx.send(
                f"✅ **[MOD]** {format_balance(amount)} granted to {member.mention}"
            )
        else:
            # Regular users must have sufficient balance
            await transfer_tokens(sender_id, recipient_id, amount)
            await ctx.send(
                f"✅ **{format_balance(amount)}** moved from {ctx.author.mention} to {member.mention}"
            )
    except InsufficientTokens:
        await ctx.reply(
            f"❌ Transaction declined. You're flat. Need **{format_balance(amount)}**.", mention_author=False
        )

async def handle_gift_command(ctx, member: discord.Member, item_query: str):
    """Handles parsing and sending an item to another user."""
    from helpers import has_authorized_role
    
    if not await is_economy_on() and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("🌑 **System Notice**: The exchange of gifts is forbidden during the blackout.", mention_author=False)

    is_authorized = has_authorized_role(ctx.author)
    
    if member.bot:
        return await ctx.reply("❌ The machine spirits have no use for physical trinkets.", mention_author=False)
    
    # Mods can gift to themselves
    if member.id == ctx.author.id and not is_authorized:
        return await ctx.reply("❌ Gifting yourself? How lonely. Seek help.", mention_author=False)

    official_name = ITEM_ALIASES.get(item_query.strip().lower())
    if not official_name:
        return await ctx.reply(f"❌ '{item_query}' isn't something you can wrap in a bow.", mention_author=False)

    # Mods can create items from thin air
    if is_authorized:
        from database import get_user_inventory, update_inventory
        recipient_inv = await get_user_inventory(member.id)
        new_qty = recipient_inv.get(official_name, 0) + 1
        await update_inventory(member.id, official_name, new_qty)
        await ctx.send(f"🎁 **[MOD]** {official_name.replace('_', ' ').title()} granted to {member.mention}!")
    else:
        # Regular users must possess the item
        success = await transfer_item(ctx.author.id, member.id, official_name)
        if success:
            await ctx.send(f"🎁 **{ctx.author.display_name}** handed a **{official_name.replace('_', ' ').title()}** to {member.mention}!")
        else:
            await ctx.reply(f"❌ You don't possess a **{official_name.replace('_', ' ').title()}** to give.", mention_author=False)


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
