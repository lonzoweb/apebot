"""
Items and Text Transformations for Discord Bot
Handles obnoxious UwU logic and Shop item definitions
"""

import random
import re
import unicodedata  # <--- REQUIRED FOR FONT NORMALIZATION

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

# Word overrides for smoother reading
UWU_WORD_MAP = {
    "you": "yuw",
    "have": "haz",
    "are": "r",
    "love": "wuv",
    "the": "da",
    "with": "wif",
    "what": "wat",
    "no": "nyo",
    "oh": "owh",
    "is": "iz",
    "to": "two",
}

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
    Transforms text into a readable, high-quality UWU style.
    Includes ANTI-CIRCUMVENTION logic to decode 'fancy fonts'.
    """
    if not text:
        return "..."

    # 0. ANTI-CIRCUMVENTION (UNICODE NORMALIZATION)
    # This converts "𝐇𝐞𝐥𝐥𝐨", "𝘏𝘦𝘭𝘭𝘰", "𝐻𝑒𝑙𝑙𝑜" etc. back to standard "Hello"
    # NFKC = Normalization Form Compatibility Composition
    text = unicodedata.normalize("NFKC", text)

    # 1. LINK/MEDIA PURGE
    text = re.sub(r"https?://[^\s]+", "", text)
    text = re.sub(r"<a?:[^:]+:\d+>|@\w+|#\w+|@&[0-9]+|<#[0-9]+>", "", text)

    if not text.strip():
        return random.choice(CLEAN_FINAL_SLOP)

    # 2. Standardize
    text = text.lower()

    # 3. Nya-fication
    text = re.sub(r"n([aeiou])", r"ny\1", text)

    # 4. Fundamental Letter Swaps
    text = text.replace("l", "w").replace("r", "w")

    words = text.split()
    transformed_words = []

    for i, word in enumerate(words):
        clean_word = word.strip(".,!?")

        # A. Check Dictionary Overrides
        if clean_word in UWU_WORD_MAP:
            word = UWU_WORD_MAP[clean_word]

        else:
            # B. Stuttering (30% chance)
            if len(word) > 3 and not word.startswith("w") and random.random() < 0.30:
                stutter = f"{word[0]}-"
                word = stutter + word

            # C. Elongation (Randomly extend vowels or 'y') - 15% Chance
            elif len(word) > 3 and random.random() < 0.35:
                vowels = [i for i, char in enumerate(word) if char in "aeiouy"]
                if vowels:
                    target_index = vowels[-1]
                    char_to_extend = word[target_index]
                    # Extend 2 to 4 times
                    extension = char_to_extend * random.randint(2, 4)
                    word = word[:target_index] + extension + word[target_index:]

            # D. Suffixes (10% chance)
            elif len(word) > 4 and random.random() < 0.30:
                word = word.rstrip("s") + random.choice(CLEAN_SUFFIXES)

        transformed_words.append(word)

        # 5. Insert Interactive Action
        if (i % random.randint(3, 6) == 0 and i > 0) and random.random() < 0.35:
            transformed_words.append(random.choice(INTERACTIVE_ACTIONS))

    text = " ".join(transformed_words)

    if text:
        text = text[0].upper() + text[1:]

    return text.strip() + random.choice(CLEAN_FINAL_SLOP)


# ============================================================
# UTILITIES
# ============================================================


def extract_gif_url(message):
    """
    Checks if a message contains a GIF via attachment or URL.
    """
    if message.attachments:
        for anim in message.attachments:
            if anim.content_type and "gif" in anim.content_type:
                return anim.url

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
