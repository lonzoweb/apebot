import random
import discord
import os
import asyncio
import logging

# ============================================================
# TAROT DECK DATA - Milo Manara Erotic Tarot
# ============================================================

TAROT_DECK = {
    # MAJOR ARCANA (0-21)
    "00-the-fool": {
        "name": "The Fool",
        "emojis": "🃏 🌀 🪄 ✨ 🌈",
        "attribution": "Uranus",
        "att2": "Unexpected, brutal or revolutionary change.",
        "description": "Magic, wonder, amazement, desire, surprise.",
    },
    "01-the-magician": {
        "name": "The Magician",
        "emojis": "🪄 🧠 📜 ⚡ 🛠️",
        "attribution": "Mercury",
        "att2": "Communication, mental planning, nervous reactions.",
        "description": "Inventiveness, intelligence, purpose, constancy, mental resources.",
    },
    "02-the-priestess": {
        "name": "The Priestess",
        "emojis": "🌙 📖 🗝️ 🔮 🌊",
        "attribution": "The Moon",
        "att2": "Fluctuation, emotionalism, reactivity.",
        "description": "Secrecy, mystery, knowledge, hidden treasure, virginity.",
    },
    "03-the-empress": {
        "name": "The Empress",
        "emojis": "♀️ 👑 🌸 💎 ✨",
        "attribution": "Venus",
        "att2": "Harmony, love, beauty.",
        "description": "Commanding personality, sincerity, fertility, power.",
    },
    "04-the-emperor": {
        "name": "The Emperor",
        "emojis": "♈ 👑 ⚔️ 🛡️ 🏛️",
        "attribution": "Aries",
        "att2": "I am, authority.",
        "description": "Security, authority, order, dignity, fecundity.",
    },
    "05-the-high-priest": {
        "name": "The High Priest",
        "emojis": "♉ 🐘 📜 📿 🏛️",
        "attribution": "Taurus",
        "att2": "I have, possessiveness, tenacity.",
        "description": "Temptation, formality, external appearances, hierarchy, experience.",
    },
    "06-the-lovers": {
        "name": "The Lovers",
        "emojis": "♊ 💞 💘 🔗 🤝",
        "attribution": "Gemini",
        "att2": "I think, communicative.",
        "description": "Emotion, empathy, choice, connection, affection, generosity.",
    },
    "07-the-chariot": {
        "name": "The Chariot",
        "emojis": "♋ 🏎️ 🏁 🛡️ 🏆",
        "attribution": "Cancer",
        "att2": "I feel, protectiveness, prudence.",
        "description": "Triumph, vanity, self advertisement, arrogance, conquest.",
    },
    "08-justice": {
        "name": "Justice",
        "emojis": "♌ ⚖️ 🗡️ 📜 🦁",
        "attribution": "Leo",
        "att2": "I want, creativity, joyfulness.",
        "description": "Sobriety, fairness, detachment, duty, responsibility, impartiality.",
    },
    "09-the-hermit": {
        "name": "The Hermit",
        "emojis": "♍ 🕯️ 🧘 📖 🏔️",
        "attribution": "Virgo",
        "att2": "I analyse, ability to see details, critical.",
        "description": "Solitude, meditation, contemplation, research, isolation.",
    },
    "10-the-mirror": {
        "name": "The Mirror",
        "emojis": "♃ 🪞 🌀 🎭 ✨",
        "attribution": "Jupiter",
        "att2": "Expansion, optimism, conservation.",
        "description": "Reflection, imagination, cyclic behaviour, uniformity.",
    },
    "11-strength": {
        "name": "Strength",
        "emojis": "♎ 💪 🛡️ ⚖️ 🦁",
        "attribution": "Libra",
        "att2": "I balance, harmony, union.",
        "description": "Power, vigour, courage, virtue, triumph over brutality, ambition.",
    },
    "12-the-punishment": {
        "name": "The Punishment",
        "emojis": "♆ ⚠️ ⛓️ 🩸 🌩️",
        "attribution": "Neptune",
        "att2": "Nebulous, impressionability, inspiration.",
        "description": "Sacrifice, ordeal, punishment, pain, contrasting point of view.",
    },
    "13-death": {
        "name": "Death",
        "emojis": "♏ 💀 🦋 🌑 ⚡",
        "attribution": "Scorpio",
        "att2": "I want, ability to penetrate, passion, secretiveness.",
        "description": "Transformation, change, the unexpected, obsession.",
    },
    "14-temperance": {
        "name": "Temperance",
        "emojis": "♐ 🏺 🌈 🕊️ 🌿",
        "attribution": "Sagittarius",
        "att2": "I aspire, generosity, depth, philosophy.",
        "description": "Balance, peace, care, healing.",
    },
    "15-the-devil": {
        "name": "The Devil",
        "emojis": "♑ 😈 🔥 🔗 💎",
        "attribution": "Capricorn",
        "att2": "I use, prudence, aspiration.",
        "description": "Excess, passion, luxury, possession, jealousy.",
    },
    "16-the-tower": {
        "name": "The Tower",
        "emojis": "♂️ 🗼 ⚡ 📉 💥",
        "attribution": "Mars",
        "att2": "Energy, warmth, setting in motion.",
        "description": "Morality, scheming, rigid thinking, refuge, prison.",
    },
    "17-the-stars": {
        "name": "The Stars",
        "emojis": "♒ ⭐ 💃 ✨ 🌀",
        "attribution": "Aquarius",
        "att2": "Detachment, scientific attitude, coldness.",
        "description": "Beauty, dance, enthusiasm, purity, enchantment.",
    },
    "18-the-moon": {
        "name": "The Moon",
        "emojis": "♓ 🌙 🌫️ 🐺 🌊",
        "attribution": "Pisces",
        "att2": "I believe, haziness, inspiration, confusion.",
        "description": "Imagination, whispering and things left unsaid, infatuation.",
    },
    "19-the-sun": {
        "name": "The Sun",
        "emojis": "☀️ 🌞 ✨ 🌻 🌈",
        "attribution": "The Sun",
        "att2": "Power, vitality, self expression.",
        "description": "Life, desire, freedom, arrogance, clarity, direction.",
    },
    "20-judgement": {
        "name": "Judgement",
        "emojis": "♇ 🎺 🌟 🕊️ 🌅",
        "attribution": "Pluto",
        "att2": "Renewal, regeneration, elimination.",
        "description": "Resurrection, annunciation, spirit, climax.",
    },
    "21-the-world": {
        "name": "The World",
        "emojis": "♄ 🌍 💃 👑 🏆",
        "attribution": "Saturn",
        "att2": "Limitation, constriction, firmness.",
        "description": "Totality, invincibility, success.",
    },
    # WATER SUIT (Imagination)
    "water-01": {
        "name": "Ace of Water",
        "emojis": "🌊 🏺 💖 ✨ ♾️",
        "attribution": "Element of Water",
        "att2": "Emotional states of awareness",
        "description": "Sensuality, falling in love, a never ending stream.",
    },
    "water-02": {
        "name": "Two of Water",
        "emojis": "🌊 💞 🐚 🌅 🤫",
        "attribution": "Venus in Cancer",
        "att2": "The need to dominate and manipulate money with care, in a personal and even an egoistic manner",
        "description": "The Idyll, romantic passion, the present moment.",
    },
    "water-03": {
        "name": "Three of Water",
        "emojis": "🌊 💬 🗣️ 🕊️ 🌈",
        "attribution": "Mercury in Cancer",
        "att2": "The need to communicate in a careful and personal manner",
        "description": "Declaration, freedom, free expression of personal feelings.",
    },
    "water-04": {
        "name": "Four of Water",
        "emojis": "🌊 🙈 🤐 🏠 🛡️",
        "attribution": "The Moon in Cancer",
        "att2": "The need to effect change in a careful and dictatorial manner",
        "description": "Rejection, shyness, diffidence, fear of one's own feelings.",
    },
    "water-05": {
        "name": "Five of Water",
        "emojis": "🌊 🛡️ 🏃 🌫️ 🌑",
        "attribution": "Mars in Scorpio",
        "att2": "The need to struggle, to evolve or fight intensely, secretly",
        "description": "Fear, avoidance of facing unpleasant events, reassurance.",
    },
    "water-06": {
        "name": "Six of Water",
        "emojis": "🌊 😌 🧠 🎐 🌿",
        "attribution": "The Sun in Scorpio",
        "att2": "The need to live secretively, intensely, passionately",
        "description": "Simplicity, intelligence, serenity.",
    },
    "water-07": {
        "name": "Seven of Water",
        "emojis": "🌊 🌀 🦄 ⚠️ 🎭",
        "attribution": "Venus in Scorpio",
        "att2": "The need to love ardently and secretly",
        "description": "Imagination, whimsy, intangible danger.",
    },
    "water-08": {
        "name": "Eight of Water",
        "emojis": "🌊 🛑 🧘 ⚓ 🏔️",
        "attribution": "Saturn in Pisces",
        "att2": "The need to focus and consolidate in an inspired way, idealistic, subtle.",
        "description": "Renunciation, responsibility, reversal of a mistaken path.",
    },
    "water-09": {
        "name": "Nine of Water",
        "emojis": "🌊 🍬 🏆 ✨ 💃",
        "attribution": "Jupiter in Pisces",
        "att2": "The need to evolve oneself by following one's own inspiration, in a nebulous and subtle way",
        "description": "Well-being, repletion, satisfaction, exhibitionism.",
    },
    "water-10": {
        "name": "Ten of Water",
        "emojis": "🌊 💎 🤝 🌅 🎭",
        "attribution": "Mars in Pisces",
        "att2": "The need to struggle, to evolve, to fight in a detached, indifferent and scientific way",
        "description": "Faithfulness, the perfection of a situation, harmony, purification.",
    },
    "water-knave": {
        "name": "Knave of Water",
        "emojis": "🌊 📮 🚢 🧢 🛤️",
        "attribution": "Beginning of summer",
        "att2": "",
        "description": "Messenger, Prince Charming, travel companion.",
    },
    "water-knight": {
        "name": "Knight of Water",
        "emojis": "🌊 🕊️ 🛡️ 🦢 🏰",
        "attribution": "Pisces",
        "att2": "Understanding, gentleness, kindness, hyper-sensitivity",
        "description": "Mystic, knight errant, purity, chastity.",
    },
    "water-queen": {
        "name": "Queen of Water",
        "emojis": "🌊 👑 💞 🔮 ✨",
        "attribution": "Cancer",
        "att2": "Lunatic, emotional, receptive",
        "description": "Lover, a faithful friend, honesty, apparition, clairvoyance, sensitivity.",
    },
    "water-king": {
        "name": "King of Water",
        "emojis": "🌊 👑 🔱 🌊 😏",
        "attribution": "Scorpio",
        "att2": "Rigidity, perspicacity, a suspicious nature, sceptical",
        "description": "Seducer, invitation, creation, strength, superficiality.",
    },
    # EARTH SUIT (Instinct)
    "earth-01": {
        "name": "Ace of Earth",
        "emojis": "🌍 💎 ✨ ♾️ 🌱",
        "attribution": "Earth element",
        "att2": "Productive and imaginative states of consciousness.",
        "description": "Magnetism, ecstasy, success, perfection.",
    },
    "earth-02": {
        "name": "Two of Earth",
        "emojis": "🌍 🃏 😂 🎭 🔄",
        "attribution": "Jupiter in Capricorn",
        "att2": "The need to develop the self ambitiously and coldly.",
        "description": "Excitement, playfulness, enjoyment, harmless jokes.",
    },
    "earth-03": {
        "name": "Three of Earth",
        "emojis": "🌍 🛠️ 🌟 🏗️ 🏆",
        "attribution": "Mars in Capricorn",
        "att2": "The need to struggle, evolve or fight in cold blood, ambitiously and with cruelty.",
        "description": "Skill, great ability, celebrity, material objects.",
    },
    "earth-04": {
        "name": "Four of Earth",
        "emojis": "🌍 💰 🏰 🛡️ 🕰️",
        "attribution": "The Sun in Capricorn",
        "att2": "The need to live intensely, in an ambitious manner.",
        "description": "Avidity, luxury, thrift, egoism.",
    },
    "earth-05": {
        "name": "Five of Earth",
        "emojis": "🌍 📉 🛑 🧱 😰",
        "attribution": "Mercury in Taurus",
        "att2": "The need to communicate in a lasting and possessive manner.",
        "description": "Difficulty, lack, no way out, resignation.",
    },
    "earth-06": {
        "name": "Six of Earth",
        "emojis": "🌍 ⚖️ 🤝 🎁✨",
        "attribution": "The Moon in Taurus",
        "att2": "The need to bring about lasting, possessive change.",
        "description": "Gifts, fairness, the just distribution of goods, balance, generosity.",
    },
    "earth-07": {
        "name": "Seven of Earth",
        "emojis": "🌍 💼 🔄 🍇 💰",
        "attribution": "Saturn in Taurus",
        "att2": "The need to focus or consolidate in a continuous and possessive manner.",
        "description": "Business, transaction, the fruit of one's own work, exchange.",
    },
    "earth-08": {
        "name": "Eight of Earth",
        "emojis": "🌍 🎨 🛠️ 🧵 📖",
        "attribution": "The Sun in Virgo",
        "att2": "The need to live in a critical and artistic way, with a love for detail.",
        "description": "Manual ability, commitment, dedication, unique gift.",
    },
    "earth-09": {
        "name": "Nine of Earth",
        "emojis": "🌍 🌿 💎 🥂 ✨",
        "attribution": "Venus in Virgo",
        "att2": "The need to love critically and partially, to manipulate money carefully and with attention to detail, often critically.",
        "description": "Wellbeing, material security, superiority, serenity.",
    },
    "earth-10": {
        "name": "Ten of Earth",
        "emojis": "🌍 🏛️ 💹 🪙 📜",
        "attribution": "Mercury in Virgo",
        "att2": "To need for critical and detailed communication.",
        "description": "Comfort, inheritance, income.",
    },
    "earth-knave": {
        "name": "Knave of Earth",
        "emojis": "🌍 🎓 📖 💡 🔍",
        "attribution": "Beginning of winter",
        "att2": "",
        "description": "A student, application, curiosity, the desire to learn.",
    },
    "earth-knight": {
        "name": "Knight of Earth",
        "emojis": "🌍 🛡️ 💼 ⚖️ 🕰️",
        "attribution": "Virgo",
        "att2": "Discernment, method, seriousness.",
        "description": "A professional person, serious, careful and responsible help.",
    },
    "earth-queen": {
        "name": "Queen of Earth",
        "emojis": "🌍 👑 💎 🍑 ✨",
        "attribution": "Capricorn",
        "att2": "Diplomacy, industriousness, concentration.",
        "description": "An heiress, opulence, magnificence, carnality.",
    },
    "earth-king": {
        "name": "King of Earth",
        "emojis": "🌍 👑 💼 🏛️ 💰",
        "attribution": "Taurus",
        "att2": "Determination, independence, stability.",
        "description": "A tradesman, human ambition, practical intelligence, success.",
    },
    # FIRE SUIT (Ardour)
    "fire-01": {
        "name": "Ace of Fire",
        "emojis": "🔥 ⚡ ✨ 💥 🚀",
        "attribution": "Element of Fire",
        "att2": "Restlessness and impulsiveness.",
        "description": "Passion, creation, the starting point, budding.",
    },
    "fire-02": {
        "name": "Two of Fire",
        "emojis": "🔥 😐 🌫️ 🛑 💭",
        "attribution": "Mars in Aries",
        "att2": "The need to struggle, to evolve and fight in an authoritative way.",
        "description": "Uncertainty, lack of stimuli or positive outlook despite of possibilities, frustration.",
    },
    "fire-03": {
        "name": "Three of Fire",
        "emojis": "🔥 🔭 🧭 🏃 🌄",
        "attribution": "The Sun in Aries",
        "att2": "Impulsive, lives assertively:",
        "description": "Exploration, discovery, taking the initiative.",
    },
    "fire-04": {
        "name": "Four of Fire",
        "emojis": "🔥 🤝 🌸 🏠 💞",
        "attribution": "Venus in Aries",
        "att2": "The need to love or manipulate money with authority.",
        "description": "Agreement, harmony, intimacy.",
    },
    "fire-05": {
        "name": "Five of Fire",
        "emojis": "🔥 ⚔️ 🏋️ 🤺 🏫",
        "attribution": "Saturn in Leo",
        "att2": "The need to focus and consolidate in an artistic manner.",
        "description": "Training, preparation, simulation.",
    },
    "fire-06": {
        "name": "Six of Fire",
        "emojis": "🔥 🎖️  sugger ⚔️ ✨",
        "attribution": "Jupiter in Leo",
        "att2": "The need to develop in a joyful, creative and pleasant manner.",
        "description": "Sign of honour, suggestion, rivalry.",
    },
    "fire-07": {
        "name": "Seven of Fire",
        "emojis": "🔥 ⚔️ 🛡️ 🦍 🌩️",
        "attribution": "Mars in Leo",
        "att2": "The need to grow and evolve, to struggle demonstratively, joyful, imaginative.",
        "description": "Struggle, challenge, argumentation, facing up to enemies who are stronger.",
    },
    "fire-08": {
        "name": "Eight of Fire",
        "emojis": "🔥 🏹 🎯 ⚡ 🌅",
        "attribution": "Mercury in Sagittarius",
        "att2": "The need to communicate openly and freely in an demonstrative way.",
        "description": "Climax, straining towards a goal, movement.",
    },
    "fire-09": {
        "name": "Nine of Fire",
        "emojis": "🔥 👁️ 🛡️ ⚖️ 🕰️",
        "attribution": "The Moon in Sagittarius",
        "att2": "The need to feel free and unencumbered when dealing with changes.",
        "description": "Vigilance, defence, limit, attention.",
    },
    "fire-10": {
        "name": "Ten of Fire",
        "emojis": "🔥 🏋️ 😵 🛡️ 🎭",
        "attribution": "Saturn in Sagittarius",
        "att2": "The need to focus and consolidate freely, on various different levels, openly.",
        "description": "Oppression, duplicity, fatigue, burden.",
    },
    "fire-knave": {
        "name": "Knave of Fire",
        "emojis": "🔥 🤝 💞 ⚡ 🛤️",
        "attribution": "Beginning of spring",
        "att2": "",
        "description": "Companion, lover, help.",
    },
    "fire-knight": {
        "name": "Knight of Fire",
        "emojis": "🔥 🐎 🗺️ 🔭 ✨",
        "attribution": "Sagittarius",
        "att2": "Joviality, generosity, optimism, ambition.",
        "description": "Traveller, departure, absence, distance, adventure.",
    },
    "fire-queen": {
        "name": "Queen of Fire",
        "emojis": "🔥 👑 🍑 🔞 ⚡",
        "attribution": "Aries",
        "att2": "Abundance of energy, restlessness, perspicacity.",
        "description": "Wife, sex, desire, provocation, disturbance.",
    },
    "fire-king": {
        "name": "King of Fire",
        "emojis": "🔥 👑 🧙 🧪 ✨",
        "attribution": "Leo",
        "att2": "Resoluteness, perseverance, independence.",
        "description": "Shaman, enchanter, inventor, experience.",
    },
    # AIR SUIT (Seduction)
    "air-01": {
        "name": "Ace of Air",
        "emojis": "🌬️ 🧠 ✨ 💡 🌫️",
        "attribution": "Element of Air",
        "att2": "Intellectual states of consciousness.",
        "description": "Beauty, thought, exaltation of the senses.",
    },
    "air-02": {
        "name": "Two of Air",
        "emojis": "🌬️ ⚖️ 🤔 🤝 ☁️",
        "attribution": "The Moon in Libra",
        "att2": "The need to bring about change in a harmonious, united and sociable way.",
        "description": "Choice, balance, ideas.",
    },
    "air-03": {
        "name": "Three of Air",
        "emojis": "🌬️ 🥶 🌪️ ⏳ 🌫️",
        "attribution": "Saturn in Libra",
        "att2": "The need to focus and consolidate harmoniously.",
        "description": "Coldness, wind, turbulence, waiting.",
    },
    "air-04": {
        "name": "Four of Air",
        "emojis": "🌬️ 🧘 💭 👀 🏔️",
        "attribution": "Jupiter in Libra",
        "att2": "The need to develop harmoniously.",
        "description": "Wakefulness, meditation, reflection, unreachable.",
    },
    "air-05": {
        "name": "Five of Air",
        "emojis": "🌬️ 🚶 📉 🛑 😞",
        "attribution": "Venus in Aquarius",
        "att2": "The need to love with detachment and to face economic questions in a scientific and calculating manner.",
        "description": "Exile, defeat, lack of dignity, obstacles which get in the way, regret.",
    },
    "air-06": {
        "name": "Six of Air",
        "emojis": "🌬️ 🔍 🗺️ 🚢 ✨",
        "attribution": "Mercury in Aquarius",
        "att2": "The need to communicate in a scientific and detached way.",
        "description": "Curiosity, travel, the challenge of the unknown.",
    },
    "air-07": {
        "name": "Seven of Air",
        "emojis": "🌬️ 🕵️ 🎣 🤫 🌫️",
        "attribution": "The Moon in Aquarius",
        "att2": "The need to bring about change in a scientific and detached way.",
        "description": "Expediency, a hidden plan, actions carried out in secret, the bait, distraction.",
    },
    "air-08": {
        "name": "Eight of Air",
        "emojis": "🌬️ 🕸️ ⛓️ 📰 ⚠️",
        "attribution": "Jupiter in Gemini",
        "att2": "The need to develop oneself mentally and communicatively.",
        "description": "Traps, bad news, obstacles to which one reacts.",
    },
    "air-09": {
        "name": "Nine of Air",
        "emojis": "🌬️ 🌀 💭 🌑 ⚡",
        "attribution": "Mars in Gemini",
        "att2": "The need to struggle and evolve or fight in a communicative and mental way.",
        "description": "Dreams, wonder, strange mental states, danger.",
    },
    "air-10": {
        "name": "Ten of Air",
        "emojis": "🌬️ 💧 😞 🏚️ 🏗️",
        "attribution": "The Sun in Gemini",
        "att2": "The need to live communicatively.",
        "description": "Tears, desolation, emptiness, research, incompleteness.",
    },
    "air-knave": {
        "name": "Knave of Air",
        "emojis": "🌬️ 🧠 ✨ 🎐 🛤️",
        "attribution": "Beginning of autumn",
        "att2": "",
        "description": "Helper, the source of inspiration, attention and grace.",
    },
    "air-knight": {
        "name": "Knight of Air",
        "emojis": "🌬️ ⚔️ 💪 🛡️ 💞",
        "attribution": "Gemini",
        "att2": "Affection, kindness, a good heart.",
        "description": "Warrior, courage, valour, authority, strength.",
    },
    "air-queen": {
        "name": "Queen of Air",
        "emojis": "🌬️ 👑 💋 🔗 🎭",
        "attribution": "Libra",
        "att2": "Pleasure, grace, rectitude.",
        "description": "Fiancée, provocation, seduction, jealousy, capriccio.",
    },
    "air-king": {
        "name": "King of Air",
        "emojis": "🌬️ 👑 🏛️ ⚖️ ⚡",
        "attribution": "Aquarius",
        "att2": "Agitation, impatience, determination.",
        "description": "Father, power, charisma, order, decision, responsibility, supervision.",
    },
}

