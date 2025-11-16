"""
Helper functions for Discord Bot
General utility functions
"""

import ephem
import discord
from config import AUTHORIZED_ROLES

# ============================================================
# PERMISSION HELPERS
# ============================================================


def has_authorized_role(member):
    """Check if member has authorized role"""
    return (
        any(role.name in AUTHORIZED_ROLES for role in member.roles)
        or member.guild_permissions.administrator
    )


# channel name


def get_forum_channel(guild, channel_name):
    """Get a channel by exact name match"""
    return discord.utils.get(guild.channels, name=channel_name)


# ============================================================
# MESSAGE HELPERS
# ============================================================


async def extract_image(message):
    """Extract image URL from message attachments or embeds"""
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image"):
                return att.url

    if message.embeds:
        for embed in message.embeds:
            if embed.image:
                return embed.image.url
            if embed.thumbnail:
                return embed.thumbnail.url

    return None


# ============================================================
# GIF DETECTION HELPERS
# ============================================================


def extract_gif_url(message):
    """Extract GIF URL from message (Tenor, GIPHY, Discord CDN)"""
    # Check message content for Tenor/GIPHY links
    content = message.content.lower()

    if "tenor.com" in content or "giphy.com" in content:
        # Extract the URL
        words = message.content.split()
        for word in words:
            if "tenor.com" in word.lower() or "giphy.com" in word.lower():
                return word.strip()

    # Check attachments for GIFs
    if message.attachments:
        for att in message.attachments:
            if att.content_type and "gif" in att.content_type:
                return att.url

    # Check embeds for GIF URLs
    if message.embeds:
        for embed in message.embeds:
            if embed.type == "gifv" or (
                embed.video and "gif" in str(embed.video.url).lower()
            ):
                return embed.video.url if embed.video else embed.url
            if embed.image and "gif" in str(embed.image.url).lower():
                return embed.image.url

    return None


def shorten_gif_url(url):
    """Shorten GIF URL for display"""
    if "tenor.com/view/" in url:
        # Extract the descriptive part
        parts = url.split("/view/")[1].split("-")
        return "-".join(parts[:-1])[:30] + "..." if len(parts) > 1 else "tenor-gif"
    elif "giphy.com" in url:
        return "giphy-gif"
    elif "cdn.discordapp.com" in url:
        return "discord-gif"
    else:
        return "gif"


# ============================================================
# MOON & ASTROLOGY HELPERS
# ============================================================


def get_moon_phase_emoji(phase):
    """Get emoji for moon phase"""
    phases = {
        "New Moon": "🌑",
        "Waxing Crescent": "🌒",
        "First Quarter": "🌓",
        "Waxing Gibbous": "🌔",
        "Full Moon": "🌕",
        "Waning Gibbous": "🌖",
        "Last Quarter": "🌗",
        "Waning Crescent": "🌘",
    }
    return phases.get(phase, "🌙")


def get_moon_phase_name(illumination):
    """Get moon phase name from illumination percentage"""
    if illumination < 0.01:
        return "New Moon"
    elif illumination < 0.25:
        return "Waxing Crescent"
    elif 0.25 <= illumination < 0.26:
        return "First Quarter"
    elif illumination < 0.49:
        return "Waxing Gibbous"
    elif 0.49 <= illumination < 0.51:
        return "Full Moon"
    elif illumination < 0.75:
        return "Waning Gibbous"
    elif 0.75 <= illumination < 0.76:
        return "Last Quarter"
    else:
        return "Waning Crescent"


def get_zodiac_sign(ecliptic_lon):
    """Get zodiac sign from ecliptic longitude"""
    signs = [
        ("♈ Aries", 0),
        ("♉ Taurus", 30),
        ("♊ Gemini", 60),
        ("♋ Cancer", 90),
        ("♌ Leo", 120),
        ("♍ Virgo", 150),
        ("♎ Libra", 180),
        ("♏ Scorpio", 210),
        ("♐ Sagittarius", 240),
        ("♑ Capricorn", 270),
        ("♒ Aquarius", 300),
        ("♓ Pisces", 330),
    ]
    # Convert radians to degrees
    degrees = float(ecliptic_lon) * 180.0 / ephem.pi
    degrees = degrees % 360  # Normalize to 0-360

    for i in range(len(signs)):
        sign_name, start = signs[i]
        if i < len(signs) - 1:
            end = signs[i + 1][1]
        else:
            end = 360

        if start <= degrees < end:
            return sign_name

    return signs[0][0]  # Default to Aries


