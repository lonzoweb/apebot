import discord
from discord.ext import commands
from zoneinfo import ZoneInfo
from datetime import datetime
import logging

# Import the core logic module
import activity as activity_tracker

# Import database/helper functions needed for on_message handling
# NOTE: Ensure these are defined in your imported modules (e.g., database.py, helpers.py, battle.py)
from database import increment_gif_count  # Example: assuming this is from database.py
from helpers import extract_gif_url  # Example: assuming this is from helpers.py
import battle  # Assuming battle module has on_message_during_battle

logger = logging.getLogger(__name__)

# Define the timezone for logging and display consistency (LA Time as per your previous command)
TIMEZONE = ZoneInfo("America/Los_Angeles")
TIMEZONE_NAME = "LA"


class ActivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure activity tables are created when the bot starts
        # NOTE: This call is now redundant if you run tracker.init_activity_tables()
        # in main.py's on_ready, but it's safe to keep here too, or just call it in setup(bot) below.
        pass

    # ============================================================
    # EVENT LISTENER: LOGS ACTIVITY & HANDLES MESSAGE EVENTS
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle all message events, logging activity and tracking GIFs/battles."""

        # 1. Ignore bots (crucial to prevent loops and unnecessary logging)
        if message.author.bot:
            # We don't call bot.process_commands here; the one in main.py will handle it
            # after all Cog listeners finish.
            return

        # --- Activity Logging ---
        # Log to in-memory buffer
        now_local = datetime.now(TIMEZONE)
        hour = now_local.strftime("%H")  # Just the hour (00-23)
        activity_tracker.log_activity_in_memory(str(message.author.id), hour)

        # --- GIF Tracking ---
        # This was moved from your old raw on_message
        gif_url = extract_gif_url(message)
        if gif_url:
            try:
                # Assuming increment_gif_count is imported from database.py
                await increment_gif_count(gif_url, message.author.id)
            except Exception as e:
                logger.error(f"Error tracking GIF: {e}")

        # --- Battle Tracking ---
        # This was also moved from your old raw on_message
        await battle.on_message_during_battle(message)

        # NOTE: We DO NOT call bot.process_commands(message) here.
        # It must be called once at the end of the raw @bot.event on_message
        # in your main.py file to ensure commands run after all listeners.

    # ============================================================
    # COMMAND: DISPLAYS ACTIVITY STATS
    # ============================================================

    @commands.command(name="activity")
    async def activity_command(self, ctx):
        """View server activity statistics (Admin only)"""

        # 1. Permission Check
        if not ctx.author.guild_permissions.administrator:
            # The custom "Peasant Detected" message is back!
            return await ctx.send("🚫 Peasant Detected")

        try:
            # 2. Get stats
            total_msgs = await activity_tracker.get_total_messages()
            top_hours_raw = await activity_tracker.get_most_active_hours(limit=5)
            top_users_raw = await activity_tracker.get_most_active_users(limit=10)

            if not total_msgs:
                return await ctx.send("📊 No activity data yet.")

            # 3. Format Top Hours (12-hour time)
            hours_text = ""
            for hour_str, count in top_hours_raw:
                hour_int = int(hour_str)
                hour_12 = hour_int % 12 or 12
                am_pm = "AM" if hour_int < 12 else "PM"
                # Use code formatting for time and bolding for count
                hours_text += f"`{hour_12}:00 {am_pm}` - **{count}** messages\n"

            # 4. Format Top Users
            users_text = ""
            medals = ["🥇", "🥈", "🥉"]

            for i, (user_id, count) in enumerate(top_users_raw):
                medal = medals[i] if i < 3 else f"{i+1}."

                # Fetch user asynchronously (more reliable than bot.get_user)
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.display_name
                except:
                    # Fallback for users who have left or are unidentifiable
                    username = f"User#{user_id[:4]}"

                users_text += f"{medal} **{username}** - **{count}** messages\n"

            # 5. Create Embed
            embed = discord.Embed(
                title="📊 Activity Statistics",
                description=f"**Total Messages Tracked:** {total_msgs:,}",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name=f"⏰ Most Active Hours ({TIMEZONE_NAME} Time)",
                value=hours_text or "No data",
                inline=True,
            )

            embed.add_field(
                name="👥 Most Active Users", value=users_text or "No data", inline=True
            )
            embed.set_footer(
                text="Data is batched and updated every 5 minutes by a background task."
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in activity command: {e}", exc_info=True)
            await ctx.send(
                f"❌ An unexpected error occurred while fetching activity stats."
            )


async def setup(bot):
    """The function Discord.py calls to load the cog."""

    # Ensure activity tables are initialized early
    await activity_tracker.init_activity_tables()

    # Add the cog to the bot
    await bot.add_cog(ActivityCog(bot))
