
import random
import discord
from PIL import Image
import io
import os

# ============================================================

# TAROT DECK DATA

# ============================================================

TAROT_DECK = {
# MAJOR ARCANA (0-21)
"00-the-fool": {
"name": "The Fool",
"upright": "New beginnings, innocence, spontaneity, leap of faith",
"reversed": "Recklessness, naivety, poor judgment, folly"
},
"01-the-magus": {
"name": "The Magus",
"upright": "Willpower, manifestation, skill, concentration",
"reversed": "Manipulation, trickery, scattered energy, illusion"
},
"02-the-priestess": {
"name": "The Priestess",
"upright": "Intuition, mystery, inner wisdom, divine feminine",
"reversed": "Hidden agendas, secrets, withdrawal, silence"
},
"03-the-empress": {
"name": "The Empress",
"upright": "Abundance, fertility, nurturing, creative expression",
"reversed": "Dependence, emptiness, neglect, creative block"
},
"04-the-emperor": {
"name": "The Emperor",
"upright": "Authority, structure, control, leadership",
"reversed": "Tyranny, rigidity, domination, inflexibility"
},
"05-the-hierophant": {
"name": "The Hierophant",
"upright": "Tradition, spiritual wisdom, conformity, education",
"reversed": "Rebellion, unconventionality, challenging norms, personal beliefs"
},
"06-the-lovers": {
"name": "The Lovers",
"upright": "Union, love, harmony, choices",
"reversed": "Imbalance, disharmony, misalignment, poor choices"
},
"07-the-chariot": {
"name": "The Chariot",
"upright": "Willpower, victory, determination, control",
"reversed": "Lack of direction, aggression, opposition, scattered focus"
},
"08-adjustment": {
"name": "Adjustment",
"upright": "Balance, justice, truth, equilibrium",
"reversed": "Imbalance, unfairness, dishonesty, karmic debt"
},
"09-the-hermit": {
"name": "The Hermit",
"upright": "Soul searching, introspection, inner guidance, solitude",
"reversed": "Isolation, loneliness, withdrawal, lost your way"
},
"10-fortune": {
"name": "Fortune",
"upright": "Change, cycles, destiny, turning point",
"reversed": "Bad luck, resistance to change, breaking cycles"
},
"11-lust": {
"name": "Lust",
"upright": "Passion, courage, strength, raw power",
"reversed": "Self-doubt, weakness, lack of discipline, repression"
},
"12-the-hanged-man": {
"name": "The Hanged Man",
"upright": "Suspension, letting go, new perspective, sacrifice",
"reversed": "Stalling, needless sacrifice, resistance, indecision"
},
"13-death": {
"name": "Death",
"upright": "Transformation, endings, renewal, letting go",
"reversed": "Resistance to change, stagnation, fear, decay"
},
"14-art": {
"name": "Art",
"upright": "Balance, alchemy, moderation, synthesis",
"reversed": "Imbalance, excess, lack of harmony, discord"
},
"15-the-devil": {
"name": "The Devil",
"upright": "Bondage, materialism, temptation, illusion",
"reversed": "Release, freedom, breaking chains, enlightenment"
},
"16-the-tower": {
"name": "The Tower",
"upright": "Sudden change, upheaval, revelation, destruction",
"reversed": "Avoiding disaster, fear of change, delaying inevitable"
},
"17-the-star": {
"name": "The Star",
"upright": "Hope, inspiration, serenity, cosmic connection",
"reversed": "Despair, disconnection, lack of faith, disillusionment"
},
"18-the-moon": {
"name": "The Moon",
"upright": "Illusion, intuition, subconscious, mystery",
"reversed": "Confusion, fear, misinterpretation, deception"
},
"19-the-sun": {
"name": "The Sun",
"upright": "Joy, success, vitality, enlightenment",
"reversed": "Temporary depression, false impressions, lack of success"
},
"20-the-aeon": {
"name": "The Aeon",
"upright": "Awakening, renewal, reckoning, inner calling",
"reversed": "Self-doubt, refusal to change, fear of judgment"
},
"21-the-universe": {
"name": "The Universe",
"upright": "Completion, accomplishment, integration, cosmic consciousness",
"reversed": "Incompletion, lack of closure, short-cuts, emptiness"
},

# WANDS (Fire - Creativity, Passion, Action)
"wands-01": {
    "name": "Ace of Wands",
    "upright": "Creative spark, inspiration, potential, new ventures",
    "reversed": "Delays, false starts, lack of direction, creative block"
},
"wands-02": {
    "name": "2 of Wands (Dominion)",
    "upright": "Planning, decisions, bold vision, personal power",
    "reversed": "Fear of unknown, lack of planning, poor decisions"
},
"wands-03": {
    "name": "3 of Wands (Virtue)",
    "upright": "Expansion, foresight, leadership, enterprise",
    "reversed": "Obstacles, delays, lack of foresight, playing it safe"
},
"wands-04": {
    "name": "4 of Wands (Completion)",
    "upright": "Celebration, harmony, homecoming, community",
    "reversed": "Lack of harmony, transition, instability, broken foundation"
},
"wands-05": {
    "name": "5 of Wands (Strife)",
    "upright": "Conflict, competition, tension, disagreement",
    "reversed": "Avoiding conflict, inner conflict, resolution, compromise"
},
"wands-06": {
    "name": "6 of Wands (Victory)",
    "upright": "Success, recognition, triumph, pride",
    "reversed": "Arrogance, lack of recognition, fall from grace, ego"
},
"wands-07": {
    "name": "7 of Wands (Valour)",
    "upright": "Courage, perseverance, standing your ground, defense",
    "reversed": "Exhaustion, giving up, overwhelmed, defenseless"
},
"wands-08": {
    "name": "8 of Wands (Swiftness)",
    "upright": "Speed, movement, rapid action, progress",
    "reversed": "Delays, frustration, waiting, slowness"
},
"wands-09": {
    "name": "9 of Wands (Strength)",
    "upright": "Resilience, persistence, boundaries, last stand",
    "reversed": "Paranoia, stubbornness, weakness, exhaustion"
},
"wands-10": {
    "name": "10 of Wands (Oppression)",
    "upright": "Burden, responsibility, stress, hard work",
    "reversed": "Release, delegation, burnout, collapse"
},
"wands-princess": {
    "name": "Princess of Wands",
    "upright": "Enthusiasm, exploration, discovery, free spirit",
    "reversed": "Unfocused energy, hastiness, lack of direction, tantrums"
},
"wands-prince": {
    "name": "Prince of Wands",
    "upright": "Charm, adventure, passion, impulsiveness",
    "reversed": "Recklessness, volatile, arrogance, passive aggression"
},
"wands-queen": {
    "name": "Queen of Wands",
    "upright": "Confidence, independence, determination, charisma",
    "reversed": "Jealousy, selfishness, demanding, intolerance"
},
"wands-knight": {
    "name": "Knight of Wands",
    "upright": "Action, adventure, fearlessness, entrepreneurial spirit",
    "reversed": "Recklessness, haste, impatience, scattered energy"
},

# CUPS (Water - Emotion, Intuition, Relationships)
"cups-01": {
    "name": "Ace of Cups",
    "upright": "Love, new relationships, emotional awakening, intuition",
    "reversed": "Emotional loss, blocked creativity, emptiness, repression"
},
"cups-02": {
    "name": "2 of Cups (Love)",
    "upright": "Partnership, unity, attraction, connection",
    "reversed": "Imbalance, broken communication, tension, disharmony"
},
"cups-03": {
    "name": "3 of Cups (Abundance)",
    "upright": "Celebration, friendship, community, joy",
    "reversed": "Overindulgence, gossip, isolation, triangle"
},
"cups-04": {
    "name": "4 of Cups (Luxury)",
    "upright": "Contemplation, apathy, reevaluation, meditation",
    "reversed": "Awareness, acceptance, new perspective, action"
},
"cups-05": {
    "name": "5 of Cups (Disappointment)",
    "upright": "Loss, regret, disappointment, emotional pain",
    "reversed": "Acceptance, moving on, healing, recovery"
},
"cups-06": {
    "name": "6 of Cups (Pleasure)",
    "upright": "Nostalgia, innocence, childhood memories, joy",
    "reversed": "Living in past, unrealistic expectations, naivety"
},
"cups-07": {
    "name": "7 of Cups (Debauch)",
    "upright": "Illusion, choices, fantasy, temptation",
    "reversed": "Clarity, reality check, alignment, decision made"
},
"cups-08": {
    "name": "8 of Cups (Indolence)",
    "upright": "Walking away, seeking deeper meaning, abandonment",
    "reversed": "Stagnation, avoidance, fear of moving on"
},
"cups-09": {
    "name": "9 of Cups (Happiness)",
    "upright": "Contentment, satisfaction, wishes fulfilled, pleasure",
    "reversed": "Dissatisfaction, greed, superficiality, unfulfilled"
},
"cups-10": {
    "name": "10 of Cups (Satiety)",
    "upright": "Harmony, alignment, happy family, emotional fulfillment",
    "reversed": "Disconnection, misalignment, values not aligned"
},
"cups-princess": {
    "name": "Princess of Cups",
    "upright": "Sensitivity, intuition, dreamer, artistic nature",
    "reversed": "Emotional immaturity, moodiness, escapism, unrealistic"
},
"cups-prince": {
    "name": "Prince of Cups",
    "upright": "Romance, charm, imagination, idealism",
    "reversed": "Moodiness, unrealistic expectations, jealousy, manipulation"
},
"cups-queen": {
    "name": "Queen of Cups",
    "upright": "Compassion, intuition, emotional security, nurturing",
    "reversed": "Emotional insecurity, codependency, martyrdom, overwhelmed"
},
"cups-knight": {
    "name": "Knight of Cups",
    "upright": "Creativity, romance, emotional depth, following the heart",
    "reversed": "Moodiness, disappointment, overly emotional, ungrounded"
},

# SWORDS (Air - Intellect, Conflict, Truth)
"swords-01": {
    "name": "Ace of Swords",
    "upright": "Raw power, victory, breakthrough, mental clarity",
    "reversed": "Chaos, defeat, confusion, mental fog"
},
"swords-02": {
    "name": "2 of Swords (Peace)",
    "upright": "Difficult choice, stalemate, balance, truce",
    "reversed": "Indecision, confusion, information overload, stalemate broken"
},
"swords-03": {
    "name": "3 of Swords (Sorrow)",
    "upright": "Heartbreak, grief, painful truth, separation",
    "reversed": "Recovery, forgiveness, moving on, healing"
},
"swords-04": {
    "name": "4 of Swords (Truce)",
    "upright": "Rest, recovery, contemplation, meditation",
    "reversed": "Restlessness, burnout, stagnation, exhaustion"
},
"swords-05": {
    "name": "5 of Swords (Defeat)",
    "upright": "Conflict, defeat, dishonor, winning at all costs",
    "reversed": "Reconciliation, making amends, moving on"
},
"swords-06": {
    "name": "6 of Swords (Science)",
    "upright": "Transition, moving on, mental clarity, travel",
    "reversed": "Resistance to change, unfinished business, baggage"
},
"swords-07": {
    "name": "7 of Swords (Futility)",
    "upright": "Deception, strategy, betrayal, cunning",
    "reversed": "Truth revealed, conscience, rethinking approach"
},
"swords-08": {
    "name": "8 of Swords (Interference)",
    "upright": "Restriction, imprisonment, victim mentality, paralysis",
    "reversed": "Release, freedom, self-acceptance, new perspective"
},
"swords-09": {
    "name": "9 of Swords (Cruelty)",
    "upright": "Anxiety, worry, nightmares, mental anguish",
    "reversed": "Hope, recovery, releasing worry, facing fears"
},
"swords-10": {
    "name": "10 of Swords (Ruin)",
    "upright": "Painful ending, betrayal, rock bottom, mental anguish",
    "reversed": "Recovery, regeneration, resisting inevitable end, survival"
},
"swords-princess": {
    "name": "Princess of Swords",
    "upright": "Curiosity, restlessness, mental agility, vigilance",
    "reversed": "Scattered thoughts, gossip, all talk no action, paranoia"
},
"swords-prince": {
    "name": "Prince of Swords",
    "upright": "Analytical, intellectual, truth-seeker, direct",
    "reversed": "Ruthless, cynical, cold, manipulative"
},
"swords-queen": {
    "name": "Queen of Swords",
    "upright": "Independence, clarity, perception, direct communication",
    "reversed": "Coldness, cruelty, bitterness, harsh judgment"
},
"swords-knight": {
    "name": "Knight of Swords",
    "upright": "Ambitious, action-oriented, assertive, driven",
    "reversed": "Aggressive, impulsive, ruthless, unfocused"
},

# DISKS (Earth - Material, Practical, Physical)
"disks-01": {
    "name": "Ace of Disks",
    "upright": "Opportunity, prosperity, new venture, manifestation",
    "reversed": "Lost opportunity, lack of planning, greed, materialism"
},
"disks-02": {
    "name": "2 of Disks (Change)",
    "upright": "Balance, adaptability, juggling, flexibility",
    "reversed": "Imbalance, overwhelmed, disorganization, chaos"
},
"disks-03": {
    "name": "3 of Disks (Works)",
    "upright": "Teamwork, collaboration, skill, achievement",
    "reversed": "Lack of teamwork, poor quality, disharmony"
},
"disks-04": {
    "name": "4 of Disks (Power)",
    "upright": "Security, control, possession, conservation",
    "reversed": "Greed, materialism, self-protection, control issues"
},
"disks-05": {
    "name": "5 of Disks (Worry)",
    "upright": "Financial loss, poverty, insecurity, hardship",
    "reversed": "Recovery, improvement, charity, spiritual poverty"
},
"disks-06": {
    "name": "6 of Disks (Success)",
    "upright": "Generosity, charity, sharing wealth, prosperity",
    "reversed": "Debt, strings attached, inequality, selfishness"
},
"disks-07": {
    "name": "7 of Disks (Failure)",
    "upright": "Frustration, delay, lack of results, reevaluation",
    "reversed": "Progress, perseverance, investment paying off"
},
"disks-08": {
    "name": "8 of Disks (Prudence)",
    "upright": "Apprenticeship, skill development, hard work, diligence",
    "reversed": "Lack of focus, perfectionism, no ambition"
},
"disks-09": {
    "name": "9 of Disks (Gain)",
    "upright": "Abundance, luxury, self-sufficiency, financial independence",
    "reversed": "Overworking, materialism, financial setback"
},
"disks-10": {
    "name": "10 of Disks (Wealth)",
    "upright": "Legacy, inheritance, financial security, family",
    "reversed": "Financial failure, debt, family conflict, instability"
},
"disks-princess": {
    "name": "Princess of Disks",
    "upright": "Practicality, studiousness, new opportunities, groundedness",
    "reversed": "Materialism, poor planning, lack of progress, wastefulness"
},
"disks-prince": {
    "name": "Prince of Disks",
    "upright": "Efficiency, routine, conservatism, methodical",
    "reversed": "Laziness, obsessiveness, perfectionism, workaholic"
},
"disks-queen": {
    "name": "Queen of Disks",
    "upright": "Nurturing, practical, provider, down-to-earth",
    "reversed": "Self-centered, jealous, work-life imbalance, smothering"
},
"disks-knight": {
    "name": "Knight of Disks",
    "upright": "Hard work, productivity, routine, reliability",
    "reversed": "Laziness, boredom, feeling stuck, workaholic"
}

}