def calculate_life_path(month, day, year):
    """Calculate life path number with master number logic"""

    def reduce_to_single_or_master(num):
        """Reduce number to single digit or master number (11, 22, 33)"""
        while num > 9:
            if num in [11, 22, 33]:
                return num
            num = sum(int(d) for d in str(num))
        return num

    # Reduce each component
    month_reduced = reduce_to_single_or_master(month)
    day_reduced = reduce_to_single_or_master(day)
    year_reduced = reduce_to_single_or_master(sum(int(d) for d in str(year)))

    # Sum them
    total = month_reduced + day_reduced + year_reduced

    # Reduce final sum (stopping at master numbers)
    life_path = reduce_to_single_or_master(total)

    return life_path


def get_life_path_traits(number):
    """Get personality traits for life path number"""
    traits = {
        1: "Independent, leader, innovative, ambitious",
        2: "Diplomatic, cooperative, sensitive, peacemaker",
        3: "Creative, expressive, optimistic, social",
        4: "Practical, disciplined, reliable, hard-working",
        5: "Adventurous, freedom-loving, versatile, dynamic",
        6: "Nurturing, responsible, loving, harmonious",
        7: "Analytical, spiritual, introspective, seeker",
        8: "Ambitious, successful, material mastery, powerful",
        9: "Compassionate, humanitarian, wise, idealistic",
        11: "Intuitive, spiritual, visionary, enlightened (Master Number)",
        22: "Master builder, practical idealist, powerful manifester (Master Number)",
        33: "Master teacher, compassionate leader, spiritual uplifter (Master Number)",
    }


import re

# Hebrew Gematria letter map (Gematrix.org standard)
HEBREW_MAP = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7,
    "H": 8,
    "I": 9,
    "J": 10,
    "K": 20,
    "L": 30,
    "M": 40,
    "N": 50,
    "O": 60,
    "P": 70,
    "Q": 80,
    "R": 90,
    "S": 100,
    "T": 200,
    "U": 300,
    "V": 400,
    "W": 406,
    "X": 490,
    "Y": 20,
    "Z": 14,
}

LETTER_REGEX = re.compile(r"[A-Z]")


def reduce_to_single_digit(n: int, keep_master_numbers: bool = True) -> int:
    """
    Reduces a number to a single digit by repeatedly summing its digits.
    Stops at master numbers (11, 22, 33) if keep_master_numbers is True.
    This matches gematrinator.com's default "Reduction" behavior.
    """
    while n > 9:
        # Stop if we hit a master number (11, 22, 33)
        if keep_master_numbers and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def text_to_letters(text: str) -> str:
    """Extract only letters from text and convert to uppercase."""
    return "".join(ch for ch in text.upper() if LETTER_REGEX.match(ch))


def ordinal_values(text: str):
    """Get ordinal values for each letter (A=1, B=2, ..., Z=26)."""
    return [ord(ch) - 64 for ch in text_to_letters(text)]


def reduction_values(text: str):
    """
    Get reduction values where each letter is pre-reduced:
    A=1, B=2...I=9, J=1, K=2...R=9, S=1, etc.
    This matches gematrinator's "FullReduction" modifier.
    """
    letters = text_to_letters(text)
    reduced = []
    for ch in letters:
        ordinal = ord(ch) - 64  # A=1, B=2, etc.
        # Reduce ordinal value to single digit (no master number exception here)
        while ordinal > 9:
            ordinal = sum(int(d) for d in str(ordinal))
        reduced.append(ordinal)
    return reduced


def reverse_values(text: str):
    """Get reverse ordinal values (Z=1, Y=2, ..., A=26)."""
    return [26 - (ord(ch) - 65) for ch in text_to_letters(text)]


def reverse_reduction_values(text: str):
    """
    Get reverse reduction values where each letter is pre-reduced.
    Z=1, Y=2...R=9, Q=10→1, etc.
    Takes reverse ordinal value, then reduces it to single digit.
    """
    letters = text_to_letters(text)
    reduced = []
    for ch in letters:
        # Get reverse ordinal: Z=1, Y=2, X=3... A=26
        reverse = 26 - (ord(ch) - 65)
        # Reduce to single digit (no master number exception at letter level)
        while reverse > 9:
            reverse = sum(int(d) for d in str(reverse))
        reduced.append(reverse)
    return reduced


