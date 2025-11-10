
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
        "description": "In spiritual matters, represents ideas and thoughts, which endeavor to transcend earth. In material matters, reveals folly, eccentricity, even mania. It represents a sudden, unexpected impulse."
    },
    "01-the-magus": {
        "name": "The Magus",
        "emojis": "☿️ 🪄 🎪 📜 🐒",
        "attribution": "Mercury • Beth",
        "description": "Skill. Wisdom. Adroitness. Elasticity. Craft. Cunning. Deceit. Theft. Sometimes esoteric wisdom or power. Messages. Business transactions. Learning or intelligence interfering with the matter in hand."
    },
    "02-the-priestess": {
        "name": "The Priestess",
        "emojis": "🌙 🏹 👸 🔮 ✨",
        "attribution": "Moon • Gimel",
        "description": "Pure, exalted and gracious influence enters the matter, bringing change, alternation, increase and decrease, fluctuation. Exuberance should be tempered and careful balance maintained."
    },
    "03-the-empress": {
        "name": "The Empress",
        "emojis": "♀️ 🌹 👑 🦢 🦅",
        "attribution": "Venus • Daleth",
        "description": "Love. Beauty. Happiness. Pleasure. Success. Fruitfulness. Good fortune. Graciousness. Elegance. Gentleness. Shadow: Dissipation. Promiscuity. Idleness. Sensuality."
    },
    "04-the-emperor": {
        "name": "The Emperor",
        "emojis": "♈ 🐏 👑 ⚔️ 🦅",
        "attribution": "Aries • Tzaddi",
        "description": "War. Conquest. Victory. Strife. Power. Stability. Originality. Government. Energy. Ambition. Shadow: Arrogance. Megalomania. Rashness."
    },
    "05-the-hierophant": {
        "name": "The Hierophant",
        "emojis": "♉ 🐘 ⭐ 🕊️ 📿",
        "attribution": "Taurus • Vau",
        "description": "Divine wisdom. Inspiration. Stubborn strength. Toil. Endurance. Persistence. Teaching. Help from superiors. Patience. Organization. Peace. Goodness of heart."
    },
    "06-the-lovers": {
        "name": "The Lovers",
        "emojis": "♊ 💑 🗡️ 🥚 🦅",
        "attribution": "Gemini • Zain",
        "description": "Inspiration. Intuition. Intelligence. Innocence. Attraction. Beauty. Love. Shadow: Self-contradiction. Instability. Indecision. Superficiality. Infatuation."
    },
    "07-the-chariot": {
        "name": "The Chariot",
        "emojis": "♋ 🏺 🦁 🐂 🌊",
        "attribution": "Cancer • Cheth",
        "description": "Triumph. Victory. Hope. Obedience. Faithfulness. Health. Success, though sometimes not enduring. Shadow: Abrupt departure from traditional ideas."
    },
    "08-adjustment": {
        "name": "Adjustment",
        "emojis": "♎ ⚖️ 🗡️ 👑 💎",
        "attribution": "Libra • Lamed",
        "description": "Justice. Balance. Adjustment. Suspension of action pending decision. May refer to lawsuits, trials, marriages, contracts, etc."
    },
    "09-the-hermit": {
        "name": "The Hermit",
        "emojis": "♍ 🪔 🥚 🐍 🌾",
        "attribution": "Virgo • Yod",
        "description": "Illumination from within. Divine inspiration. Wisdom. Circumspection. Retirement."
    },
    "10-fortune": {
        "name": "Fortune",
        "emojis": "♃ 🎡 🦁 🐒 🐍",
        "attribution": "Jupiter • Kaph",
        "description": "Change of fortune, generally good. Destiny."
    },
    "11-lust": {
        "name": "Lust",
        "emojis": "♌ 🦁 👸 🏺 🔥",
        "attribution": "Leo • Teth",
        "description": "Courage. Strength. Energy. Use of magical power. Control of the life force. Great love affair."
    },
    "12-the-hanged-man": {
        "name": "The Hanged Man",
        "emojis": "🌊 ☠️ 🐍 ⚓ 🔺",
        "attribution": "Water • Mem",
        "description": "Redemption through sacrifice. New perspectives. Shadow: Punishment. Loss. Defeat. Failure. Suffering."
    },
    "13-death": {
        "name": "Death",
        "emojis": "♏ 🦂 💀 🦅 🐟",
        "attribution": "Scorpio • Nun",
        "description": "Transformation. Change, voluntary or involuntary, perhaps sudden and unexpected. Illusory death. Release through destruction."
    },
    "14-art": {
        "name": "Art",
        "emojis": "♐ 🌈 ⚗️ 🦅 🦁",
        "attribution": "Sagittarius • Samech",
        "description": "Combination of forces. Realization. Action based on accurate calculation. Economy. Management. Success after elaborate maneuvers. The way of Escape."
    },
    "15-the-devil": {
        "name": "The Devil",
        "emojis": "♑ 🐐 👁️ 🍇 🪐",
        "attribution": "Capricorn • Ayin",
        "description": "Blind impulse. Irresistibly strong. Unscrupulous. Ambition. Temptation. Obsession. Secret plan. Hard work. Endurance. Discontent. Materialism. Fate."
    },
    "16-the-tower": {
        "name": "The Tower",
        "emojis": "♂️ ⚡ 🗼 👁️ 🕊️",
        "attribution": "Mars • Peh",
        "description": "Quarrel. Combat. Danger. Ruin. Destruction of plans. Ambition. Courage. Sudden death. Escape from prison and all it implies."
    },
    "17-the-star": {
        "name": "The Star",
        "emojis": "♒ ⭐ 🌊 🌊 🌀",
        "attribution": "Aquarius • Heh",
        "description": "Hope. Unexpected help. Clarity of vision. Spiritual insight. Shadow: Dreaminess. Disappointment."
    },
    "18-the-moon": {
        "name": "The Moon",
        "emojis": "♓ 🌙 🦂 🐺 🌊",
        "attribution": "Pisces • Qoph",
        "description": "Illusion. Deception. Bewilderment. Falsehood. Voluntary change. Shadow: Hysteria. Madness."
    },
    "19-the-sun": {
        "name": "The Sun",
        "emojis": "☀️ 👶 🦋 🌹 ✨",
        "attribution": "Sun • Resh",
        "description": "Glory. Gain. Riches. Triumph. Pleasure. Truth. Shamelessness. Manifestation. Recovery. Shadow: Arrogance. Vanity."
    },
    "20-the-aeon": {
        "name": "The Aeon",
        "emojis": "🔥 👶 🌟 🐍 ✨",
        "attribution": "Fire • Shin",
        "description": "Closure. Resolution. Definitive action."
    },
    "21-the-universe": {
        "name": "The Universe",
        "emojis": "🪐 🌍 💃 🐍 ♄",
        "attribution": "Saturn • Earth • Tau",
        "description": "Essential questions. Synthesis. Delay. Completion. Opposition. Inertia. Perseverance. Patience. Crystallized thinking."
    },
    
    # WANDS - Fire
    "wands-01": {
        "name": "Ace of Wands",
        "emojis": "🔥 🌳 ⚡ 💫 🔆",
        "attribution": "Root of Fire",
        "description": "Energy. Strength. Natural Force. Sexual vigor. Natural force as opposed to invoked force."
    },
    "wands-02": {
        "name": "Two of Wands - Dominion",
        "emojis": "♂️ ♈ 🔥 ⚔️ 👑",
        "attribution": "Mars in Aries • Chokmah",
        "description": "Fire in its highest form. Force of energy. Harmony of power and justice. Influence. Boldness. Courage. Fierceness. Shadow: Restlessness. Turbulence. Obstinacy."
    },
    "wands-03": {
        "name": "Three of Wands - Virtue",
        "emojis": "☀️ ♈ 🌺 👑 ✨",
        "attribution": "Sun in Aries • Binah",
        "description": "Established strength. Success after struggle. Pride and arrogance. Realization of hope. Shadow: Conceit."
    },
    "wands-04": {
        "name": "Four of Wands - Completion",
        "emojis": "♀️ ♈ 🐏 🕊️ 🏰",
        "attribution": "Venus in Aries • Chesed",
        "description": "Perfection. Settlement. Rest. Subtlety. Cleverness. Knowledge brings conclusions. Shadow: Unreliable outcomes from overzealous action."
    },
    "wands-05": {
        "name": "Five of Wands - Strife",
        "emojis": "♄ ♌ ⚔️ 🔥 💥",
        "attribution": "Saturn in Leo • Geburah",
        "description": "Quarreling. Fighting. Competition. Cruelty. Violence. Lust. Desire. Generosity or excess spending."
    },
    "wands-06": {
        "name": "Six of Wands - Victory",
        "emojis": "♃ ♌ 🏆 🌟 ⚡",
        "attribution": "Jupiter in Leo • Tiphareth",
        "description": "Balanced energy. Love. Gain and success. Triumph after strife. Shadow: Insolence and pride."
    },
    "wands-07": {
        "name": "Seven of Wands - Valour",
        "emojis": "♂️ ♌ ⚔️ 🛡️ 🔥",
        "attribution": "Mars in Leo • Netzach",
        "description": "Struggles. Small victories. Courage to meet obstacles. Victory in small things. Shadow: Quarreling."
    },
    "wands-08": {
        "name": "Eight of Wands - Swiftness",
        "emojis": "☿️ ♐ ⚡ 🌈 💬",
        "attribution": "Mercury in Sagittarius • Hod",
        "description": "Speech. Light. Electricity. Energy of high velocity. Activity. Approaching goals. Letter. Message. Boldness. Freedom. Shadow: Too much force applied too suddenly."
    },
    "wands-09": {
        "name": "Nine of Wands - Strength",
        "emojis": "🌙 ♐ 🏹 💪 ☀️",
        "attribution": "Moon in Sagittarius • Yesod",
        "description": "Power. Health. Success after conflict. Tremendous force. Recovery. Victory follows fear. Change brings stability."
    },
    "wands-10": {
        "name": "Ten of Wands - Oppression",
        "emojis": "♄ ♐ ⚔️ 🔥 💔",
        "attribution": "Saturn in Sagittarius • Malkuth",
        "description": "Force detached from spiritual sources. Fire in its most destructive aspect. Cruelty and malice. Selfishness. Lying. Repression. Slander. Ill will. Shadow: Self-sacrifice and generosity."
    },
    "wands-princess": {
        "name": "Princess of Wands",
        "emojis": "🔥 🌍 ☀️ 💃 ⚡",
        "attribution": "Earthy part of Fire",
        "description": "Energetic, individualistic, brilliant and daring, expressive in love or anger, enthusiastic. Shadow: Superficial, theatrical, shallow, cruel, unreliable, faithless."
    },
    "wands-prince": {
        "name": "Prince of Wands",
        "emojis": "🔥 💨 🦅 🐉 ⚡",
        "attribution": "Airy part of Fire",
        "description": "A young man, swift and strong, impulsive, violent, just, noble and generous with a sense of humor. Shadow: Proud, intolerant, cruel, cowardly, and prejudiced."
    },
    "wands-queen": {
        "name": "Queen of Wands",
        "emojis": "🔥 🌊 👑 🐆 🔥",
        "attribution": "Watery part of Fire",
        "description": "Adaptability, persistent energy, calm authority, powers of attraction, generous but intolerant. Shadow: Obstinacy, revenge, dominance."
    },
    "wands-knight": {
        "name": "Knight of Wands",
        "emojis": "🔥 🔥 🏇 ⚡ 👑",
        "attribution": "Fiery part of Fire",
        "description": "Activity, generosity, pride and swiftness. Shadow: Cruelty, bigotry, petulance."
    },
    
    # CUPS - Water
    "cups-01": {
        "name": "Ace of Cups",
        "emojis": "🌊 🏺 🌊 💖 🌹",
        "attribution": "Root of Water",
        "description": "Fertility. Productivity. Beauty. Pleasure and happiness."
    },
    "cups-02": {
        "name": "Two of Cups - Love",
        "emojis": "♀️ ♋ 💑 🐬 🌺",
        "attribution": "Venus in Cancer • Chokmah",
        "description": "Harmony of male and female sensibilities. Radiant joy. Ecstasy. Pleasure. Warm friendship. Intimacy. Shadow: Carelessness. Dissipation. Waste."
    },
    "cups-03": {
        "name": "Three of Cups - Abundance",
        "emojis": "☿️ ♋ 🍇 🌺 🎉",
        "attribution": "Mercury in Cancer • Binah",
        "description": "Spiritual basis of fertility. Plenty. Hospitality. Pleasure. Sensuality. Passive success. Love. Kindness. Bounty. Transient pleasure."
    },
    "cups-04": {
        "name": "Four of Cups - Luxury",
        "emojis": "🌙 ♋ 🏺 🌊 💔",
        "attribution": "Moon in Cancer • Chesed",
        "description": "Weakness. Abandonment to desire. Pleasure mixed with anxiety. Injustice. The seeds of decay in the fruits of pleasure."
    },
    "cups-05": {
        "name": "Five of Cups - Disappointment",
        "emojis": "♂️ ♏ 💔 🌧️ 😢",
        "attribution": "Mars in Scorpio • Geburah",
        "description": "Unexpected disturbance. Misfortune. Heartache. Unkindness from friends. Betrayal. Resentment. Sadness. Regret."
    },
    "cups-06": {
        "name": "Six of Cups - Pleasure",
        "emojis": "☀️ ♏ 🌺 💖 ✨",
        "attribution": "Sun in Scorpio • Tiphareth",
        "description": "Well-being. Effortless harmony. Ease. Satisfaction. Happiness. Success. Fulfillment of sexual will. Beginnings of improvements. Shadow: Presumptuous. Vain. Thankless."
    },
    "cups-07": {
        "name": "Seven of Cups - Debauch",
        "emojis": "♀️ ♏ 🍷 💀 😵",
        "attribution": "Venus in Scorpio • Netzach",
        "description": "Illusory success. Drug addiction. Intoxication. Guilt. Lying. Deceit. Promises unfulfilled. Lust. Dissipation of love and friendship."
    },
    "cups-08": {
        "name": "Eight of Cups - Indolence",
        "emojis": "♄ ♓ 🌊 💤 🥀",
        "attribution": "Saturn in Pisces • Hod",
        "description": "Abandoned success. Declining interest. Temporary success. Instability. Misery. Transience which may lead away from material success."
    },
    "cups-09": {
        "name": "Nine of Cups - Happiness",
        "emojis": "♃ ♓ 🎉 💖 ✨",
        "attribution": "Jupiter in Pisces • Yesod",
        "description": "Complete success. Pleasure. Physical well-being. Shadow: Vanity, conceit and overindulgence."
    },
    "cups-10": {
        "name": "Ten of Cups - Satiety",
        "emojis": "♂️ ♓ 🏺 🌊 🌹",
        "attribution": "Mars in Pisces • Malkuth",
        "description": "Pursuit of pleasure. Desired outcome. Success. Peacemaking. Generosity. Shadow: Dissipation. Overindulgence. Pity. Waste. Stagnation."
    },
    "cups-princess": {
        "name": "Princess of Cups",
        "emojis": "🌊 🌍 🦢 🐢 🐬",
        "attribution": "Earthy part of Water",
        "description": "Gracious, sweet, voluptuous, gentle, kind, romantic and dreamy. Shadow: Indolent, selfish and luxurious."
    },
    "cups-prince": {
        "name": "Prince of Cups",
        "emojis": "🌊 💨 🦅 🐍 🌊",
        "attribution": "Airy part of Water",
        "description": "Subtlety, secret violence, craft. An artist whose calm surface masks intense passion. Shadow: Ruthless in his aims. Ambitious and obtuse."
    },
    "cups-queen": {
        "name": "Queen of Cups",
        "emojis": "🌊 🌊 🦢 🌊 🔮",
        "attribution": "Watery part of Water",
        "description": "An observer, dreamy, tranquil, poetic, imaginative, kind yet passive. Impressionable to other card influences."
    },
    "cups-knight": {
        "name": "Knight of Cups",
        "emojis": "🌊 🔥 🏇 🦚 ♋️",
        "attribution": "Fiery part of Water",
        "description": "Commitment issues. Amiable but passive. Attracted to excitement. Unsustainable enthusiasm. Sensitive but shallow. Shadow: Sensual and idle, untruthful, prone to depression and drug abuse."
    },
    
    # SWORDS - Air
    "swords-01": {
        "name": "Ace of Swords",
        "emojis": "💨 🗡️ 👑 ⚡ ⚖️",
        "attribution": "Root of Air",
        "description": "Invoked force. Power for good or evil. Conquest. Activity. Strength through trouble. Just punishment."
    },
    "swords-02": {
        "name": "Two of Swords - Peace",
        "emojis": "🌙 ♎ 🗡️ 🌹 ⚖️",
        "attribution": "Moon in Libra • Chokmah",
        "description": "Dual nature. Sacrifice and trouble giving birth to strength. Conflict leading to peace. Pleasure after pain. Truth and untruth. Indecision. Ambivalence."
    },
    "swords-03": {
        "name": "Three of Swords - Sorrow",
        "emojis": "♄ ♎ 💔 😢 🗡️",
        "attribution": "Saturn in Libra • Binah",
        "description": "Melancholy. Unhappiness. Tears. Disruption. Discord. Delay. Absence. Separation. Deceit. Faith. Honesty."
    },
    "swords-04": {
        "name": "Four of Swords - Truce",
        "emojis": "♃ ♎ 🗡️ 🌹 ✝️",
        "attribution": "Jupiter in Libra • Chesed",
        "description": "Rest from sorrow. Peace after war. Relief from anxiety. Recovery from sickness, Change after struggle. Intellectual authority. Convention."
    },
    "swords-05": {
        "name": "Five of Swords - Defeat",
        "emojis": "♀️ ♒ 💔 🗡️ 😞",
        "attribution": "Venus in Aquarius • Geburah",
        "description": "Loss. Malice. Spite. Weakness. Slander. Failure. Anxiety, Poverty. Dishonor. Trouble. Grief. Lies. Gossip. Interference."
    },
    "swords-06": {
        "name": "Six of Swords - Science",
        "emojis": "☿️ ♒ 🗡️ 🌹 ✝️",
        "attribution": "Mercury in Aquarius • Tiphareth",
        "description": "Directed intelligence. Labor. Work. Success after challenge. Passage from difficulty. Journey by water. Shadow: Self-centeredness. Intellectual conceit."
    },
    "swords-07": {
        "name": "Seven of Swords - Futility",
        "emojis": "🌙 ♒ 🗡️ 🌙 😔",
        "attribution": "Moon in Aquarius • Netzach",
        "description": "Unstable effort. Vacillation. Striving in vain. Incomplete success due to exhaustion. Journey by land. Untrustworthy person."
    },
    "swords-08": {
        "name": "Eight of Swords - Interference",
        "emojis": "♃ ♊ 🗡️ ⚔️ 🔗",
        "attribution": "Jupiter in Gemini • Hod",
        "description": "Misdirected energy. Neglect of important matters. Lack of persistence. Unforeseen bad luck. Restriction. Great care in some areas, disorder in others."
    },
    "swords-09": {
        "name": "Nine of Swords - Cruelty",
        "emojis": "♂️ ♊ 🗡️ 😭 💀",
        "attribution": "Mars in Gemini • Yesod",
        "description": "Mental anguish. Despair. Hopelessness. Worry. Suffering. Loss. Illness. Malice. Burden. Oppression. Lying. Shame. Shadow: Obedience. Faithfulness. Patience. Unselfishness."
    },
    "swords-10": {
        "name": "Ten of Swords - Ruin",
        "emojis": "☀️ ♊ 🗡️ 💀 ☠️",
        "attribution": "Sun in Gemini • Malkuth",
        "description": "Faulty reasoning. Death. Failure. Disruption. Clever. Eloquent but impertinent person. Spiritually, may herald the end of delusion."
    },
    "swords-princess": {
        "name": "Princess of Swords",
        "emojis": "💨 🌍 🗡️ ⚔️ 👸",
        "attribution": "Earthy part of Air",
        "description": "Stern and revengeful, with destructive logic, firm and aggressive, skilled in practical affairs. Shadow: Cunning, frivolous, and manipulative."
    },
    "swords-prince": {
        "name": "Prince of Swords",
        "emojis": "💨 💨 🗡️ 🧚 ⚡",
        "attribution": "Airy part of Air",
        "description": "A young intellectual man, full of ideas and designs, domineering, intensely clever but unstable. Elusive. Impressionable. Shadow: Harsh, malicious, plotting, unreliable, fanatic."
    },
    "swords-queen": {
        "name": "Queen of Swords",
        "emojis": "💨 🌊 👑 🗡️ 💀",
        "attribution": "Watery part of Air",
        "description": "Graceful, intensely perceptive, a keen observer, subtle interpreter, an intense individualist. Confident and gracious. Shadow: Cruel, sly, deceitful and unreliable. Superficially attractive."
    },
    "swords-knight": {
        "name": "Knight of Swords",
        "emojis": "💨 🔥 🏇 🗡️ 🌪️",
        "attribution": "Fiery part of Air",
        "description": "An active man, skillful and clever. Fierce and courageous, but often unreflective. Shadow: Incapable of decision, deceitful and over-bearing."
    },
    
    # DISKS - Earth
    "disks-01": {
        "name": "Ace of Disks",
        "emojis": "🌍 💎 🪙 🌱 ✨",
        "attribution": "Root of Earth",
        "description": "Material gain. Power. Labor. Wealth. Contentment. Materialism."
    },
    "disks-02": {
        "name": "Two of Disks - Change",
        "emojis": "♃ ♑ ☯️ 🐍 🔄",
        "attribution": "Jupiter in Capricorn • Chokmah",
        "description": "Harmony. Alternating gain and loss, weakness and strength, elation and melancholy. Varying occupation. Wandering. Visit to friends. Pleasant change. Industrious, yet unreliable."
    },
    "disks-03": {
        "name": "Three of Disks - Works",
        "emojis": "♂️ ♑ 🔺 ⚙️ 🏗️",
        "attribution": "Mars in Capricorn • Binah",
        "description": "Business. Commercial transaction. Constructive. Increase of material things. Growth. Commencement of projects. Shadow: Selfish, narrow, unrealistic, greedy."
    },
    "disks-04": {
        "name": "Four of Disks - Power",
        "emojis": "☀️ ♑ 🏰 👑 🛡️",
        "attribution": "Sun in Capricorn • Chesed",
        "description": "Law and order. Gain of money and influence. Success. Rank. Dominion. Physical skill. Shadow: Prejudice. Envy. Suspicion. Lack of originality."
    },
    "disks-05": {
        "name": "Five of Disks - Worry",
        "emojis": "☿️ ♉ 💰 😰 ⭐",
        "attribution": "Mercury in Taurus • Geburah",
        "description": "Intense strain. Inactivity. Financial loss. Professional setbacks. Monetary anxiety. Poverty. Shadow: Labor. Real estate. Business acumen."
    },
    "disks-06": {
        "name": "Six of Disks - Success",
        "emojis": "🌙 ♉ 💰 ⚖️ ✨",
        "attribution": "Moon in Taurus • Tiphareth",
        "description": "Material gain. Power. Influence. Philanthropy. Transitory situation. Shadow: Insolence. Conceit with wealth. Excessive spending."
    },
    "disks-07": {
        "name": "Seven of Disks - Failure",
        "emojis": "♄ ♉ 🌾 😞 💔",
        "attribution": "Saturn in Taurus • Netzach",
        "description": "Unfinished work. Unprofitable speculation. Unmet goals. Hopes deceived. Disappointment. Little gain from much effort. Shadow: Delayed growth. Honorable undertakings."
    },
    "disks-08": {
        "name": "Eight of Disks - Prudence",
        "emojis": "☀️ ♍ 🌳 ⚙️ 💰",
        "attribution": "Sun in Virgo • Hod",
        "description": "Intelligence in material affairs. Agriculture. Building. Skill. Cunning. Industriousness. Shadow: 'Penny wise and pound foolish.' Avarice. Meanness. Failure to see the big picture."
    },
    "disks-09": {
        "name": "Nine of Disks - Gain",
        "emojis": "♀️ ♍ 💎 🌟 🏆",
        "attribution": "Venus in Virgo • Yesod",
        "description": "Good fortune. Inheritance. Improved wealth. Shadow: Envy, loss, waste."
    },
    "disks-10": {
        "name": "Ten of Disks - Wealth",
        "emojis": "☿️ ♍ 💰 🪙 🏛️",
        "attribution": "Mercury in Virgo • Malkuth",
        "description": "Prosperity. Creativity. Old age. Shadow: Laziness. Indifference. Dullness of mind."
    },
    "disks-princess": {
        "name": "Princess of Disks",
        "emojis": "🌍 🌍 🐏 💎 🌾",
        "attribution": "Earthy part of Earth",
        "description": "Beautiful and strong, pregnant with life. Generous, kind, diligent, and benevolent. Shadow: Wasteful and at war with their dignity."
    },
    "disks-prince": {
        "name": "Prince of Disks",
        "emojis": "🌍 💨 🐂 🌾 ⚙️",
        "attribution": "Airy part of Earth",
        "description": "An energetic young man. A capable manager and steadfast worker, competent, perhaps dull, somewhat skeptical of spirituality, slow to anger but implacable if aroused."
    },
    "disks-queen": {
        "name": "Queen of Disks",
        "emojis": "🌍 🌊 🐐 🌹 👑",
        "attribution": "Watery part of Earth",
        "description": "Ambitious, yet affectionate and kind, charming, timid, practical, quiet and domesticated. Shadow: Dull. Servile. Foolish. Capricious. Moody."
    },
    "disks-knight": {
        "name": "Knight of Disks",
        "emojis": "🌍 🔥 🏇 🐴 🌾",
        "attribution": "Fiery part of Earth",
        "description": "A farmer, patient, laborious and clever. Somewhat dull and preoccupied with material things. Shadow: Avaricious, surly, petty, jealous."
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
    emojis = card["emojis"]
    attribution = card["attribution"]
    description = card["description"]
    
    # Create embed
    embed = discord.Embed(
        title=card_name,
        description=f"\n{emojis}  \n*({attribution})*\n\n{description}",
        color=discord.Color.from_rgb(0, 0, 128)
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