# ============================================================

# HELPER FUNCTIONS

# ============================================================

def get_image_path(card_key):
"""Get the file path for a card image"""
return f"images/tarot/{card_key}.png"

def rotate_image(image_path):
"""Rotate image 180 degrees for reversed cards"""
img = Image.open(image_path)
rotated = img.rotate(180, expand=True)
buffer = io.BytesIO()
rotated.save(buffer, format='PNG')
buffer.seek(0)
return buffer

def draw_card():
"""Draw a random card with 50% chance of reversal"""
card_key = random.choice(list(TAROT_DECK.keys()))
is_reversed = random.choice([True, False])
return card_key, is_reversed

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

async def send_tarot_card(ctx, card_key=None, is_reversed=None):
"""Send a tarot card to Discord channel"""
# If no card specified, draw random
if card_key is None:
card_key, is_reversed = draw_card()

# Get card data
card = TAROT_DECK[card_key]
card_name = card["name"]

# Get keywords based on orientation
if is_reversed:
    keywords = f"(REVERSED) {card['reversed']}"
    color = discord.Color.purple()
else:
    keywords = card["upright"]
    color = discord.Color.blue()

# Create embed
embed = discord.Embed(
    title=card_name,
    description=keywords,
    color=color
)

# Get image
image_path = get_image_path(card_key)

# Check if image exists
if not os.path.exists(image_path):
    embed.set_footer(text="⚠️ Image file not found")
    await ctx.send(embed=embed)
    return

# Rotate if reversed
if is_reversed:
    image_buffer = rotate_image(image_path)
    file = discord.File(image_buffer, filename=f"{card_key}.png")
else:
    file = discord.File(image_path, filename=f"{card_key}.png")

# Set image in embed
embed.set_image(url=f"attachment://{card_key}.png")

# Send to Discord
await ctx.send(file=file, embed=embed)
