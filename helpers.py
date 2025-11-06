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
