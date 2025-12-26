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

# NOTE: The list of unreadable/unwanted final slop is manually curated here
CLEAN_FINAL_SLOP = [
    " (✿◡‿◡)",
    " UwU",
    " owo",
    " :3",
    " ^-^",
    " *blushes*",
    " hehehe",
    " *teehee*",
    " *snuggles*",
    " *pats head*",
]

# Specific word overrides for smoother reading
UWU_WORD_MAP = {
    "you": "yuw",
    "have": "haz",
    "are": "r",
    "love": "wuv",
    "the": "da",
    "this": "dis",
    "that": "dat",
    "with": "wif",
    "what": "wat",
    "no": "nyo",
    "oh": "owh",
    "is": "iz",
    "to": "two",
}

# Define interactive insertions with the exact formatting: **\*phrase\***
INTERACTIVE_ACTIONS = [
    " **\*bweops your nose\***",
    " **\*kisses your cheek\***",
    " **\*leaks\***",
    " **\*giggles\***",
    " **\*pouts\***",
    " **\*pwease\***",
    " **\*sniffles\***",
    " **\*wags tail\***",
]

CLEAN_SUFFIXES = ["-ie", "-wie", "-y", "-wy"]


def aggressive_uwu(text: str) -> str:
    """
    Transforms text into a readable, high-quality UWU style by removing links/media
    and applying refined transformations.
    """
    if not text:
        return "..."

    # 1. LINK/MEDIA PURGE
    # Remove URLs
    text = re.sub(r"https?://[^\s]+", "", text)
    # Remove Discord formatting (emotes, mentions, channel links)
    text = re.sub(r"<a?:[^:]+:\d+>|@\w+|#\w+|@&[0-9]+|<#[0-9]+>", "", text)

    if not text.strip():
        return random.choice(CLEAN_FINAL_SLOP)

    # 2. Standardize
    text = text.lower()

    # 3. "Nya-fication" (Turn na/ne/ni/no/nu into nya/nye/nyi/nyo/nyu)
    # Checks for n followed by a vowel, replaces with ny+vowel
    text = re.sub(r"n([aeiou])", r"ny\1", text)

    # 4. Fundamental Letter Swaps
    # We do this before splitting to catch partials, but after Nya-fication
    text = text.replace("l", "w").replace("r", "w")
    text = text.replace("th", "fw")

    words = text.split()
    transformed_words = []

    # 5. Word-by-Word Processing
    for i, word in enumerate(words):
        # Clean punctuation for dictionary lookup
        clean_word = word.strip(".,!?")

        # A. Check Dictionary Overrides First (Highest Quality)
        if clean_word in UWU_WORD_MAP:
            # Replace the word but keep punctuation attached if possible
            # Simple replace for now, context usually implies punctuation isn't critical for uwu
            word = UWU_WORD_MAP[clean_word]

        else:
            # B. Aggressive but Controlled Stuttering (30% chance)
            # Don't stutter short words (<=3) or words starting with w (looks weird)
            if len(word) > 3 and not word.startswith("w") and random.random() < 0.30:
                stutter = f"{word[0]}-"
                word = stutter + word

            # C. Apply clean suffixes logic (10% chance)
            # Only if word is long enough and doesn't already end in a vowel-like sound
            if len(word) > 4 and random.random() < 0.10:
                word = word.rstrip("s") + random.choice(CLEAN_SUFFIXES)

        transformed_words.append(word)

        # 6. Insert Interactive Action (After 3-6 words, 15% chance)
        # We ensure it doesn't happen at the very start
        if (i % random.randint(3, 6) == 0 and i > 0) and random.random() < 0.15:
            transformed_words.append(random.choice(INTERACTIVE_ACTIONS))

    text = " ".join(transformed_words)

    # 7. Final Polish
    if text:
        # Capitalize the first letter for readability
        text = text[0].upper() + text[1:]

    # Remove excessive whitespace and append final slop
    return text.strip() + random.choice(CLEAN_FINAL_SLOP)


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
