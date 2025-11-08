"""
Thoth Tarot Module for Discord Bot
Contains deck data and card drawing functionality
"""

import random
import discord
from PIL import Image
import io
import os

# ============================================================
# TAROT DECK DATA - Full Aleister Crowley Thoth LWB Descriptions
# ============================================================

TAROT_DECK = {
    # MAJOR ARCANA (0-21)
    "00-the-fool": {
        "name": "The Fool",
        "description": "Idea, thought, spirituality, that which endeavors to transcend earth. Folly, eccentricity, or even mania. Redemption from material matters. Vagabond, wanderer. Poetical and dreamy nature."
    },
    "01-the-magus": {
        "name": "The Magus",
        "description": "Skill, wisdom, adaptation, craft, cunning, eloquence, subtlety in material matters. Flexibility, Business transactions. Learning or intelligence in hand."
    },
    "02-the-priestess": {
        "name": "The Priestess",
        "description": "Pure, exalted and gracious influence enters the matter. Change, alternation, increase and decrease. Fluctuation whether for good or evil is definitely indicated maintained."
    },
    "03-the-empress": {
        "name": "The Empress",
        "description": "Love, Beauty, Happiness, Pleasure, Success, Luxury, Good fortune, Graciousness, Elegance, Gentleness. Dissipation, Debauchery, Idleness, Sensuality."
    },
    "04-the-emperor": {
        "name": "The Emperor",
        "description": "War, Conquest, Victory, Strife, Stability, Power. Originally: Government, Energy, Ambition. Over-weening pride, Megalomania, Rashness. Stubborn strength, Toil, Endurance, Persistance. Teaching, Help from superiors. Patience, Organization, Peace, Goodness of heart. Occult force voluntarily invoked."
    },
    "05-the-hierophant": {
        "name": "The Hierophant",
        "description": "Divine wisdom, Manifestation, Explanation, Teaching, Stubborn strength, Toil, Endurance, Persistence. Teaching, Help from superiors. Patience, Organization, Peace, Goodness of heart, Occult force voluntarily invoked."
    },
    "06-the-lovers": {
        "name": "The Lovers",
        "description": "Openness to inspiration, Intuition, Intelligence, Goodness, Kindness, Gentleness, Beauty, Love. Self-contradiction, Instability, Indecision. Union in a shallow degree with others, Superficiality."
    },
    "07-the-chariot": {
        "name": "The Chariot",
        "description": "Triumph, Victory, Hope, Obedience, Faithfulness, Health, Success, though sometimes not enduring. Authority under authority. Violence in maintaining traditional."
    },
    "08-adjustment": {
        "name": "Adjustment",
        "description": "Justice, Balance, Adjustment, Suspension of action pending decision. May refer to lawsuits, trials, marriages, divorces."
    },
    "09-the-hermit": {
        "name": "The Hermit",
        "description": "Illumination from within, Divine inspiration, Wisdom, Prudence, Circumspection, Retirement from participation in current events."
    },
    "10-fortune": {
        "name": "Fortune",
        "description": "Change of fortune, generally good. Destiny, Luck. Inevitability of Fate. Control of the force. Great love affair. Resort to magic."
    },
    "11-lust": {
        "name": "Lust",
        "description": "Courage, Strength, Energy, Action, Magnanimity. A noble woman. Power not arrested in the act of judgment. Ill-dignified: Cruelty, Lust, Wickedness."
    },
    "12-the-hanged-man": {
        "name": "The Hanged Man",
        "description": "Redemption through sacrifice, Enforced sacrifice, Scheming, Punishment, Loss, Defeat, Failure, Death. Transformation, Change, voluntary or involuntary, perhaps sudden and unexpected. Apparent death or destruction of body and goods from a Higher perspective."
    },
    "13-death": {
        "name": "Death",
        "description": "Transformation, Change, voluntary or involuntary, perhaps sudden and unexpected. Apparent death or destruction of body and goods from a Higher perspective. Time, Creation, ultimate practicable action, Realization, Action based on accurate calculation, Economy, Management. The way of escape."
    },
    "14-art": {
        "name": "Art",
        "description": "Combination of Forces, Realization, Action. Combination of forces sometimes good but sometimes disruptive. Productive of strife and disease. Truth, Shamelessness, Manifestation. Recovery from sickness, but sometimes a long and dangerous convalescence. Death."
    },
    "15-the-devil": {
        "name": "The Devil",
        "description": "Blind impulse, Irresistibly strong and unscrupulous ambition. Temptation. Obsession. Secret plan about to be executed. Ill-dignified: Bondage, Weakness. Malice prepense. Fate."
    },
    "16-the-tower": {
        "name": "The Tower",
        "description": "Quarrel, Combat, Danger, Ruin. Destruction of accustomed ideas and disruption. Courage, Sudden death. Escape from prison and all it implies."
    },
    "17-the-star": {
        "name": "The Star",
        "description": "Hope, Unexpected help, Clarity of vision, Spiritual insight. Error of judgment, Dreaminess, Disappointment."
    },
    "18-the-moon": {
        "name": "The Moon",
        "description": "Illusion, Deception, Bewilderment, Hysterical, Madness, Dreaminess, Falsehood, Voluntary change. The brink of an important change. This card is very sensitive to dignity. May mean poetic or artistic ability. Practical error. Truth, Shamelessness, Manifestation. Recovery from sickness, but sometimes sudden death."
    },
    "19-the-sun": {
        "name": "The Sun",
        "description": "Glory, Gain, riches, display, vanity, arrogance. Sudden break up or overturn. Truth, Shamelessness, Manifestation. Recovery from sickness, but sometimes sudden death. Arrogance, Vanity."
    },
    "20-the-aeon": {
        "name": "The Aeon",
        "description": "Final decision concerning the past. New current for the future. Always represents the taking of a definite step."
    },
    "21-the-universe": {
        "name": "The Universe",
        "description": "The matter itself, Synthesis, World. The end of the matter, Delay, Opposition, Inertia, Perseverance. Patience, The crystallization of the whole matter involved."
    },
    
    # WANDS - Fire
    "wands-01": {
        "name": "Ace of Wands",
        "description": "Root of the Powers of Fire. Energy, Strength. Natural Force as opposed to invoked force."
    },
    "wands-02": {
        "name": "Two of Wands - Dominion",
        "description": "Fire in its most destructive aspect. Cruelty and malice. Selfishness. Lust of result. Bold, fierce, aggressive but often intolerant and lacking in persistence. Another: Boldness, Courage, Fierceness, Shamelessness. Turbulence, Generosity."
    },
    "wands-03": {
        "name": "Three of Wands - Virtue",
        "description": "Established strength. Success after struggle. Pride and arrogance. Realization of hope. Nobility. Conceit and self-assertion. Another: Ill-dignified: Pride and arrogance."
    },
    "wands-04": {
        "name": "Four of Wands - Completion",
        "description": "Perfected work. Settlement. Completion after much labour. Rest. Subtlety. Cleverness. Conclusions from experience. Unreliability from fickleness and hurriedness of action."
    },
    "wands-05": {
        "name": "Five of Wands - Strife",
        "description": "Quarreling, Competition, Cruelty. Violence, Lust and desire. May be prodigality or generosity according to dignity."
    },
    "wands-06": {
        "name": "Six of Wands - Victory",
        "description": "Energy tried and justified by victory. Triumph, Energy in life at starting but too much force applied too rapidly. Possible victory. Obstacles and difficulties yet courage to meet them. Victory in small things."
    },
    "wands-07": {
        "name": "Seven of Wands - Valour",
        "description": "Possible victory dependent on the energy of high velocity. Activity. Approach to goal. Letter or message. Rapidly. Boldness. Freedom. Too much force applied too quickly. Ill-dignified: Quarreling."
    },
    "wands-08": {
        "name": "Eight of Wands - Swiftness",
        "description": "Too much force applied too rapidly. Violent but quite transient effect. Speech, communication, conversation. Swiftness. Hasty. Boldness. Freedom. Approach to goal. Letter or message. Rapidly. Boldness. Freedom."
    },
    "wands-09": {
        "name": "Nine of Wands - Strength",
        "description": "Power, Health, Success after opposition and strife, Tremendous force, Recovery from sickness, Victory after apprehension and fear."
    },
    "wands-10": {
        "name": "Ten of Wands - Oppression",
        "description": "Force detached from spiritual sources. Cruel and overbearing strength. Malice. Revenge. Injustice. Obstinacy. Ill-dignified: Generosity if particularly well-dignified."
    },
    "wands-princess": {
        "name": "Princess of Wands",
        "description": "Represents the earthy part of fire. A young woman, strong and beautiful, enthusiastic. Ill-dignified: Superficial, Theatrical, Cruel, Unstable, Domineering."
    },
    "wands-prince": {
        "name": "Prince of Wands",
        "description": "Represents the airy part of fire. A young man, swift and strong, impulsive, violent, just, noble and generous with a sense of ideas. Ill-dignified: Cruel, Intolerant, Prejudiced, who may be a coward."
    },
    "wands-queen": {
        "name": "Queen of Wands",
        "description": "Represents the watery part of fire. A woman of adaptability, persistent energy, calm authority, with great power to attract. Ill-dignified: A woman who is stupid, obstinate, revengeful, tyrannical, domineering and interfering."
    },
    "wands-knight": {
        "name": "Knight of Wands",
        "description": "Represents the fiery part of life. A man with the qualities of activity, generosity, impetuosity, pride and swiftness, with strength but sometimes changeable."
    },
    
    # CUPS - Water
    "cups-01": {
        "name": "Ace of Cups",
        "description": "Root of the Powers of Water. Fertility, Productiveness, Beauty, Pleasure and happiness."
    },
    "cups-02": {
        "name": "Two of Cups - Love",
        "description": "Harmony of male and female interpreted in the widest sense. Harmony between various factors on any question. Love, Friendship, Pleasure. Warm friendship, Mirth. Folly, Dissipation, Waste, Silly actions."
    },
    "cups-03": {
        "name": "Three of Cups - Abundance",
        "description": "Spiritual basis of fertility. Plenty. Hospitality. Pleasure. Sensuality. Passive success. Love, Kindness. Abundance. Plenty. Passive success. The good things of life in a transient and therefore cannot be relied on."
    },
    "cups-04": {
        "name": "Four of Cups - Luxury",
        "description": "Weakness. Abandonment to desire. Pleasure. Possibly approaching their end. Impatience. The seeds of decay in pleasure."
    },
    "cups-05": {
        "name": "Five of Cups - Disappointment",
        "description": "End of pleasure. Disturbance when least expected. Misfortune. Disappointment in love. Unkindness from friends. Loss of friendship. Treachery. Ill will. Sadness. Vain regret."
    },
    "cups-06": {
        "name": "Six of Cups - Pleasure",
        "description": "Well-being. Harmony of natural forces without effort or strain. Ease. Satisfaction. Happiness. Success. Fulfillment of sexual will. Beginning of steady increase (but beginning only). Complacency. Vanity. Thanklessness. Another: Intoxication. Guilt. Lying. Deceit. Promises unfulfilled. Lust. Formation. Dissipation in love and friendship. Vanity."
    },
    "cups-07": {
        "name": "Seven of Cups - Debauch",
        "description": "Delusion. Illusory success. Drug addiction. Intoxication. Guilt. Lying. Deceit. Promises unfulfilled. Lust. Formation. Dissipation in love and friendship. Vanity."
    },
    "cups-08": {
        "name": "Eight of Cups - Indolence",
        "description": "Abandoned success. Decline of interest in anything. Temporary success but without further result. Instability. Misery and repining. Journeying from place to place. May mean leaving material success for something higher."
    },
    "cups-09": {
        "name": "Nine of Cups - Happiness",
        "description": "Complete success. Pleasure and happiness, wishes fulfilled. Self-satisfaction. Sensuality. Perfect or almost perfect happiness. Almost perfect but perhaps temporary. Well-dignified: Danger of vanity, self-praise, complacent smugness."
    },
    "cups-10": {
        "name": "Ten of Cups - Satiety",
        "description": "Pursuit of pleasure crowned with perfect success but incomplete. Matters arranged and settled as wished. Complete success. Pleasure, dissipation, debauchery. Lasting success. Inspired action from above. Permanent peaceful happiness."
    },
    "cups-princess": {
        "name": "Princess of Cups",
        "description": "Represents the earthy part of water. A young woman, innocent, gracious, at sweetness, voluptuousness, gentle, kind and tender. A dreamy, at times indolent person. Ill-dignified: Selfish and luxurious woman."
    },
    "cups-prince": {
        "name": "Prince of Cups",
        "description": "Represents the airy part of water. A young man whose characteristics are subtle, secret and artistic, whose calm surface masks intense passion, caring intensely for power and wisdom and ruthless in his own aims. Ill-dignified: Intensely evil, merciless, grasping man."
    },
    "cups-queen": {
        "name": "Queen of Cups",
        "description": "Represents the watery part of water. A woman who may be beloved for the sweetness of her nature, loving, beautiful, not always constant or reliable or liable to break her words. She is much affected by surrounding influences, therefore more dependent on others for good or ill than most people. She is poetic and dreamy. Ill-dignified: Indolent, selfish and luxurious woman."
    },
    "cups-knight": {
        "name": "Knight of Cups",
        "description": "Represents the fiery part of water. A man whose nature is a compound of noble moral qualities, graceful and somewhat ethereal, but with lack of conscience or sense of responsibility. Ill-dignified: Subtlety, artifice, intensity, fierce and overbearing nature."
    },
    
    # SWORDS - Air
    "swords-01": {
        "name": "Ace of Swords",
        "description": "Root of the Powers of Air. Invoked force as contrasted with natural force (compare Ace of Wands). Represents great power for good or evil but invoked. Conquest, Whirling force, Activity. Strength through trouble. As affirmation of justice upholding Divine authority, may become sword of wrath, punishment and affliction."
    },
    "swords-02": {
        "name": "Two of Swords - Peace",
        "description": "Contradictory characteristics in the same nature, Sacrifice and trouble giving birth to strength, Quarrel made up and peace restored, yet tension remaining. Pleasure after pain. Truth and untruth. Indecision. Actions sometimes selfish, sometimes unselfish."
    },
    "swords-03": {
        "name": "Three of Swords - Sorrow",
        "description": "Melancholy. Unhappiness. Tears. Disruption. Sowing of discord and strife. Delay. Absence. Separation. Mirth in forbidden pleasures. Deceit. Well-dignified: Singing, Faithfulness in promises. Honesty in money transactions."
    },
    "swords-04": {
        "name": "Four of Swords - Truce",
        "description": "Rest from strife. Relief. Peace after war. Relaxation of anxiety. Refuge from mental chaos. Recovery from sickness, Change for the better after struggle. Authority in the intellectual field. Stability. Establishment of dogma."
    },
    "swords-05": {
        "name": "Five of Swords - Defeat",
        "description": "Loss, Contest, Defeat, Strife. Weakness, Slander, Failure. Lying. Malice and spite. Cruelty. Calumny. Cowardice. Ill-dignified: Perverseness. Tact. Stiffness. Pettiness. Lies. Separator of friends. A busybody, cruel yet cowardly, evil speaking."
    },
    "swords-06": {
        "name": "Six of Swords - Science",
        "description": "Earned success. Intelligence in material things. Logical Labor. Work. Success after anxiety. Passage from difficulty. Selfishness by way of intellect. Ill-dignified: Selfishness in labour. Conceit."
    },
    "swords-07": {
        "name": "Seven of Swords - Futility",
        "description": "Unstable effort. Vacillation. Vain striving. Journey by land. Unprofitable speculation. Disappointment. Journeying perhaps with a dishonest companion. Yielding when victory is within the grasp. Inclination too powerful for resistance but not necessarily a sign of wickedness. Crime or dishonor not necessarily implied. Journey by land. Untrustworthy person."
    },
    "swords-08": {
        "name": "Eight of Swords - Interference",
        "description": "Wants courage to rely on details quarrel. Narrowness. Pettiness. Overruled by intelligence. Shilly. Pettiness of persistence. Shilly-shallying, lack of persistence. Unforeseen bad luck. Restriction. Great force applied to small matters and so wasted. Too much force expended in detail against something too strong."
    },
    "swords-09": {
        "name": "Nine of Swords - Cruelty",
        "description": "Agony of mind. Despair. Hopelessness. Suffering. Burden. Obsession. Illness. Loss. Misery. Burden. Oppression. Unrelieved fatigue. Death-like condition. Lying. Slander. Dishonesty. Faithlessness. Patience. Unselfishness."
    },
    "swords-10": {
        "name": "Ten of Swords - Ruin",
        "description": "Reason divorced from reality. Death. Failure. Disruption. The latter chiefly if such a mode of Dissolution is natural. Clever, eloquent and insolent person, immoral and tale-bearer. Spiritually, may herald the end of delusion."
    },
    "swords-princess": {
        "name": "Princess of Swords",
        "description": "Represents the earthy part of air. A young woman, stern and revengeful, with destructive logic, firm and aggressive, with great practical wisdom and subtlety, dexterous in material and practical affairs."
    },
    "swords-prince": {
        "name": "Prince of Swords",
        "description": "Represents the airy part of air. A young man, swift and clever, fierce, delicate and courageous but often unreliable."
    },
    "swords-queen": {
        "name": "Queen of Swords",
        "description": "Represents the watery part of air. A graceful woman, intensely perceptive, a keen observer, subtle interpreter, intense individualism, calm exterior, accurate at recording and sensing, gracious and just. Ill-dignified: Cruel, sly, deceitful and unreliable, she may be domineering and very faithless."
    },
    "swords-knight": {
        "name": "Knight of Swords",
        "description": "Represents the fiery part of air. A skillful and clever, fierce, delicate and courageous but often unreliable. A man with many good qualities, but hardly lovable and more to be respected than liked. Ill-dignified: A man remarkable in the same skillful and clever, fierce, delicate and courageous but often unreliable."
    },
    
    # DISKS - Earth
    "disks-01": {
        "name": "Ace of Disks",
        "description": "Root of the Powers of Earth. Material gain. Power. Labor. Wealth. Contentment. Materiality in all senses. For Crowley, this card is affirmation of the identity of Sun and earth, spirit and matter."
    },
    "disks-02": {
        "name": "Two of Disks - Change",
        "description": "Harmony of change. Alternation of gain and loss, weakness and strength, elation and melancholy. Varying occupation. Wandering. Visit to friends. Pleasant change. Industrious, clever, kind and trustworthy person."
    },
    "disks-03": {
        "name": "Three of Disks - Works",
        "description": "Paid employment. Commercial transaction. Constructive building up. Increase of material things. Commencement of matters to be established later. Business, Paid employment. Commercial transaction. Constructive building up. Ill-dignified: Narrow, prejudiced, greedy person seeking impossibilities."
    },
    "disks-04": {
        "name": "Four of Disks - Power",
        "description": "Earthly power. Law and order. Gain of money and influence. Earthly power but nothing beyond. Success. Rank. Dominion. Skill in directing practical forces. Prejudice. Covetousness."
    },
    "disks-05": {
        "name": "Five of Disks - Worry",
        "description": "Intense strain with continued inaction. Loss of money. Profession or business in danger. Monetary anxiety. Poverty. Well-dignified: Labor. Toil. Loss of profession. Loss of money. Trouble about material things."
    },
    "disks-06": {
        "name": "Six of Disks - Success",
        "description": "Success and gain in material things. Power. Influence. Nobility. Philanthropy. Somewhat dreamy and transitory situation. Insolence. Concern with wealth. Prodigality."
    },
    "disks-07": {
        "name": "Seven of Disks - Failure",
        "description": "Labor abandoned. Sloth. Unprofitable speculations. Little gain for much labor. Promises unfulfilled. Disappointment. Little gain from much labor. Well-dignified: Delay but growth. Honorable work undertaken for the love of work with no hope of reward."
    },
    "disks-08": {
        "name": "Eight of Disks - Prudence",
        "description": "Intelligence applied to material affairs. Agriculture. Building. Skill. Cunning. Industriousness. Ill-dignified: Penny wise and pound foolish attitudes. Avariciousness and hoarding. Meanness. Over-carefulness in small things at the expense of the great."
    },
    "disks-09": {
        "name": "Nine of Disks - Gain",
        "description": "Much increase of goods or of money in material affairs. Inheritance. Great increase of wealth. Complete confidence of material affairs. Theft and knavery. Disappearance or dissipation of goods. Substance. Gain. Treasures and riches. Good things of this world. Complacency. Consciousness. Thrift. Wisdom. Certainty."
    },
    "disks-10": {
        "name": "Ten of Disks - Wealth",
        "description": "Material prosperity and riches. Completion of material fortune, but nothing beyond. Completion of material gain, mean partial loss, dullness of mind with acuity and profit in money transactions. Meanness. Sordid selfishness."
    },
    "disks-princess": {
        "name": "Princess of Disks",
        "description": "Represents the earthy part of earth. A young woman, beautiful and strong, generous and kind, charming and magnetic in all directions, affectionate and kind, charming, magnetic in all directions, affectionate and kind. Serious and thoughtful. Ill-dignified: Servile. Foolish. Capricious. Prone to debauch and moodiness."
    },
    "disks-prince": {
        "name": "Prince of Disks",
        "description": "Represents the airy part of earth. A young man at his best when in authority, manager, steadfast worker, competent, perhaps considered dull, somewhat lacking in emotion or sentiment of spiritual types, slow to anger but fearsome if aroused."
    },
    "disks-queen": {
        "name": "Queen of Disks",
        "description": "Represents the watery part of earth. A woman of great heart and intelligence, thoughtful and kindly yet capable of much fascination. She is quiet and strong, as if befriending a secret wonder, which she will not reveal. She is generous and gracious, benevolent, preserving. Ill-dignified: Wasteful and prodigal woman at war with the elements or else unduly possessive."
    },
    "disks-knight": {
        "name": "Knight of Disks",
        "description": "Represents the fiery part of earth. A farmer, patient, laborious, reliable in material things, perhaps somewhat dull and heavy, or too Ill-dignified: Avaricious, grasping, dull, jealous and animal man."
    }
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
    description = card["description"]
    
    # Create embed
    embed = discord.Embed(
        title=card_name,
        description=description,
        color=discord.Color.blue()
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