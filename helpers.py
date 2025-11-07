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
