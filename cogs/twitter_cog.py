"""
Twitter/X Cog - Fetch posts from X (Twitter) accounts
Commands:
  .x <username> [count]   — fetch N posts (30 tokens/post, admins free)
  .x <username> follow    — follow the account (admin only)
"""

import os
import json
import logging
import discord
from discord.ext import commands
from datetime import timezone

import economy
from database import get_balance, update_balance
from config import TWITTER_COOKIES_FILE

logger = logging.getLogger(__name__)

TOKENS_PER_POST = 30
MAX_POSTS = 5


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
                    # Validate it's proper JSON before writing
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
                    "Either run setup_twitter.py locally and commit the file, "
                    "or set the TWITTER_COOKIES_JSON environment variable on Railway."
                )

        client = Client(language="en-US")
        client.load_cookies(TWITTER_COOKIES_FILE)
        self._client = client
        logger.info("✅ twikit client initialized from cookies.")
        return client

    @commands.command(name="x", aliases=["tweet", "tweets"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def x_command(self, ctx, username: str = None, action: str = "3"):
        """Fetch recent X posts or follow an account.
        Usage: .x <username> [count] | .x <username> follow"""

        if not username:
            return await ctx.reply(
                "❌ Usage:\n"
                "`  .x zherka 3`     → fetch 3 posts (90 tokens)\n"
                "`  .x zherka follow` → follow that account (admin only)",
                mention_author=False
            )

        username = username.lstrip("@")

        # Route to follow handler
        if action.lower() == "follow":
            return await self._handle_follow(ctx, username)

        # Parse count
        try:
            count = int(action)
        except ValueError:
            return await ctx.reply(
                "❌ Invalid usage. Use a number for count or `follow`.\n"
                "**Examples:** `.x zherka 3`  |  `.x zherka follow`",
                mention_author=False
            )

        # Clamp count between 1 and MAX_POSTS
        count = max(1, min(count, MAX_POSTS))

        is_admin = ctx.author.guild_permissions.administrator
        total_cost = TOKENS_PER_POST * count

        # Token check for non-admins
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
                    return await ctx.reply(
                        f"❌ Account `@{username}` not found on X.",
                        mention_author=False
                    )
                logger.error(f"Error fetching X user @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    f"❌ Could not fetch `@{username}`. X may be rate limiting us — try again in a bit.",
                    mention_author=False
                )

            try:
                # Fetch a larger batch so we have room to filter out replies/mentions
                raw_tweets = await client.get_user_tweets(user.id, tweet_type="Tweets", count=20)
            except Exception as e:
                logger.error(f"Error fetching tweets for @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    "❌ Failed to retrieve posts. X may be rate limiting — try again shortly.",
                    mention_author=False
                )

            # Filter: exclude replies and tweets that start with @mention
            filtered = []
            for tweet in raw_tweets:
                # Skip replies
                if getattr(tweet, "in_reply_to", None):
                    continue
                text = getattr(tweet, "text", "") or ""
                # Skip tweets that are just @mentions (retweet-like quote-tweets are fine)
                if text.startswith("@"):
                    continue
                filtered.append(tweet)
                if len(filtered) >= count:
                    break

            if not filtered:
                return await ctx.reply(
                    f"❌ No original posts found for `@{username}` (replies and @-mentions are excluded).",
                    mention_author=False
                )

            # Deduct tokens from non-admins (only charge for posts actually retrieved)
            actual_count = len(filtered)
            actual_cost = TOKENS_PER_POST * actual_count

            if not is_admin:
                await update_balance(ctx.author.id, -actual_cost)

            # Build embeds
            embeds = []
            avatar_url = getattr(user, "profile_image_url", None)
            display_name = getattr(user, "name", username)

            for tweet in filtered:
                tweet_id = getattr(tweet, "id", None)
                tweet_url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else None

                created_at = getattr(tweet, "created_at", None)
                if created_at:
                    try:
                        # twikit returns a string like "Mon Jan 01 00:00:00 +0000 2024"
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(created_at).astimezone(timezone.utc)
                        timestamp = dt
                    except Exception:
                        timestamp = None
                else:
                    timestamp = None

                favorite_count = getattr(tweet, "favorite_count", 0) or 0
                retweet_count = getattr(tweet, "retweet_count", 0) or 0

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

                stats_parts = []
                if favorite_count:
                    stats_parts.append(f"❤️ {favorite_count:,}")
                if retweet_count:
                    stats_parts.append(f"🔁 {retweet_count:,}")
                footer_text = "  ".join(stats_parts) if stats_parts else "X (Twitter)"
                if not is_admin:
                    footer_text += f"  •  -{economy.format_balance(TOKENS_PER_POST)} tokens"

                embed.set_footer(text=footer_text)

                # Attach first media if present
                try:
                    media = getattr(tweet, "media", None)
                    if media:
                        first_media = media[0]
                        media_url = getattr(first_media, "media_url_https", None) or \
                                    getattr(first_media, "url", None)
                        if media_url and first_media.type == "photo":
                            embed.set_image(url=media_url)
                except Exception:
                    pass

                embeds.append(embed)

            await ctx.send(embeds=embeds)

    @x_command.error
    async def x_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return  # Let global handler deal with it
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "❌ Usage: `.x <username> [count]`\n**Example:** `.x zherka 3`",
                mention_author=False
            )

    async def _handle_follow(self, ctx, username: str):
        """Admin-only: follow a Twitter/X account using the bot's session."""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply(
                "🚫 Only admins can follow accounts.",
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
                    return await ctx.reply(
                        f"❌ Account `@{username}` not found on X.",
                        mention_author=False
                    )
                logger.error(f"Error looking up X user @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    f"❌ Could not find `@{username}`. X may be rate limiting — try again shortly.",
                    mention_author=False
                )

            display_name = getattr(user, "name", username)
            avatar_url = getattr(user, "profile_image_url", None)
            is_private = getattr(user, "protected", False)

            try:
                await user.follow()
            except Exception as e:
                logger.error(f"Error following X user @{username}: {e}", exc_info=True)
                return await ctx.reply(
                    f"❌ Failed to follow `@{username}`: {e}",
                    mention_author=False
                )

            embed = discord.Embed(
                description=(
                    f"{'🔒 ' if is_private else ''}**{display_name}** (`@{username}`) followed.\n"
                    + ("A follow request has been sent — they'll need to accept before posts are visible." if is_private
                       else "Original posts can now be fetched with `.x "+username+"`")
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
