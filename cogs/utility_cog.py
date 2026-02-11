"""
Utility Cog - General utility commands
Commands: gem, rev, ud, flip, roll, 8ball, moon, lp, w, crypto, gifs, key, stats, time, location
"""

import discord
from discord.ext import commands
import logging
import random
import asyncio
import time
import urllib.parse
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
import ephem

import economy
from database import get_balance, update_balance, get_user_timezone, set_user_timezone, increment_gif_count, get_top_gifs, get_gif_by_rank
from helpers import (
    calculate_all_gematria,
    get_moon_phase_name,
    get_moon_phase_emoji,
    get_zodiac_sign,
    calculate_life_path,
    get_life_path_traits,
    get_chinese_zodiac_animal,
    get_chinese_zodiac_element,
    get_chinese_animal_traits,
    get_chinese_element_traits,
    get_generation,
    shorten_gif_url,
    extract_image,
    has_authorized_role,
)
from api import urban_dictionary_lookup, google_lens_fetch_results, lookup_location
import crypto_api

logger = logging.getLogger(__name__)

# Constants
GEMATRIA_TOKEN_COST = 2
REVERSE_IMAGE_TOKEN_COST = 2

# Cooldown tracking
weather_user_cooldowns = {}
weather_user_hourly = {}


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gem")
    async def gematria_command(self, ctx, *, text: str = None):
        """Calculate gematria values for text (costs 2 tokens)"""
        
        if ctx.message.reference:
            reply_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text = reply_msg.content

        if not text or not any(ch.isalnum() for ch in text):
            return await ctx.reply(
                "⚠️ Nothing to read here.", mention_author=False
            )

        if len(text) > 53:
            return await ctx.reply("❌ Too many words. Keep it under 53 characters.", mention_author=False)

        balance = await get_balance(ctx.author.id)
        if balance < GEMATRIA_TOKEN_COST:
            cost_str = economy.format_balance(GEMATRIA_TOKEN_COST)
            return await ctx.reply(
                f"❌ Requires {cost_str}. You're flat.", mention_author=False
            )

        await update_balance(ctx.author.id, -GEMATRIA_TOKEN_COST)

        results = calculate_all_gematria(text)

        embed = discord.Embed(
            title=f"Gematria for: {text}", color=discord.Color.dark_grey()
        )

        embed.add_field(name="Hebrew", value=str(results["hebrew"]), inline=False)
        embed.add_field(name="English", value=str(results["english"]), inline=False)
        embed.add_field(name="Ordinal", value=str(results["ordinal"]), inline=False)
        embed.add_field(name="Reduction", value=str(results["reduction"]), inline=False)
        embed.add_field(name="Reverse", value=str(results["reverse"]), inline=False)
        embed.add_field(
            name="Reverse Reduction", value=str(results["reverse_reduction"]), inline=False
        )
        embed.add_field(name="Latin", value=str(results["latin"]), inline=False)
        embed.add_field(
            name="Reverse Sumerian", value=str(results["reverse_sumerian"]), inline=False
        )

        is_exempt = ctx.author.guild_permissions.administrator

        if not is_exempt:
            embed.set_footer(text=f"{ctx.author.display_name}")

        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="rev")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def reverse_command(self, ctx):
        """Reverse search the most relevant image in chat using Google Lens (costs 2 tokens)"""
        async with ctx.channel.typing():
            image_url = None
            if ctx.message.reference:
                try:
                    replied = await ctx.channel.fetch_message(
                        ctx.message.reference.message_id
                    )
                    image_url = await extract_image(replied)
                except Exception as e:
                    logger.error(f"Error fetching replied message: {e}")

            if not image_url:
                async for msg in ctx.channel.history(limit=20):
                    image_url = await extract_image(msg)
                    if image_url:
                        break

            if not image_url:
                return await ctx.reply("⚠️ No image found in the last 20 messages.")

            balance = await get_balance(ctx.author.id)
            if balance < REVERSE_IMAGE_TOKEN_COST:
                cost_str = economy.format_balance(REVERSE_IMAGE_TOKEN_COST)
                bal_str = economy.format_balance(balance)
                return await ctx.reply(
                    f"❌ Requires {cost_str}. Balance: {bal_str}.",
                    mention_author=False,
                )

            await update_balance(ctx.author.id, -REVERSE_IMAGE_TOKEN_COST)

            try:
                data = await google_lens_fetch_results(image_url, limit=3)
            except ValueError as e:
                return await ctx.reply(f"❌ Configuration error: {e}")
            except RuntimeError as e:
                return await ctx.reply(f"❌ Search error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in reverse search: {e}")
                return await ctx.reply(f"❌ Unexpected error: {type(e).__name__}")

            if not data or not data.get("results"):
                return await ctx.reply("❌ No similar images found.")

            embed = discord.Embed(
                title="🔍 Google Lens Reverse Image Search", color=discord.Color.blue()
            )

            for i, r in enumerate(data["results"], start=1):
                title_truncated = r["title"][:100] if r["title"] else "Untitled"
                field_name = f"{i}. {title_truncated}"
                field_value = (
                    f"📌 Source: {r['source']}\n🔗 [View Image]({r['link']})"
                    if r["link"]
                    else f"📌 Source: {r['source']}"
                )
                embed.add_field(name=field_name, value=field_value, inline=False)

            if data.get("search_page"):
                embed.add_field(
                    name="🌐 Full Search Results",
                    value=f"[View on Google Lens]({data['search_page']})",
                    inline=False,
                )

            embed.set_footer(text="Powered by SerpApi + Google Lens")
            embed.set_thumbnail(url=image_url)

            await ctx.reply(embed=embed)

    @commands.command(name="ud")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urban_command(self, ctx, *, term: str):
        """Look up a term on Urban Dictionary"""
        if len(term) > 100:
            return await ctx.send("❌ Term too long (max 100 characters)")

        data = await urban_dictionary_lookup(term)

        if not data:
            return await ctx.send("❌ Request timed out or an error occurred")

        if not data.get("list"):
            return await ctx.send(f"No definition found for **{term}**.")

        first = data["list"][0]
        definition = first["definition"][:1000]
        example = first.get("example", "")[:500]

        embed = discord.Embed(
            title=f"Definition of {term}",
            description=f"{definition}\n\n*Example: {example}*" if example else definition,
            color=discord.Color.dark_purple(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="flip")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def flip_command(self, ctx):
        """Flip a coin"""
        await asyncio.sleep(1)
        result = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 **{result}**")

    @commands.command(name="roll")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roll_command(self, ctx):
        """Roll a random number between 1-33"""
        await asyncio.sleep(0.5)
        result = random.randint(1, 33)
        await ctx.send(f"{ctx.author.display_name} rolls 🎲 **{result}**")

    @commands.command(name="8ball")
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def eightball_command(self, ctx, *, question: str = None):
        """Ask the magic 8-ball a question"""
        if not question:
            return await ctx.send("❌ Ask a question cuh.")

        responses = [
            "You bet your fucking life.",
            "Absolutely, no doubt about it.",
            "100%. Go for it.",
            "Hell yeah.",
            "Does a bear shit in the woods?",
            "Is water wet cuh? Yes.",
            "Maybe, maybe not. Figure it out yourself.",
            "Ask me later, I'm busy.",
            "Unclear. Try again when I care bitch.",
            "Eh, could go either way.",
            "Sheeeeit, ion know",
            "Hell no.",
            "Not a chance in hell.",
            "Absolutely fucking not.",
            "Are you stupid? No.",
            "In your dreams cuh.",
            "Nope. Don't even think about it cuh.",
        ]

        msg = await ctx.send(f"**{ctx.author.display_name}:** {question}\n🎱 *shaking...*")
        await asyncio.sleep(5)
        await msg.edit(
            content=f"**{ctx.author.display_name}:** {question}\n🎱 **{random.choice(responses)}**"
        )

    @commands.command(name="moon")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def moon_command(self, ctx):
        """Show current moon phase and upcoming moons"""
        try:
            now = ephem.now()
            moon = ephem.Moon()
            moon.compute(now)

            illumination = moon.phase / 100.0
            phase_name = get_moon_phase_name(illumination)
            phase_emoji = get_moon_phase_emoji(phase_name)

            moon_ecliptic = ephem.Ecliptic(moon)
            current_sign = get_zodiac_sign(moon_ecliptic.lon)

            next_new = ephem.next_new_moon(now)
            new_moon = ephem.Moon()
            new_moon.compute(next_new)
            new_moon_ecliptic = ephem.Ecliptic(new_moon)
            new_moon_sign = get_zodiac_sign(new_moon_ecliptic.lon)
            days_to_new = int((ephem.Date(next_new) - ephem.Date(now)))

            next_full = ephem.next_full_moon(now)
            full_moon = ephem.Moon()
            full_moon.compute(next_full)
            full_moon_ecliptic = ephem.Ecliptic(full_moon)
            full_moon_sign = get_zodiac_sign(full_moon_ecliptic.lon)
            days_to_full = int((ephem.Date(next_full) - ephem.Date(now)))

            new_date_str = ephem.Date(next_new).datetime().strftime("%B %d, %Y")
            full_date_str = ephem.Date(next_full).datetime().strftime("%B %d, %Y")

            embed = discord.Embed(title="Moon Phase", color=discord.Color.blue())

            embed.add_field(
                name="Current",
                value=f"{phase_emoji} **{phase_name}** ({int(illumination * 100)}% illuminated)\nMoon in: **{current_sign}**",
                inline=False,
            )

            embed.add_field(
                name="Upcoming",
                value=(
                    f"**Next New Moon:** {new_date_str} (in {days_to_new} days)\n"
                    f"Moon in: **{new_moon_sign}**\n\n"
                    f"**Next Full Moon:** {full_date_str} (in {days_to_full} days)\n"
                    f"Moon in: **{full_moon_sign}**"
                ),
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in moon command: {e}", exc_info=True)
            await ctx.send(f"❌ Error calculating moon phase: {str(e)}")

    @commands.command(name="lp")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lifepathnumber_command(self, ctx, date: str = None):
        """Calculate Life Path Number from birthdate with Chinese Zodiac"""
        if not date:
            return await ctx.send(
                "❌ Please provide a date.\n"
                "**Format:** `.lp MM/DD/YYYY`\n"
                "**Example:** `.lp 05/15/1990`"
            )

        try:
            parts = date.split("/")
            if len(parts) != 3:
                raise ValueError("Invalid format")

            month = int(parts[0])
            day = int(parts[1])
            year = int(parts[2])

            if not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
                raise ValueError("Invalid date values")

            life_path = calculate_life_path(month, day, year)
            traits = get_life_path_traits(life_path)

            zodiac_animal, zodiac_emoji = get_chinese_zodiac_animal(year, month, day)
            zodiac_element = get_chinese_zodiac_element(year, month, day)
            animal_traits = get_chinese_animal_traits(zodiac_animal)
            element_traits = get_chinese_element_traits(zodiac_element)

            today = datetime.now()
            age = today.year - year
            if (today.month, today.day) < (month, day):
                age -= 1

            generation = get_generation(year)

            date_obj = datetime(year, month, day)
            formatted_date = date_obj.strftime("%B %d, %Y")

            is_master = life_path in [11, 22, 33]

            embed = discord.Embed(title="Life Path Number", color=discord.Color.purple())

            embed.add_field(name="Birthday", value=formatted_date, inline=False)

            embed.add_field(
                name="Life Path",
                value=f"**{life_path}**" + (" (Master Number)" if is_master else ""),
                inline=False,
            )

            embed.add_field(name="Traits", value=traits, inline=False)

            compact_info = (
                f"{zodiac_element} {zodiac_animal} {zodiac_emoji} • {age} • {generation}"
            )
            embed.add_field(
                name="Chinese Zodiac • Age • Generation", value=compact_info, inline=False
            )

            embed.add_field(
                name=f"{zodiac_animal} Traits", value=animal_traits, inline=False
            )
            embed.add_field(
                name=f"{zodiac_element} Element", value=element_traits, inline=False
            )

            await ctx.send(embed=embed)

        except ValueError:
            await ctx.send(
                "❌ Invalid date format.\n"
                "**Format:** `.lp MM/DD/YYYY`\n"
                "**Example:** `.lp 05/15/1990`"
            )
        except Exception as e:
            logger.error(f"Error in life path command: {e}")
            await ctx.send("❌ Error calculating life path number.")

    @commands.command(name="w")
    async def weather_command(self, ctx, *, location: str = None):
        """Gets current weather for a location (zip code, city, neighborhood, etc.)"""

        if self.bot.aiohttp_session is None or self.bot.aiohttp_session.closed:
            self.bot.aiohttp_session = aiohttp.ClientSession()

        if ctx.message.reference and not location:
            try:
                replied_message = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                replied_user = replied_message.author

                timezone_name, city = await get_user_timezone(replied_user.id)
                if city:
                    location = city
                else:
                    timezone_name, city = await get_user_timezone(ctx.author.id)
                    if city:
                        location = city
                    else:
                        await ctx.reply(
                            "❌ Neither you nor the user you replied to has a location set. Use `.location <city>` to set one.",
                            mention_author=False,
                        )
                        return
            except:
                pass

        if not location:
            timezone_name, city = await get_user_timezone(ctx.author.id)
            if city:
                location = city
            else:
                await ctx.reply(
                    "❌ Please provide a location or set your location with `.location <city>`",
                    mention_author=False,
                )
                return

        is_admin = ctx.author.guild_permissions.administrator

        if not is_admin:
            current_time = time.time()
            user_id = ctx.author.id

            if user_id in weather_user_cooldowns:
                time_since_last = current_time - weather_user_cooldowns[user_id]
                if time_since_last < 3:
                    return

            if user_id not in weather_user_hourly:
                weather_user_hourly[user_id] = []

            weather_user_hourly[user_id] = [
                t for t in weather_user_hourly[user_id] if current_time - t < 3600
            ]

            if len(weather_user_hourly[user_id]) >= 30:
                return

            weather_user_cooldowns[user_id] = current_time
            weather_user_hourly[user_id].append(current_time)

        API_KEY = "904009bb087585331892946d3b7a5386"

        if API_KEY == "YOUR_API_KEY_HERE":
            await ctx.reply("❌ Weather API key not configured!", mention_author=False)
            return

        us_state_abbrevs = {
            "alabama": "al", "al": "al", "alaska": "ak", "ak": "ak",
            "arizona": "az", "az": "az", "arkansas": "ar", "ar": "ar",
            "california": "ca", "ca": "ca", "colorado": "co", "co": "co",
            "connecticut": "ct", "ct": "ct", "delaware": "de", "de": "de",
            "florida": "fl", "fl": "fl", "georgia": "ga", "ga": "ga",
            "hawaii": "hi", "hi": "hi", "idaho": "id", "id": "id",
            "illinois": "il", "il": "il", "indiana": "in", "in": "in",
            "iowa": "ia", "ia": "ia", "kansas": "ks", "ks": "ks",
            "kentucky": "ky", "ky": "ky", "louisiana": "la", "la": "la",
            "maine": "me", "me": "me", "maryland": "md", "md": "md",
            "massachusetts": "ma", "ma": "ma", "michigan": "mi", "mi": "mi",
            "minnesota": "mn", "mn": "mn", "mississippi": "ms", "ms": "ms",
            "missouri": "mo", "mo": "mo", "montana": "mt", "mt": "mt",
            "nebraska": "ne", "ne": "ne", "nevada": "nv", "nv": "nv",
            "new hampshire": "nh", "nh": "nh", "new jersey": "nj", "nj": "nj",
            "new mexico": "nm", "nm": "nm", "new york": "ny", "ny": "ny",
            "north carolina": "nc", "nc": "nc", "north dakota": "nd", "nd": "nd",
            "ohio": "oh", "oh": "oh", "oklahoma": "ok", "ok": "ok",
            "oregon": "or", "or": "or", "pennsylvania": "pa", "pa": "pa",
            "rhode island": "ri", "ri": "ri", "south carolina": "sc", "sc": "sc",
            "south dakota": "sd", "sd": "sd", "tennessee": "tn", "tn": "tn",
            "texas": "tx", "tx": "tx", "utah": "ut", "ut": "ut",
            "vermont": "vt", "vt": "vt", "virginia": "va", "va": "va",
            "washington": "wa", "wa": "wa", "west virginia": "wv", "wv": "wv",
            "wisconsin": "wi", "wi": "wi", "wyoming": "wy", "wy": "wy",
        }

        location_stripped = location.strip()
        location_parts = location_stripped.lower().split()

        if location_stripped.isdigit() and len(location_stripped) == 5:
            url = f"https://api.openweathermap.org/data/2.5/weather?zip={location_stripped},us&appid={API_KEY}&units=metric"
        elif location_parts and location_parts[-1] in us_state_abbrevs:
            state_abbrev = us_state_abbrevs[location_parts[-1]]
            city = " ".join(location_parts[:-1])
            formatted_location = f"{city},{state_abbrev},us"
            encoded_location = urllib.parse.quote(formatted_location)
            url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_location}&appid={API_KEY}&units=metric"
        else:
            encoded_location = urllib.parse.quote(location_stripped)
            url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_location}&appid={API_KEY}&units=metric"

        try:
            if self.bot.aiohttp_session is None or self.bot.aiohttp_session.closed:
                self.bot.aiohttp_session = aiohttp.ClientSession()

            async with self.bot.aiohttp_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    location_name = data["name"]
                    country = data["sys"]["country"]
                    temp_c = data["main"]["temp"]
                    temp_f = (temp_c * 9 / 5) + 32
                    condition = data["weather"][0]["description"].title()

                    weather_msg = f"**{location_name}, {country}**\n{condition} • {temp_f:.1f}°F / {temp_c:.1f}°C"
                    await ctx.send(weather_msg)

                elif response.status == 404:
                    await ctx.reply(
                        f"❌ Location '{location}' not found!", mention_author=False
                    )
                elif response.status == 401:
                    await ctx.reply(
                        "❌ Invalid API key! Check your OpenWeatherMap API key.",
                        mention_author=False,
                    )
                else:
                    await ctx.reply(
                        f"❌ Failed to fetch weather data. Status: {response.status}",
                        mention_author=False,
                    )

        except Exception as e:
            await ctx.reply(f"❌ Error: {e}", mention_author=False)

    @commands.command(name="crypto", aliases=["btc", "eth"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def crypto_command(self, ctx):
        """Displays real-time prices for the top 5 cryptocurrencies."""

        loading_msg = await ctx.send("🌐 Fetching real-time crypto prices... ⏳")

        crypto_data = await crypto_api.fetch_crypto_prices(self.bot.aiohttp_session, 5)

        if not crypto_data:
            await loading_msg.edit(
                content="❌ Could not retrieve crypto prices. The API may be down or experiencing issues."
            )
            return

        embed = discord.Embed(
            title="📈 Top 5 Cryptocurrencies (USD)",
            description="Data provided by CoinGecko.",
            color=discord.Color.from_rgb(255, 165, 0),
            timestamp=datetime.now(),
        )

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name} | User ID: {ctx.author.id}"
        )

        def format_price(price: float) -> str:
            if price is None:
                return "N/A"
            if price >= 100:
                return f"${price:,.2f}"
            elif price >= 1:
                return f"${price:.4f}"
            else:
                return f"${price:.6f}"

        def format_change(change: float) -> str:
            if change is None:
                return "N/A"
            sign = "+" if change >= 0 else ""
            emoji = "🟢" if change >= 0 else "🔴"
            return f"{emoji} {sign}{change:.2f}%"

        for i, coin in enumerate(crypto_data, 1):
            price_str = format_price(coin["price"])
            change_str = format_change(coin["change_24h"])

            name_field = f"{i}. {coin['name']} (`{coin['symbol']}`)"
            value_field = f"**Price:** {price_str}\n**24H Change:** {change_str}"

            embed.add_field(name=name_field, value=value_field, inline=True)

        if len(crypto_data) % 3 == 2:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        await loading_msg.edit(content=None, embed=embed)

    @commands.command(name="gifs")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gifs_command(self, ctx):
        """Show top 10 most sent GIFs"""
        top_gifs = await get_top_gifs(limit=10)

        if not top_gifs:
            return await ctx.send("📊 No GIFs tracked yet. Send some GIFs!")

        description = ""
        medals = ["🥇", "🥈", "🥉"]

        for i, (gif_url, count, last_sent_by) in enumerate(top_gifs, start=1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            shortened = shorten_gif_url(gif_url)

            user = self.bot.get_user(int(last_sent_by))
            username = user.display_name if user else f"User#{last_sent_by[:4]}"

            description += f"{medal} **{count} sends** - `{shortened}` - @{username}\n"

        embed = discord.Embed(
            title="🏆 Top 10 Most Sent GIFs",
            description=description + "\n💡 React 1️⃣-🔟 to see a GIF!",
            color=discord.Color.purple(),
        )

        msg = await ctx.send(embed=embed)

        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(min(len(top_gifs), 10)):
            await msg.add_reaction(reactions[i])

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in reactions
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            rank = reactions.index(str(reaction.emoji)) + 1
            gif_url = await get_gif_by_rank(rank)

            if gif_url:
                await ctx.send(f"**#{rank} GIF:**\n{gif_url}")
        except asyncio.TimeoutError:
            pass

    @commands.command(name="key")
    async def kek_command(self, ctx):
        """Sends a specific sticker 6 times (1 min cooldown for non-admins)"""

        REWARD_AMOUNT = 3
        last_used = getattr(self.bot, 'key_last_used', {})
        current_time = time.time()
        
        # 1. Global Cooldown (3 minutes)
        global_cooldown_duration = 180
        last_global_use = getattr(self.bot, 'key_global_last_used', 0)
        
        is_admin = ctx.author.guild_permissions.administrator
        is_capo = any(role.name == "Capo" for role in ctx.author.roles)
        
        if not (is_admin or is_capo):
            cooldown_messages = [
                "Rest...",
                "Patience...",
                "The abyss awaits...",
                "You will wait...",
                "Not on my watch...",
                "The void beckons...",
            ]
            # Check Global Cooldown first
            if current_time - last_global_use < global_cooldown_duration:
                await ctx.send(random.choice(cooldown_messages))
                return

            # 2. Per-User Cooldown (3 minutes)
            user_cooldown_duration = 180
            if "key" in last_used:
                time_since_last_use = current_time - last_used["key"]
                if time_since_last_use < user_cooldown_duration:
                    await ctx.send(random.choice(cooldown_messages))
                    return

        STICKER_ID = 1416504837436342324

        try:
            sticker = await ctx.guild.fetch_sticker(STICKER_ID)

            await ctx.send(f"{ctx.author.display_name} ʰᵃˢ ᵖᵃᶦᵈ ᵗʳᶦᵇᵘᵗᵉ")

            sticker_count = 6 if (is_admin or is_capo) else 2
            for _ in range(sticker_count):
                await ctx.send(stickers=[sticker])

            await update_balance(ctx.author.id, REWARD_AMOUNT)

            if not (is_admin or is_capo):
                self.bot.key_global_last_used = current_time
                last_used["key"] = current_time
                self.bot.key_last_used = last_used

        except discord.NotFound:
            await ctx.reply(
                "❌ Sticker not found! Make sure it's from this server.",
                mention_author=False,
            )
        except discord.HTTPException as e:
            await ctx.reply(f"❌ Failed to send sticker: {e}. My hands are tied!", mention_author=False)

    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Show bot statistics (Admin only)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("🚫 Peasant Detected. Begone!", mention_author=False)
            return

        bot_start_time = getattr(self.bot, 'start_time', datetime.now())
        uptime_delta = datetime.now() - bot_start_time
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        from database import load_quotes_from_db
        quote_count = len(await load_quotes_from_db())

        embed = discord.Embed(title="📊 Bot Stats", color=discord.Color.teal())
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="Quotes", value=str(quote_count), inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="time")
    async def time_command(self, ctx, member: discord.Member = None):
        """Check time for a user"""

        if ctx.message.reference and not member:
            try:
                reply_msg = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                member = reply_msg.author
            except:
                pass

        if not member:
            member = ctx.author

        timezone_name, city = await get_user_timezone(member.id)
        if not timezone_name or not city:
            await ctx.reply(
                f"❌ {member.display_name} has not set their location yet. Use `.location <city>`. Are they lost in the mists?", mention_author=False
            )
            return
        try:
            now = datetime.now(ZoneInfo(timezone_name))
            time_str = now.strftime("%-I:%M %p").lower()
            await ctx.send(f"{time_str} in {city}")
        except Exception as e:
            logger.error(f"Error getting time: {e}")
            await ctx.reply(f"❌ Error getting time: {e}. The sands of time are shifting strangely!", mention_author=False)

    @commands.command(name="location")
    async def location_command(self, ctx, *, args: str = None):
        """Set your timezone location"""
        if not args:
            return await ctx.reply(
                "❌ Please provide a location. Usage: `.location <city>`. Don't wander aimlessly!", mention_author=False
            )

        args_split = args.split()
        target_member = ctx.author
        location_query = args

        if ctx.message.mentions:
            if has_authorized_role(ctx.author):
                target_member = ctx.message.mentions[0]
                location_query = " ".join(
                    word for word in args_split if not word.startswith("<@")
                )
            else:
                await ctx.reply("🚫 You are not authorized to set other users' locations. Stay in your lane!", mention_author=False)
                return

        timezone_name, city = await lookup_location(location_query)
        if not timezone_name:
            await ctx.reply(f"❌ Could not find a location matching '{location_query}'. Is it a phantom city?", mention_author=False)
            return

        await ctx.send(
            f"I found **{city}**. Confirm this as the location for {target_member.display_name}? (yes/no)"
        )

        def check(m):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.lower() in ["yes", "no"]
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            if msg.content.lower() == "yes":
                await set_user_timezone(target_member.id, timezone_name, city)
                await ctx.send(
                    f"✅ Location set for {target_member.display_name} as **{city}**."
                )
            else:
                await ctx.reply("❌ Location setting cancelled. Perhaps another time, wanderer.", mention_author=False)
        except asyncio.TimeoutError:
            await ctx.reply("⌛ Timeout. Location setting cancelled. My patience wears thin!", mention_author=False)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