logger = logging.getLogger(__name__)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_image_path(card_key):
    """Get the file path for a card image"""
    return os.path.join("images", "manara", f"{card_key}.jpg")

def draw_card():
    """Draw a random card"""
    card_key = random.choice(list(TAROT_DECK.keys()))
    return card_key

async def read_card_image(card_key):
    """Reads the image file in a separate thread pool."""
    image_path = get_image_path(card_key)
    loop = asyncio.get_event_loop()

    def blocking_file_op():
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Manara image not found at: {image_path}")
        return discord.File(image_path, filename=f"{card_key}.jpg")

    return await loop.run_in_executor(None, blocking_file_op)

async def send_tarot_card(ctx, card_key=None):
    """Send a tarot card to Discord channel"""
    if card_key is None:
        card_key = draw_card()

    card = TAROT_DECK[card_key]
    card_name = card["name"]
    emojis = card["emojis"]
    attribution = card["attribution"]
    description = card["description"]
    att2 = card["att2"]

    embed = discord.Embed(
        title=card_name,
        description=f"\n{emojis}  \n*({attribution})*\n*{att2}*\n\n{description}",
        color=discord.Color.red(), # Keeping it a bit spicy
    )

    try:
        file = await read_card_image(card_key)
        embed.set_image(url=f"attachment://{card_key}.jpg")
        
        # User footer
        if not ctx.author.guild_permissions.administrator:
            embed.set_footer(text=f"{ctx.author.name}")
            
        await ctx.send(file=file, embed=embed)
    except FileNotFoundError:
        embed.set_footer(text="⚠️ The image is lost in the void.")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Error loading Manara image {card_key}: {e}", exc_info=True)
        await ctx.send("❌ Error loading card.")
