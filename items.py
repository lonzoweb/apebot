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
        "shop_desc": "Silences a target for 30 minutes. No words, no commands.",
        "feedback": "🤐 Muzzle applied. Target cannot speak or use commands for 30m",
    },
    "uwu": {
        "cost": 400,
        "duration_sec": 600,  # 10 mins
        "type": "curse",
        "shop_desc": "Forces target to speak in uwu-speak for 10 minutes.",
        "feedback": "🎀 Dawww~, cute for 10m",
    },
    "echo_ward": {
        "cost": 500,
        "type": "defense",
        "shop_desc": "Blocks the next curse/hex directed at you. One-time use.",
        "feedback": "🛡️ Echo Ward added to inventory. Blocks next hex on you.",
    },
    "echo_ward_max": {
        "cost": 700,
        "type": "defense",
        "shop_desc": "Reflects the next curse back at the sender. One-time use.",
        "feedback": "🔮 **ECHO WARD MAX!** Reverses the next hex back at the sender!",
    },
    "kush_pack": {
        "cost": 60,
        "type": "fun",
        "shop_desc": "OG APEIRON KUSH WITH AUTO SHIELD.",
        "feedback": "Sparking Apeiron Kush Pack. Shields active.",
    },
    "ping_everyone": {
        "cost": 2400,
        "type": "broadcast",
        "shop_desc": "Pings @everyone with your message. 24h cooldown.",
        "feedback": "📡 Global Apeiron Ping. 24h cooldown.",
    },
    "npass": {
        "cost": 2500,
        "type": "role_grant",
        "role_id": 1168965931918176297,
        "shop_desc": "Grants the N-Pass role. Freedom of speech.",
        "feedback": "🎫 Nigga pass obtained! Real freedom of speech.",
    },
    "storm": {
        "cost": 1100,
        "type": "event",
        "shop_desc": "Triggers a Token Storm. Next 10 speakers get bonus tokens.",
        "feedback": "⛈️ **TOKEN STORM!** The next 10 unique users to talk in this channel earn 50 bonus tokens!",
    },
    "luck_curse": {
        "cost": 7,
        "type": "buff",
        "restricted": True,
        "hidden": True,
        "shop_desc": "You are cursed with good luck. 50% increased earnings for 24 hours.",
        "feedback": "✨ **LUCK CURSE ACTIVATED.** Enjoy your heightened fortune for 24h. Earnings +50%.",
    },
    "hot_potato": {
        "cost": 520,
        "type": "event",
        "shop_desc": "Spawns a Hot Potato. Holder explodes (muzzled) after 3m.",
        "feedback": "🥔🔥 **HOT POTATO!** A ticking muzzle is loose in the chat! Talk to pass it. Every pass earns you 15 tokens!",
    },
    "black_mirror": {
        "cost": 3000,
        "type": "defense",
        "shop_desc": "Ancient obsidian. Intercepts and reflects 5 licks/curses before shattering. (Multi-use Ward Max)",
        "feedback": "🪞 **BLACK MIRROR SECURED.** Your essence is guarded by 5 layers of obsidian reflection.",
    },
    "blood_altar": {
        "cost": 9000,
        "type": "event",
        "shop_desc": "Initiate the Blood Moon. 1 hour of doubled earnings for all, but robbery is forbidden.",
        "feedback": "🩸 **THE ALTAR IS PREPARED.** A sacrifice has been made. The Blood Moon rises for 1 hour!",
    },
    "feast": {
        "cost": 250,
        "type": "event",
        "shop_desc": "Starts a Crazed Feast. Steal tokens from inactive chatters.",
        "feedback": "🍗🧛 **CRAZED FEAST!** You begin feasting upon the sleeping members of the chat...\n💡 *Speak in chat to block attacks.*",
    },
    "the_reaping": {
        "cost": 3000,
        "type": "event",
        "shop_desc": "Initiate The Reaping. 30min casino tax event. 4% tithe per game, players get paid.",
        "feedback": "🌾 **REAPING IN SESSION**\n\nT.\nAll players pay their tithes.\n\nDuration: 30 minutes",
    },
    "night_vision": {
        "cost": 200,
        "type": "protection",
        "shop_desc": "5-hour overnight shield. Blocks theft but prevents all token gains.",
        "feedback": "🌙 **NIGHT VISION ACTIVATED.**\n\nProtecting your assets until you awaken.\n\n*The void watches its own.*",
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
    "echo ward": "echo_ward",
    "maxward": "echo_ward_max",
    "echomax": "echo_ward_max",
    "mirror": "echo_ward_max",
    "max_ward": "echo_ward_max",
    "ward max": "echo_ward_max",
    "echo max": "echo_ward_max",
    "eco max": "echo_ward_max",
    "echo ward max": "echo_ward_max",
    "black_mirror": "black_mirror",
    "black mirror": "black_mirror",
    "obsidian": "black_mirror",
    "altar": "blood_altar",
    "blood_altar": "blood_altar",
    "blood altar": "blood_altar",
    "sacrifice": "blood_altar",
    "kush": "kush_pack",
    "weed": "kush_pack",
    "pack": "kush_pack",
    "everyone": "ping_everyone",
    "ping": "ping_everyone",
    "broadcast": "ping_everyone",
    "npass": "npass",
    "n-pass": "npass",
    "pass": "npass",
    "storm": "storm",
    "token_storm": "storm",
    "token storm": "storm",
    "luck_curse": "luck_curse",
    "luck": "luck_curse",
    "blessing": "luck_curse",
    "hot_potato": "hot_potato",
    "hot potato": "hot_potato",
    "potato": "hot_potato",
    "feast": "feast",
    "the_reaping": "the_reaping",
    "reaping": "the_reaping",
    "harvest": "the_reaping",
    "night_vision": "night_vision",
    "night vision": "night_vision",
    "nv": "night_vision",
    "sleep": "night_vision",
    "night": "night_vision",
    "vision": "night_vision",
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
