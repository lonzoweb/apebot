"""
Twitter/X Cog - Fetch posts from X (Twitter) accounts
Commands:
  .x <username> [count]   — fetch N posts (30 tokens/post, admins free)
  .x <username> follow    — queue a follow request (any user); admin-only if already following
  .x follows              — admin: view & action pending follow requests
"""

import os
import json
import logging
import time
import discord
from discord.ext import commands
from datetime import timezone, datetime

import economy
from database import (
    get_balance, update_balance,
    add_follow_request, get_pending_follow_requests,
    get_follow_request, update_follow_request_status,
    has_pending_follow_request,
)
from config import TWITTER_COOKIES_FILE

logger = logging.getLogger(__name__)

TOKENS_PER_POST = 30
MAX_POSTS = 5


# ─────────────────────────────────────────────────────────────
# APPROVAL QUEUE UI  (button view per request)
# ─────────────────────────────────────────────────────────────

class FollowApprovalView(discord.ui.View):
    """Approve / Deny buttons for a single follow request."""

    def __init__(self, cog: "TwitterCog", request_id: int, username: str, requester_id: int):
        super().__init__(timeout=None)  # Persistent — survives restarts
        self.cog = cog
        self.request_id = request_id
        self.username = username
        self.requester_id = requester_id

    async def _resolve(self, interaction: discord.Interaction, approved: bool):
        """Shared handler for approve / deny."""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "🚫 Admins only.", ephemeral=True
            )

        status = "approved" if approved else "denied"
        await update_follow_request_status(self.request_id, status)

        # Disable buttons on the message
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        requester = interaction.guild.get_member(self.requester_id) or \
                    await interaction.guild.fetch_member(self.requester_id)
        username = self.username

        if approved:
            # Actually follow on X
            try:
                client = await self.cog._get_client()
                user = await client.get_user_by_screen_name(username)
                await user.follow()
                is_private = getattr(user, "protected", False)
                note = " (follow request sent — account is private)" if is_private else ""
                await interaction.response.send_message(
                    f"✅ Followed `@{username}`{note}.", ephemeral=False
                )
            except Exception as e:
                logger.error(f"Follow error for @{username}: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"⚠️ Approved in DB but X follow failed: `{e}`", ephemeral=False
                )

            # DM the requester
            try:
                if requester:
                    await requester.send(
                        f"✅ Your follow request for `@{username}` on X was **approved**."
                    )
            except Exception:
                pass  # DMs may be closed
        else:
            await interaction.response.send_message(
                f"❌ Follow request for `@{username}` denied.", ephemeral=False
            )
            try:
                if requester:
                    await requester.send(
                        f"❌ Your follow request for `@{username}` on X was **denied**."
                    )
            except Exception:
                pass

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success, custom_id="follow_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, approved=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger, custom_id="follow_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, approved=False)


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class TwitterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._client = None  # Lazy-initialized twikit client

    async def _get_client(self):
        """Lazily initializes and returns the twikit client using saved cookies."""
        if self._client is not None:
            return self._client

        try:
            from twikit import Client
        except ImportError:
            raise RuntimeError("twikit is not installed. Run: pip install twikit")

        # If the file doesn't exist, try writing it from the TWITTER_COOKIES_JSON env var
        # (set this in Railway with the contents of twitter_cookies.json)
        if not os.path.exists(TWITTER_COOKIES_FILE):
            cookies_json = os.getenv("TWITTER_COOKIES_JSON")
            if cookies_json:
                try:
                    json.loads(cookies_json)
                    os.makedirs(os.path.dirname(os.path.abspath(TWITTER_COOKIES_FILE)), exist_ok=True)
                    with open(TWITTER_COOKIES_FILE, "w") as f:
                        f.write(cookies_json)
                    logger.info(f"✅ Wrote Twitter cookies from env var to {TWITTER_COOKIES_FILE}")
                except Exception as e:
                    raise RuntimeError(f"TWITTER_COOKIES_JSON env var is invalid: {e}")
            else:
                raise RuntimeError(
                    f"Twitter cookies file not found: `{TWITTER_COOKIES_FILE}`. "
                    "Either run setup_twitter.py locally, or set the TWITTER_COOKIES_JSON "
                    "environment variable on Railway."
                )

        client = Client(language="en-US")
        client.load_cookies(TWITTER_COOKIES_FILE)
        self._client = client
        logger.info("✅ twikit client initialized from cookies.")
        return client

    # ── Main command ────────────────────────────────────────────

    @commands.command(name="x", aliases=["tweet", "tweets"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def x_command(self, ctx, username: str = None, action: str = "3"):
        """Fetch recent X posts or queue/manage follow requests.
        Usage: .x <username> [count] | .x <username> follow | .x follows"""

        # ── .x follows  (admin queue panel) ──────────────────
        if username and username.lower() == "follows":
            return await self._show_follow_queue(ctx)

        if not username:
            return await ctx.reply(
                "❌ Usage:\n"
                "`  .x zherka 3`      → fetch 3 posts (90 tokens)\n"
                "`  .x zherka follow` → request a follow (admin approval required)\n"
                "`  .x follows`       → [admin] view pending follow requests",
                mention_author=False
            )

        username = username.lstrip("@")

        # ── .x <username> follow  (queue a request) ──────────
        if action.lower() == "follow":
            return await self._handle_follow_request(ctx, username)

        # ── .x <username> [count]  (fetch posts) ─────────────
        try:
            count = int(action)
        except ValueError:
            return await ctx.reply(
                "❌ Invalid usage. Use a number for count, or `follow`.\n"
                "**Examples:** `.x zherka 3`  |  `.x zherka follow`",
                mention_author=False
            )

        await self._fetch_posts(ctx, username, count)

    @x_command.error
    async def x_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "❌ Usage: `.x <username> [count]` or `.x <username> follow`",
                mention_author=False
            )

    # ── Fetch posts ──────────────────────────────────────────

    async def _fetch_posts(self, ctx, username: str, count: int):
        count = max(1, min(count, MAX_POSTS))
        is_admin = ctx.author.guild_permissions.administrator
        total_cost = TOKENS_PER_POST * count

        if not is_admin:
            balance = await get_balance(ctx.author.id)
            if balance < total_cost:
                cost_str = economy.format_balance(total_cost)
                bal_str = economy.format_balance(balance)
                return await ctx.reply(
                    f"❌ Fetching **{count}** post{'s' if count != 1 else ''} costs "
                    f"**{cost_str}** tokens. Your balance: **{bal_str}**.",
                    mention_author=False
                )

        async with ctx.channel.typing():
            try:
                client = await self._get_client()
            except RuntimeError as e:
                return await ctx.reply(f"❌ Twitter setup error: {e}", mention_author=False)

            try:
                user = await client.get_user_by_screen_name(username)
            except Exception as e:
                err_str = str(e).lower()
                if "not found" in err_str or "no user" in err_str or "404" in err_str:
                    return await ctx.reply(f"❌ Account `@{username}` not found on X.", mention_author=False)
                logger.error(f"Error fetching X user @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    f"❌ Could not fetch `@{username}`. X may be rate limiting — try again in a bit.",
                    mention_author=False
                )

            try:
                raw_tweets = await client.get_user_tweets(user.id, tweet_type="Tweets", count=20)
            except Exception as e:
                logger.error(f"Error fetching tweets for @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    "❌ Failed to retrieve posts. X may be rate limiting — try again shortly.",
                    mention_author=False
                )

            filtered = []
            for tweet in raw_tweets:
                if getattr(tweet, "in_reply_to", None):
                    continue
                text = getattr(tweet, "text", "") or ""
                if text.startswith("@"):
                    continue
                filtered.append(tweet)
                if len(filtered) >= count:
                    break

            if not filtered:
                return await ctx.reply(
                    f"❌ No original posts found for `@{username}` (replies and @-mentions excluded).",
                    mention_author=False
                )

            actual_cost = TOKENS_PER_POST * len(filtered)
            if not is_admin:
                await update_balance(ctx.author.id, -actual_cost)

            embeds = []
            avatar_url = getattr(user, "profile_image_url", None)
            display_name = getattr(user, "name", username)

            for tweet in filtered:
                tweet_id = getattr(tweet, "id", None)
                tweet_url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else None

                timestamp = None
                created_at = getattr(tweet, "created_at", None)
                if created_at:
                    try:
                        from email.utils import parsedate_to_datetime
                        timestamp = parsedate_to_datetime(created_at).astimezone(timezone.utc)
                    except Exception:
                        pass

                favorite_count = getattr(tweet, "favorite_count", 0) or 0
                retweet_count  = getattr(tweet, "retweet_count", 0) or 0

                embed = discord.Embed(
                    description=tweet.text[:4090] if tweet.text else "*[no text]*",
                    color=0x1DA1F2,
                    url=tweet_url,
                    timestamp=timestamp
                )
                embed.set_author(
                    name=f"{display_name} (@{username})",
                    url=f"https://x.com/{username}",
                    icon_url=avatar_url
                )

                stats = []
                if favorite_count: stats.append(f"❤️ {favorite_count:,}")
                if retweet_count:  stats.append(f"🔁 {retweet_count:,}")
                footer = "  ".join(stats) if stats else "X (Twitter)"
                if not is_admin:
                    footer += f"  •  -{economy.format_balance(TOKENS_PER_POST)} tokens"
                embed.set_footer(text=footer)

                try:
                    media = getattr(tweet, "media", None)
                    if media:
                        first = media[0]
                        media_url = getattr(first, "media_url_https", None) or getattr(first, "url", None)
                        if media_url and first.type == "photo":
                            embed.set_image(url=media_url)
                except Exception:
                    pass

                embeds.append(embed)

            await ctx.send(embeds=embeds)

    # ── Queue a follow request (any user) ────────────────────

    async def _handle_follow_request(self, ctx, username: str):
        is_admin = ctx.author.guild_permissions.administrator

        # Admins skip the queue and follow directly
        if is_admin:
            return await self._do_follow(ctx, username)

        # Check for duplicate pending request
        if await has_pending_follow_request(username):
            return await ctx.reply(
                f"⏳ A follow request for `@{username}` is already pending admin approval.",
                mention_author=False
            )

        request_id = await add_follow_request(ctx.author.id, username)

        # Confirm to user
        await ctx.reply(
            f"📬 Your request to follow `@{username}` has been submitted for admin approval.\n"
            f"You'll receive a DM when it's actioned. (Request #{request_id})",
            mention_author=False
        )

        # Ping admin in the bot-logs / system-logs channel
        log_channel = (
            discord.utils.get(ctx.guild.text_channels, name="bot-logs") or
            discord.utils.get(ctx.guild.text_channels, name="system-logs")
        )
        if log_channel:
            embed = discord.Embed(
                title="📬 New X Follow Request",
                description=(
                    f"**Account:** `@{username}` — [View on X](https://x.com/{username})\n"
                    f"**Requested by:** {ctx.author.mention} (`{ctx.author.display_name}`)\n"
                    f"**Request ID:** #{request_id}\n\n"
                    f"Use `.x follows` to review the queue."
                ),
                color=0x1DA1F2,
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=embed)

    # ── Admin: show follow queue ─────────────────────────────

    async def _show_follow_queue(self, ctx):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply("🚫 Admins only.", mention_author=False)

        pending = await get_pending_follow_requests()

        if not pending:
            return await ctx.reply("✅ No pending follow requests.", mention_author=False)

        await ctx.reply(
            f"📋 **{len(pending)} pending follow request{'s' if len(pending) != 1 else ''}** — "
            "use the buttons to approve or deny each one.",
            mention_author=False
        )

        for req_id, requester_id_str, username, requested_at in pending:
            requester_id = int(requester_id_str)
            member = ctx.guild.get_member(requester_id)
            member_name = member.display_name if member else f"User {requester_id}"

            dt = datetime.fromtimestamp(requested_at, tz=timezone.utc)
            time_str = dt.strftime("%b %d, %Y %H:%M UTC")

            embed = discord.Embed(
                title=f"Follow Request #{req_id}",
                description=(
                    f"**Account:** `@{username}` — [View on X](https://x.com/{username})\n"
                    f"**Requested by:** {member_name}\n"
                    f"**Submitted:** {time_str}"
                ),
                color=0x1DA1F2
            )

            view = FollowApprovalView(
                cog=self,
                request_id=req_id,
                username=username,
                requester_id=requester_id
            )
            await ctx.send(embed=embed, view=view)

    # ── Admin: direct follow (no queue) ─────────────────────

    async def _do_follow(self, ctx, username: str):
        async with ctx.channel.typing():
            try:
                client = await self._get_client()
            except RuntimeError as e:
                return await ctx.reply(f"❌ Twitter setup error: {e}", mention_author=False)

            try:
                user = await client.get_user_by_screen_name(username)
            except Exception as e:
                err_str = str(e).lower()
                if "not found" in err_str or "no user" in err_str or "404" in err_str:
                    return await ctx.reply(f"❌ Account `@{username}` not found on X.", mention_author=False)
                logger.error(f"Error looking up X user @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    f"❌ Could not find `@{username}`. X may be rate limiting — try again shortly.",
                    mention_author=False
                )

            display_name = getattr(user, "name", username)
            avatar_url   = getattr(user, "profile_image_url", None)
            is_private   = getattr(user, "protected", False)

            try:
                await user.follow()
            except Exception as e:
                logger.error(f"Error following X user @{username}: {e}", exc_info=True)
                return await ctx.reply(f"❌ Failed to follow `@{username}`: {e}", mention_author=False)

            embed = discord.Embed(
                description=(
                    f"{'🔒 ' if is_private else ''}**{display_name}** (`@{username}`) followed.\n"
                    + ("A follow request has been sent — they'll need to accept it." if is_private
                       else f"Posts can now be fetched with `.x {username}`")
                ),
                color=0x1DA1F2
            )
            embed.set_author(
                name=f"{display_name} (@{username})",
                url=f"https://x.com/{username}",
                icon_url=avatar_url
            )
            embed.set_footer(text="X (Twitter)")
            await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(TwitterCog(bot))
