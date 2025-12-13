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

# pink

# --- database.py ---
# ... (existing setup_db function)


# --- NEW: Pink Vote Table Creation ---
def create_pink_tables():
    conn = get_db_connection()
    c = conn.cursor()

    # Stores each individual vote (Lazy Expiration by timestamp)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pink_votes (
            voted_id TEXT NOT NULL,
            voter_id TEXT NOT NULL,
            timestamp REAL NOT NULL, 
            PRIMARY KEY (voted_id, voter_id)
        )
    """
    )

    # Stores users who currently have the role and when it needs to be removed
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS masochist_roles (
            user_id TEXT PRIMARY KEY,
            removal_time REAL NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()


# IMPORTANT: Call this new function in your main setup_db function!
# def setup_db():
#     create_balance_table()
#     create_pink_tables() # <--- MAKE SURE THIS IS ADDED!
#     ...

# --- NEW: Pink Vote Management Functions ---


def update_pink_vote(voted_id: str, voter_id: str):
    """Inserts a new vote, updating the timestamp if the vote already exists."""
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()

    # SQLite UPSERT (INSERT OR REPLACE)
    c.execute(
        """
        INSERT OR REPLACE INTO pink_votes (voted_id, voter_id, timestamp) 
        VALUES (?, ?, ?)
    """,
        (voted_id, voter_id, now),
    )

    conn.commit()
    conn.close()


def get_active_pink_vote_count(voted_id: str) -> int:
    """Counts votes cast within the last 48 hours (LIGHTWEIGHT strategy)."""
    conn = get_db_connection()
    c = conn.cursor()

    # 48 hours in seconds = 48 * 3600 = 172800
    expiration_time = time.time() - 172800

    c.execute(
        """
        SELECT COUNT(voter_id) FROM pink_votes 
        WHERE voted_id = ? AND timestamp > ?
    """,
        (voted_id, expiration_time),
    )

    count = c.fetchone()[0]
    conn.close()
    return count


def add_masochist_role_removal(user_id: str, removal_time: float):
    """Adds or updates a user for scheduled role removal."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO masochist_roles (user_id, removal_time)
        VALUES (?, ?)
    """,
        (user_id, removal_time),
    )
    conn.commit()
    conn.close()


def get_pending_role_removals() -> list:
    """Retrieves all users whose role removal time is past (for cleanup loop)."""
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()

    # Select all users whose removal time has passed
    c.execute("SELECT user_id FROM masochist_roles WHERE removal_time <= ?", (now,))

    users_to_remove = [row[0] for row in c.fetchall()]
    conn.close()
    return users_to_remove


def remove_masochist_role_record(user_id: str):
    """Deletes the record after role removal is successful."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM masochist_roles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


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
