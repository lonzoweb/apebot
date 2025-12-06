"""
Rider-Waite-Smith Tarot Deck
"""

import random
import discord
import os

RWS_DECK = {
    "0-the-fool": {
        "name": "The Fool",
        "emojis": "",
        "attribution": "Uranus/Mercury in the sense of open-mindedness, curiosity, spontaneity, and mad whims. Combined with Neptune as a sign of having guidance.",
        "att2": "",
        "description": "spontaneous new beginnings, open-mindedness, playful lightheartedness, refreshing experiences",
    },
    "1-the-magician": {
        "name": "The Magician",
        "emojis": "",
        "attribution": "The Sun in the sense of strength and charisma. Mercury with respect to agility and skillfulness.",
        "att2": "",
        "description": "cleverness, self-confidence, active creation, mastering problems, strong fascination",
    },
    "2-the-high-priestess": {
        "name": "The High Priestess",
        "emojis": "",
        "attribution": "The Moon as an expression of our lunar consciousness, our sense of understanding, and the strength of our unconscious powers.",
        "att2": "",
        "description": "subconscious powers, intuition, deep understanding, patience, mysterious wisdom",
    },
    "3-the-empress": {
        "name": "The Empress",
        "emojis": "",
        "attribution": "Venus in Taurus in the sense of fertility and growth.",
        "att2": "",
        "description": "fertility, growth, creativity, liveliness, new birth",
    },
    "4-the-emperor": {
        "name": "The Emperor",
        "emojis": "",
        "attribution": "Sun in Capricorn in the sense of responsibility, order, security, structure, continuity, and perseverance.",
        "att2": "",
        "description": "structure, stability, security, order, consistency, realism",
    },
    "5-the-hierophant": {
        "name": "The Hierophant",
        "emojis": "",
        "attribution": "Sun in Sagittarius as the proclaimer and teacher of religious values.",
        "att2": "",
        "description": "deep trust, religious values, search for meaning, moral principles",
    },
    "6-the-lovers": {
        "name": "The Lovers",
        "emojis": "",
        "attribution": "Venus/Jupiter as an expression of great love and Venus/Mars as the decision that is made with love.",
        "att2": "",
        "description": "great love, necessary decision, unconditional yes, wholehearted commitment",
    },
    "7-the-chariot": {
        "name": "The Chariot",
        "emojis": "",
        "attribution": "Aries as the emerging of the powers.",
        "att2": "",
        "description": "departure, great leap forward, courage, willingness to take risks",
    },
    "8-strength": {
        "name": "Strength",
        "emojis": "",
        "attribution": "Leo in the sense of an affirmation of life, vitality, pride, desire, and passion.",
        "att2": "",
        "description": "vitality, passion, courage, inner harmony, zest for life",
    },
    "9-the-hermit": {
        "name": "The Hermit",
        "emojis": "",
        "attribution": "Saturn in Aquarius as striving for wisdom and preserving independence.",
        "att2": "",
        "description": "seclusion, introspection, reflection, deep perception, inner clarity",
    },
    "10-wheel-of-fortune": {
        "name": "Wheel of Fortune",
        "emojis": "",
        "attribution": "Saturn in its function as the ruler of time and as a teacher.",
        "att2": "",
        "description": "destiny, karma, turning point, accepting necessary changes",
    },
    "11-justice": {
        "name": "Justice",
        "emojis": "",
        "attribution": "Jupiter/Mars as the power of judgment and Venus in Libra in the sense of fairness and balance.",
        "att2": "",
        "description": "objective clarity, fairness, balance, getting what you deserve, personal responsibility",
    },
    "12-the-hanged-man": {
        "name": "The Hanged Man",
        "emojis": "",
        "attribution": "Pisces in the sense of the sacrifice and enlightenment. Sun in 12th house as imprisonment and the change of one’s ways on the basis of deep insight.",
        "att2": "",
        "description": "forced repose, reversal of views, letting go, change of perspective",
    },
    "13-death": {
        "name": "Death",
        "emojis": "",
        "attribution": "Saturn in 8th house. The planet of limitations, separation, and departure in the field of dying and becoming.",
        "att2": "",
        "description": "parting, end, letting go, transformation, new beginning",
    },
    "14-temperance": {
        "name": "Temperance",
        "emojis": "",
        "attribution": "Venus in the sense of harmony and balance.",
        "att2": "",
        "description": "moderation, harmony, peace of mind, health, balance",
    },
    "15-the-devil": {
        "name": "The Devil",
        "emojis": "",
        "attribution": "Pluto in its expression as dark power.",
        "att2": "",
        "description": "temptation, dependence, loss of will, playing with fire, inner shadows",
    },
    "16-the-tower": {
        "name": "The Tower",
        "emojis": "",
        "attribution": "Uranus/Saturn as the sudden bursting of incrustations.",
        "att2": "",
        "description": "sudden change, bursting of rigid structures, liberation, breakthrough",
    },
    "17-the-star": {
        "name": "The Star",
        "emojis": "",
        "attribution": "Jupiter in 11th house in the sense of confidence and far-sightedness.",
        "att2": "",
        "description": "hope, starting things that will reach far, wisdom, higher guidance",
    },
    "18-the-moon": {
        "name": "The Moon",
        "emojis": "",
        "attribution": "The Moon in Scorpio as the dark knowledge of the depths of the soul, or the Sun in the 8th house as the descent into the underworld.",
        "att2": "",
        "description": "illusion, fear, uncertain road, dream realm, hidden tides",
    },
    "19-the-sun": {
        "name": "The Sun",
        "emojis": "",
        "attribution": "The Sun in 5th house in the sense of joy in living, creativity, and playful pleasure.",
        "att2": "",
        "description": "vitality, joy of living, clear vision, youthful energy, warmth",
    },
    "20-judgment": {
        "name": "Judgment",
        "emojis": "",
        "attribution": "Jupiter/Uranus in harmonious connection to the Sun, or the sign of Aquarius as expression of liberation and release.",
        "att2": "",
        "description": "liberation, redemption, resurrection, finding the treasure, decisive step",
    },
    "21-the-world": {
        "name": "The World",
        "emojis": "",
        "attribution": "Jupiter in Pisces as expression of deliverance, or Jupiter in harmonious connection with Saturn as the happy ending.",
        "att2": "",
        "description": "unity, harmony, happy ending, finding one's place, arrival",
    },
    "ace-of-wands": {
        "name": "Ace of Wands",
        "emojis": "",
        "attribution": "Sun/Mars in the sense of courage, decisiveness, willingness to take risks, and the power of self-fulfillment.",
        "att2": "",
        "description": "initiative, courage, risk-taking, enthusiasm, self-fulfillment",
    },
    "2-of-wands": {
        "name": "2 of Wands",
        "emojis": "",
        "attribution": "Mars in Libra as the theoretical decision without inner commitment or practical consequences.",
        "att2": "",
        "description": "neutral attitude, indifference, half-heartedness, theoretical decision",
    },
    "3-of-wands": {
        "name": "3 of Wands",
        "emojis": "",
        "attribution": "Mercury in Leo in the sense of confidence and far-sightedness in harmonious connection with Saturn as the dependable basis.",
        "att2": "",
        "description": "reaching heights, solid ground, broad view, promising prospects",
    },
    "4-of-wands": {
        "name": "4 of Wands",
        "emojis": "",
        "attribution": "Venus in 5th house as joy, play, and pleasure, or the Moon/Venus in the sense of safety and sociability.",
        "att2": "",
        "description": "peace, opening up, sociability, enjoyment, stability",
    },
    "5-of-wands": {
        "name": "5 of Wands",
        "emojis": "",
        "attribution": "Mars in 5th house in the sense of playful and sporting competition.",
        "att2": "",
        "description": "challenge, measuring strength, sporting competition, playfulness",
    },
    "6-of-wands": {
        "name": "6 of Wands",
        "emojis": "",
        "attribution": "Jupiter in 10th house as an expression of success and recognition.",
        "att2": "",
        "description": "victory, success, recognition, good news, satisfaction",
    },
    "7-of-wands": {
        "name": "7 of Wands",
        "emojis": "",
        "attribution": "Mercury/Mars in aspect to Saturn as the skilled struggle against resistance.",
        "att2": "",
        "description": "attacked, competition, envy, defending one's position, holding one's own",
    },
    "8-of-wands": {
        "name": "8 of Wands",
        "emojis": "",
        "attribution": "The time factor in astrological forecasting; the moment of the triggering of transits, directions, progressions, rhythms, etc.",
        "att2": "",
        "description": "events in motion, something in the air, quick developments, good news",
    },
    "9-of-wands": {
        "name": "9 of Wands",
        "emojis": "",
        "attribution": "Saturn/Venus as a protective and defensive stance.",
        "att2": "",
        "description": "defiance, resistance, defensive stance, old wounds, closing off",
    },
    "10-of-wands": {
        "name": "10 of Wands",
        "emojis": "",
        "attribution": "Saturn/Sun in the sense of heaviness and oppression, or Saturn in 11th house as expression of lacking perspective.",
        "att2": "",
        "description": "oppression, burden, stress, excessive demands, heaviness",
    },
    "page-of-wands": {
        "name": "Page of Wands",
        "emojis": "",
        "attribution": "Venus in connection with the Moon in Sagittarius as the opportunity that is enthusiastically accepted.",
        "att2": "",
        "description": "rousing impulse, opportunity for growth, adventure, courage",
    },
    "knight-of-wands": {
        "name": "Knight of Wands",
        "emojis": "",
        "attribution": "Mars in Aries as expression of initiative, desire for experience, thirst for adventure, temperament, and impatience.",
        "att2": "",
        "description": "hot atmosphere, high spirits, impatience, passion, impulsiveness",
    },
    "queen-of-wands": {
        "name": "Queen of Wands",
        "emojis": "",
        "attribution": "The Moon in Leo in the sense of love of life, temperament, pride, self-determination, and uncontrollability.",
        "att2": "",
        "description": "self-confidence, self-determination, thirst for life, independence",
    },
    "king-of-wands": {
        "name": "King of Wands",
        "emojis": "",
        "attribution": "Sun in Leo as expression of self assurance and sovereignty.",
        "att2": "",
        "description": "dynamic power, self-assurance, persuasion, strong motivation",
    },
    "ace-of-swords": {
        "name": "Ace of Swords",
        "emojis": "",
        "attribution": "Mercury/Mars in the sense of astuteness and decisive power or Mercury/Jupiter as growth of perception and higher reason.",
        "att2": "",
        "description": "higher reason, clarity, decision power, analyzing problems",
    },
    "2-of-swords": {
        "name": "2 of Swords",
        "emojis": "",
        "attribution": "Moon in Gemini as expression of deep inner doubt.",
        "att2": "",
        "description": "gnawing doubts, inner conflict, blocking intuition, stalemate",
    },
    "3-of-swords": {
        "name": "3 of Swords",
        "emojis": "",
        "attribution": "Mars/Moon as expression of hurt feelings. In connection with Mercury as the decision is made in opposition to the feelings.",
        "att2": "",
        "description": "painful insight, decision against feelings, disappointment, heartache",
    },
    "4-of-swords": {
        "name": "4 of Swords",
        "emojis": "",
        "attribution": "Saturn in 5th house as expression of forestalled creativity or in 6th house as a sign of illness.",
        "att2": "",
        "description": "stagnation, forced rest, illness, exhaustion, need for break",
    },
    "5-of-swords": {
        "name": "5 of Swords",
        "emojis": "",
        "attribution": "Mars in Scorpio in its dark expression as destructive power and vileness.",
        "att2": "",
        "description": "callousness, destruction, vileness, humiliation, Pyrrhic victory",
    },
    "6-of-swords": {
        "name": "6 of Swords",
        "emojis": "",
        "attribution": "Mars in 4th house as the departure from familiar surroundings, and Mercury in 9th house as the search for new horizons.",
        "att2": "",
        "description": "departure, uncertainty, reaching new shores, leaving the familiar",
    },
    "7-of-swords": {
        "name": "7 of Swords",
        "emojis": "",
        "attribution": "Mercury in the sense of cunning, fraud, baseness, and insincerity.",
        "att2": "",
        "description": "cunning, trickery, dishonesty, deception, impudence",
    },
    "8-of-swords": {
        "name": "8 of Swords",
        "emojis": "",
        "attribution": "Saturn in 4th house, an expression of inner inhibitions.",
        "att2": "",
        "description": "inhibitions, inner barriers, feeling trapped, self-imposed restriction",
    },
    "9-of-swords": {
        "name": "9 of Swords",
        "emojis": "",
        "attribution": "Saturn/Moon as worry, depression, and feelings of guilt.",
        "att2": "",
        "description": "worry, depression, sleepless nights, guilt, fear of failure",
    },
    "10-of-swords": {
        "name": "10 of Swords",
        "emojis": "",
        "attribution": "Mars/Saturn as the random violent end.",
        "att2": "",
        "description": "arbitrary end, violent separation, painful cutting of ties, drawing a line",
    },
    "page-of-swords": {
        "name": "Page of Swords",
        "emojis": "",
        "attribution": "Mars in 3rd house or in difficult aspect to Mercury as the sower of disputes and discord.",
        "att2": "",
        "description": "conflict, clarifying dispute, criticism, fresh breeze, threat",
    },
    "knight-of-swords": {
        "name": "Knight of Swords",
        "emojis": "",
        "attribution": "Saturn/Venus as coldness and harshness in relationships and contacts, or Mars/Mercury as the acuteness of perception and confrontation.",
        "att2": "",
        "description": "coldness, harsh conflict, aggression, biting criticism, discord",
    },
    "queen-of-swords": {
        "name": "Queen of Swords",
        "emojis": "",
        "attribution": "Sun in Aquarius in the sense of independence, individuality, and wise perception.",
        "att2": "",
        "description": "independence, sharp wit, alertness, cleverness, self-reliance",
    },
    "king-of-swords": {
        "name": "King of Swords",
        "emojis": "",
        "attribution": "Mercury in Gemini in the sense of witty, well-versed, cunning, and tricky.",
        "att2": "",
        "description": "sharp intellect, analytical mind, strategy, criticism, emotional coolness",
    },
    "ace-of-pentacles": {
        "name": "Ace of Pentacles",
        "emojis": "",
        "attribution": "Venus in 2nd house as the opportunity to attain inner as well as external happiness and riches.",
        "att2": "",
        "description": "inner and outer wealth, great opportunity, stability, happiness",
    },
    "2-of-pentacles": {
        "name": "2 of Pentacles",
        "emojis": "",
        "attribution": "The Moon close to the Ascendant in the sense of an easy willingness to adapt and Moon/Mars in the sense of fickleness.",
        "att2": "",
        "description": "flexibility, playfulness, adaptability, carefree indecision",
    },
    "3-of-pentacles": {
        "name": "3 of Pentacles",
        "emojis": "",
        "attribution": "Jupiter/Mars in the sense of successful activity; or Saturn’s transit over its radix position as an entry into a new period of life.",
        "att2": "",
        "description": "successful test, qualification, moving up, higher level",
    },
    "4-of-pentacles": {
        "name": "4 of Pentacles",
        "emojis": "",
        "attribution": "Saturn in 2nd house as the expression of a compulsive drive for security.",
        "att2": "",
        "description": "clinging, exaggerated security, greed, rigidity, fear of change",
    },
    "5-of-pentacles": {
        "name": "5 of Pentacles",
        "emojis": "",
        "attribution": "Saturn in 2nd house as expression of crises and tight spots.",
        "att2": "",
        "description": "crisis, deprivation, insecurity, poverty consciousness, tight spot",
    },
    "6-of-pentacles": {
        "name": "6 of Pentacles",
        "emojis": "",
        "attribution": "Jupiter in Pisces as willingness to help, Jupiter in Leo as generosity, Jupiter in Aquarius as tolerance.",
        "att2": "",
        "description": "generosity, helpfulness, tolerance, support, reward",
    },
    "7-of-pentacles": {
        "name": "7 of Pentacles",
        "emojis": "",
        "attribution": "Jupiter/Saturn in the sense of patience and slow but certain growth.",
        "att2": "",
        "description": "patience, slow growth, waiting for harvest, perseverance",
    },
    "8-of-pentacles": {
        "name": "8 of Pentacles",
        "emojis": "",
        "attribution": "Mercury in 3rd house in the sense of desire to learn and skillfulness.",
        "att2": "",
        "description": "new beginning, learning, apprentice, promising start, skill",
    },
    "9-of-pentacles": {
        "name": "9 of Pentacles",
        "emojis": "",
        "attribution": "Jupiter/Venus in 5th house as the great gain.",
        "att2": "",
        "description": "favorable opportunity, surprise profit, making a catch, windfall",
    },
    "10-of-pentacles": {
        "name": "10 of Pentacles",
        "emojis": "",
        "attribution": "Jupiter in 2nd house in the sense of abundance and wealth.",
        "att2": "",
        "description": "wealth, abundance, security, stability, richness of thought",
    },
    "page-of-pentacles": {
        "name": "Page of Pentacles",
        "emojis": "",
        "attribution": "Uranus and Venus in connection with Taurus as the surprising and valuable opportunity.",
        "att2": "",
        "description": "concrete offer, solid opportunity, feasible suggestion, sensual experience",
    },
    "knight-of-pentacles": {
        "name": "Knight of Pentacles",
        "emojis": "",
        "attribution": "Jupiter in Taurus as the sense of lasting, solid, and mature values.",
        "att2": "",
        "description": "solid foundation, perseverance, diligence, reliability, realism",
    },
    "queen-of-pentacles": {
        "name": "Queen of Pentacles",
        "emojis": "",
        "attribution": "The Moon in Taurus in the sense of rootedness, fertility, and sense of family.",
        "att2": "",
        "description": "pragmatism, fertility, down-to-earth warmth, sensuality, steadfastness",
    },
    "king-of-pentacles": {
        "name": "King of Pentacles",
        "emojis": "",
        "attribution": "The Sun in Taurus as an expression of striving for possessions, sensual pleasure, and objectivity.",
        "att2": "",
        "description": "sense of reality, reliability, enjoyment, tangible assets, consistency",
    },
    "ace-of-cups": {
        "name": "Ace of Cups",
        "emojis": "",
        "attribution": "Neptune/Jupiter in harmonious relation to the Sun as the grace of deepest fulfillment.",
        "att2": "",
        "description": "deepest fulfillment, true love, grace, chance for happiness",
    },
    "2-of-cups": {
        "name": "2 of Cups",
        "emojis": "",
        "attribution": "Venus at the Ascendant in the sense of a loving encounter.",
        "att2": "",
        "description": "loving encounter, reconciliation, flirtation, harmony, partnership",
    },
    "3-of-cups": {
        "name": "3 of Cups",
        "emojis": "",
        "attribution": "Venus as the expression of cheerfulness and thankfulness.",
        "att2": "",
        "description": "joy, gratitude, celebration, happy times, fulfillment",
    },
    "4-of-cups": {
        "name": "4 of Cups",
        "emojis": "",
        "attribution": "Mars in Cancer as expression of vexation and sullenness.",
        "att2": "",
        "description": "sullenness, apathy, hurt feelings, overlooking opportunities",
    },
    "5-of-cups": {
        "name": "5 of Cups",
        "emojis": "",
        "attribution": "Saturn/Venus or Saturn/Moon as expression of parting, pain, distress, and dejection.",
        "att2": "",
        "description": "sorrow, pain, disappointment, regret, breaking up",
    },
    "6-of-cups": {
        "name": "6 of Cups",
        "emojis": "",
        "attribution": "Moon in Pisces as expression of wistful, melancholy remembrance, or Moon in Cancer as romantic dreaminess.",
        "att2": "",
        "description": "memories, nostalgia, looking back, romantic dreaminess, childhood",
    },
    "7-of-cups": {
        "name": "7 of Cups",
        "emojis": "",
        "attribution": "Neptune as expression of deception, illusion, and withdrawal from the world.",
        "att2": "",
        "description": "illusions, deception, false hopes, dream castles, confusion",
    },
    "8-of-cups": {
        "name": "8 of Cups",
        "emojis": "",
        "attribution": "Saturn/Moon as parting with a heavy heart.",
        "att2": "",
        "description": "parting with heavy heart, leaving familiar for unknown, letting go",
    },
    "9-of-cups": {
        "name": "9 of Cups",
        "emojis": "",
        "attribution": "Moon in Taurus in the sense of enjoyment and sociability.",
        "att2": "",
        "description": "joy of life, sociability, enjoyment, carefree pleasure",
    },
    "10-of-cups": {
        "name": "10 of Cups",
        "emojis": "",
        "attribution": "Jupiter/Moon as expression of security and wonderful closeness.",
        "att2": "",
        "description": "harmony, security, family happiness, deep love, peace",
    },
    "page-of-cups": {
        "name": "Page of Cups",
        "emojis": "",
        "attribution": "Venus in 1st house as a reconciliatory impulse or in 5th house as playful pleasure.",
        "att2": "",
        "description": "friendly gesture, reconciliation, offer of peace, sympathy, invitation",
    },
    "knight-of-cups": {
        "name": "Knight of Cups",
        "emojis": "",
        "attribution": "Venus/Moon as expression of intense closeness and good moods.",
        "att2": "",
        "description": "romantic mood, harmony, being in love, peace, good atmosphere",
    },
    "queen-of-cups": {
        "name": "Queen of Cups",
        "emojis": "",
        "attribution": "Moon in Pisces as expression of tact, willingness to help, and mediality.",
        "att2": "",
        "description": "sensitivity, intuition, mediality, helpfulness, mysteriousness",
    },
    "king-of-cups": {
        "name": "King of Cups",
        "emojis": "",
        "attribution": "Sun in Pisces as expression of mediality, intuitive knowledge, and willingness to help.",
        "att2": "",
        "description": "emotional depth, mediality, intuitive knowledge, understanding, healing",
    },
}


def get_image_path(card_key):
    """Get the file path for a card image"""
    return f"images/rws/{card_key}.png"


def draw_card():
    """Draw a random card (no reversals)"""
    card_key = random.choice(list(RWS_DECK.keys()))
    return card_key


def search_card(keyword):
    """Search for a card by name or keyword"""
    keyword_lower = keyword.lower()
    for card_key, card_data in RWS_DECK.items():
        if keyword_lower in card_data["name"].lower():
            return card_key
    return None


async def send_tarot_card(ctx, card_key=None):
    """Send a tarot card to Discord channel"""
    # If no card specified, draw random
    if card_key is None:
        card_key = draw_card()

    # Get card data
    card = RWS_DECK[card_key]
    card_name = card["name"]
    emojis = card["emojis"]
    attribution = card["attribution"]
    description = card["description"]
    att2 = card["att2"]

    # Create embed
    embed = discord.Embed(
        title=card_name,
        description=f"\n{emojis}  \n*({attribution})*\n*{att2}*\n\n{description}",
        color=discord.Color.from_rgb(0, 0, 128),
    )

    embed.set_footer(text="RWS")

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
