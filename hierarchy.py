"""
Fallen Angel and Demon Hierarchy Module
Comprehensive database across multiple traditions
"""

import random
import discord
from config import AUTHORIZED_ROLES

# ============================================================
# HIERARCHY DATABASE
# ============================================================

HIERARCHY_DB = {
    # SUPREME RULER
    "lucifer": {
        "name": "Lucifer",
        "alt_names": ["Satan", "The Adversary", "Light-Bearer", "Morning Star"],
        "rank": "Supreme Ruler",
        "domain": "Pride, Rebellion, Enlightenment",
        "legions": "Countless",
        "tradition": "Christian, Jewish, Islamic, Occult",
        "superior": "None",
        "subordinates": "All fallen angels and demons",
        "symbols": "Morning star, serpent, dragon, inverted pentagram",
        "description": "The most powerful fallen angel, cast from Heaven for pride and rebellion. Name means 'Light-Bearer' in Latin. Supreme commander of Hell's armies across most traditions."
    },
    
    # THE SEVEN PRINCES (Deadly Sins)
    "mammon": {
        "name": "Mammon",
        "alt_names": ["Prince of Greed"],
        "rank": "Prince of Hell",
        "domain": "Greed, Avarice, Material Wealth",
        "legions": "Unknown",
        "tradition": "Christian Demonology (Binsfeld)",
        "superior": "Lucifer",
        "subordinates": "Demons of greed and materialism",
        "symbols": "Gold, coins, treasure",
        "description": "Demon of greed and wealth. Name derived from Aramaic/Hebrew meaning 'riches' or 'profit.' Tempts humans with promises of material gain."
    },
    
    "asmodeus": {
        "name": "Asmodeus",
        "alt_names": ["Asmoday", "Ashmedai", "Sydonay"],
        "rank": "King/Prince of Hell",
        "domain": "Lust, Revenge, Wrath",
        "legions": "72 (Ars Goetia)",
        "tradition": "Jewish (Talmud), Christian, Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "Demons of lust and revenge",
        "symbols": "Three heads (bull, ram, man), rooster feet, serpent tail",
        "description": "King of demons in Jewish tradition. Appeared in Book of Tobit. Known for killing seven husbands of Sarah. One of the Kings in Ars Goetia, teaching mathematics and crafts."
    },
    
    "leviathan": {
        "name": "Leviathan",
        "alt_names": ["The Twisted Serpent", "Dragon of the Sea"],
        "rank": "Prince of Hell",
        "domain": "Envy, Chaos, The Abyss",
        "legions": "Unknown",
        "tradition": "Jewish, Christian (Binsfeld)",
        "superior": "Lucifer",
        "subordinates": "Sea demons and spirits of envy",
        "symbols": "Sea serpent, dragon, twisted coils",
        "description": "Primordial sea monster from Hebrew Bible. Represents chaos and the untamable ocean. In Christian demonology, became a demon of envy. Gate of Hell in some traditions."
    },
    
    "beelzebub": {
        "name": "Beelzebub",
        "alt_names": ["Baal Zebub", "Lord of Flies", "Beelzebul"],
        "rank": "Prince of Hell",
        "domain": "Gluttony, Pride, False Gods",
        "legions": "66+",
        "tradition": "Jewish, Christian, Occult",
        "superior": "Lucifer (or equal in some traditions)",
        "subordinates": "66 legions of demons",
        "symbols": "Flies, throne, crown",
        "description": "Originally Philistine god Ba'al Zebub ('Lord of Flies'). Second only to Satan in many hierarchies. Called 'Prince of Demons' in Matthew 12:24. Grand Duke of Hell's western regions."
    },
    
    "belphegor": {
        "name": "Belphegor",
        "alt_names": ["Baal-Peor"],
        "rank": "Prince of Hell",
        "domain": "Sloth, Apathy, Discoveries",
        "legions": "Unknown",
        "tradition": "Christian (Binsfeld), Occult",
        "superior": "Lucifer",
        "subordinates": "Demons of sloth and apathy",
        "symbols": "Toilet (often depicted on), inventions",
        "description": "Demon of sloth and ingenious inventions. Originally Moabite god Baal-Peor. Tempts through laziness and offering people clever discoveries. Sometimes depicted sitting on a toilet."
    },
    
    "satan": {
        "name": "Satan/Amon",
        "alt_names": ["The Adversary", "Samael", "Amon"],
        "rank": "Prince of Hell",
        "domain": "Wrath, Anger, Accusation",
        "legions": "Countless",
        "tradition": "Jewish, Christian, Islamic",
        "superior": "None (or aspect of Lucifer)",
        "subordinates": "Demons of wrath and violence",
        "symbols": "Serpent, accuser's finger, flames",
        "description": "The Adversary and Accuser. In Jewish tradition, a role rather than a being. In Christianity, often conflated with Lucifer. Islamic Shaytan. Demon of wrath in Binsfeld's classification."
    },
    
    # THE WATCHERS (Book of Enoch)
    "semyaza": {
        "name": "Semyaza",
        "alt_names": ["Shemhazai", "Azazyel", "Shamgaz"],
        "rank": "Leader of the Watchers",
        "domain": "Forbidden Knowledge, Rebellion",
        "legions": "200 Watchers",
        "tradition": "Book of Enoch, Jewish mysticism",
        "superior": "Originally under Heaven, now fallen",
        "subordinates": "199 other Watchers",
        "symbols": "Book, chains",
        "description": "Leader of the 200 Watchers who descended to Mount Hermon and bred with human women, creating the Nephilim. Taught enchantments and root-cutting. Bound until the Day of Judgment."
    },
    
    "azazel": {
        "name": "Azazel",
        "alt_names": ["Azael", "The Scapegoat"],
        "rank": "Watcher, Teacher of Forbidden Arts",
        "domain": "Forbidden Knowledge, Warfare, Vanity",
        "legions": "Unknown",
        "tradition": "Book of Enoch, Jewish mysticism, Yom Kippur",
        "superior": "Semyaza (among Watchers)",
        "subordinates": "Various demons of vanity and war",
        "symbols": "Weapons, cosmetics, jewelry",
        "description": "Taught humans to make weapons, cosmetics, and jewelry. Led humans to sin through vanity and warfare. Bound beneath the desert until Judgment Day. The scapegoat is sent to Azazel in Leviticus 16."
    },
    
    "kokabiel": {
        "name": "Kokabiel",
        "alt_names": ["Kôkabîêl", "Star of God"],
        "rank": "Watcher",
        "domain": "Astrology, Constellations",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Stars, astronomical charts",
        "description": "Watcher who taught humans astrology and the constellations. Name means 'Star of God.' Revealed the knowledge of the stars and their movements to humanity."
    },
    
    # ARS GOETIA - 72 DEMONS (Selected Major Ones)
    "bael": {
        "name": "Bael",
        "alt_names": ["Baal", "Ba'al"],
        "rank": "King",
        "domain": "Invisibility, Wisdom",
        "legions": "66",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "66 legions",
        "symbols": "Three heads (cat, toad, man), spider legs",
        "description": "First demon in the Ars Goetia. Appears with three heads. Teaches science and makes men invisible. Commands 66 legions. Originally Phoenician god Ba'al."
    },
    
    "paimon": {
        "name": "Paimon",
        "alt_names": ["Paymon"],
        "rank": "King",
        "domain": "Arts, Sciences, Secret Knowledge",
        "legions": "200",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "200 legions",
        "symbols": "Crown, dromedary camel, loud voice",
        "description": "One of the Kings in the Ars Goetia. Teaches all arts, sciences, and secret things. Gives good familiars. Appears riding a dromedary with a loud trumpet. Very obedient to Lucifer."
    },
    
    "beleth": {
        "name": "Beleth",
        "alt_names": ["Bileth", "Bilet"],
        "rank": "King",
        "domain": "Love, Desire",
        "legions": "85",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "85 legions",
        "symbols": "Horse, crown, trumpets",
        "description": "Mighty and terrible King. Procures love between men and women. Rides a pale horse preceded by musicians. Must be received respectfully with offerings."
    },
    
    "astaroth": {
        "name": "Astaroth",
        "alt_names": ["Astarte", "Ashtaroth"],
        "rank": "Duke/Prince",
        "domain": "Past, Present, Future Knowledge",
        "legions": "40",
        "tradition": "Ars Goetia, Christian Demonology",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Dragon, viper, crown",
        "description": "Great Duke of Hell. Teaches liberal sciences and reveals hidden treasures. Answers all questions about past, present, and future. Originally Phoenician goddess Astarte. Rides a dragon holding a viper."
    },
    
    "vassago": {
        "name": "Vassago",
        "alt_names": ["Vasago"],
        "rank": "Prince",
        "domain": "Divination, Finding Lost Things",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Good nature",
        "description": "Prince who declares things past, present, and future. Discovers hidden and lost things. One of the few demons described as having a good nature. Commands 26 legions."
    },
    
    "buer": {
        "name": "Buer",
        "alt_names": [],
        "rank": "President",
        "domain": "Healing, Philosophy, Logic",
        "legions": "50",
        "tradition": "Ars Goetia, Pseudomonarchia Daemonum",
        "superior": "Lucifer",
        "subordinates": "50 legions",
        "symbols": "Star shape, five goat legs, lion head",
        "description": "President of Hell appearing as a five-pointed star with lion head and goat legs radiating from center. Teaches philosophy, logic, and virtues of herbs. Heals diseases and gives good familiars."
    },
    
    "forneus": {
        "name": "Forneus",
        "alt_names": ["Fornier"],
        "rank": "Marquis",
        "domain": "Rhetoric, Languages, Reputation",
        "legions": "29",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "29 legions",
        "symbols": "Sea monster",
        "description": "Great Marquis appearing as a sea monster. Makes men wonderfully knowing in rhetoric and languages. Causes men to be beloved by friends and foes. Commands 29 legions."
    },
    
    "ronove": {
        "name": "Ronove",
        "alt_names": ["Roneve", "Ronwe"],
        "rank": "Marquis/Count",
        "domain": "Languages, Servants",
        "legions": "19",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "19 legions",
        "symbols": "Monster form",
        "description": "Marquis and Count who teaches rhetoric and languages. Gives good servants and knowledge of tongues. Manifests in monstrous form but is otherwise helpful."
    },
    
    "andras": {
        "name": "Andras",
        "alt_names": [],
        "rank": "Marquis",
        "domain": "Discord, Murder",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Angel body, raven head, sword, black wolf",
        "description": "Dangerous Marquis with angel body and raven head. Rides a black wolf and wields a sword. Sows discord and kills the unwary. Must be handled with extreme caution."
    },
    
    "barbatos": {
        "name": "Barbatos",
        "alt_names": [],
        "rank": "Duke/Count",
        "domain": "Nature, Animals, Hidden Treasures",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Four trumpets, animals",
        "description": "Duke who understands the singing of birds and voices of animals. Reveals hidden treasures. Reconciles friends and those in power. Appears when the sun is in Sagittarius."
    },
    
    # QLIPHOTH (Kabbalah)
    "thaumiel": {
        "name": "Thaumiel",
        "alt_names": ["The Twins of God", "Qemetiel"],
        "rank": "Qliphothic Archdemons",
        "domain": "Duality, Division, Separation from God",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "None (highest qliphah)",
        "subordinates": "All lower qliphoth",
        "symbols": "Two contending forces, twin heads",
        "description": "The dual contending forces opposed to Kether. Represents division and separation from divine unity. The highest shell of the Qliphothic tree. Associated with Satan and Moloch as twin demons."
    },
    
    "ghagiel": {
        "name": "Ghagiel",
        "alt_names": ["The Hinderers"],
        "rank": "Qliphothic Shell",
        "domain": "Obstruction, Hindrance",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of obstruction",
        "symbols": "Black heads, obstacles",
        "description": "The Qliphah opposed to Chokmah. The Hinderers who obstruct divine wisdom. Associated with Beelzebub. Represents confusion and purposeless energy."
    },
    
    "satariel": {
        "name": "Satariel",
        "alt_names": ["The Concealers"],
        "rank": "Qliphothic Shell",
        "domain": "Concealment, Illusion",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of concealment",
        "symbols": "Veils, hidden faces",
        "description": "The Concealers opposed to Binah. Hides and obscures divine understanding. Associated with Lucifuge Rofocale. Creates illusions and false appearances."
    },
    
    "gamchicoth": {
        "name": "Gamchicoth",
        "alt_names": ["The Disturbers", "Devourers"],
        "rank": "Qliphothic Shell",
        "domain": "Disruption, Absorption",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of disruption",
        "symbols": "Devouring mouths, chaos",
        "description": "The Disturbers opposed to Chesed. Devours and disrupts divine mercy. Associated with Astaroth. Represents uncontrolled absorption and greed."
    },
    
    # MESOPOTAMIAN DEMONS
    "pazuzu": {
        "name": "Pazuzu",
        "alt_names": ["King of Wind Demons"],
        "rank": "Demon King",
        "domain": "Wind, Fever, Pestilence",
        "legions": "Wind demons",
        "tradition": "Mesopotamian (Assyrian/Babylonian)",
        "superior": "Hanbi (father)",
        "subordinates": "Wind demons, Labubu",
        "symbols": "Wings, dog/lion face, talons, scorpion tail",
        "description": "Ancient Mesopotamian demon king of the wind. Son of Hanbi. Protects against other demons, especially Lamashtu. Famous from The Exorcist. Has dog or lion face, eagle talons, wings, and scorpion tail."
    },
    
    "labubu": {
        "name": "Labubu",
        "alt_names": [],
        "rank": "Wind Demon",
        "domain": "Wind, Pestilence",
        "legions": "Unknown",
        "tradition": "Mesopotamian (Assyrian/Babylonian)",
        "superior": "Pazuzu",
        "subordinates": "None",
        "symbols": "Wind, companion to Pazuzu",
        "description": "Mesopotamian wind demon associated with Pazuzu. Companion and subordinate to the demon king. Part of the ancient Near Eastern hierarchy of wind demons bringing disease and pestilence."
    },
    
    "lamashtu": {
        "name": "Lamashtu",
        "alt_names": ["Dimme"],
        "rank": "Demon Goddess",
        "domain": "Child Murder, Pregnancy Complications, Nightmares",
        "legions": "Unknown",
        "tradition": "Mesopotamian (Sumerian/Akkadian)",
        "superior": "Daughter of Anu",
        "subordinates": "Various minor demons",
        "symbols": "Lion head, donkey teeth, bird feet, nursing pigs/dogs",
        "description": "Most feared Mesopotamian demon. Kills children, causes miscarriages, brings nightmares. Daughter of sky god Anu. Pazuzu protects against her. Depicted with lion head, nursing pigs and dogs."
    },
    
    "lilitu": {
        "name": "Lilitu",
        "alt_names": ["Ardat-Lili", "Lilith (Hebrew)"],
        "rank": "Night Demon",
        "domain": "Night, Seduction, Infant Death",
        "legions": "Unknown",
        "tradition": "Mesopotamian/Sumerian, later Jewish",
        "superior": "Various",
        "subordinates": "Lesser night spirits",
        "symbols": "Night, owl, wind",
        "description": "Night demon class from Mesopotamia. Became Lilith in Jewish tradition. Seduces men in their sleep, harms infants and pregnant women. Associated with wind and wilderness."
    },
    
    # JEWISH MYSTICISM
    "lilith": {
        "name": "Lilith",
        "alt_names": ["The First Eve", "Queen of Demons", "Lilitu"],
        "rank": "Queen of Demons",
        "domain": "Night, Seduction, Infant Death",
        "legions": "Lilin (demon children)",
        "tradition": "Jewish mysticism, Kabbalah, Talmud",
        "superior": "Samael (consort)",
        "subordinates": "The Lilin (her demon children)",
        "symbols": "Owl, screech owl, serpent, moon",
        "description": "Adam's first wife who refused submission and fled Eden. Became queen of demons. Seduces men in sleep, strangles infants. Mother of demons. Consort of Samael. Appears in Isaiah 34:14."
    },
    
    "samael": {
        "name": "Samael",
        "alt_names": ["Poison of God", "Venom of God", "Blind God"],
        "rank": "Archangel/Demon Prince",
        "domain": "Death, Accusation, Temptation",
        "legions": "Unknown",
        "tradition": "Jewish mysticism, Kabbalah, Talmud",
        "superior": "Depends on tradition",
        "subordinates": "Various demons, consort Lilith",
        "symbols": "Sword, serpent, poison",
        "description": "Fallen archangel, Angel of Death in some texts. Accused of being the serpent in Eden. Consort of Lilith. Rules the Fifth Heaven. Name means 'Venom of God.' Both angel and demon in different sources."
    },
    
    # ISLAMIC TRADITION
    "iblis": {
        "name": "Iblis",
        "alt_names": ["Shaytan", "Azazil"],
        "rank": "Fallen Jinn Leader",
        "domain": "Pride, Temptation, Misguidance",
        "legions": "All shayatin (demons)",
        "tradition": "Islamic (Quran, Hadith)",
        "superior": "None among jinn",
        "subordinates": "All shayatin and evil jinn",
        "symbols": "Fire, pride, refusal",
        "description": "Islamic devil figure. Originally righteous jinn Azazil who refused to bow to Adam out of pride. Cast out of Paradise. Granted respite until Judgment Day to test humanity. Father of all demons in Islam."
    },
    
    # ADDITIONAL GOETIC DEMONS
    "botis": {
        "name": "Botis",
        "alt_names": ["Otis"],
        "rank": "President/Count",
        "domain": "Reconciliation, Past/Future Knowledge",
        "legions": "60",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "60 legions",
        "symbols": "Viper form, sword, human form",
        "description": "President and Count appearing as viper or human with sword and horns. Tells past and future, reconciles friends and foes. Commands 60 legions."
    },
    
    "stolas": {
        "name": "Stolas",
        "alt_names": ["Stolos"],
        "rank": "Prince",
        "domain": "Astronomy, Herbs, Precious Stones",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Raven, crown, owl (modern)",
        "description": "Great Prince who teaches astronomy, herbs, and properties of precious stones. Appears as raven initially, then as human. Commands 26 legions. Popular in modern occultism."
    },
    
    "phenex": {
        "name": "Phenex",
        "alt_names": ["Phoenix"],
        "rank": "Marquis",
        "domain": "Poetry, Sciences, Hope of Return",
        "legions": "20",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "20 legions",
        "symbols": "Phoenix bird, child's voice",
        "description": "Great Marquis appearing as phoenix bird. Speaks with child's voice. Excellent poet, teaches sciences. Hopes to return to Heaven after 1,200 years. Commands 20 legions."
    },
    
    "halphas": {
        "name": "Halphas",
        "alt_names": ["Malthus", "Malthas"],
        "rank": "Count",
        "domain": "War, Weapons, Towers",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Stock-dove, fire",
        "description": "Count who builds towers, provides weapons, and sends men to war. Appears as stock-dove with hoarse voice. Burns cities and enemies. Commands 26 legions."
    },
    
    "malphas": {
        "name": "Malphas",
        "alt_names": [],
        "rank": "President",
        "domain": "Building, Deception, Familiars",
        "legions": "40",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Crow, human form",
        "description": "Mighty President appearing as crow, then human. Builds houses and towers, gives good familiars, reveals enemies' desires and thoughts. Receives sacrifices but deceives. Commands 40 legions."
    },
    
    "raum": {
        "name": "Raum",
        "alt_names": ["Raim"],
        "rank": "Count",
        "domain": "Theft, Reconciliation, Destruction",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Crow, human form",
        "description": "Count appearing as crow who takes human form. Steals treasures, destroys cities and dignities. Reconciles friends and foes. Commands 30 legions."
    },
    
    "focalor": {
        "name": "Focalor",
        "alt_names": ["Forcalor", "Furcalor"],
        "rank": "Duke",
        "domain": "Sea, Drowning, Wind",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Gryphon wings, human form",
        "description": "Duke with gryphon wings. Drowns men and ships, commands seas and winds. Hoped to return to Heaven after 1,000 years. Commands 30 legions."
    },
    
    "vepar": {
        "name": "Vepar",
        "alt_names": ["Separ"],
        "rank": "Duke",
        "domain": "Seas, Ships, Death by Water",
        "legions": "29",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "29 legions",
        "symbols": "Mermaid form",
        "description": "Duke appearing as mermaid. Guides waters, guides ships, causes storms and death by water. Can cause wounds to putrefy. Commands 29 legions."
    },
    
    "sabnock": {
        "name": "Sabnock",
        "alt_names": ["Sabnach", "Sab Nac"],
        "rank": "Marquis",
        "domain": "Fortification, Wounds, Decay",
        "legions": "50",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "50 legions",
        "symbols": "Armed soldier, lion head",
        "description": "Marquis appearing as armed soldier with lion head. Builds fortifications, provides weapons, afflicts wounds with worms and decay. Commands 50 legions."
    },
    
    "shax": {
        "name": "Shax",
        "alt_names": ["Chax", "Scox"],
        "rank": "Marquis",
        "domain": "Theft, Deception, Discovery",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Stock-dove, hoarse voice",
        "description": "Marquis appearing as stock-dove with hoarse voice. Takes away sight, hearing, or understanding. Steals money, discovers hidden things. Must be in triangle or deceives. Commands 30 legions."
    },
    
    "vine": {
        "name": "Vine",
        "alt_names": ["Vinea"],
        "rank": "King/Count",
        "domain": "Knowledge, Witchcraft, Hidden Things",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Lion riding black horse, serpent",
        "description": "King and Count appearing as lion riding black horse, holding serpent. Knows past, present, future. Discovers witches and hidden things. Builds towers, destroys walls. Commands 36 legions."
    },
    
    "bifrons": {
        "name": "Bifrons",
        "alt_names": [],
        "rank": "Count",
        "domain": "Necromancy, Astrology, Herbs",
        "legions": "6",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "6 legions",
        "symbols": "Monster, candles, two faces",
        "description": "Count appearing as monster or with two faces. Teaches astrology, geometry, herbs, and precious stones. Moves corpses, lights candles on graves. Commands only 6 legions."
    },
    
    "vual": {
        "name": "Vual",
        "alt_names": ["Voval", "Vual"],
        "rank": "Duke",
        "domain": "Love, Friendship, Languages",
        "legions": "37",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "37 legions",
        "symbols": "Dromedary, Egyptian form",
        "description": "Duke appearing as dromedary, then as Egyptian. Procures love of women, tells past/present/future, causes friendship. Speaks Egyptian. Commands 37 legions."
    },
    
    "haagenti": {
        "name": "Haagenti",
        "alt_names": [],
        "rank": "President",
        "domain": "Alchemy, Transformation",
        "legions": "33",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "33 legions",
        "symbols": "Bull wings, gryphon",
        "description": "President appearing as bull with gryphon wings. Makes men wise, transmutes metals into gold, changes water into wine and wine into water. Commands 33 legions."
    },
    
    "crocell": {
        "name": "Crocell",
        "alt_names": ["Crokel"],
        "rank": "Duke",
        "domain": "Warmth, Hidden Things, Geometry",
        "legions": "48",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "48 legions",
        "symbols": "Angel form, rushing waters",
        "description": "Duke appearing as angel. Speaks of hidden things mystically. Teaches geometry. Makes water warm, discovers baths. Sound of rushing waters heard when he appears. Commands 48 legions."
    },
    
    "furcas": {
        "name": "Furcas",
        "alt_names": ["Forcas"],
        "rank": "Knight",
        "domain": "Philosophy, Rhetoric, Logic",
        "legions": "20",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "20 legions",
        "symbols": "Cruel old man, beard, white horse",
        "description": "Knight appearing as cruel old man with long beard riding pale horse. Teaches philosophy, rhetoric, logic, astrology, and chiromancy. Commands 20 legions."
    },
    
    "balam": {
        "name": "Balam",
        "alt_names": ["Balaam"],
        "rank": "King",
        "domain": "Invisibility, Wit, Future Knowledge",
        "legions": "40",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Three heads (bull, ram, man), serpent tail, bear",
        "description": "Terrible King with three heads (bull, ram, man), serpent tail, riding a bear. Gives perfect answers about past, present, future. Makes men invisible and witty. Commands 40 legions."
    },
    
    "alloces": {
        "name": "Alloces",
        "alt_names": ["Allocer", "Alocer"],
        "rank": "Duke",
        "domain": "Astronomy, Liberal Sciences",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Lion face, red eyes, knight on horse",
        "description": "Duke appearing as soldier on great horse with lion face, red eyes, and inflamed visage. Teaches astronomy and liberal sciences. Gives good familiars. Commands 36 legions."
    },
    
    "caim": {
        "name": "Caim",
        "alt_names": ["Camio", "Caym"],
        "rank": "President",
        "domain": "Understanding Animals, Future Knowledge",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Thrush bird, burning ashes, sword",
        "description": "President appearing as thrush or man with sword on burning ashes. Understands birds, dogs, and all creatures. Gives true answers about the future. Commands 30 legions."
    },
    
    "murmur": {
        "name": "Murmur",
        "alt_names": ["Murmus"],
        "rank": "Duke/Count",
        "domain": "Necromancy, Philosophy, Souls",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Soldier, griffin, crown, trumpet",
        "description": "Duke and Count appearing as soldier before griffin wearing crown. Trumpets sound. Teaches philosophy, constrains souls to answer questions. Was partly in Order of Angels. Commands 30 legions."
    },
    
    "orobas": {
        "name": "Orobas",
        "alt_names": [],
        "rank": "Prince",
        "domain": "Past/Future, Favor, Truth",
        "legions": "20",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "20 legions",
        "symbols": "Horse, human form",
        "description": "Prince appearing as horse who takes human form. Gives true answers of past, present, future. Gives favor with friends and foes, never deceives. Was of Order of Thrones. Commands 20 legions."
    },
    
    "gremory": {
        "name": "Gremory",
        "alt_names": ["Gamori", "Gemory"],
        "rank": "Duke",
        "domain": "Love, Treasure, Past/Present/Future",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Beautiful woman, duchess crown, camel",
        "description": "Strong Duke appearing as beautiful woman with duchess crown, riding camel. Tells past, present, future. Procures love of women. Reveals hidden treasures. Commands 26 legions."
    },
    
    "ose": {
        "name": "Ose",
        "alt_names": ["Osé", "Voso"],
        "rank": "President",
        "domain": "Insanity, Transformation, Deception",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Leopard, human form",
        "description": "President appearing as leopard, then human. Makes men insane or wise, changes shape. Makes one believe they are any creature. Gives true answers of divine things. Commands 30 legions."
    },
    
    "amy": {
        "name": "Amy",
        "alt_names": ["Avnas"],
        "rank": "President",
        "domain": "Astrology, Liberal Sciences, Familiars",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Flaming fire, human form",
        "description": "President appearing in flaming fire, then human. Teaches astrology and liberal sciences. Gives good familiars, reveals treasures guarded by spirits. Hopes to return to Heaven. Commands 36 legions."
    },
    
    "orias": {
        "name": "Orias",
        "alt_names": ["Oriax"],
        "rank": "Marquis",
        "domain": "Astrology, Transformation, Favor",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Lion, horse tail, serpent",
        "description": "Marquis appearing as lion with horse tail, holding serpents. Teaches astrology, transforms men, gives favor with friends and foes. Commands 30 legions."
    },
    
    "vapula": {
        "name": "Vapula",
        "alt_names": ["Naphula"],
        "rank": "Duke",
        "domain": "Philosophy, Handicrafts, Sciences",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Lion wings",
        "description": "Duke appearing with lion wings. Teaches philosophy, handicrafts, and all sciences. Makes men skilled in professions. Commands 36 legions."
    },
    
    "zagan": {
        "name": "Zagan",
        "alt_names": ["Zagam"],
        "rank": "King/President",
        "domain": "Alchemy, Wit, Transformation",
        "legions": "33",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "33 legions",
        "symbols": "Bull wings, griffin form",
        "description": "King and President appearing as bull with griffin wings, then human. Makes men witty, turns wine to water and blood to wine, turns metals to coin. Makes fools wise. Commands 33 legions."
    },
    
    "volac": {
        "name": "Volac",
        "alt_names": ["Valak", "Ualac"],
        "rank": "President",
        "domain": "Serpents, Hidden Treasures",
        "legions": "38",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "38 legions",
        "symbols": "Child with angel wings, dragon",
        "description": "President appearing as child with angel wings riding two-headed dragon. Gives true answers about hidden treasures, reveals where serpents may be seen. Commands 38 legions."
    },
    
    "andras": {
        "name": "Andras",
        "alt_names": [],
        "rank": "Marquis",
        "domain": "Discord, Murder",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Angel body, raven head, sword, wolf",
        "description": "Dangerous Marquis with angel body, raven/owl head, riding black wolf, waving sword. Sows discord, kills master and servants if not careful. Very perilous. Commands 30 legions."
    },
    
    "haures": {
        "name": "Haures",
        "alt_names": ["Flauros", "Havres"],
        "rank": "Duke",
        "domain": "Past/Present/Future, Fire, Enemies",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Leopard, fiery eyes, human form",
        "description": "Duke appearing as leopard with fiery eyes, then human. Tells of past, present, future. Speaks of divinity and world creation. Destroys enemies with fire. Was of Order of Angels. Commands 36 legions."
    },
    
    "andrealphus": {
        "name": "Andrealphus",
        "alt_names": [],
        "rank": "Marquis",
        "domain": "Geometry, Astronomy, Transformation",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Peacock, loud noise, human form",
        "description": "Marquis appearing as peacock with great noise, then human. Teaches geometry, astronomy, and mensuration. Transforms men into birds. Commands 30 legions."
    },
    
    "kimaris": {
        "name": "Kimaris",
        "alt_names": ["Cimeies", "Cimejes"],
        "rank": "Marquis",
        "domain": "Logic, Rhetoric, Lost Things",
        "legions": "20",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "20 legions",
        "symbols": "Black horse, warrior",
        "description": "Marquis appearing as valiant warrior on black horse. Teaches logic, rhetoric, grammar. Discovers lost/hidden things, treasures. Makes man like soldier. Commands 20 legions."
    },
    
    "amdusias": {
        "name": "Amdusias",
        "alt_names": ["Amdukias"],
        "rank": "Duke",
        "domain": "Music, Trees, Trumpets",
        "legions": "29",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "29 legions",
        "symbols": "Unicorn, trumpets, trees",
        "description": "Duke appearing as unicorn, then human at request. Causes trumpets and instruments to be heard. Makes trees bend. Gives excellent familiars. Commands 29 legions."
    },
    
    "belial": {
        "name": "Belial",
        "alt_names": ["Beliar", "Belias"],
        "rank": "King",
        "domain": "Worthlessness, Lawlessness, Favors",
        "legions": "80",
        "tradition": "Ars Goetia, Hebrew Bible, Christian",
        "superior": "Lucifer (or independent)",
        "subordinates": "80 legions",
        "symbols": "Beautiful angel, chariot of fire",
        "description": "Mighty King appearing as beautiful angel in chariot of fire. Speaks pleasantly. Fell first among angels. Gives favors of senators and places. Must receive offerings or will not be truthful. Commands 80 legions."
    },
    
    "decarabia": {
        "name": "Decarabia",
        "alt_names": [],
        "rank": "Marquis",
        "domain": "Birds, Herbs, Precious Stones",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Star in pentacle, human form",
        "description": "Marquis appearing as star in pentacle, then human. Knows virtues of birds, herbs, precious stones. Makes bird familiars to sing. Commands 30 legions."
    },
    
    "seere": {
        "name": "Seere",
        "alt_names": ["Sear", "Seir"],
        "rank": "Prince",
        "domain": "Swiftness, Discovery, Theft",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Beautiful man, winged horse",
        "description": "Prince appearing as beautiful man on winged horse. Goes and returns instantly. Discovers theft, hidden treasure, many things. Brings abundance. Good natured. Commands 26 legions."
    },
    
    "dantalion": {
        "name": "Dantalion",
        "alt_names": [],
        "rank": "Duke",
        "domain": "Thoughts, Love, Knowledge",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Multiple faces (male/female), book",
        "description": "Duke appearing with many faces of men and women, holding book. Teaches all arts and sciences. Knows thoughts of all people, can change them. Procures love. Shows visions. Commands 36 legions."
    },
    
    "andromalius": {
        "name": "Andromalius",
        "alt_names": [],
        "rank": "Count",
        "domain": "Thieves, Wickedness, Hidden Things",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Man with serpent, hand",
        "description": "Count appearing as man with serpent in hand. Reveals thieves and stolen goods, discovers wickedness and underhand dealings. Punishes thieves. Last of 72 spirits. Commands 36 legions."
    },
    
    # ADDITIONAL DEMONS FROM OTHER TRADITIONS
    "abaddon": {
        "name": "Abaddon",
        "alt_names": ["Apollyon", "The Destroyer"],
        "rank": "Angel/Demon of the Abyss",
        "domain": "Destruction, The Abyss, Locusts",
        "legions": "Locust army",
        "tradition": "Christian (Book of Revelation)",
        "superior": "Bound in the Abyss",
        "subordinates": "Locust army from the pit",
        "symbols": "Key to the Abyss, locusts, smoke",
        "description": "Angel of the Abyss in Revelation 9:11. Name means 'Destruction' in Hebrew, 'Apollyon' in Greek. Commands locust army with scorpion tails released from bottomless pit during End Times."
    },
    
    "mastema": {
        "name": "Mastema",
        "alt_names": ["Chief of Evil Spirits"],
        "rank": "Prince of Demons",
        "domain": "Hostility, Testing, Accusation",
        "legions": "Unknown",
        "tradition": "Book of Jubilees, Dead Sea Scrolls",
        "superior": "Allowed to operate by God",
        "subordinates": "Evil spirits",
        "symbols": "Hostility, testing",
        "description": "Chief of evil spirits in Book of Jubilees. Name means 'Hostility.' Tests humanity with permission from God. Parallel to Satan's role as accuser. Requested spirits to remain on earth after the Flood."
    },
    
    "gressil": {
        "name": "Gressil",
        "alt_names": [],
        "rank": "Demon",
        "domain": "Impurity, Uncleanness",
        "legions": "Unknown",
        "tradition": "Christian Demonology",
        "superior": "Various",
        "subordinates": "Demons of impurity",
        "symbols": "Filth",
        "description": "Demon of impurity and uncleanness. Third demon of the Possession of Loudun in 17th century France. Specializes in temptation through uncleanliness and impure thoughts."
    },
    
    "sonneillon": {
        "name": "Sonneillon",
        "alt_names": [],
        "rank": "Demon",
        "domain": "Hatred, Discord",
        "legions": "Unknown",
        "tradition": "Christian Demonology",
        "superior": "Various",
        "subordinates": "Demons of hatred",
        "symbols": "Discord",
        "description": "Demon of hatred who creates discord between people. Associated with the Loudun possessions. Promotes enmity and destroys relationships."
    },
    
    "verrier": {
        "name": "Verrier",
        "alt_names": ["Verrine"],
        "rank": "Demon",
        "domain": "Impatience, Health",
        "legions": "Unknown",
        "tradition": "Christian Demonology",
        "superior": "Various",
        "subordinates": "Unknown",
        "symbols": "Restlessness",
        "description": "Demon of impatience and health afflictions. Second demon of Loudun possessions. Causes restlessness, anxiety, and various health problems."
    },
    
    "python": {
        "name": "Python",
        "alt_names": ["Spirit of Divination"],
        "rank": "Demon",
        "domain": "Divination, False Prophecy",
        "legions": "Unknown",
        "tradition": "Christian (New Testament)",
        "superior": "Various",
        "subordinates": "Spirits of divination",
        "symbols": "Serpent, divination",
        "description": "Spirit of divination mentioned in Acts 16:16. Associated with false prophecy and fortune-telling. Named after Python serpent of Greek mythology slain by Apollo at Delphi."
    },
    
    "naamah": {
        "name": "Naamah",
        "alt_names": ["The Pleasing One"],
        "rank": "Demon Princess",
        "domain": "Seduction, Lust",
        "legions": "Unknown",
        "tradition": "Jewish mysticism, Kabbalah",
        "superior": "Various",
        "subordinates": "Succubi",
        "symbols": "Beauty, seduction",
        "description": "Female demon of seduction, one of four queens of demons with Lilith. Name means 'pleasing.' Mother of demons through relations with fallen angels. Associated with Lilith as corrupter."
    },
    
    "agrat bat mahlat": {
        "name": "Agrat bat Mahlat",
        "alt_names": ["Igrat"],
        "rank": "Demon Queen",
        "domain": "Night, Seduction",
        "legions": "Hosts of demons",
        "tradition": "Jewish mysticism, Zohar",
        "superior": "One of four queens",
        "subordinates": "Legions of demons",
        "symbols": "Night, chariot",
        "description": "One of four demon queens with Lilith. Rides in chariot, rules Wednesday nights. Mates with Samael. Commands hosts of demons who roam at night seducing men."
    },
    
    "eisheth zenunim": {
        "name": "Eisheth Zenunim",
        "alt_names": ["Woman of Whoredom"],
        "rank": "Demon Queen",
        "domain": "Prostitution, Corruption",
        "legions": "Unknown",
        "tradition": "Jewish mysticism, Kabbalah",
        "superior": "One of four queens",
        "subordinates": "Demons of prostitution",
        "symbols": "Corruption",
        "description": "One of four demon queens with Lilith. Name means 'Woman of Whoredom.' Rules demons of sacred prostitution and temple corruption. Mates with fallen angels."
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_random_entity():
    """Get a random entity from the hierarchy"""
    return random.choice(list(HIERARCHY_DB.keys()))

def search_hierarchy(keyword):
    """Search hierarchy by keyword in name, domain, or description"""
    keyword_lower = keyword.lower()
    results = []
    
    for key, entity in HIERARCHY_DB.items():
        # Search in name, alt names, domain, and description
        if (keyword_lower in entity["name"].lower() or
            keyword_lower in entity["domain"].lower() or
            keyword_lower in entity["description"].lower() or
            any(keyword_lower in alt.lower() for alt in entity.get("alt_names", []))):
            results.append((key, entity))
    
    return results

def get_entity_list(page=1, per_page=20):
    """Get paginated list of all entities"""
    sorted_keys = sorted(HIERARCHY_DB.keys(), key=lambda k: HIERARCHY_DB[k]["name"])
    total = len(sorted_keys)
    total_pages = (total + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    page_keys = sorted_keys[start_idx:end_idx]
    page_entities = [(k, HIERARCHY_DB[k]) for k in page_keys]
    
    return page_entities, page, total_pages, total

def get_full_hierarchy_chart():
    """Generate ASCII hierarchy chart"""
    chart = """
═══════════════════════════════════════════
        HIERARCHY OF THE FALLEN
═══════════════════════════════════════════

👑 SUPREME RULER
   Lucifer/Satan (The Adversary)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚔️ THE SEVEN PRINCES (Deadly Sins)
   ├─ Lucifer - Pride
   ├─ Mammon - Greed  
   ├─ Asmodeus - Lust
   ├─ Leviathan - Envy
   ├─ Beelzebub - Gluttony
   ├─ Satan/Amon - Wrath
   └─ Belphegor - Sloth

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👁️ THE WATCHERS (Book of Enoch)
   ├─ Semyaza - Leader of 200
   ├─ Azazel - Forbidden Knowledge
   └─ Kokabiel - Astrology

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗡️ ARS GOETIA (72 Demons)
   Kings: Bael, Paimon, Beleth, Asmoday, 
          Vine, Balam, Zagan, Belial, Purson
   
   Dukes: Astaroth, Barbatos, Alloces, 
          Murmur, Gremory, and 18 more...
   
   Princes: Vassago, Stolas, Orobas, Seere
   
   Marquises: Forneus, Ronove, Phenex, 
              Andras, and 10 more...
   
   Counts: Botis, Bifrons, and 8 more...
   
   Presidents: Buer, Malphas, Haagenti, 
               Caim, and 7 more...
   
   Knights: Furcas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌑 QLIPHOTH (Kabbalah Shadow Tree)
   ├─ Thaumiel - Duality (vs Kether)
   ├─ Ghagiel - Hindrance (vs Chokmah)
   ├─ Satariel - Concealment (vs Binah)
   └─ Gamchicoth - Disruption (vs Chesed)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏺 MESOPOTAMIAN HIERARCHY
   ├─ Pazuzu - King of Wind Demons
   ├─ Labubu - Wind Demon
   ├─ Lamashtu - Child Killer
   └─ Lilitu - Night Demons

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✡️ JEWISH MYSTICISM
   ├─ Lilith - Queen of Demons
   ├─ Samael - Angel of Death
   ├─ Naamah - Seduction
   ├─ Agrat bat Mahlat - Night Queen
   └─ Eisheth Zenunim - Whoredom

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☪️ ISLAMIC TRADITION
   └─ Iblis - Fallen Jinn Leader

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use .hierarchy [name] for detailed info
Use .hierarchy random for random entity
Use .hierarchy search [keyword] to find entities
"""
    return chart

# ============================================================
# DISCORD EMBED FUNCTIONS
# ============================================================

async def send_entity_details(ctx, entity_key):
    """Send detailed information about a specific entity"""
    if entity_key not in HIERARCHY_DB:
        await ctx.send(f"❌ Entity '{entity_key}' not found.")
        return
    
    entity = HIERARCHY_DB[entity_key]
    
    # Create embed
    embed = discord.Embed(
        title=f"👿 {entity['name']}",
        description=entity['description'],
        color=discord.Color.from_rgb(139, 0, 0)  # Dark red
    )
    
    # Add fields
    if entity.get('alt_names'):
        embed.add_field(
            name="Also Known As",
            value=", ".join(entity['alt_names']),
            inline=False
        )
    
    embed.add_field(name="Rank", value=entity['rank'], inline=True)
    embed.add_field(name="Domain", value=entity['domain'], inline=True)
    embed.add_field(name="Legions", value=entity['legions'], inline=True)
    
    embed.add_field(name="Tradition", value=entity['tradition'], inline=False)
    
    if entity.get('superior'):
        embed.add_field(name="Superior", value=entity['superior'], inline=True)
    
    if entity.get('subordinates'):
        embed.add_field(name="Subordinates", value=entity['subordinates'], inline=True)
    
    if entity.get('symbols'):
        embed.add_field(name="Symbols", value=entity['symbols'], inline=False)
    
    embed.set_footer(text="Use .hierarchy search [keyword] to find related entities")
    
    await ctx.send(embed=embed)

async def send_search_results(ctx, results):
    """Send search results"""
    if not results:
        await ctx.send("❌ No entities found matching your search.")
        return
    
    # Limit to 10 results
    results = results[:10]
    
    description = "\n".join([
        f"**{entity['name']}** - {entity['rank']}\n*{entity['domain']}*"
        for key, entity in results
    ])
    
    embed = discord.Embed(
        title=f"🔍 Search Results ({len(results)} found)",
        description=description,
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    embed.set_footer(text="Use .hierarchy [name] for detailed info")
    
    await ctx.send(embed=embed)

async def send_entity_list(ctx, page=1):
    """Send paginated list of all entities"""
    entities, current_page, total_pages, total = get_entity_list(page)
    
    if not entities:
        await ctx.send("❌ Invalid page number.")
        return
    
    description = "\n".join([
        f"**{entity['name']}** ({entity['rank']})"
        for key, entity in entities
    ])
    
    embed = discord.Embed(
        title=f"📜 Hierarchy List",
        description=description,
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    embed.set_footer(text=f"Page {current_page}/{total_pages} • {total} total entities • .hierarchy list [page]")
    
    await ctx.send(embed=embed)

async def send_hierarchy_chart(ctx):
    """Send full hierarchy chart"""
    chart = get_full_hierarchy_chart()
    
    # Split into multiple messages if needed
    chunks = [chart[i:i+1900] for i in range(0, len(chart), 1900)]
    
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=f"📊 Fallen Angel Hierarchy" + (f" (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else ""),
            description=f"```\n{chunk}\n```",
            color=discord.Color.from_rgb(139, 0, 0)
        )
        if i == len(chunks) - 1:  # Last chunk
            embed.set_footer(text="Use .hierarchy [name] for detailed info • .hierarchy list for full alphabetical list")
        await ctx.send(embed=embed)
