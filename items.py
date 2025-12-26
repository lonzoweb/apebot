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
]

# The list of approved internal interactive actions remains the same, but 'tail' is fixed.
# NOTE: interactive_actions list is used for internal inserts, not final slop

# NOTE: The list of unreadable/unwanted final slop is manually curated here
CLEAN_FINAL_SLOP = [
    " (✿◡‿◡)", " UwU", " owo", " :3", " ^-^", " *blushes*",
    " hehehe", " *teehee*", " *snuggles*", " *pats head*",
]

def aggressive_uwu(text: str) -> str:
    """
    Transforms text into a readable, high-quality UWU style by removing links/media
    and applying refined transformations.
    """
    if not text:
        return "..."

    # 1. LINK/MEDIA PURGE (New step: Remove all URLs and Discord formatting)
    # Target: URLs, Discord mentions (<@...>), Discord emotes (<:name:id>), and channel links (<#...>)
    
    # Remove URLs (simplified regex)
    text = re.sub(r'https?://[^\s]+', '', text) 
    
    # Remove Discord formatting (emotes, mentions, channel links - simplified regex)
    text = re.sub(r'<a?:[^:]+:\d+>|@\w+|#\w+|@&[0-9]+|<#[0-9]+>', '', text)
    
    # 2. Standardize and Lowercase
    text = text.lower()

    # 3. Fundamental UWU Swaps (L/R -> W, Th -> Fw/Tw)
    text = text.replace("l", "w").replace("r", "w")
    text = text.replace("th", "fw").replace("the", "da").replace("to", "two")

    # 4. Aggressive but Controlled Stuttering (25% chance)
    words = text.split()
    transformed_words = []

    # Define interactive insertions with the exact formatting: **\*phrase\***
    interactive_actions = [
        " **\*bweops your nose\***",
        " **\*kisses your cheek\***",
        " **\*leaks\***",
        " **\*giggles\***",
        " **\*pouts\***",
        " **\*pwease\***",
        " **\*sniffles\***",
        " **\*wags tail\***", # Corrected from 'taiw'
    ]
    
    # Define cleaner suffixes
    clean_suffixes = ["-ie", "-wie", "-y", "-wy", "s-sama"] # Removed -kun, -chan

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

        # Apply clean suffixes logic (10% chance)
        if random.random() < 0.10:
            word = word.rstrip("s") + random.choice(clean_suffixes)

        transformed_words.append(word)

        # 4. Insert Interactive Action (After 3-5 words, 15% chance)
        if (i % random.randint(3, 5) == 0 and i > 0) and random.random() < 0.15:
            transformed_words.append(random.choice(interactive_actions))

    text = " ".join(transformed_words)

    # 5. Final Polish and Emoji
    if text:
        # Capitalize the first letter for readability
        text = text[0].upper() + text[1:]

    # Remove excessive whitespace and append final slop
    return text.strip() + random.choice(CLEAN_FINAL_SLOP)