def hebrew_values(text: str):
    """Get Hebrew Gematria values for each letter."""
    return [HEBREW_MAP.get(ch, 0) for ch in text_to_letters(text)]


def english_gematria_values(text: str):
    """English Gematria is Ordinal * 6 (also called Sumerian)."""
    return [v * 6 for v in ordinal_values(text)]


def fibonacci_values(text: str):
    """Get Fibonacci sequence values for each letter."""
    # Fibonacci values for A-Z from the gematrinator code
    fib_map = [
        1,
        1,
        2,
        3,
        5,
        8,
        13,
        21,
        34,
        55,
        89,
        144,
        233,
        233,
        144,
        89,
        55,
        34,
        21,
        13,
        8,
        5,
        3,
        2,
        1,
        1,
    ]
    letters = text_to_letters(text)
    return [fib_map[ord(ch) - 65] for ch in letters]


def latin_values(text: str):
    """
    Get Latin Gematria values (classical Latin alphabet order).
    Letter order: A B C D E F G H I K L M N O P Q R S T U X Y Z J V W
    Values: 1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400,500,600,700,900
    """
    # Map letters to their Latin gematria values
    latin_map = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "I": 9,
        "K": 10,
        "L": 20,
        "M": 30,
        "N": 40,
        "O": 50,
        "P": 60,
        "Q": 70,
        "R": 80,
        "S": 90,
        "T": 100,
        "U": 200,
        "X": 300,
        "Y": 400,
        "Z": 500,
        "J": 600,
        "V": 700,
        "W": 900,
    }
    letters = text_to_letters(text)
    return [latin_map.get(ch, 0) for ch in letters]


def calculate_ordinal(text: str) -> int:
    """Calculate simple ordinal sum (A=1, B=2, ..., Z=26)."""
    return sum(ordinal_values(text))


def calculate_reduction(text: str) -> int:
    """
    Calculate full reduction (gematrinator style):
    Each letter gets its reduced ordinal value (J=1, K=2, etc.), then sum them.
    No further reduction of the total.
    """
    return sum(reduction_values(text))


def calculate_reverse(text: str) -> int:
    """Calculate reverse ordinal sum (Z=1, Y=2, ..., A=26)."""
    return sum(reverse_values(text))


def calculate_reverse_reduction(text: str) -> int:
    """
    Calculate reverse reduction (gematrinator style):
    Each letter gets its reduced reverse value, then sum them.
    No further reduction of the total.
    """
    return sum(reverse_reduction_values(text))


def calculate_fibonacci(text: str) -> int:
    """Calculate Fibonacci cipher sum."""
    return sum(fibonacci_values(text))


def calculate_latin(text: str) -> int:
    """Calculate Latin Gematria sum."""
    return sum(latin_values(text))


def calculate_all_gematria(text: str):
    """Calculate all gematria cipher values for the given text."""
    ord_vals = ordinal_values(text)
    red_vals = reduction_values(text)
    rev_vals = reverse_values(text)
    rev_red_vals = reverse_reduction_values(text)
    heb_vals = hebrew_values(text)
    eng_vals = english_gematria_values(text)
    fib_vals = fibonacci_values(text)
    lat_vals = latin_values(text)

    return {
        "hebrew": sum(heb_vals),
        "english": sum(eng_vals),
        "ordinal": sum(ord_vals),
        "reduction": sum(red_vals),
        "reverse": sum(rev_vals),
        "reverse_reduction": sum(rev_red_vals),
        "fibonacci": sum(fib_vals),
        "latin": sum(lat_vals),
    }


# Example usage and tests
if __name__ == "__main__":
    test_phrase = "hello world"

    print(f"Testing: '{test_phrase}'")
    print(f"Ordinal: {calculate_ordinal(test_phrase)}")
    print(f"Reduction: {calculate_reduction(test_phrase)}")
    print(f"Reverse: {calculate_reverse(test_phrase)}")
    print(f"Reverse Reduction: {calculate_reverse_reduction(test_phrase)}")
    print(f"Fibonacci: {calculate_fibonacci(test_phrase)}")
    print()
    print("All values:", calculate_all_gematria(test_phrase))
