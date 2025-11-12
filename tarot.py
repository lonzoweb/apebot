import random
import discord
import os

# ============================================================
# TAROT DECK DATA - Aleister Crowley Thoth Tarot
# ============================================================

TAROT_DECK = {
    # MAJOR ARCANA (0-21)
    "00-the-fool": {
        "name": "The Fool",
        "emojis": "💨 🌈 🃏 ⚡ 🎭",
        "attribution": "Air • Aleph",
        "att2": "",
        "description": "Original potential, creative chaos, carefree, new beginnings, starting off into the unknown, jester's license, foolhardiness",
    },
    "01-the-magus": {
        "name": "The Magus",
        "emojis": "☿️ 🪄 🎪 📜 🐒",
        "attribution": "Mercury • Beth",
        "att2": "",
        "description": "Primer, activity, resolution, willpower, concentration, vital force, mastery, self-realization, assertion, skillfulness, trickiness",
    },
    "02-the-priestess": {
        "name": "The Priestess",
        "emojis": "🌙 🏹 👸 🔮 ✨",
        "attribution": "Moon • Gimel",
        "att2": "",
        "description": "Inner guidance, wisdom, female intuition, visions, fantasies, secrets, waiting willingness to be guided",
    },
    "03-the-empress": {
        "name": "The Empress",
        "emojis": "♀️ 🌹 👑 🦢 🦅",
        "attribution": "Venus • Daleth",
        "att2": "",
        "description": "Growth, creative potential, intuitive power, renewal, pregnancy, birth, consideration",
    },
    "04-the-emperor": {
        "name": "The Emperor",
        "emojis": "♈ 🐏 👑 ⚔️ 🦅",
        "attribution": "Aries • Tzaddi",
        "att2": "",
        "description": "Sense of reality, willingness to take responsibility, initiative, sense of security, continuity, strength of leadership, uprightness, pragmatism",
    },
    "05-the-hierophant": {
        "name": "The Hierophant",
        "emojis": "♉ 🐘 ⭐ 🕊️ 📿",
        "attribution": "Taurus • Vau",
        "att2": "",
        "description": "Trust, search for truth, experience of meaning, power of conviction, virtue, expansion of consciousness, strength of faith",
    },
    "06-the-lovers": {
        "name": "The Lovers",
        "emojis": "♊ 💑 🗡️ 🥚 🦅",
        "attribution": "Gemini • Zain",
        "att2": "",
        "description": "Union, love, heartfelt actions, decisions of the heart, overcoming opposites, collecting details",
    },
    "07-the-chariot": {
        "name": "The Chariot",
        "emojis": "♋ 🏺 🦁 🐂 🌊",
        "attribution": "Cancer • Cheth",
        "att2": "",
        "description": "Mood of departure, thirst for adventure, boldness, conscious of goal, assertive will",
    },
    "08-adjustment": {
        "name": "Adjustment",
        "emojis": "♎ ⚖️ 🗡️ 👑 💎",
        "attribution": "Libra • Lamed",
        "att2": "",
        "description": "Objectivity, clarity, balance, justice, karma, sober perception, personal responsibility, self-criticism",
    },
    "09-the-hermit": {
        "name": "The Hermit",
        "emojis": "♍ 🪔 🥚 🐍 🌾",
        "attribution": "Virgo • Yod",
        "att2": "",
        "description": "Contemplating what is essential, defining one's position, seclusion, seriousness, retreat, getting to the bottom of things, life experience",
    },
    "10-fortune": {
        "name": "Fortune",
        "emojis": "♃ 🎡 🦁 🐒 🐍",
        "attribution": "Jupiter • Kaph",
        "att2": "",
        "description": "Changes, shift, new beginning, happiness, fateful events, task in life",
    },
    "11-lust": {
        "name": "Lust",
        "emojis": "♌ 🦁 👸 🏺 🔥",
        "attribution": "Leo • Teth",
        "att2": "",
        "description": "Courage, vitality, love of life, strength, passion, intrepidity",
    },
    "12-the-hanged-man": {
        "name": "The Hanged Man",
        "emojis": "🌊 ☠️ 🐍 ⚓ 🔺",
        "attribution": "Water • Mem",
        "att2": "",
        "description": "Being worn down between two opposites, dilemma, test of patience, powerlessness, dead-end street, involuntary learning processes, crisis in life, forced break, having to make a sacrifice",
    },
    "13-death": {
        "name": "Death",
        "emojis": "♏ 🦂 💀 🦅 🐟",
        "attribution": "Scorpio • Nun",
        "att2": "",
        "description": "Parting, natural end, fear of life, futile clinging, being forced to let go, renunciation",
    },
    "14-art": {
        "name": "Art",
        "emojis": "♐ 🌈 ⚗️ 🦅 🦁",
        "attribution": "Sagittarius • Samech",
        "att2": "",
        "description": "Finding the right proportions, balance of powers, harmony, relaxation, overcoming differences, healing",
    },
    "15-the-devil": {
        "name": "The Devil",
        "emojis": "♑ 🐐 👁️ 🍇 🪐",
        "attribution": "Capricorn • Ayin",
        "att2": "",
        "description": "Shadows, instinctiveness, lack of moderation, greed, thirst for power, temptation, unconscious forces",
    },
    "16-the-tower": {
        "name": "The Tower",
        "emojis": "♂️ ⚡ 🗼 👁️ 🕊️",
        "attribution": "Mars • Peh",
        "att2": "",
        "description": "Sudden perception, upheaval, breakthrough, liberation, blow of fate",
    },
    "17-the-star": {
        "name": "The Star",
        "emojis": "♒ ⭐ 🌊 🌊 🌀",
        "attribution": "Aquarius • Heh",
        "att2": "",
        "description": "Good prospects, hope, trust in the future, harmony, higher guidance",
    },
    "18-the-moon": {
        "name": "The Moon",
        "emojis": "♓ 🌙 🦂 🐺 🌊",
        "attribution": "Pisces • Qoph",
        "att2": "",
        "description": "Fear of the threshold before an important step, feelings of insecurity, nightmares, stage fright, threatening memories, dark premonitions",
    },
    "19-the-sun": {
        "name": "The Sun",
        "emojis": "☀️ 👶 🦋 🌹 ✨",
        "attribution": "Sun • Resh",
        "att2": "",
        "description": "Happiness, enjoying the sunny side of life, new birth, high spirits, success, self-development, steering toward a culminating point",
    },
    "20-the-aeon": {
        "name": "The Aeon",
        "emojis": "🔥 👶 🌟 🐍 ✨",
        "attribution": "Fire • Shin",
        "att2": "",
        "description": "Transformation, new beginning, hope, self-discovery, spiritual development",
    },
    "21-the-universe": {
        "name": "The Universe",
        "emojis": "🪐 🌍 💃 🐍 ♄",
        "attribution": "Saturn • Earth • Tau",
        "att2": "",
        "description": "Completion, joy of living, being at the right place at the right time, resting in one's center, fulfillment, return home, reconciliation",
    },
    # WANDS - Fire
    "wands-01": {
        "name": "Ace of Wands",
        "emojis": "🔥 🌳 ⚡ 💫 🔆",
        "attribution": "Root of Fire",
        "att2": "Initiative (Y), joy of life (2), growth (#)",
        "description": "Hopeful new beginning, initiative, willpower, decisiveness, electrifying idea, surge of creativity, opportunity for self-development, becoming inflamed about something",
    },
    "wands-02": {
        "name": "Two of Wands - Dominion",
        "emojis": "♂️ ♈ 🔥 ⚔️ 👑",
        "attribution": "Mars in Aries • Chokmah",
        "att2": "Forces of the ego, energy (c*) spirit of departure (Y)",
        "description": "Eagerness to fight, courage, willingness to take risks, willpower, becoming inflamed about something, spontaneous assertion, violent forging ahead, inconsideration",
    },
    "wands-03": {
        "name": "Three of Wands - Virtue",
        "emojis": "☀️ ♈ 🌺 👑 ✨",
        "attribution": "Sun in Aries • Binah",
        "att2": "Self-confidence, being centered, vitality (©) in connection with a pioneering spirit and an urge to move forward (Y)",
        "description": "Healthy basis, confidence, success, initiative, vitality",
    },
    "wands-04": {
        "name": "Four of Wands - Completion",
        "emojis": "♀️ ♈ 🐏 🕊️ 🏰",
        "attribution": "Venus in Aries • Chesed",
        "att2": "Charm and accommodation (Q) in balanced combination with a fighting spirit and desire to conquer (Y)",
        "description": "Order and harmony, balanced dynamics, self-assurance, equilibrium",
    },
    "wands-05": {
        "name": "Five of Wands - Strife",
        "emojis": "♄ ♌ ⚔️ 🔥 💥",
        "attribution": "Saturn in Leo • Geburah",
        "att2": "Courage (2) to be responsible (R) and persistent (R) self-development (2)",
        "description": "Comparison of strength, ambition, aggressiveness, challenge, overstepping bounds",
    },
    "wands-06": {
        "name": "Six of Wands - Victory",
        "emojis": "♃ ♌ 🏆 🌟 ⚡",
        "attribution": "Jupiter in Leo • Tiphareth",
        "att2": "Abundance, wealth, success (2+) in connection with self-assurance, self-fulfillment, strength, triumph (2)",
        "description": "Reward for accomplished effort, good news, optimism, victory",
    },
    "wands-07": {
        "name": "Seven of Wands - Valour",
        "emojis": "♂️ ♌ ⚔️ 🛡️ 🔥",
        "attribution": "Mars in Leo • Netzach",
        "att2": "Courage, decisiveness, and willingness to engage in conflict (c*) in connection with self-confidence certain of success (2)",
        "description": "Risking a single-handed effort, growing beyond one's own limitations, struggling with difficulties, taking a risk",
    },
    "wands-08": {
        "name": "Eight of Wands - Swiftness",
        "emojis": "☿️ ♐ ⚡ 🌈 💬",
        "attribution": "Mercury in Sagittarius • Hod",
        "att2": "Confident, farsighted, hopeful (#) thinking and perceiving (¥)",
        "description": "'Aha' experience, sudden solution to problems, flashes of inspiration, being a 'live wire'",
    },
    "wands-09": {
        "name": "Nine of Wands - Strength",
        "emojis": "🌙 ♐ 🏹 💪 ☀️",
        "attribution": "Moon in Sagittarius • Yesod",
        "att2": "Confidence and urge to develop (#) rising from the unconscious (D)",
        "description": "Drawing on abundant resources, experiencing a flow of energy, anticipation, inspiration",
    },
    "wands-10": {
        "name": "Ten of Wands - Oppression",
        "emojis": "♄ ♐ ⚔️ 🔥 💔",
        "attribution": "Saturn in Sagittarius • Malkuth",
        "att2": "Blockage, inhibition, suppression (R) of enthusiasm, power of conviction, life philosophy, expansion (#)",
        "description": "Blocked development, problems with authority, frustration, fear of life, 'straitjacket'",
    },
    "wands-princess": {
        "name": "Princess of Wands",
        "emojis": "🔥 🌍 ☀️ 💃 ⚡",
        "attribution": "Earthy part of Fire",
        "att2": "Earthy part of Fire",
        "description": "Young, dynamic, impulsive, zestful woman; amazon, primer, impetuous new beginning, enthusiasm, desire for adventure, impatience",
    },
    "wands-prince": {
        "name": "Prince of Wands",
        "emojis": "🔥 💨 🦅 🐉 ⚡",
        "attribution": "Airy part of Fire",
        # "att2": "Airy part of Fire",
        "description": "Daredevil, conqueror, hero, sprinter, hothead, new momentum, initiative, enthusiasm",
    },
    "wands-queen": {
        "name": "Queen of Wands",
        "emojis": "🔥 🌊 👑 🐆 🔥",
        "attribution": "Watery part of Fire",
        # "att2": "Watery part of Fire",
        "description": "Healthy sense of self-assurance, iniative, openness, impulsiveness, independence, self-fulfillment; high-spirited, charismatic, generous woman who is mature in terms of human experience",
    },
    "wands-knight": {
        "name": "Knight of Wands",
        "emojis": "🔥 🔥 🏇 ⚡ 👑",
        "attribution": "Fiery part of Fire",
        # "att2": "Fiery part of Fire",
        "description": "Self-confidence, courage, striving for ideals, strong enterprising spirit; strong-willed, dynamic mature man; exemplary personality, leader nature",
    },
    # CUPS - Water
    "cups-01": {
        "name": "Ace of Cups",
        "emojis": "🌊 🏺 🌊 💖 🌹",
        "attribution": "Root of Water",
        "att2": "Emotional depth ($), emotional strength (M,), devotion and empathy (3€)",
        "description": "Bliss, inner wealth, openness, harmony, opportunity to find fulfillment",
    },
    "cups-02": {
        "name": "Two of Cups - Love",
        "emojis": "♀️ ♋ 💑 🐬 🌺",
        "attribution": "Venus in Cancer • Chokmah",
        "att2": "Loving, delightful (Q) devotion and feelings ($) of emotional ($) connection (Q)",
        "description": "Happy relationship, cooperation, reconciliation, joyful encounter",
    },
    "cups-03": {
        "name": "Three of Cups - Abundance",
        "emojis": "☿️ ♋ 🍇 🌺 🎉",
        "attribution": "Mercury in Cancer • Binah",
        "att2": "Emotional ($) exchange (¥), emotional ($) intelligence (¥)",
        "description": "Fulfillment, joy, fertile exchange, gratitude, well-being, rich harvest",
    },
    "cups-04": {
        "name": "Four of Cups - Luxury",
        "emojis": "🌙 ♋ 🏺 🌊 💔",
        "attribution": "Moon in Cancer • Chesed",
        "att2": "Caring, motherly, devoted ($) feelings (D)",
        "description": "Reveling, enjoying life, emotional security, sense of security",
    },
    "cups-05": {
        "name": "Five of Cups - Disappointment",
        "emojis": "♂️ ♏ 💔 🌧️ 😢",
        "attribution": "Mars in Scorpio • Geburah",
        "att2": "Power (c*) growing from decay (M,)",
        "description": "Disappointed expectations, faded hope, melancholy, painful perceptions, transformational crisis",
    },
    "cups-06": {
        "name": "Six of Cups - Pleasure",
        "emojis": "☀️ ♏ 🌺 💖 ✨",
        "attribution": "Sun in Scorpio • Tiphareth",
        "att2": "Deep, self-renewing (M,) joy of life (©)",
        "description": "Reawakening spirits, drawing from the depths, finding fulfillment, emotional recovery, well-being",
    },
    "cups-07": {
        "name": "Seven of Cups - Debauch",
        "emojis": "♀️ ♏ 🍷 💀 😵",
        "attribution": "Venus in Scorpio • Netzach",
        "att2": "Depths (M,) of desire (Q), pleasure (Q) that leads to dependence (M,)",
        "description": "Disaster, dangerous temptation, addictions, deception, threatening calamity",
    },
    "cups-08": {
        "name": "Eight of Cups - Indolence",
        "emojis": "♄ ♓ 🌊 💤 🥀",
        "attribution": "Saturn in Pisces • Hod",
        "att2": "Hardened, dead (R) feelings (3€)",
        "description": "Weakness, broken hopes, disheartenment, resignation, necessity of changing one's ways, stagnation, depression",
    },
    "cups-09": {
        "name": "Nine of Cups - Happiness",
        "emojis": "♃ ♓ 🎉 💖 ✨",
        "attribution": "Jupiter in Pisces • Yesod",
        "att2": "Happiness, growth, trust (2+) in spirituality and all-encompassing love (3€)",
        "description": "Bliss, optimism, meaningful experience, charity, trust in God, quiet happiness",
    },
    "cups-10": {
        "name": "Ten of Cups - Satiety",
        "emojis": "♂️ ♓ 🏺 🌊 🌹",
        "attribution": "Mars in Pisces • Malkuth",
        "att2": "Fulfillment (3€) and a new beginning (c*), emotional (3€) strength (c*)",
        "description": "Fulfillment, culmination, completion, gratitude, sociableness",
    },
    "cups-princess": {
        "name": "Princess of Cups",
        "emojis": "🌊 🌍 🦢 🐢 🐬",
        "attribution": "Earthy part of Water",
        "att2": "",
        "description": "Sensitive young woman, enchanting seductress, dreamer, muse, longing for union, romance, deep feelings, daydreaming, quiet joy",
    },
    "cups-prince": {
        "name": "Prince of Cups",
        "emojis": "🌊 💨 🦅 🐍 🌊",
        "attribution": "Airy part of Water",
        "att2": "",
        "description": "Tender, romantic man; seducer, charmer, warm personality, gushing enthusiasm",
    },
    "cups-queen": {
        "name": "Queen of Cups",
        "emojis": "🌊 🌊 🦢 🌊 🔮",
        "attribution": "Watery part of Water",
        "att2": "",
        "description": "Sensitivity, devotion, inspiration, depth of feeling, receptivity, mercy; intuition, maturity, an artistic woman",
    },
    "cups-knight": {
        "name": "Knight of Cups",
        "emojis": "🌊 🔥 🏇 🦚 ♋️",
        "attribution": "Fiery part of Water",
        "att2": "",
        "description": "Emotional depth, artistic talent, medial abilities, imagination, sensitivity; mature, helpful, sensitive man; intuitive advisor",
    },
    # SWORDS - Air
    "swords-01": {
        "name": "Ace of Swords",
        "emojis": "💨 🗡️ 👑 ⚡ ⚖️",
        "attribution": "Root of Air",
        "att2": "Curiosity (II), sociability (#), intellect (=)",
        "description": "Intellectual interests, thirst for knowledge, the power of reason, good opportunity to clarify something, making sensible and clear decisions",
    },
    "swords-02": {
        "name": "Two of Swords - Peace",
        "emojis": "🌙 ♎ 🗡️ 🌹 ⚖️",
        "attribution": "Moon in Libra • Chokmah",
        "att2": "Balanced, peaceful (#) feelings (D), need (D) for harmony (#)",
        "description": "State of balance, relaxation, serenity, thoughtfulness, fairness, compromise",
    },
    "swords-03": {
        "name": "Three of Swords - Sorrow",
        "emojis": "♄ ♎ 💔 😢 🗡️",
        "attribution": "Saturn in Libra • Binah",
        "att2": "Blockage/end (R) of peace and harmony (#)",
        "description": "Bad news, disappointment, weakness, sorrow, helplessness, chaos, disillusionment, renunciation, loss",
    },
    "swords-04": {
        "name": "Four of Swords - Truce",
        "emojis": "♃ ♎ 🗡️ 🌹 ✝️",
        "attribution": "Jupiter in Libra • Chesed",
        "att2": "Faith/hope (2+) for peace and justice (#)",
        "description": "Sham peace, temporary retreat, calm before the storm, cowardice, forced break, isolation, building up one's strength",
    },
    "swords-05": {
        "name": "Five of Swords - Defeat",
        "emojis": "♀️ ♒ 💔 🗡️ 😞",
        "attribution": "Venus in Aquarius • Geburah",
        "att2": "Willful, unpredictable, frosty (=) conduct in relationship (Q)",
        "description": "Capitulation, betrayal, humiliation, suffering 'shipwreck,' vileness",
    },
    "swords-06": {
        "name": "Six of Swords - Science",
        "emojis": "☿️ ♒ 🗡️ 🌹 ✝️",
        "attribution": "Mercury in Aquarius • Tiphareth",
        "att2": "Innovative (=) thinking (¥) and philosophical, scientific (=) perceiving (¥)",
        "description": "Perception, progress, openness, insight, objectivity, intelligence",
    },
    "swords-07": {
        "name": "Seven of Swords - Futility",
        "emojis": "🌙 ♒ 🗡️ 🌙 😔",
        "attribution": "Moon in Aquarius • Netzach",
        "att2": "Changeable, moody (D) theories and concepts (=)",
        "description": "Unexpected obstacles, impairment, self-deception, fraud, cowardice",
    },
    "swords-08": {
        "name": "Eight of Swords - Interference",
        "emojis": "♃ ♊ 🗡️ ⚔️ 🔗",
        "attribution": "Jupiter in Gemini • Hod",
        "att2": "High goals (2+) that are threatened by doubts and inner conflicts (II)",
        "description": "Difficult progress because of distractions, inner conflicts, doubt, absentmindedness, slip-ups, flightiness",
    },
    "swords-09": {
        "name": "Nine of Swords - Cruelty",
        "emojis": "♂️ ♊ 🗡️ 😭 💀",
        "attribution": "Mars in Gemini • Yesod",
        "att2": "Merciless harshness (c*) and heartless calculating attitude (II)",
        "description": "Adversity, powerlessness, failure, feelings of guilt, worries, panic",
    },
    "swords-10": {
        "name": "Ten of Swords - Ruin",
        "emojis": "☀️ ♊ 🗡️ 💀 ☠️",
        "attribution": "Sun in Gemini • Malkuth",
        "att2": "Fragmentation (II) of vital force (©)",
        "description": "Random end, making a clean sweep, putting a stop to something, breakdown, out-of-control destructive energies",
    },
    "swords-princess": {
        "name": "Princess of Swords",
        "emojis": "💨 🌍 🗡️ ⚔️ 👸",
        "attribution": "Earthy part of Air",
        #  "att2": "Earthy part of Air",
        "description": "Young, intellectual woman; female rebel who is nimble-minded and knowledgeable; esprit, clarity, mental renewal, provocation, restlessness, quarrelsome nature",
    },
    "swords-prince": {
        "name": "Prince of Swords",
        "emojis": "💨 💨 🗡️ 🧚 ⚡",
        "attribution": "Airy part of Air",
        #  "att2": "Airy part of Air",
        "description": "The intellectual, the eloquent individual, the technocrat, the position-changer, independence, aimlessness, lightness, slyness, cynicism",
    },
    "swords-queen": {
        "name": "Queen of Swords",
        "emojis": "💨 🌊 👑 🗡️ 💀",
        "attribution": "Watery part of Air",
        #  "att2": "Watery part of Air",
        "description": "Wealth of ideas, presence of mind, independence, quick-wittedness; rationally oriented, cultivated, emancipated, critical, clever woman; female individualist",
    },
    "swords-knight": {
        "name": "Knight of Swords",
        "emojis": "💨 🔥 🏇 🗡️ 🌪️",
        "attribution": "Fiery part of Air",
        #  "att2": "Fiery part of Air",
        "description": "Versatility, discernment, flexibility, intelligence, objectivity, too much emphasis on rational mind, calculation; clever, eloquent, brilliant, goal-oriented man; experienced advisor",
    },
    # DISKS - Earth
    "disks-01": {
        "name": "Ace of Disks",
        "emojis": "🌍 💎 🪙 🌱 ✨",
        "attribution": "Root of Earth",
        "att2": "Enjoyment (8), sense of reality (IP), and stability (V8)",
        "description": "Affluence, material happiness, health, inner and outer strength, stability, opportunity for lasting success, sensuality",
    },
    "disks-02": {
        "name": "Two of Disks - Change",
        "emojis": "♃ ♑ ☯️ 🐍 🔄",
        "attribution": "Jupiter in Capricorn • Chokmah",
        "att2": "Expansion (2+) and concentration (V8)",
        "description": "Change, flexible exchange, mutual fructification, variety",
    },
    "disks-03": {
        "name": "Three of Disks - Works",
        "emojis": "♂️ ♑ 🔺 ⚙️ 🏗️",
        "attribution": "Mars in Capricorn • Binah",
        "att2": "Forming and processing (c*) matter and reality (V8) with strength (c*) and consistent staying power (V8)",
        "description": "Taking concrete steps, translating ideas into reality, building structures, slow but continuous progress, perseverance, consolidation",
    },
    "disks-04": {
        "name": "Four of Disks - Power",
        "emojis": "☀️ ♑ 🏰 👑 🛡️",
        "attribution": "Sun in Capricorn • Chesed",
        "att2": "Self-fulfillment and vitality (©) through security, structure, and order (V8)",
        "description": "Stability, safeguarding, sense of reality, control, structuring",
    },
    "disks-05": {
        "name": "Five of Disks - Worry",
        "emojis": "☿️ ♉ 💰 😰 ⭐",
        "attribution": "Mercury in Taurus • Geburah",
        "att2": "Bogged-down, obstinate (8) thinking (¥)",
        "description": "Helplessness, fear of loss, constriction, drudgery without results, frustration at nothing working out",
    },
    "disks-06": {
        "name": "Six of Disks - Success",
        "emojis": "🌙 ♉ 💰 ⚖️ ✨",
        "attribution": "Moon in Taurus • Tiphareth",
        "att2": "Fertility (D) and growth (8), feelings (D) of abundance and enjoyment (8)",
        "description": "Increase, material gain, favorable interplay of the forces, welcome development",
    },
    "disks-07": {
        "name": "Seven of Disks - Failure",
        "emojis": "♄ ♉ 🌾 😞 💔",
        "attribution": "Saturn in Taurus • Netzach",
        "att2": "Blockade, end, departure (R) from possessions and stability (8)",
        "description": "Destroyed hope, bad circumstances, bad luck, unhappiness, pessimism, loss",
    },
    "disks-08": {
        "name": "Eight of Disks - Prudence",
        "emojis": "☀️ ♍ 🌳 ⚙️ 💰",
        "attribution": "Sun in Virgo • Hod",
        "att2": "Mindful, worldly-wise, prudent (IP) nature (©)",
        "description": "Cautious new beginning, moderation, skillfulness, care, patience",
    },
    "disks-09": {
        "name": "Nine of Disks - Gain",
        "emojis": "♀️ ♍ 💎 🌟 🏆",
        "attribution": "Venus in Virgo • Yesod",
        "att2": "Fortuna (Q) brings in the harvest (IP)",
        "description": "Change for the better, well-being, stroke of luck, material increase",
    },
    "disks-10": {
        "name": "Ten of Disks - Wealth",
        "emojis": "☿️ ♍ 💰 🪙 🏛️",
        "attribution": "Mercury in Virgo • Malkuth",
        "att2": "Cleverness and skill (¥) in business area (IP)",
        "description": "Solid success, wealth, secure circumstances, having achieved the goal",
    },
    "disks-princess": {
        "name": "Princess of Disks",
        "emojis": "🌍 🌍 🐏 💎 🌾",
        "attribution": "Earthy part of Earth",
        # "att2": "Earthy part of Earth",
        "description": "Young, sensual, fertile woman; naturalness, creativity, growth, pregnancy",
    },
    "disks-prince": {
        "name": "Prince of Disks",
        "emojis": "🌍 💨 🐂 🌾 ⚙️",
        "attribution": "Airy part of Earth",
        # "att2": "Airy part of Earth",
        "description": "Energetic young man, prime mover, person with imperturbable staying power ('steamroller'), sense of reality, persistence, endurance, concentration, initiative",
    },
    "disks-queen": {
        "name": "Queen of Disks",
        "emojis": "🌍 🌊 🐐 🌹 👑",
        "attribution": "Watery part of Earth",
        # "att2": "Watery part of Earth",
        "description": "Fertility, sense of security, sensuality, serenity, endurance; a mature, experienced woman; being calm, patient, stable, trustworthy",
    },
    "disks-knight": {
        "name": "Knight of Disks",
        "emojis": "🌍 🔥 🏇 🐴 🌾",
        "attribution": "Fiery part of Earth",
        # "att2": "Fiery part of Earth",
        "description": "Firmness, sobriety, perseverance, stable values, reliability, straightforwardness; mature, sensual man; realist, pragmatist, guarantee of security",
    },
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_image_path(card_key):
    """Get the file path for a card image"""
    return f"images/tarot/{card_key}.png"


def draw_card():
    """Draw a random card (no reversals)"""
    card_key = random.choice(list(TAROT_DECK.keys()))
    return card_key


def search_card(keyword):
    """Search for a card by name or keyword"""
    keyword_lower = keyword.lower()
    for card_key, card_data in TAROT_DECK.items():
        if keyword_lower in card_data["name"].lower():
            return card_key
    return None


# ============================================================
# DISCORD EMBED FUNCTION
# ============================================================


async def send_tarot_card(ctx, card_key=None):
    """Send a tarot card to Discord channel"""
    # If no card specified, draw random
    if card_key is None:
        card_key = draw_card()

    # Get card data
    card = TAROT_DECK[card_key]
    card_name = card["name"]
    emojis = card["emojis"]
    attribution = card["attribution"]
    description = card["description"]

    # Create embed
    embed = discord.Embed(
        title=card_name,
        description=f"\n{emojis}  \n*({attribution})*\n*({card['att2']})*\n\n{description}",
        color=discord.Color.from_rgb(0, 0, 128),
    )

    # Get image
    image_path = get_image_path(card_key)

    # Check if image exists
    if not os.path.exists(image_path):
        embed.set_footer(text="⚠️ Image file not found")
        await ctx.send(embed=embed)
        return

    file = discord.File(image_path, filename=f"{card_key}.png")
    embed.set_image(url=f"attachment://{card_key}.png")

    # Send to Discord
    await ctx.send(file=file, embed=embed)
