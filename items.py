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
        "feedback": "🎀 Dawww~",
    },
    "echo_ward": {
        "cost": 400,
        "type": "defense",
        "feedback": "🛡️ Echo Ward added to inventory. Automatically reversing the next hex!",
    },
    "kush_pack": {
        "cost": 60,
        "type": "fun",
        "feedback": "Sparking Apeiron Kush Pack. Shields active.",
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

import random


def aggressive_uwu(text: str) -> str:
    """
    Transforms text into a readable, high-quality UWU style with integrated interactive actions
    formatted as **\*bolded phrase*** (literal bolded asterisks).
    """
    if not text:
        return "..."

    # 1. Standardize and Lowercase
    text = text.lower()

    # 2. Fundamental UWU Swaps (L/R -> W, Th -> Fw/Tw)
    text = text.replace("l", "w").replace("r", "w")
    text = text.replace("th", "fw").replace("the", "da").replace("to", "two")

    # 3. Aggressive but Controlled Stuttering (25% chance)
    words = text.split()
    transformed_words = []

    # Define interactive insertions with the exact formatting: **\*phrase\***
    # NOTE: The double space at the start of the string will be stripped later, but adds spacing here.
    interactive_actions = [
        " **\*bweops your nose\***",
        " **\*kisses your cheek\***",
        " **\*leaks\***",
        " **\*giggles\***",
        " **\*pouts\***",
        " **\*pwease\***",
        " **\*sniffles\***",
        " **\*wags taiw\***",
    ]

    # Controlled insertion chance: 15% chance to insert an action between words
    for i, word in enumerate(words):

        # Apply stuttering logic (unchanged)
        if (
            len(word) > 4
            and not word.startswith(("<", "@", "http", "da", "two"))
            and random.random() < 0.25
        ):
            stutter = f"{word[0]}-"
            word = stutter + word

        # Apply clean suffixes logic (unchanged)
        if random.random() < 0.10:
            word = word.rstrip("s") + random.choice(["-kun", "-chan", "-sama"])

        transformed_words.append(word)

        # 4. Insert Interactive Action (After 3-5 words, 15% chance)
        if (i % random.randint(3, 5) == 0 and i > 0) and random.random() < 0.15:
            transformed_words.append(random.choice(interactive_actions))

    text = " ".join(transformed_words)

    # 5. Final Polish and Emoji
    if text:
        # Capitalize the first letter for readability
        text = text[0].upper() + text[1:]

    final_slop = [
        " (✿◡‿◡)",
        " UwU",
        " owo",
        " grr",
        " :3",
        " ts",
        " *blushes*",
        " *dies*",
        " lol",
        " *stop*",
    ]

    # Remove excessive whitespace and append final slop
    return text.strip() + random.choice(final_slop)


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
