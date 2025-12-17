"""
Items and Text Transformations for Discord Bot
Handles obnoxious UwU logic and Shop item definitions
"""

import random
import re

# ============================================================
# ITEM REGISTRY (Prices and Metadata)
# ============================================================

ITEM_REGISTRY = {
    "muzzle": {
        "cost": 600,
        "duration_sec": 1800,  # 30 mins
        "type": "curse",
        "feedback": "🤐 Muzzle applied. They cannot speak or use commands!",
    },
    "uwu": {
        "cost": 300,
        "duration_sec": 600,  # 10 mins
        "type": "curse",
        "feedback": "🎀 Awww~",
    },
    "saturn_uwu": {
        "cost": 350,
        "duration_sec": 600,  # 10 mins
        "type": "curse",
        "feedback": "🧿 Saturn Uwu upon you, cursed baby-talk.",
    },
    "echo_ward": {
        "cost": 400,
        "type": "defense",
        "feedback": "🛡️ Echo Ward added to inventory. Automatically reversing the next hex!",
    },
    "kush_pack": {
        "cost": 60,
        "type": "fun",
        "feedback": "Sparking up the legendary Apeiron Kush pack. The vibes are immaculate.",
    },
}

# Aliases to make buying/using easier for users
ITEM_ALIASES = {
    "muzzle": "muzzle",
    "mute": "muzzle",
    "silence": "muzzle",
    "uwu": "uwu",
    "uwuify": "uwu",
    "saturn": "saturn_uwu",
    "babytalk": "saturn_uwu",
    "saturn_uwu": "saturn_uwu",
    "ward": "echo_ward",
    "echo": "echo_ward",
    "shield": "echo_ward",
    "kush": "kush_pack",
    "weed": "kush_pack",
    "pack": "kush_pack",
}

# ============================================================
# TRANSFORMATION LOGIC
# ============================================================


def aggressive_uwu(text: str, saturn: bool = False) -> str:
    """
    Transforms text into obnoxious, embarrassing baby-talk.
    saturn=True adds extra cursed variations like 'v' -> 'b' and 'pwease'.
    """
    if not text:
        return "..."

    # 1. Fundamental Swaps
    text = text.replace("L", "W").replace("R", "W").replace("l", "w").replace("r", "w")
    text = text.replace("th", "fw").replace("TH", "FW")

    # 2. Aggressive Word-Start Stuttering
    words = text.split()
    transformed_words = []

    for word in words:
        # Don't stutter very short words or mentions
        if (
            len(word) > 3
            and not word.startswith(("<", "@", "http"))
            and random.random() < 0.4
        ):
            stutter = f"{word[0]}-{word[0]}-"
            word = stutter + word

        # 3. Obnoxious Suffixes (15% chance per word)
        if random.random() < 0.15:
            word += random.choice(["-w-wuv", "ie-wie", "y-wy", "-kun", "-chan"])

        transformed_words.append(word)

    text = " ".join(transformed_words)

    # 4. Saturn's Cursed Logic (Aggressive Baby-talk)
    if saturn:
        text = text.lower()  # Saturn speak is always lowercase
        text = text.replace("v", "b").replace("V", "B")
        text = text.replace("na", "nya").replace("no", "nyo")

        # Aggressive insertions
        interjections = [
            " *nuzzles u*",
            " *paws at ur chest*",
            " *sniffles*",
            " UNGGGHHH",
            " PWEASE",
            " *wags taiw*",
        ]
        if random.random() < 0.3:
            text += random.choice(interjections)

    # 5. Emoji Slop (Always append one)
    slop = [
        " (✿◡‿◡)",
        " (人◕ω◕)",
        " (｡♥‿♥｡)",
        " UwU",
        " >w<",
        " owo",
        " rawr x3",
        " :3",
        " ^-^",
        " *blushes*",
        " *sweats*",
    ]
    text += random.choice(slop)

    return text


# ============================================================
# UTILITIES
# ============================================================


def extract_gif_url(message):
    """
    Checks if a message contains a GIF via attachment or URL.
    Used for GIF tracking logic in main.py.
    """
    # Check attachments
    if message.attachments:
        for anim in message.attachments:
            if anim.content_type and "gif" in anim.content_type:
                return anim.url

    # Check text for Tenor/Giphy links
    gif_patterns = [
        r"https?://[^\s]+giphy\.com/[^\s]+",
        r"https?://[^\s]+tenor\.com/[^\s]+",
        r"https?://[^\s]+\.gif",
    ]
    for pattern in gif_patterns:
        match = re.search(pattern, message.content)
        if match:
            return match.group(0)

    return None
