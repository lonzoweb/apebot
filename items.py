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
        "cost": 900,
        "duration_sec": 1800,  # 30 mins
        "type": "curse",
        "feedback": "🤐 Muzzle applied. They cannot speak or use commands!",
    },
    "uwu": {
        "cost": 400,
        "duration_sec": 600,  # 10 mins
        "type": "curse",
        "feedback": "🎀 Dawww~",
    },
    "echo_ward": {
        "cost": 500,
        "type": "defense",
        "feedback": "🛡️ Echo Ward added to inventory. Automatically reversing the next hex!",
    },
    "kush_pack": {
        "cost": 60,
        "type": "fun",
        "feedback": "Sparking Apeiron Kush Pack. Shields active.",
    },
    "ping_everyone": {
        "cost": 700,
        "type": "broadcast",
        "feedback": "📡 PING SENT",
    },
    "npass": {
        "cost": 2500,
        "type": "role_grant",
        "role_id": 1168965931918176297,
        "feedback": "🎫 Nigga pass obtained! Real freedom of speech.",
    },
    "rain": {
        "cost": 1100,
        "type": "event",
        "feedback": "🌧️ **TOKEN RAIN!** The next 10 unique users to talk in this channel will earn 50 bonus tokens!",
    },
    "hot_potato": {
        "cost": 520,
        "type": "event",
        "feedback": "🥔🔥 **HOT POTATO!** A ticking muzzle is loose in the chat! Talk to pass it. Every pass earns you 15 tokens!",
    },
    "feast": {
        "cost": 330,
        "type": "event",
        "feedback": "🍗🧛 **CRAZED FEAST!** You begin feasting upon the sleeping members of the chat...\n💡 *To block attacks, you must speak in this channel!*",
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
    "everyone": "ping_everyone",
    "ping": "ping_everyone",
    "broadcast": "ping_everyone",
    "npass": "npass",
    "n-pass": "npass",
    "pass": "npass",
    "rain": "rain",
    "token_rain": "rain",
    "hot_potato": "hot_potato",
    "potato": "hot_potato",
    "feast": "feast",
}

# ============================================================
# TRANSFORMATION LOGIC
# ============================================================

CLEAN_FINAL_SLOP = [
    " *runs away*",
    " *snuggles you*",
    " *gets on their knees*",
    " *blushes*",
    " *kisses your cheek*",
    " *teehee*",
    " *snuggles*",
    " *bops your nose*",
]

# Word overrides for smoother reading
UWU_WORD_MAP = {
    # Core uwu exceptions
    "you": "yuw",
    "your": "yuw",
    "you're": "yuw",
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
    # Common words that need smooth handling
    "please": "pwease",
    "sorry": "sowwy",
    "very": "vewy",
    "really": "weawwy",
    "little": "wittwe",
    "people": "peopwe",
    "think": "fink",
    "this": "dis",
    "that": "dat",
    "there": "dere",
    "their": "dere",
    "they're": "deyre",
    # Cute overrides
    "yes": "yesh",
    "now": "nyow",
    "know": "knyow",
    "hi": "haiii",
    "hello": "hewwo",
    "thanks": "thxxx",
}

INTERACTIVE_ACTIONS = [
    " ***boops your nose***",
    " ***blushes***",
    " ***whispers to self***",
    " ***giggles***",
    " ***pouts***",
    " ***runs away***",
    " ***glomps and huggles***",
    " ***kisses your cheek***",
    " ***omg im coming***",
]

KAOMOJI_POOL = [
    " **(ᵘﻌᵘ)**",
    " **(｡ᴜ‿‿ᴜ｡)**",
    " **:･ﾟ✧(ꈍᴗꈍ)✧･ﾟ:**",
    " **( ͡o ꒳ ͡o )**",
    " **(◕‿◕✿)**",
    " **UwU**",
    " **owo**",
    " **>w<**",
    " **^w^**",
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

    # 1. LINK/MEDIA PURGE (ENHANCED)
    # Remove URLs (http/https)
    text = re.sub(r"https?://[^\s]+", "", text)

    # Remove Discord-specific: emojis, mentions, channels, roles
    text = re.sub(r"<a?:[^:]+:\d+>", "", text)  # Custom emojis
    text = re.sub(r"@\w+", "", text)  # @mentions (simple)
    text = re.sub(r"<@!?\d+>", "", text)  # User mentions (full)
    text = re.sub(r"<@&\d+>", "", text)  # Role mentions
    text = re.sub(r"<#\d+>", "", text)  # Channel links

    # Remove common image/gif hosts and file extensions
    text = re.sub(r"(tenor|giphy|imgur|cdn\.discordapp)\.[^\s]+", "", text)
    text = re.sub(r"\.(gif|png|jpg|jpeg|webp|mp4)[^\s]*", "", text, flags=re.IGNORECASE)

    if not text.strip():
        # User requested silent deletion for emoji/link only messages
        return ""

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
            # B. Enhanced Stuttering (30% chance, 1-3 character repetitions)
            if len(word) > 3 and not word.startswith("w") and random.random() < 0.30:
                stutter_count = random.choice([1, 2, 3])
                stutter = "-".join([word[0]] * stutter_count) + "-"
                word = stutter + word

            # C. Elongation (Randomly extend vowels or 'y') - 35% Chance
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

        # 5. Insert Kaomoji (15% chance after each word)
        if random.random() < 0.15:
            transformed_words.append(random.choice(KAOMOJI_POOL))

        # 6. Insert Interactive Action (increased frequency)
        if (i % random.randint(3, 5) == 0 and i > 0) and random.random() < 0.25:
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
