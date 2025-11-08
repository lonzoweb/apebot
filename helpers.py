"""
Helper functions for Discord Bot
General utility functions
"""

from config import AUTHORIZED_ROLES

# ============================================================
# PERMISSION HELPERS
# ============================================================

def has_authorized_role(member):
    """Check if member has authorized role"""
    return any(role.name in AUTHORIZED_ROLES for role in member.roles) or member.guild_permissions.administrator

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
            if embed.type == "gifv" or (embed.video and "gif" in str(embed.video.url).lower()):
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
        "Waning Crescent": "🌘"
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

def get_zodiac_sign(longitude):
    """Get zodiac sign from ecliptic longitude"""
    signs = [
        ("♈ Aries", 0), ("♉ Taurus", 30), ("♊ Gemini", 60),
        ("♋ Cancer", 90), ("♌ Leo", 120), ("♍ Virgo", 150),
        ("♎ Libra", 180), ("♏ Scorpio", 210), ("♐ Sagittarius", 240),
        ("♑ Capricorn", 270), ("♒ Aquarius", 300), ("♓ Pisces", 330)
    ]
    degrees = (longitude * 180 / ephem.pi) % 360
    for i, (sign, start) in enumerate(signs):
        next_start = signs[(i + 1) % 12][1]
        if next_start == 0:
            next_start = 360
        if start <= degrees < next_start:
            return sign
    return signs[0][0]

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
        33: "Master teacher, compassionate leader, spiritual uplifter (Master Number)"
    }
    return traits.get(number, "Unknown")
