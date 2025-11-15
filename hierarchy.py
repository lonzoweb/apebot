"""
Fallen Angel and Demon Hierarchy Module - ENHANCED
Comprehensive database across multiple traditions
"""

import random
import discord
from config import AUTHORIZED_ROLES

#embed function

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

async def send_goetia_list(ctx, page=1):
    """Send list of Goetia spirits"""
    goetia_spirits = get_goetia_spirits()
    
    # Paginate (10 per page for Goetia)
    per_page = 10
    total = len(goetia_spirits)
    total_pages = (total + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    page_spirits = goetia_spirits[start_idx:end_idx]
    
    if not page_spirits:
        await ctx.send("❌ Invalid page number.")
        return
    
    description = "\n".join([
        f"**{start_idx + i + 1}. {entity['name']}** - {entity['rank']}\n*{entity['domain']}*"
        for i, (key, entity) in enumerate(page_spirits)
    ])
    
    embed = discord.Embed(
        title=f"📖 The 72 Spirits of the Ars Goetia",
        description=description,
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    embed.set_footer(text=f"Page {page}/{total_pages} • {total} total spirits • .hierarchy goetia [page]")
    
    await ctx.send(embed=embed)

async def send_tradition_list(ctx, tradition):
    """Send list of entities from a specific tradition"""
    results = get_entities_by_tradition(tradition)
    
    if not results:
        await ctx.send(f"❌ No entities found for tradition '{tradition}'.")
        return
    
    # Limit to 15 results
    results = results[:15]
    
    description = "\n".join([
        f"**{entity['name']}** - {entity['rank']}\n*{entity['domain']}*"
        for key, entity in results
    ])
    
    embed = discord.Embed(
        title=f"📚 {tradition.title()} Tradition",
        description=description,
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    embed.set_footer(text=f"Showing {len(results)} entities • Use .hierarchy [name] for details")
    
    await ctx.send(embed=embed)

async def send_rank_list(ctx, rank):
    """Send list of entities of a specific rank"""
    results = get_entities_by_rank(rank)
    
    if not results:
        await ctx.send(f"❌ No entities found with rank '{rank}'.")
        return
    
    # Limit to 15 results
    results = results[:15]
    
    description = "\n".join([
        f"**{entity['name']}**\n*{entity['domain']}*"
        for key, entity in results
    ])
    
    embed = discord.Embed(
        title=f"⚔️ Rank: {rank.title()}",
        description=description,
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    embed.set_footer(text=f"Showing {len(results)} entities • Use .hierarchy [name] for details")
    
    await ctx.send(embed=embed)

def get_stats():
    """Get statistics about the hierarchy database"""
    total = len(HIERARCHY_DB)
    
    # Count by tradition
    traditions = {}
    for entity in HIERARCHY_DB.values():
        trad = entity['tradition'].split(',')[0].strip()
        traditions[trad] = traditions.get(trad, 0) + 1
    
    # Count by rank
    ranks = {}
    for entity in HIERARCHY_DB.values():
        rank = entity['rank'].split('/')[0].strip()
        ranks[rank] = ranks.get(rank, 0) + 1
    
    # Count Goetia
    goetia_count = sum(1 for e in HIERARCHY_DB.values() if 'Ars Goetia' in e['tradition'])
    
    # Count Watchers
    watcher_count = sum(1 for e in HIERARCHY_DB.values() if 'Watcher' in e['rank'])
    
    return {
        'total': total,
        'goetia': goetia_count,
        'watchers': watcher_count,
        'traditions': traditions,
        'ranks': ranks
    }

async def send_stats(ctx):
    """Send database statistics"""
    stats = get_stats()
    
    embed = discord.Embed(
        title="📊 Hierarchy Database Statistics",
        description=f"**Total Entities:** {stats['total']}",
        color=discord.Color.from_rgb(139, 0, 0)
    )
    
    # Add special counts
    embed.add_field(
        name="📖 Ars Goetia Spirits",
        value=f"{stats['goetia']}/72 Complete!",
        inline=True
    )
    
    embed.add_field(
        name="👁️ Watchers",
        value=f"{stats['watchers']} documented",
        inline=True
    )
    
    # Top traditions
    top_traditions = sorted(stats['traditions'].items(), key=lambda x: x[1], reverse=True)[:5]
    traditions_text = "\n".join([f"• {trad}: {count}" for trad, count in top_traditions])
    embed.add_field(
        name="🌍 Top Traditions",
        value=traditions_text,
        inline=False
    )
    
    # Top ranks
    top_ranks = sorted(stats['ranks'].items(), key=lambda x: x[1], reverse=True)[:5]
    ranks_text = "\n".join([f"• {rank}: {count}" for rank, count in top_ranks])
    embed.add_field(
        name="⚔️ Top Ranks",
        value=ranks_text,
        inline=False
    )
    
    embed.set_footer(text="Database includes all major demonological traditions")
    
    await ctx.send(embed=embed)

# ============================================================
# HIERARCHY DATABASE - EXPANDED
# ============================================================

HIERARCHY_DB = {
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
    
    # ARS GOETIA - 72 DEMONS (NOW COMPLETE)
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
    
    "agares": {
        "name": "Agares",
        "alt_names": ["Agreas"],
        "rank": "Duke",
        "domain": "Languages, Earthquakes, Runaways",
        "legions": "31",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "31 legions",
        "symbols": "Old man on crocodile, hawk",
        "description": "Second spirit of the Goetia. Appears as old man riding crocodile with hawk. Teaches all languages, brings back runaways, causes earthquakes. Makes those who run stand still. Commands 31 legions."
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
        "description": "Third spirit. Prince who declares things past, present, and future. Discovers hidden and lost things. One of the few demons described as having a good nature. Commands 26 legions."
    },
    
    "samigina": {
        "name": "Samigina",
        "alt_names": ["Gamigin", "Gamygin"],
        "rank": "Marquis",
        "domain": "Necromancy, Liberal Sciences",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Little horse or ass, human form",
        "description": "Fourth spirit. Marquis appearing as little horse who takes human form. Teaches liberal sciences, gives account of souls who died in sin. Commands 30 legions."
    },
    
    "marbas": {
        "name": "Marbas",
        "alt_names": ["Barbas"],
        "rank": "President",
        "domain": "Healing, Mechanics, Shape-shifting",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Great lion, human form",
        "description": "Fifth spirit. President appearing as great lion who takes human form. Answers truly of hidden things, causes diseases, cures them. Teaches mechanics and transforms men. Commands 36 legions."
    },
    
    "valefor": {
        "name": "Valefor",
        "alt_names": ["Valefar", "Malephar"],
        "rank": "Duke",
        "domain": "Theft, Familiars",
        "legions": "10",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "10 legions",
        "symbols": "Lion with ass head, many heads",
        "description": "Sixth spirit. Duke appearing as lion with ass head. Gives good familiars, leads to theft until caught. Despite evil nature, good to those who employ him. Commands 10 legions."
    },
    
    "amon": {
        "name": "Amon",
        "alt_names": ["Aamon"],
        "rank": "Marquis",
        "domain": "Future Knowledge, Reconciliation",
        "legions": "40",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Wolf with serpent tail, raven head, human form",
        "description": "Seventh spirit. Marquis appearing as wolf with serpent tail and raven head, or as human with dog teeth. Tells of past and future, reconciles friendships. Commands 40 legions."
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
        "description": "Eighth spirit. Duke who understands the singing of birds and voices of animals. Reveals hidden treasures. Reconciles friends and those in power. Appears when the sun is in Sagittarius."
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
        "description": "Ninth spirit. One of the Kings in the Ars Goetia. Teaches all arts, sciences, and secret things. Gives good familiars. Appears riding a dromedary with a loud trumpet. Very obedient to Lucifer."
    },
    
    "gusion": {
        "name": "Gusion",
        "alt_names": ["Gusoin", "Gusoyn"],
        "rank": "Duke",
        "domain": "Past/Present/Future, Honor, Reconciliation",
        "legions": "40",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Xenophilus (strange guest), baboon",
        "description": "Eleventh spirit. Duke appearing as Xenophilus or baboon. Tells past, present, future. Reveals meaning of questions, reconciles friendships, gives honor and dignity. Commands 40 legions."
    },
    
    "sitri": {
        "name": "Sitri",
        "alt_names": ["Bitru"],
        "rank": "Prince",
        "domain": "Lust, Love, Revealing Secrets",
        "legions": "60",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "60 legions",
        "symbols": "Leopard head, griffin wings, beautiful form",
        "description": "Twelfth spirit. Prince appearing with leopard head and griffin wings who takes beautiful form. Inflames men with women's love and women with men's love. Shows people naked if desired. Commands 60 legions."
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
        "description": "Thirteenth spirit. Mighty and terrible King. Procures love between men and women. Rides a pale horse preceded by musicians. Must be received respectfully with offerings."
    },
    
    "leraje": {
        "name": "Leraje",
        "alt_names": ["Leraie", "Leraikha"],
        "rank": "Marquis",
        "domain": "Archery, Battles, Wounds",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Archer in green, bow and quiver",
        "description": "Fourteenth spirit. Marquis appearing as archer in green with bow and quiver. Causes great battles, makes arrow wounds putrefy. Commands 30 legions."
    },
    
    "eligos": {
        "name": "Eligos",
        "alt_names": ["Abigor", "Eligor"],
        "rank": "Duke",
        "domain": "War, Warriors, Hidden Things",
        "legions": "60",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "60 legions",
        "symbols": "Goodly knight, lance, ensign, serpent",
        "description": "Fifteenth spirit. Duke appearing as goodly knight with lance, ensign, and serpent. Discovers hidden things, causes love of lords and knights. Knows of wars and soldiers. Commands 60 legions."
    },
    
    "zepar": {
        "name": "Zepar",
        "alt_names": ["Vepar (confusion with #42)"],
        "rank": "Duke",
        "domain": "Love, Lust, Barrenness",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Soldier in red, armor",
        "description": "Sixteenth spirit. Duke appearing in red apparel and armor like a soldier. Makes women love men, brings them together in love. Makes women barren. Commands 26 legions."
    },
    
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
        "description": "Seventeenth spirit. President and Count appearing as viper or human with sword and horns. Tells past and future, reconciles friends and foes. Commands 60 legions."
    },
    
    "bathin": {
        "name": "Bathin",
        "alt_names": ["Bathym", "Mathim"],
        "rank": "Duke",
        "domain": "Herbs, Stones, Transportation",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Strong man, serpent tail, pale horse",
        "description": "Eighteenth spirit. Duke appearing as strong man with serpent tail, riding pale horse. Knows virtues of herbs and precious stones. Transports men suddenly from country to country. Commands 30 legions."
    },
    
    "sallos": {
        "name": "Sallos",
        "alt_names": ["Saleos", "Zaleos"],
        "rank": "Duke",
        "domain": "Love Between Genders",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Gallant soldier, ducal crown, crocodile",
        "description": "Nineteenth spirit. Duke appearing as gallant soldier with ducal crown, riding crocodile. Causes love between man and woman, is peaceful. Commands 30 legions."
    },
    
    "purson": {
        "name": "Purson",
        "alt_names": ["Curson"],
        "rank": "King",
        "domain": "Hidden Things, Treasure, Past/Present/Future",
        "legions": "22",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "22 legions",
        "symbols": "Man with lion face, bear, viper, trumpet",
        "description": "Twentieth spirit. King appearing with lion face, carrying viper, riding bear. Trumpet sounds. Knows hidden things, finds treasures, tells of past/present/future. Gives good familiars. Commands 22 legions."
    },
    
    "marax": {
        "name": "Marax",
        "alt_names": ["Morax", "Foraii"],
        "rank": "President/Count",
        "domain": "Astronomy, Liberal Sciences, Herbs",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Bull, human form",
        "description": "Twenty-first spirit. President and Count appearing as great bull with man's face. Teaches astronomy and liberal sciences, gives good familiars knowing virtues of herbs and stones. Commands 30 legions."
    },
    
    "ipos": {
        "name": "Ipos",
        "alt_names": ["Ipes", "Ayperos"],
        "rank": "Prince/Count",
        "domain": "Wit, Boldness, Future Knowledge",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Angel, lion head, goose feet, hare tail",
        "description": "Twenty-second spirit. Prince and Count appearing as angel with lion head, goose feet, and hare tail. Makes men witty and bold, knows past/present/future. Commands 36 legions."
    },
    
    "aim": {
        "name": "Aim",
        "alt_names": ["Aym", "Haborym"],
        "rank": "Duke",
        "domain": "Fire, Destruction, Wit",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Three heads (serpent, man, calf), serpent, torch",
        "description": "Twenty-third spirit. Duke appearing with three heads (serpent, man with two stars, calf) riding viper with firebrand. Sets cities/castles aflame, makes men witty. Commands 26 legions."
    },
    
    "naberius": {
        "name": "Naberius",
        "alt_names": ["Nebiros", "Cerberus", "Cerbere"],
        "rank": "Marquis",
        "domain": "Arts, Sciences, Rhetoric, Necromancy",
        "legions": "19",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "19 legions",
        "symbols": "Black crane, three-headed dog",
        "description": "Twenty-fourth spirit. Marquis appearing as black crane or three-headed dog. Teaches arts, sciences, especially rhetoric. Restores lost dignities and honors. Commands 19 legions."
    },
    
    "glasya-labolas": {
        "name": "Glasya-Labolas",
        "alt_names": ["Caacrinolaas", "Caassimolar"],
        "rank": "President/Count",
        "domain": "Manslaughter, Bloodshed, Knowledge",
        "legions": "36",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "36 legions",
        "symbols": "Dog with griffin wings",
        "description": "Twenty-fifth spirit. President and Count appearing as dog with griffin wings. Teaches all arts instantly, is captain of manslaughter and bloodshed. Tells of past and future, causes love. Commands 36 legions."
    },
    
    "bune": {
        "name": "Bune",
        "alt_names": ["Bime"],
        "rank": "Duke",
        "domain": "Necromancy, Riches, Eloquence",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Dragon with three heads (dog, griffin, man)",
        "description": "Twenty-sixth spirit. Duke appearing as dragon with three heads (dog, griffin, man). Changes place of the dead, gives riches, makes men wise and eloquent. Commands 30 legions."
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
        "description": "Twenty-seventh spirit. Marquis and Count who teaches rhetoric and languages. Gives good servants and knowledge of tongues. Manifests in monstrous form but is otherwise helpful."
    },
    
    "berith": {
        "name": "Berith",
        "alt_names": ["Beal", "Bolfri"],
        "rank": "Duke",
        "domain": "Alchemy, Past/Present/Future",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Red soldier, crown, red horse",
        "description": "Twenty-eighth spirit. Duke appearing as soldier in red with golden crown, riding red horse. Tells of past/present/future, turns metals into gold. Gives dignities but lies. Commands 26 legions."
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
        "description": "Thirtieth spirit. Great Marquis appearing as sea monster. Makes men wonderfully knowing in rhetoric and languages. Causes men to be beloved by friends and foes. Commands 29 legions."
    },
    
    "foras": {
        "name": "Foras",
        "alt_names": ["Forcas", "Forras"],
        "rank": "President",
        "domain": "Logic, Ethics, Herbs, Invisibility",
        "legions": "29",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "29 legions",
        "symbols": "Strong man",
        "description": "Thirty-first spirit. President appearing as strong man. Teaches logic, ethics, virtues of herbs and stones. Discovers treasures, makes men invisible, witty, eloquent. Recovers lost things. Commands 29 legions."
    },
    
    "asmoday": {
        "name": "Asmoday",
        "alt_names": ["Asmodeus", "Sydonay"],
        "rank": "King",
        "domain": "Arithmetic, Astronomy, Geometry, Handicrafts",
        "legions": "72",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "72 legions",
        "symbols": "Three heads, serpent tail, goose feet, dragon",
        "description": "Thirty-second spirit. King with three heads (bull, man, ram), serpent tail, goose feet, riding dragon with lance. Teaches arithmetic, astronomy, geometry, and handicrafts. Gives ring of virtues, guards treasures. Commands 72 legions."
    },
    
    "gaap": {
        "name": "Gaap",
        "alt_names": ["Tap", "Goap"],
        "rank": "President/Prince",
        "domain": "Philosophy, Liberal Sciences, Love/Hate",
        "legions": "66",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "66 legions",
        "symbols": "Human form, four kings",
        "description": "Thirty-third spirit. President and Prince appearing as human when sun is in southern signs. Teaches philosophy and liberal sciences, causes love or hatred, makes men insensible or invisible. Commands 66 legions with four kings."
    },
    
    "furfur": {
        "name": "Furfur",
        "alt_names": [],
        "rank": "Count",
        "domain": "Love, Storms, Thunder",
        "legions": "26",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Hart with fiery tail, angel",
        "description": "Thirty-fourth spirit. Count appearing as hart with fiery tail, then angel. Creates love between man and wife, speaks with hoarse voice. Commands thunder, lightning, wind. Commands 26 legions."
    },
    
    "marchosias": {
        "name": "Marchosias",
        "alt_names": [],
        "rank": "Marquis",
        "domain": "Strength, True Answers, Aspiration to Heaven",
        "legions": "30",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Wolf with griffin wings, serpent tail, fire",
        "description": "Thirty-fifth spirit. Marquis appearing as cruel wolf with griffin wings and serpent tail, breathing fire. Gives true answers, very strong fighter. Hopes to return to Heaven after 1,200 years. Commands 30 legions."
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
        "description": "Thirty-sixth spirit. Great Prince who teaches astronomy, herbs, and properties of precious stones. Appears as raven initially, then as human. Commands 26 legions. Popular in modern occultism."
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
        "description": "Thirty-seventh spirit. Great Marquis appearing as phoenix bird. Speaks with child's voice. Excellent poet, teaches sciences. Hopes to return to Heaven after 1,200 years. Commands 20 legions."
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
        "description": "Thirty-eighth spirit. Count who builds towers, provides weapons, and sends men to war. Appears as stock-dove with hoarse voice. Burns cities and enemies. Commands 26 legions."
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
        "description": "Thirty-ninth spirit. Mighty President appearing as crow, then human. Builds houses and towers, gives good familiars, reveals enemies' desires and thoughts. Receives sacrifices but deceives. Commands 40 legions."
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
        "description": "Fortieth spirit. Count appearing as crow who takes human form. Steals treasures, destroys cities and dignities. Reconciles friends and foes. Commands 30 legions."
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
        "description": "Forty-first spirit. Duke with gryphon wings. Drowns men and ships, commands seas and winds. Hoped to return to Heaven after 1,000 years. Commands 30 legions."
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
        "description": "Forty-second spirit. Duke appearing as mermaid. Guides waters, guides ships, causes storms and death by water. Can cause wounds to putrefy. Commands 29 legions."
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
        "description": "Forty-third spirit. Marquis appearing as armed soldier with lion head. Builds fortifications, provides weapons, afflicts wounds with worms and decay. Commands 50 legions."
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
        "description": "Forty-fourth spirit. Marquis appearing as stock-dove with hoarse voice. Takes away sight, hearing, or understanding. Steals money, discovers hidden things. Must be in triangle or deceives. Commands 30 legions."
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
        "description": "Forty-fifth spirit. King and Count appearing as lion riding black horse, holding serpent. Knows past, present, future. Discovers witches and hidden things. Builds towers, destroys walls. Commands 36 legions."
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
        "description": "Forty-sixth spirit. Count appearing as monster or with two faces. Teaches astrology, geometry, herbs, and precious stones. Moves corpses, lights candles on graves. Commands only 6 legions."
    },
    
    "uvall": {
        "name": "Uvall",
        "alt_names": ["Vual", "Voval"],
        "rank": "Duke",
        "domain": "Love, Friendship, Languages",
        "legions": "37",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "37 legions",
        "symbols": "Dromedary, Egyptian form",
        "description": "Forty-seventh spirit. Duke appearing as dromedary, then as Egyptian. Procures love of women, tells past/present/future, causes friendship. Speaks Egyptian. Commands 37 legions."
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
        "description": "Forty-eighth spirit. President appearing as bull with gryphon wings. Makes men wise, transmutes metals into gold, changes water into wine and wine into water. Commands 33 legions."
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
        "description": "Forty-ninth spirit. Duke appearing as angel. Speaks of hidden things mystically. Teaches geometry. Makes water warm, discovers baths. Sound of rushing waters heard when he appears. Commands 48 legions."
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
        "description": "Fiftieth spirit. Knight appearing as cruel old man with long beard riding pale horse. Teaches philosophy, rhetoric, logic, astrology, and chiromancy. Commands 20 legions."
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
        "description": "Fifty-first spirit. Terrible King with three heads (bull, ram, man), serpent tail, riding a bear. Gives perfect answers about past, present, future. Makes men invisible and witty. Commands 40 legions."
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
        "description": "Fifty-second spirit. Duke appearing as soldier on great horse with lion face, red eyes, and inflamed visage. Teaches astronomy and liberal sciences. Gives good familiars. Commands 36 legions."
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
        "description": "Fif ty-third spirit. President appearing as thrush or man with sword on burning ashes. Understands birds, dogs, and all creatures. Gives true answers about the future. Commands 30 legions."
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
        "description": "Fifty-fourth spirit. Duke and Count appearing as soldier before griffin wearing crown. Trumpets sound. Teaches philosophy, constrains souls to answer questions. Was partly in Order of Angels. Commands 30 legions."
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
        "description": "Fifty-fifth spirit. Prince appearing as horse who takes human form. Gives true answers of past, present, future. Gives favor with friends and foes, never deceives. Was of Order of Thrones. Commands 20 legions."
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
        "description": "Fifty-sixth spirit. Strong Duke appearing as beautiful woman with duchess crown, riding camel. Tells past, present, future. Procures love of women. Reveals hidden treasures. Commands 26 legions."
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
        "description": "Fifty-seventh spirit. President appearing as leopard, then human. Makes men insane or wise, changes shape. Makes one believe they are any creature. Gives true answers of divine things. Commands 30 legions."
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
        "description": "Fifty-eighth spirit. President appearing in flaming fire, then human. Teaches astrology and liberal sciences. Gives good familiars, reveals treasures guarded by spirits. Hopes to return to Heaven. Commands 36 legions."
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
        "description": "Fifty-ninth spirit. Marquis appearing as lion with horse tail, holding serpents. Teaches astrology, transforms men, gives favor with friends and foes. Commands 30 legions."
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
        "description": "Sixtieth spirit. Duke appearing with lion wings. Teaches philosophy, handicrafts, and all sciences. Makes men skilled in professions. Commands 36 legions."
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
        "description": "Sixty-first spirit. King and President appearing as bull with griffin wings, then human. Makes men witty, turns wine to water and blood to wine, turns metals to coin. Makes fools wise. Commands 33 legions."
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
        "description": "Sixty-second spirit. President appearing as child with angel wings riding two-headed dragon. Gives true answers about hidden treasures, reveals where serpents may be seen. Commands 38 legions."
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
        "description": "Sixty-third spirit. Dangerous Marquis with angel body, raven/owl head, riding black wolf, waving sword. Sows discord, kills master and servants if not careful. Very perilous. Commands 30 legions."
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
        "description": "Sixty-fourth spirit. Duke appearing as leopard with fiery eyes, then human. Tells of past, present, future. Speaks of divinity and world creation. Destroys enemies with fire. Was of Order of Angels. Commands 36 legions."
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
        "description": "Sixty-fifth spirit. Marquis appearing as peacock with great noise, then human. Teaches geometry, astronomy, and mensuration. Transforms men into birds. Commands 30 legions."
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
        "description": "Sixty-sixth spirit. Marquis appearing as valiant warrior on black horse. Teaches logic, rhetoric, grammar. Discovers lost/hidden things, treasures. Makes man like soldier. Commands 20 legions."
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
        "description": "Sixty-seventh spirit. Duke appearing as unicorn, then human at request. Causes trumpets and instruments to be heard. Makes trees bend. Gives excellent familiars. Commands 29 legions."
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
        "description": "Sixty-eighth spirit. Mighty King appearing as beautiful angel in chariot of fire. Speaks pleasantly. Fell first among angels. Gives favors of senators and places. Must receive offerings or will not be truthful. Commands 80 legions."
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
        "description": "Sixty-ninth spirit. Marquis appearing as star in pentacle, then human. Knows virtues of birds, herbs, precious stones. Makes bird familiars to sing. Commands 30 legions."
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
        "description": "Seventieth spirit. Prince appearing as beautiful man on winged horse. Goes and returns instantly. Discovers theft, hidden treasure, many things. Brings abundance. Good natured. Commands 26 legions."
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
        "description": "Seventy-first spirit. Duke appearing with many faces of men and women, holding book. Teaches all arts and sciences. Knows thoughts of all people, can change them. Procures love. Shows visions. Commands 36 legions."
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
        "description": "Seventy-second and final spirit. Count appearing as man with serpent in hand. Reveals thieves and stolen goods, discovers wickedness and underhand dealings. Punishes thieves. Last of 72 spirits. Commands 36 legions."
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
    
    # ADDITIONAL QLIPHOTH SHELLS (Complete the 10)
    "golachab": {
        "name": "Golachab",
        "alt_names": ["The Burners", "Flaming Ones"],
        "rank": "Qliphothic Shell",
        "domain": "Destruction, Burning, Cruelty",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of cruelty and burning",
        "symbols": "Fire, burning",
        "description": "The Burners opposed to Geburah. Represents cruelty without judgment, destructive force without mercy. Associated with Asmodeus. Burns away divine strength with unholy fire."
    },
    
    "tagiriron": {
        "name": "Tagiriron",
        "alt_names": ["The Hagglers", "Disputers"],
        "rank": "Qliphothic Shell",
        "domain": "Dispute, Litigation, Beauty Perverted",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of dispute",
        "symbols": "Endless argument, perverted beauty",
        "description": "The Disputers opposed to Tiphareth. Perverts divine beauty into endless litigation and meaningless dispute. Associated with Belphegor. Represents beauty turned to ugliness."
    },
    
    "harab serapel": {
        "name": "Harab Serapel",
        "alt_names": ["The Ravens of Death", "Harab Seraph"],
        "rank": "Qliphothic Shell",
        "domain": "Obscenity, Corruption of Love",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Ravens of death, demons of lust",
        "symbols": "Raven, corrupted love",
        "description": "The Ravens of Death opposed to Netzach. Corrupts divine love and victory into obscenity and depravity. Associated with Baal. The shells of Venus turned demonic."
    },
    
    "samael": {
        "name": "Samael (Qliphoth)",
        "alt_names": ["The Liar", "Poison of God"],
        "rank": "Qliphothic Shell",
        "domain": "Falsehood, Deception",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of lies",
        "symbols": "Serpent, lies, poison",
        "description": "The Liar opposed to Hod. Not the same as the angel Samael. Represents pure falsehood and deception opposing divine truth. The shell of Mercury corrupted."
    },
    
    "gamaliel": {
        "name": "Gamaliel",
        "alt_names": ["The Obscene Ones"],
        "rank": "Qliphothic Shell",
        "domain": "Obscenity, Sexual Perversion",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of obscenity",
        "symbols": "Obscene imagery",
        "description": "The Obscene Ones opposed to Yesod. Lilith rules here. Corrupts the foundation of creation through sexual perversion and obscenity. The shell of the Moon."
    },
    
    "nehemoth": {
        "name": "Nehemoth",
        "alt_names": ["The Whisperers", "Groaning Ones"],
        "rank": "Qliphothic Shell",
        "domain": "Materialism, Earthly Corruption",
        "legions": "Unknown",
        "tradition": "Kabbalah, Qliphoth",
        "superior": "Thaumiel",
        "subordinates": "Demons of materialism",
        "symbols": "Earth corrupted, groaning",
        "description": "The Whisperers opposed to Malkuth. Represents pure materialism and corruption of the physical world. Nehema/Naamah rules here. The final shell separating from divine presence."
    },
    
    # GRAND GRIMOIRE DEMONS
    
    "satanachia": {
        "name": "Satanachia",
        "alt_names": ["Satanackia"],
        "rank": "General/Commander",
        "domain": "Women, Subjugation",
        "legions": "45-54",
        "tradition": "Grand Grimoire, Grimorium Verum",
        "superior": "Lucifer",
        "subordinates": "Sergutthy, Heramael, Trimasael, Sustugriel",
        "symbols": "Command over women",
        "description": "Great General commanding 45-54 legions. Has power over all women and girls. Subordinates to Lucifer. One of three prime ministers in Grand Grimoire along with Lucifuge and Agaliarept."
    },
    
    "agaliarept": {
        "name": "Agaliarept",
        "alt_names": [],
        "rank": "General/Commander",
        "domain": "Secrets, Discovery",
        "legions": "Unknown",
        "tradition": "Grand Grimoire, Grimorium Verum",
        "superior": "Lucifer",
        "subordinates": "Buer, Gusoyn, Botis",
        "symbols": "Revealing secrets",
        "description": "General commanding second division. Reveals all secrets and mysteries. One of Lucifer's three prime ministers. Commands demons of discovery and revelation."
    },
    
    "fleurety": {
        "name": "Fleurety",
        "alt_names": [],
        "rank": "Lieutenant General",
        "domain": "Night Operations, Hail, Snow",
        "legions": "Unknown",
        "tradition": "Grand Grimoire, Grimorium Verum",
        "superior": "Beelzebub",
        "subordinates": "Various demons",
        "symbols": "Hail, snow, night",
        "description": "Lieutenant General under Beelzebub. Controls operations at night. Can produce hail, snow, and storms. Described as terrible in appearance."
    },
    
    "sargatanas": {
        "name": "Sargatanas",
        "alt_names": ["Satarnas"],
        "rank": "Brigadier Major",
        "domain": "Invisibility, Transport, Opening Locks",
        "legions": "Several brigades",
        "tradition": "Grand Grimoire",
        "superior": "Astaroth",
        "subordinates": "Various demons",
        "symbols": "Keys, invisibility",
        "description": "Brigadier Major under Astaroth. Makes one invisible, transports anywhere, opens all locks, reveals secrets, teaches cunning. Described as having special powers."
    },
    
    "nebiros": {
        "name": "Nebiros",
        "alt_names": ["Naberius", "Cerberus"],
        "rank": "Field Marshal/Marquis",
        "domain": "Necromancy, Evil Schemes",
        "legions": "19",
        "tradition": "Grand Grimoire, Grimorium Verum",
        "superior": "Astaroth",
        "subordinates": "19 legions",
        "symbols": "Three-headed dog, black crane",
        "description": "Field Marshal and inspector general of Astaroth's armies. Teaches necromancy and evil arts. Appears as three-headed dog or black crane. Same as Naberius from Goetia but with expanded role."
    },
    
    # PSEUDOMONARCHIA DAEMONUM VARIANTS
    "baal": {
        "name": "Baal (Pseudomonarchia)",
        "alt_names": ["King Bael"],
        "rank": "King",
        "domain": "Invisibility, Cat/Toad/Man Forms",
        "legions": "66",
        "tradition": "Pseudomonarchia Daemonum",
        "superior": "None (first king)",
        "subordinates": "66 legions",
        "symbols": "Three heads, hoarse voice",
        "description": "First king listed in Pseudomonarchia Daemonum by Johann Weyer (1577). Predecessor to Ars Goetia. Appears with three heads (cat, toad, man) or as single-headed man. Makes men wise and invisible."
    },
    
    "pruflas": {
        "name": "Pruflas",
        "alt_names": ["Busas"],
        "rank": "Prince/Duke",
        "domain": "Discord, Lies, Destruction by Fire",
        "legions": "26",
        "tradition": "Pseudomonarchia Daemonum",
        "superior": "Various",
        "subordinates": "26 legions",
        "symbols": "Flame-headed night owl",
        "description": "Prince and duke with head of great night owl or surrounded by flames. Dwells in Tower of Babel. Promotes discord and quarrels. Will lie but eventually tell truth. Destroys by fire."
    },
    
    # HINDU/VEDIC DEMON EQUIVALENTS
    "ravana": {
        "name": "Ravana",
        "alt_names": ["Ten-Headed Demon King"],
        "rank": "Rakshasa King",
        "domain": "Knowledge, Warfare, Lanka",
        "legions": "Rakshasa armies",
        "tradition": "Hindu (Ramayana)",
        "superior": "None among demons",
        "subordinates": "All Rakshasas",
        "symbols": "Ten heads, twenty arms",
        "description": "Great demon king of Lanka with ten heads and twenty arms. Incredibly learned Brahmin and warrior. Abducted Sita, defeated by Rama. Devotee of Shiva despite demonic nature."
    },
    
    "kali": {
        "name": "Kali (Asura)",
        "alt_names": ["Demon of Kali Yuga"],
        "rank": "Demon Lord",
        "domain": "Evil of the Age, Corruption, Vice",
        "legions": "Demons of the age",
        "tradition": "Hindu Puranas",
        "superior": "None",
        "subordinates": "Demons of Kali Yuga",
        "symbols": "Dice, crow, dog, darkness",
        "description": "Demon lord personifying the evils of Kali Yuga (age of vice). Not the goddess Kali. Represents gambling, intoxication, prostitution, and animal slaughter. Opposed by Vishnu."
    },
    
    "hiranyakashipu": {
        "name": "Hiranyakashipu",
        "alt_names": ["Golden-Clothed One"],
        "rank": "Daitya King",
        "domain": "Tyranny, False Divinity",
        "legions": "Daitya armies",
        "tradition": "Hindu Puranas",
        "superior": "None",
        "subordinates": "All Daityas",
        "symbols": "Golden garments, throne",
        "description": "Tyrannical demon king who gained near-invincibility through penance. Demanded to be worshipped as god. Killed by Narasimha (Vishnu's avatar) who exploited loophole in his boon. Father of devotee Prahlada."
    },
    
    "mahishasura": {
        "name": "Mahishasura",
        "alt_names": ["Buffalo Demon"],
        "rank": "Asura General",
        "domain": "Shape-shifting, Warfare",
        "legions": "Asura armies",
        "tradition": "Hindu (Devi Mahatmya)",
        "superior": "None",
        "subordinates": "Asura forces",
        "symbols": "Buffalo form",
        "description": "Buffalo demon who conquered the three worlds and defeated the gods. Could shift between buffalo and human form. Eventually slain by goddess Durga after nine-day battle. Celebrated during Navaratri."
    },
    
    "shukracharya": {
        "name": "Shukracharya",
        "alt_names": ["Guru of Asuras", "Venus"],
        "rank": "Asura Guru/Teacher",
        "domain": "Necromancy, Resurrection, Knowledge",
        "legions": "Advisor to all Asuras",
        "tradition": "Hindu Mythology",
        "superior": "Teacher to demons",
        "subordinates": "All Asuras (as students)",
        "symbols": "Planet Venus, one eye",
        "description": "Sage and guru of the Asuras with only one eye. Possesses Mrita Sanjivani mantra to resurrect the dead. Advisor to demon kings. Associated with planet Venus. Rival to Brihaspati, guru of the gods."
    },
    
    # ZOROASTRIAN DEMONS (Daevas)
    "ahriman": {
        "name": "Ahriman",
        "alt_names": ["Angra Mainyu", "Hostile Spirit"],
        "rank": "Supreme Evil Being",
        "domain": "Evil, Death, Darkness, Destruction",
        "legions": "All daevas and divs",
        "tradition": "Zoroastrianism",
        "superior": "None (opposed to Ahura Mazda)",
        "subordinates": "All daevas",
        "symbols": "Darkness, serpent, scorpion",
        "description": "Supreme evil being in Zoroastrianism, eternal opponent of Ahura Mazda. Created death, disease, sin. Father of all daevas (demons). Will be defeated at end of time. Persian equivalent to Satan."
    },
    
    "aeshma": {
        "name": "Aeshma",
        "alt_names": ["Aesma Daeva", "Demon of Wrath"],
        "rank": "Arch-Daeva",
        "domain": "Wrath, Fury, Violence",
        "legions": "Demons of wrath",
        "tradition": "Zoroastrianism",
        "superior": "Ahriman",
        "subordinates": "Demons of violence",
        "symbols": "Bloody spear",
        "description": "Daeva of wrath and fury. Rides with bloody spear. Likely origin of Asmodeus in Jewish and Christian tradition. One of seven arch-daevas opposing the Amesha Spentas."
    },
    
    "az": {
        "name": "Az",
        "alt_names": ["Azi", "Demon of Greed"],
        "rank": "Arch-Daeva",
        "domain": "Greed, Avarice, Gluttony",
        "legions": "Unknown",
        "tradition": "Zoroastrianism",
        "superior": "Ahriman",
        "subordinates": "Demons of greed",
        "symbols": "Insatiable hunger",
        "description": "Female daeva of greed and insatiable desire. Represents avarice and gluttony. Attempts to swallow all of creation. One of the seven arch-daevas."
    },
    
    "azhi dahaka": {
        "name": "Azhi Dahaka",
        "alt_names": ["Azi Dahaka", "Zahak", "Three-Headed Dragon"],
        "rank": "Dragon Demon",
        "domain": "Tyranny, Suffering, Drought",
        "legions": "Unknown",
        "tradition": "Zoroastrianism, Persian Mythology",
        "superior": "Ahriman",
        "subordinates": "Serpents and demons",
        "symbols": "Three heads, six eyes, serpents from shoulders",
        "description": "Three-headed dragon demon with six eyes and three jaws. Two serpents grow from his shoulders. Symbol of tyranny. Will break free at end times but be slain. Legendary tyrant king in Persian mythology."
    },
    
    "bushyasta": {
        "name": "Bushyasta",
        "alt_names": ["Bushasp", "Demon of Sloth"],
        "rank": "Arch-Daeva",
        "domain": "Sloth, Laziness, Sleep",
        "legions": "Demons of laziness",
        "tradition": "Zoroastrianism",
        "superior": "Ahriman",
        "subordinates": "Demons of sloth",
        "symbols": "Long hands, sleep",
        "description": "Daeva of sloth and laziness with long hands. Brings lethargy and discourages worship. Prevents people from waking for prayers. Opposes Asha (truth/order). One of the arch-daevas."
    },
    
    "druj": {
        "name": "Druj",
        "alt_names": ["The Lie", "Deception"],
        "rank": "Arch-Daeva",
        "domain": "Lies, Deception, Chaos",
        "legions": "Demons of lies",
        "tradition": "Zoroastrianism",
        "superior": "Ahriman",
        "subordinates": "All drujes (lie demons)",
        "symbols": "Chaos, deceit",
        "description": "Female principle of the Lie opposing Asha (Truth). Not a single demon but cosmic principle. Mother of all drujes. Represents chaos, disorder, and deception. Fundamental evil in Zoroastrianism."
    },
    
    # EGYPTIAN DEMONS
    "apep": {
        "name": "Apep",
        "alt_names": ["Apophis", "Apepi"],
        "rank": "Chaos Serpent Deity",
        "domain": "Chaos, Darkness, Destruction",
        "legions": "Demons of darkness",
        "tradition": "Egyptian Mythology",
        "superior": "None (primordial chaos)",
        "subordinates": "Demons of night and chaos",
        "symbols": "Giant serpent, darkness",
        "description": "Giant serpent embodying chaos and darkness. Enemy of Ra, tries to swallow sun each night. Never fully defeated, eternally recurring threat. Represents primordial chaos opposing cosmic order (Ma'at)."
    },
    
    "set": {
        "name": "Set",
        "alt_names": ["Seth", "Sutekh", "Lord of Chaos"],
        "rank": "God of Chaos/Desert",
        "domain": "Chaos, Desert, Storms, Disorder",
        "legions": "Desert demons",
        "tradition": "Egyptian Mythology",
        "superior": "None (major god)",
        "subordinates": "Demons of desert and storm",
        "symbols": "Set animal, was scepter, desert",
        "description": "God of desert, storms, disorder, and chaos. Murdered Osiris. Sometimes hero, sometimes villain in myths. Associated with foreigners and wild places. Not purely evil but chaotic and dangerous. Patron of warriors."
    },
    
    "ammit": {
        "name": "Ammit",
        "alt_names": ["Ammut", "Devourer of the Dead", "Eater of Hearts"],
        "rank": "Demon/Divine Entity",
        "domain": "Judgment, Devouring Souls",
        "legions": "None",
        "tradition": "Egyptian Mythology",
        "superior": "Serves Ma'at/divine judgment",
        "subordinates": "None",
        "symbols": "Crocodile head, lion body, hippo hindquarters",
        "description": "Demoness who devours hearts of wicked in Hall of Ma'at. Composite creature: crocodile head, lion body, hippopotamus hindquarters. Not evil but enforcer of divine justice. The 'second death' - soul annihilation."
    },
    
    "sebau": {
        "name": "Sebau",
        "alt_names": ["Demons of Decay"],
        "rank": "Demon Group",
        "domain": "Decay, Rebellion, Corruption",
        "legions": "Multiple sebau demons",
        "tradition": "Egyptian Mythology",
        "superior": "Apep/Set",
        "subordinates": "Various decay demons",
        "symbols": "Corruption, rebellion",
        "description": "Class of demons representing decay, rebellion, and corruption. Followers of Apep. Attempt to prevent sun's journey. Fought against by the deceased in the underworld. Shapeshifters causing disasters."
    },
    
    # CHRISTIAN APOCRYPHA & ADDITIONAL
    "azazel": {
        "name": "Azazel",
        "alt_names": ["The Scapegoat", "Azael"],
        "rank": "Watcher Chief/Demon Prince",
        "domain": "Forbidden Arts, Scapegoat, Desert",
        "legions": "Se'irim (goat demons)",
        "tradition": "Book of Enoch, Leviticus, Apocalypse of Abraham",
        "superior": "Among chief Watchers",
        "subordinates": "Se'irim, demons of vanity",
        "symbols": "Scapegoat, weapons, cosmetics",
        "description": "In Apocalypse of Abraham, appears as unclean bird trying to prevent Abraham's vision. Bound in desert with sharp stones over him. The scapegoat of Yom Kippur carries sins to Azazel. Taught vanity and warfare."
    },
    
    "beliar": {
        "name": "Beliar",
        "alt_names": ["Belial", "Worthless One"],
        "rank": "Demon Prince",
        "domain": "Lawlessness, Worthlessness, Antichrist",
        "legions": "Unknown",
        "tradition": "Dead Sea Scrolls, Testament of the Twelve Patriarchs",
        "superior": "Prince of Evil (opposed to Michael)",
        "subordinates": "Sons of Beliar, lawless ones",
        "symbols": "Lawlessness, chaos",
        "description": "In Dead Sea Scrolls, cosmic force of evil opposing Prince of Light. Leader of Sons of Darkness. In Testament of Solomon, appears as beautiful angel, the first fallen. Associated with Antichrist in some texts."
    },
    
    "ornias": {
        "name": "Ornias",
        "alt_names": [],
        "rank": "Demon",
        "domain": "Strangulation, Star-Shifting, Desire",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Strangling, stars, desire",
        "description": "First demon bound by King Solomon using magical ring. Appears as vampire, strangles men, feeds on desire. Can shift shape to beautiful woman. Changes into constellation Aquarius at night. Thwarted by name of Archangel Uriel."
    },
    
    "asmodeus": {
        "name": "Asmodeus (Testament of Solomon)",
        "alt_names": ["King of Demons", "Asmoday"],
        "rank": "King of Demons",
        "domain": "Lust, Gambling, Plots",
        "legions": "All demons",
        "tradition": "Testament of Solomon",
        "superior": "None (king)",
        "subordinates": "All demons",
        "symbols": "Multiple heads, plots",
        "description": "In Testament of Solomon, king of all demons. Plots against newlyweds, induces madness, promotes gambling and lust. Has power over all demons. Thwarted by name of God and smoke of fish liver/heart."
    },
    
    "beelzeboul": {
        "name": "Beelzeboul (Testament of Solomon)",
        "alt_names": ["Prince of Demons"],
        "rank": "Prince of Demons",
        "domain": "All Demons, Destruction of Kingdoms",
        "legions": "All demons",
        "tradition": "Testament of Solomon",
        "superior": "Formerly highest angel",
        "subordinates": "All demons under him",
        "symbols": "Princely authority over demons",
        "description": "In Testament of Solomon, prince of demons, formerly highest angel in heaven. Declares he destroys kings, arouses demons to worship, causes jealousies and murders. Bound by Solomon to help build temple."
    },
    
    "ephippas": {
        "name": "Ephippas",
        "alt_names": ["Wind Demon"],
        "rank": "Demon of Wind",
        "domain": "Wind, Capsizing Ships, Transformation",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Wind, waves, sea",
        "description": "Wind demon who causes shipwrecks. Can transform into waves, clouds, or breezes. Declares he separates friends, churns up enmities. Thwarted by names of the winds or name of the Spirit."
    },
    
    # ADDITIONAL GRIMOIRE DEMONS
    "bael": {
        "name": "Bael (Grimorium Verum)",
        "alt_names": ["First King"],
        "rank": "King",
        "domain": "Invisibility, Command of Legions",
        "legions": "66",
        "tradition": "Grimorium Verum",
        "superior": "Lucifer",
        "subordinates": "Agares, Marbas, Pruslas",
        "symbols": "Three heads",
        "description": "First of three supreme kings in Grimorium Verum. Commands eastern division. Subordinates include Agares, Marbas, and Pruslas. Makes men invisible and grants wisdom."
    },
    
    "syrach": {
        "name": "Syrach",
        "alt_names": ["Sirchade"],
        "rank": "Demon",
        "domain": "Discovery of Hidden Things",
        "legions": "Unknown",
        "tradition": "Grimorium Verum",
        "superior": "Agliarept",
        "subordinates": "None",
        "symbols": "Discovery, revelation",
        "description": "Demon under Agliarept's command. Has power to make discoveries, reveal hidden treasures and secrets. Appears in Grimorium Verum as one of Lucifer's servants."
    },
    
    "clauneck": {
        "name": "Clauneck",
        "alt_names": [],
        "rank": "Demon of Riches",
        "domain": "Wealth, Treasure, Power over Riches",
        "legions": "Unknown",
        "tradition": "Grimorium Verum, Secrets of Solomon",
        "superior": "Lucifer",
        "subordinates": "None",
        "symbols": "Gold, treasure, wealth",
        "description": "Greatly favored by Lucifer. Has power over all riches and treasures. Can make one discover hidden treasures. Grants wealth to those who make pacts. One of most sought-after demons in grimoire tradition."
    },
    
    "musisin": {
        "name": "Musisin",
        "alt_names": ["Musin"],
        "rank": "Demon",
        "domain": "Control of the Dead, Power over Great Lords",
        "legions": "Unknown",
        "tradition": "Grimorium Verum",
        "superior": "Beelzebub",
        "subordinates": "None",
        "symbols": "Death, lordship",
        "description": "Demon under Beelzebuth's command. Has power over great lords, teaches everything that happens in the Republics, and rules over the dead. Reveals secrets of the deceased."
    },
    
    "frimost": {
        "name": "Frimost",
        "alt_names": ["Frumoss"],
        "rank": "Demon",
        "domain": "Women, Desire",
        "legions": "Unknown",
        "tradition": "Grimorium Verum",
        "superior": "Satanachia",
        "subordinates": "None",
        "symbols": "Women, desire",
        "description": "Demon under Satanachia's command. Has power over women and girls. Can command them to perform any task. Part of the feminine subjugation hierarchy in Grimorium Verum."
    }

# MORE GOETIC-ADJACENT DEMONS
    "biffant": {
        "name": "Biffant",
        "alt_names": ["Bifrons variant"],
        "rank": "Count",
        "domain": "Light, Illumination of Tombs",
        "legions": "26",
        "tradition": "Pseudomonarchia Daemonum",
        "superior": "Lucifer",
        "subordinates": "26 legions",
        "symbols": "Candles on graves",
        "description": "Count who lights candles upon graves of the dead. Makes one knowing in astrology and geometry. Variant name and expanded role of Bifrons in earlier grimoires."
    },
    
    "orias": {
        "name": "Orias (Expanded)",
        "alt_names": ["Oriax", "Volac confusion"],
        "rank": "Marquis",
        "domain": "Divination of Stars, Transformation",
        "legions": "30",
        "tradition": "Various Grimoires",
        "superior": "Lucifer",
        "subordinates": "30 legions",
        "symbols": "Lion with serpents, horse tail",
        "description": "Teaches divination by stars, knows mansions of planets. Transforms men into any shape. Procures favor of friends and foes. Gives dignities and confirmations."
    },
    
    # ADDITIONAL TESTAMENT OF SOLOMON DEMONS
    "onoskelis": {
        "name": "Onoskelis",
        "alt_names": ["She with Ass's Legs"],
        "rank": "Female Demon",
        "domain": "Seduction, Perversion, Shape-shifting",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Beautiful woman with ass legs",
        "description": "Female demon with beautiful upper body but ass's legs. Lives in caves, seduces men in sleep, leads them to ruin and perversion. Can become beautiful woman or take bestial form. Thwarted by writing out Joel 2:27."
    },
    
    "kunopegos": {
        "name": "Kunopegos",
        "alt_names": ["Dog-Strangler"],
        "rank": "Demon",
        "domain": "Stomach Ailments, Shape-shifting",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Horse-like front, fish tail",
        "description": "Demon appearing as horse in front with fish tail behind. Causes stomach ailments and pains. Name means 'dog-strangler.' Can take various forms. Thwarted by placing of green smaragdus stone."
    },
    
    "lix tetrax": {
        "name": "Lix Tetrax",
        "alt_names": ["Whirlwind Demon"],
        "rank": "Demon of Storms",
        "domain": "Whirlwinds, Storms, Destruction",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Whirlwind, storm",
        "description": "Spirit of whirlwinds appearing in blast of fire. Causes destruction through storms. Declares he creates divisions among men, ruins houses, causes sore suffering. Thwarted by writing 'Michael, imprison Lix Tetrax.'"
    },
    
    "enepsigos": {
        "name": "Enepsigos",
        "alt_names": ["Kronokrator"],
        "rank": "Female Demon",
        "domain": "Moon phases, Transformation, Deception",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Two heads, changing forms",
        "description": "Female demon with many forms depending on moon phase. Has two heads, can appear as woman with horns or beast. Deceives by prophecy, causes diseases. Thwarted by angel Rathanael invoked three times."
    },
    
    "kuntopegos": {
        "name": "Kuntopegos",
        "alt_names": ["Sea Demon"],
        "rank": "Sea Demon",
        "domain": "Sea Storms, Shipwrecks",
        "legions": "None",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Sea waves, drowning",
        "description": "Sea demon causing waves and drowning sailors. Creates sea storms and shipwrecks. Lives in depths of ocean. Thwarted by jameth of marmaraoth inscription."
    },
    
    "the seven sisters": {
        "name": "The Seven Sisters",
        "alt_names": ["Decans", "Planetary Spirits"],
        "rank": "Demon Group",
        "domain": "Headaches, Ailments, Planetary Influence",
        "legions": "7 demons",
        "tradition": "Testament of Solomon",
        "superior": "Bound by Solomon",
        "subordinates": "None",
        "symbols": "Seven stars, heads",
        "description": "Seven female demons causing headaches and various ailments. Each rules different part of head/body. Connected to planetary influences. Include Deception, Strife, Fate, Distress, Error, Power, and 'The Worst.' Thwarted by angel names."
    },
    
    "abezethibou": {
        "name": "Abezethibou",
        "alt_names": ["Abezi-Thibod"],
        "rank": "Fallen Angel/Demon",
        "domain": "Red Sea Pillar, Plots, Hardening of Hearts",
        "legions": "Unknown",
        "tradition": "Testament of Solomon",
        "superior": "Formerly angelic",
        "subordinates": "None",
        "symbols": "One winged, Red Sea pillar",
        "description": "Fallen angel with one wing who lives in pillar of Red Sea. Plotted against Moses by hardening Pharaoh's heart. Held by angel Jamael. One of Moses's chief opponents in Testament of Solomon."
    },
    
    # MORE JEWISH MYSTICISM DEMONS
    "ashmedai": {
        "name": "Ashmedai",
        "alt_names": ["King of Demons - Talmudic"],
        "rank": "King of Demons",
        "domain": "Lust, Construction, Wisdom",
        "legions": "All demons",
        "tradition": "Talmud, Jewish Folklore",
        "superior": "None (king)",
        "subordinates": "All demons",
        "symbols": "Rooster feet, multiple animal heads",
        "description": "Talmudic king of demons, more complex than Christian Asmodeus. Helps Solomon build temple, captured with chain bearing God's name. Sometimes wise, sometimes destructive. Has rooster feet, rules earth's demons."
    },
    
    "ketev meriri": {
        "name": "Ketev Meriri",
        "alt_names": ["Noonday Demon", "Destroyer at Noon"],
        "rank": "Demon of Destruction",
        "domain": "Noon Destruction, Heat Stroke, Madness",
        "legions": "Unknown",
        "tradition": "Jewish Mysticism, Psalm 91",
        "superior": "Various",
        "subordinates": "Noon demons",
        "symbols": "Blazing noon sun",
        "description": "Noonday demon mentioned in Psalm 91:6. Strikes at noon with heat, madness, and death. Has multiple heads covered with scales and eyes. Brings plague and destruction in daylight hours. Most dangerous between noon and 3pm."
    },
    
    "mahalath": {
        "name": "Mahalath",
        "alt_names": ["Queen of Demons"],
        "rank": "Demon Queen",
        "domain": "Night, Dance, Seduction",
        "legions": "478 camps of demons",
        "tradition": "Zohar, Jewish Mysticism",
        "superior": "One of four queens",
        "subordinates": "478 demon camps",
        "symbols": "Dancing, night",
        "description": "Queen of demons ruling 478 camps. Dances with Lilith on new moon. Grandmother of Ashmedai in some texts. Rules Friday nights. One of four queens alongside Lilith, Naamah, and Agrat bat Mahlat."
    },
    
    "rahab": {
        "name": "Rahab (Angel of the Sea)",
        "alt_names": ["Prince of the Sea", "Angel of Pride"],
        "rank": "Fallen Angel/Sea Demon",
        "domain": "Sea, Pride, Chaos",
        "legions": "Sea demons",
        "tradition": "Jewish Mysticism, Talmud",
        "superior": "Destroyed but essence remains",
        "subordinates": "Sea demons",
        "symbols": "Sea monster, chaos waters",
        "description": "Angel of the sea who refused to part Red Sea for Moses. Killed by God but essence persists. Embodies primordial chaos and pride. Sometimes confused with Leviathan. Prince of the primordial waters."
    },
    
    "dumah": {
        "name": "Dumah",
        "alt_names": ["Angel of Silence", "Prince of Sheol"],
        "rank": "Angel of Death/Sheol",
        "domain": "Silence of Death, Punishment of Wicked",
        "legions": "Myriads of destroying angels",
        "tradition": "Jewish Mysticism, Talmud",
        "superior": "Ambiguous (angel or demon)",
        "subordinates": "Destroying angels",
        "symbols": "Silence, Sheol, flaming staff",
        "description": "Angel of silence ruling Sheol (underworld). Commands myriads of destroying angels. Punishes wicked souls with rod of fire. Name means 'silence.' Ambiguous between angel and demon in different texts."
    },
    
    "af": {
        "name": "Af",
        "alt_names": ["Angel of Anger"],
        "rank": "Angel/Demon of Wrath",
        "domain": "Divine Anger, Destruction",
        "legions": "Destroying angels",
        "tradition": "Jewish Mysticism",
        "superior": "Serves divine wrath",
        "subordinates": "Angels of anger",
        "symbols": "Fire, wrath",
        "description": "Angel of anger embodying divine wrath. Works with Hemah (fury). Made entirely of chains of black and red fire. Swallows souls. Moses faced Af when receiving Torah. Represents the wrathful aspect of divine justice."
    },
    
    "hemah": {
        "name": "Hemah",
        "alt_names": ["Angel of Fury"],
        "rank": "Angel/Demon of Fury",
        "domain": "Divine Fury, Punishment",
        "legions": "Destroying angels",
        "tradition": "Jewish Mysticism",
        "superior": "Serves divine fury",
        "subordinates": "Angels of fury",
        "symbols": "Poison, fury",
        "description": "Angel of fury working with Af. Can swallow world in one gulp. Made of chains of fire. Moses faced both Af and Hemah. Represents extreme divine punishment. Name means 'fury' or 'poison.'"
    },
    
    # SLAVIC DEMONS
    "chernobog": {
        "name": "Chernobog",
        "alt_names": ["Black God", "Czorneboh"],
        "rank": "Dark God",
        "domain": "Darkness, Misfortune, Death",
        "legions": "Dark spirits",
        "tradition": "Slavic Mythology",
        "superior": "None (opposed to Belobog)",
        "subordinates": "Dark spirits and demons",
        "symbols": "Darkness, black",
        "description": "Black god of darkness and misfortune in Slavic mythology. Opposite of Belobog (White God). Brings bad luck, death, and calamity. Few records survive of pre-Christian Slavic demons. Associated with darkness and evil."
    },
    
    "bies": {
        "name": "Bies",
        "alt_names": ["Demon", "Devil"],
        "rank": "Demon",
        "domain": "Evil, Misfortune, Temptation",
        "legions": "Various",
        "tradition": "Slavic (Polish) Mythology",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Evil, darkness",
        "description": "Generic term for demon in Polish. Represents evil spirits causing misfortune. After Christianization, became equivalent to devil. Associated with forests, crossroads, and wild places. Causes nightmares and disease."
    },
    
    "likho": {
        "name": "Likho",
        "alt_names": ["Lykho", "Evil Eye"],
        "rank": "Evil Spirit",
        "domain": "Misfortune, Bad Luck, Evil Eye",
        "legions": "None",
        "tradition": "Slavic (Russian) Mythology",
        "superior": "None",
        "subordinates": "None",
        "symbols": "One eye, misfortune",
        "description": "Personification of evil fate and misfortune. Often depicted as tall, emaciated woman with one eye. Brings bad luck to those she encounters. Name means 'evil' or 'misfortune.' Avoid eye contact or mentioning it."
    },
    
    # NORSE/GERMANIC DEMONS & DARK ENTITIES
    "hel": {
        "name": "Hel",
        "alt_names": ["Hela", "Queen of Helheim"],
        "rank": "Goddess/Demon of Death",
        "domain": "Death, Underworld, Disease",
        "legions": "Dishonored dead",
        "tradition": "Norse Mythology",
        "superior": "Daughter of Loki",
        "subordinates": "The dishonored dead",
        "symbols": "Half-corpse, half-living",
        "description": "Daughter of Loki ruling realm of the dead (Helheim). Half her body living, half corpse. Rules those who die of disease or old age. Will lead army against gods at Ragnarok. Name means 'hidden' or 'concealed.'"
    },
    
    "fenrir": {
        "name": "Fenrir",
        "alt_names": ["Fenris Wolf", "Hrodvitnir"],
        "rank": "Giant Wolf/Monster",
        "domain": "Destruction, Binding, Ragnarok",
        "legions": "Wolves",
        "tradition": "Norse Mythology",
        "superior": "Son of Loki",
        "subordinates": "Wolves Skoll and Hati (sons)",
        "symbols": "Giant wolf, chains",
        "description": "Monstrous wolf son of Loki, bound by gods with magical chain Gleipnir. Will break free at Ragnarok and devour Odin. Grows larger until he can swallow world. Father of wolves Skoll (chases sun) and Hati (chases moon)."
    },
    
    "jormungandr": {
        "name": "Jormungandr",
        "alt_names": ["Midgard Serpent", "World Serpent"],
        "rank": "Serpent/Monster",
        "domain": "Ocean, Chaos, Venom",
        "legions": "Sea monsters",
        "tradition": "Norse Mythology",
        "superior": "Son of Loki",
        "subordinates": "Sea serpents",
        "symbols": "Serpent encircling world",
        "description": "Gigantic serpent son of Loki, cast into ocean by Odin. Grew so large it encircles Midgard (Earth) and bites own tail. Enemy of Thor. Will rise at Ragnarok, kill Thor with venom (but be slain). Ouroboros-like symbol."
    },
    
    "nidhogg": {
        "name": "Nidhogg",
        "alt_names": ["Nithhoggr", "Malice Striker"],
        "rank": "Dragon/Serpent",
        "domain": "Corpses, Roots of Yggdrasil, Malice",
        "legions": "Serpents",
        "tradition": "Norse Mythology",
        "superior": "None",
        "subordinates": "Countless serpents",
        "symbols": "Dragon gnawing roots",
        "description": "Dragon gnawing at roots of world tree Yggdrasil. Chews corpses of the wicked in realm of the dead. Name means 'malice striker' or 'curse striker.' Eternal enemy of eagle atop Yggdrasil. Will survive Ragnarok."
    },
    
    "draugr": {
        "name": "Draugr",
        "alt_names": ["Aptrgangr", "After-goer"],
        "rank": "Undead Spirit",
        "domain": "Undeath, Treasure Guarding, Curses",
        "legions": "Various draugr",
        "tradition": "Norse Mythology",
        "superior": "None (type of being)",
        "subordinates": "None",
        "symbols": "Undead, treasure mounds",
        "description": "Undead creature guarding treasure mounds. Possesses superhuman strength, can increase size, smell of decay. Can drive men mad, enter dreams, bring pestilence. Cannot cross running water. Killed by beheading and burning."
    },
    
    "mare": {
        "name": "Mare",
        "alt_names": ["Mara", "Night Mare"],
        "rank": "Night Spirit",
        "domain": "Nightmares, Sleep Paralysis",
        "legions": "Night demons",
        "tradition": "Germanic/Norse Mythology",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Night, crushing chest, horses",
        "description": "Female spirit causing nightmares and sleep paralysis. Sits on chest of sleeping victims, causing breathlessness and bad dreams. Origin of word 'nightmare.' Can take form of animals. Passes through keyholes as mist."
    },
    
    # ADDITIONAL MESOPOTAMIAN DEMONS
    "ereshkigal": {
        "name": "Ereshkigal",
        "alt_names": ["Queen of the Dead"],
        "rank": "Goddess of Underworld",
        "domain": "Death, Underworld, Judgment",
        "legions": "Underworld demons",
        "tradition": "Mesopotamian (Sumerian/Akkadian)",
        "superior": "None (queen)",
        "subordinates": "Namtar, Nergal (consort), underworld demons",
        "symbols": "Underworld, death",
        "description": "Queen of the underworld (Kur/Irkalla). Sister of Inanna/Ishtar. Rules the dead with iron fist. Trapped in underworld, envious of living. Cannot be escaped once you enter her domain. Judges the dead."
    },
    
    "namtar": {
        "name": "Namtar",
        "alt_names": ["Fate", "Destiny"],
        "rank": "Demon of Fate/Disease",
        "domain": "Disease, Pestilence, Fate",
        "legions": "60 diseases",
        "tradition": "Mesopotamian (Sumerian/Akkadian)",
        "superior": "Servant of Ereshkigal",
        "subordinates": "Commands 60 diseases",
        "symbols": "Disease, plague",
        "description": "Demon and vizier of Ereshkigal in underworld. Name means 'fate' or 'destiny.' Commands 60 diseases. Responsible for carrying plague to humanity. Can be invoked to cause disease. Appears in Epic of Gilgamesh."
    },
    
    "alu": {
        "name": "Alu",
        "alt_names": ["Demon of Night"],
        "rank": "Night Demon",
        "domain": "Night terrors, Fatigue, Disease",
        "legions": "Various",
        "tradition": "Mesopotamian (Akkadian/Babylonian)",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Faceless, lurking",
        "description": "Faceless demon lurking in shadows and ruins. Causes night terrors, stalks at night. No mouth, ears, or face. Hides in corners waiting to attack. Causes exhaustion and wasting diseases. Related to lilitu spirits."
    },
    
    "gallu": {
        "name": "Gallu",
        "alt_names": ["Galla Demons"],
        "rank": "Demon Class",
        "domain": "Dragging Souls to Underworld",
        "legions": "Seven Gallu",
        "tradition": "Mesopotamian (Sumerian)",
        "superior": "Servants of Ereshkigal",
        "subordinates": "None",
        "symbols": "Underworld, dragging souls",
        "description": "Class of underworld demons who drag souls to Kur. Cannot be bribed with offerings. Appear in Inanna's descent - follow her back from underworld. Seven Gallu mentioned most often. Merciless pursuers of the dead."
    },
    
    "rabisu": {
        "name": "Rabisu",
        "alt_names": ["The Croucher", "Lurker"],
        "rank": "Demon Class",
        "domain": "Ambush, Lurking, Doorways",
        "legions": "Various",
        "tradition": "Mesopotamian (Akkadian/Babylonian)",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Doorways, thresholds, ambush",
        "description": "Demons that crouch at doorways and thresholds waiting to ambush. Attack those entering/leaving buildings. Hide in shadows. Possibly inspired biblical concept of 'sin crouching at door' (Genesis 4:7). Warded off with apotropaic images."
    },
    
    "utukku": {
        "name": "Utukku",
        "alt_names": ["Utukki Limnuti - Evil Utukku"],
        "rank": "Demon Class",
        "domain": "Various Evil Acts, Disease",
        "legions": "Seven Evil Utukku",
        "tradition": "Mesopotamian (Sumerian/Akkadian)",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Seven winds, evil",
        "description": "Class of demons or spirits, can be good or evil. Utukki Limnuti are seven evil ones. Attack humans, cause disease. Associated with seven winds. Neither living nor dead, neither male nor female. Formless chaos entities."
    },
    
    # ARABIC/ISLAMIC DEMONS (JINN)
    "ifrit": {
        "name": "Ifrit",
        "alt_names": ["Efreet", "Afreet"],
        "rank": "Powerful Jinn Class",
        "domain": "Fire, Power, Revenge",
        "legions": "Various ifrit",
        "tradition": "Islamic, Arabian Mythology",
        "superior": "Iblis (some traditions)",
        "subordinates": "Lesser jinn",
        "symbols": "Fire, smoke, great power",
        "description": "Powerful class of jinn made from smokeless fire. Known for cunning and strength. Can be good or evil. Associated with underworld and ruins. Live long lives (thousands of years). Feature in Arabian Nights."
    },
    
    "marid": {
        "name": "Marid",
        "alt_names": ["Marids"],
        "rank": "Jinn Class",
        "domain": "Water, Power, Pride",
        "legions": "Various marid",
        "tradition": "Islamic, Arabian Mythology",
        "superior": "Most powerful jinn type",
        "subordinates": "Other jinn",
        "symbols": "Water, great power",
        "description": "Most powerful type of jinn. Associated with water and seas. Extremely proud and difficult to control. Blue-skinned in some descriptions. Grant wishes but dangerous to deal with. Require powerful magic to bind."
    },
    
    "qareen": {
        "name": "Qareen",
        "alt_names": ["Qarin", "Shadow Self"],
        "rank": "Personal Jinn",
        "domain": "Temptation, Whispering, Personal Evil",
        "legions": "One per person",
        "tradition": "Islamic Tradition",
        "superior": "Iblis",
        "subordinates": "None",
        "symbols": "Shadow, whispering",
        "description": "Personal jinn assigned to every human at birth. Whispers evil suggestions, tries to lead astray. Every person has a qareen except prophets (whose qareen submitted to Islam). Shadowy companion throughout life."
    },
    
    "ghul": {
        "name": "Ghul",
        "alt_names": ["Ghoul"],
        "rank": "Demon/Jinn",
        "domain": "Graveyards, Consuming Dead, Shape-shifting",
        "legions": "Various ghuls",
        "tradition": "Islamic, Arabian Mythology",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Graveyards, corpses, desert",
        "description": "Demon dwelling in graveyards and deserts. Consumes human flesh, especially corpses. Can shape-shift into animals or beautiful women (ghulah). Lures travelers to death. Origin of English word 'ghoul.' Mentioned in Arabian Nights."
    },
    
    "si'lat": {
        "name": "Si'lat",
        "alt_names": ["Female Jinn"],
        "rank": "Jinn Class",
        "domain": "Seduction, Trickery",
        "legions": "Various",
        "tradition": "Arabian/Islamic",
        "superior": "Various",
        "subordinates": "None",
        "symbols": "Beauty, deception",
        "description": "Female jinn or demoness. Uses beauty and trickery to seduce and mislead humans. Appears in tales from Arabian mythology. Can be malicious or neutral depending on story."
    },
    
    # CELTIC DEMONS & DARK FAE
    "balor": {
        "name": "Balor",
        "alt_names": ["Balor of the Evil Eye", "Balar"],
        "rank": "Fomorian King",
        "domain": "Evil Eye, Death, Destruction",
        "legions": "Fomorian armies",
        "tradition": "Irish/Celtic Mythology",
        "superior": "King of Fomorians",
        "subordinates": "Fomorian demons",
        "symbols": "Evil eye, death gaze",
        "description": "King of Fomorians with poisonous eye that kills what it sees. Eye requires four men to lift the lid. Killed by grandson Lugh at Second Battle of Moytura. Represents destructive forces opposing gods (Tuatha Dé Danann)."
    },
    
    "carman": {
        "name": "Carman",
        "alt_names": ["The Witch"],
        "rank": "Witch/Demon",
        "domain": "Blight, Destruction, Dark Magic",
        "legions": "Three sons (Dub, Dother, Dian)",
        "tradition": "Irish Mythology",
        "superior": "None",
        "subordinates": "Three demon sons",
        "symbols": "Blight, crops dying",
        "description": "Greek witch who came to Ireland with three demon sons. Caused blight and destruction with magic. Her sons: Dub (darkness), Dother (evil), and Dian (violence). Defeated by Tuatha Dé Danann druids, bound with spells."
    },
    
    "abhartach": {
        "name": "Abhartach",
        "alt_names": ["Irish Vampire"],
        "rank": "Undead Demon",
        "domain": "Blood, Undeath",
        "legions": "None",
        "tradition": "Irish Folklore",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Blood drinking, rising from grave",
        "description": "Tyrannical dwarf chieftain who became vampire after death. Rose from grave nightly demanding blood from subjects. Killed three times before druid revealed must be buried upside down with thorn stake. Possible inspiration for Dracula."
    },
    
    "dullahan": {
        "name": "Dullahan",
        "alt_names": ["Headless Horseman", "Gan Ceann"],
        "rank": "Death Spirit",
        "domain": "Death Omen, Souls",
        "legions": "Various",
        "tradition": "Irish Folklore",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Headless, black horse, whip of spine",
        "description": "Headless horseman carrying own head. Rides black horse, uses human spine as whip. When stops riding, someone dies. Calls person's name and they die immediately. Only gold can drive off. Cannot be stopped or observed. Death omen."
    },
    
    "banshee": {
        "name": "Banshee",
        "alt_names": ["Bean Sidhe", "Woman of the Faerie Mound"],
        "rank": "Death Spirit",
        "domain": "Death Omens, Wailing",
        "legions": "Various",
        "tradition": "Irish/Scottish Folklore",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Wailing, combing hair, washing shrouds",
        "description": "Female spirit whose wailing warns of death. Appears washing bloody clothes at river or combing long hair. Attached to certain families. Wail heard when family member about to die. Can appear as old woman or beautiful maiden. Not evil but omen of death."
    },
    
    "nuckelavee": {
        "name": "Nuckelavee",
        "alt_names": ["Most Terrible of Demons"],
        "rank": "Sea Demon",
        "domain": "Plague, Drought, Blight",
        "legions": "None",
        "tradition": "Orcadian (Scottish) Folklore",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Skinless horse-man hybrid",
        "description": "Most terrible demon from Orkney. Half-man, half-horse fused together, entirely skinless showing muscles and veins. Head ten feet wide, breath destroys crops, causes plague and drought. Confined to sea most of year. Cannot cross fresh water."
    },
    
    # GREEK DEMONS & MONSTERS
    "typhon": {
        "name": "Typhon",
        "alt_names": ["Typhoeus", "Father of Monsters"],
        "rank": "Primordial Monster",
        "domain": "Chaos, Storms, Monsters",
        "legions": "All monsters",
        "tradition": "Greek Mythology",
        "superior": "Son of Gaia and Tartarus",
        "subordinates": "All monsters (as father)",
        "symbols": "Hundred serpent heads, fire, storms",
        "description": "Most deadly monster in Greek mythology. Hundred serpent heads breathing fire, eyes flashing. Father of many monsters (Cerberus, Hydra, Chimera). Challenged Zeus, nearly defeated Olympians. Cast into Tartarus under Mt. Etna."
    },

    "echidna": {
        "name": "Echidna",
        "alt_names": ["Mother of Monsters"],
        "rank": "Primordial Monster",
        "domain": "Monsters, Serpents",
        "legions": "All monsters (as mother)",
        "tradition": "Greek Mythology",
        "superior": "Mate of Typhon",
        "subordinates": "Monster offspring",
        "symbols": "Half-woman, half-serpent",
        "description": "Mother of Monsters, mate of Typhon. Half beautiful woman, half serpent. Bore many famous monsters: Cerberus, Hydra, Chimera, Sphinx, Nemean Lion. Lives in cave, devours passersby. Immortal but confined by Zeus."
    },
    
    "lamia": {
        "name": "Lamia",
        "alt_names": ["Child-Eater"],
        "rank": "Demon/Monster",
        "domain": "Child Murder, Seduction",
        "legions": "Lamiae (plural)",
        "tradition": "Greek Mythology",
        "superior": "Cursed by Hera",
        "subordinates": "Other Lamiae",
        "symbols": "Snake lower body, beautiful woman upper",
        "description": "Queen of Libya cursed by Hera to devour children. Can remove eyes from sockets. Seduces men then drinks their blood. Lower body of serpent. Mother of monsters. Name became generic for child-eating female demons (lamiae)."
    },
    
    "empusa": {
        "name": "Empusa",
        "alt_names": ["Empousa"],
        "rank": "Demon/Demi-Goddess",
        "domain": "Seduction, Blood-drinking, Shape-shifting",
        "legions": "Empusae (servants of Hecate)",
        "tradition": "Greek Mythology",
        "superior": "Servant of Hecate",
        "subordinates": "Other Empusae",
        "symbols": "One bronze leg, one donkey leg, beautiful woman",
        "description": "Shape-shifting demon servant of Hecate. One bronze leg, one donkey leg. Transforms into beautiful woman to seduce young men, then drinks their blood. Guards roads and crossroads. Sent by Hecate to frighten travelers."
    },
    
    "mormo": {
        "name": "Mormo",
        "alt_names": ["Mormolyke"],
        "rank": "Demon Spirit",
        "domain": "Fear, Children's Nightmares",
        "legions": "None",
        "tradition": "Greek Mythology",
        "superior": "Servant of Hecate",
        "subordinates": "None",
        "symbols": "Fearsome form, child-frightener",
        "description": "Female spirit servant of Hecate who bites naughty children. Used by parents to frighten children into obedience. Shape-shifter taking terrifying forms. Name became synonymous with bogeywoman. Associated with Lamia and Empusa."
    },
    
    "hecate": {
        "name": "Hecate (Dark Aspect)",
        "alt_names": ["Hekate", "Queen of Ghosts"],
        "rank": "Goddess of Witchcraft",
        "domain": "Witchcraft, Necromancy, Crossroads, Night",
        "legions": "Ghosts, Empusae, hounds",
        "tradition": "Greek/Roman Mythology",
        "superior": "Titan/Olympian goddess",
        "subordinates": "Empusae, ghosts, spirits",
        "symbols": "Three-faced, torches, keys, dogs",
        "description": "Goddess of witchcraft, necromancy, and crossroads. Commands ghosts and demons. Three-faced (maiden, mother, crone). Accompanied by spectral hounds. Holds keys to underworld. Taught Medea witchcraft. Dark moon goddess."
    },
    
    "alecto": {
        "name": "Alecto",
        "alt_names": ["The Unceasing", "Fury"],
        "rank": "Fury/Erinys",
        "domain": "Unceasing Anger, Moral Crimes",
        "legions": "None",
        "tradition": "Greek/Roman Mythology",
        "superior": "Born from Uranus's blood",
        "subordinates": "None",
        "symbols": "Serpents, whip, torch",
        "description": "One of three Furies punishing moral crimes. Name means 'unceasing anger.' Hair of snakes, eyes dripping blood, bat wings. Punishes oath-breakers and those who sin against family. Drives victims mad with guilt."
    },
    
    "megaera": {
        "name": "Megaera",
        "alt_names": ["The Jealous Rage", "Fury"],
        "rank": "Fury/Erinys",
        "domain": "Jealousy, Envy, Marital Crimes",
        "legions": "None",
        "tradition": "Greek/Roman Mythology",
        "superior": "Born from Uranus's blood",
        "subordinates": "None",
        "symbols": "Serpents, whip",
        "description": "Fury punishing crimes of jealousy and marital infidelity. Name means 'jealous rage.' Covered in serpents, eyes bleeding. Torments the guilty with unrelenting pursuit. Cannot be escaped or appeased."
    },
    
    "tisiphone": {
        "name": "Tisiphone",
        "alt_names": ["Avenger of Murder", "Fury"],
        "rank": "Fury/Erinys",
        "domain": "Murder, Blood Crimes, Vengeance",
        "legions": "None",
        "tradition": "Greek/Roman Mythology",
        "superior": "Born from Uranus's blood",
        "subordinates": "None",
        "symbols": "Serpents, blood, whip",
        "description": "Fury avenging murder and blood crimes. Name means 'avenger of murder.' Most terrible of three Furies. Wears bloody robe, serpents in hair. Guards gates of Tartarus. Drove mortals to madness and suicide."
    },
    
    "cerberus": {
        "name": "Cerberus",
        "alt_names": ["Kerberos", "Hound of Hades"],
        "rank": "Guardian Beast",
        "domain": "Guarding Underworld Gates",
        "legions": "None",
        "tradition": "Greek/Roman Mythology",
        "superior": "Guards for Hades",
        "subordinates": "None",
        "symbols": "Three heads, serpent tail, snake mane",
        "description": "Three-headed dog guarding gates of underworld. Son of Typhon and Echidna. Prevents dead from leaving and living from entering. Serpent tail, snake mane. Only defeated by Heracles, charmed by Orpheus, drugged by Aeneas."
    },
    
    # ROMAN DEMONS
    "cacus": {
        "name": "Cacus",
        "alt_names": ["Fire-Breather"],
        "rank": "Monster/Demon",
        "domain": "Fire, Theft, Murder",
        "legions": "None",
        "tradition": "Roman Mythology",
        "superior": "Son of Vulcan",
        "subordinates": "None",
        "symbols": "Fire-breathing, cave",
        "description": "Giant fire-breathing demon living in cave on Aventine Hill. Son of Vulcan. Terrorized countryside, stole Hercules's cattle. Dragged them backward into cave to hide tracks. Slain by Hercules who strangled him."
    },
    
    "lemures": {
        "name": "Lemures",
        "alt_names": ["Larvae"],
        "rank": "Restless Dead Spirits",
        "domain": "Haunting, Malevolent Spirits",
        "legions": "Many lemures",
        "tradition": "Roman Mythology",
        "superior": "None",
        "subordinates": "None",
        "symbols": "Ghosts, haunting",
        "description": "Malevolent spirits of the restless dead. Haunt living, especially their descendants. During Lemuria festival (May), Romans performed rites to appease them. Walk at night, enter homes. Distinct from benevolent Lares (household spirits)."
    },
    
    "manes": {
        "name": "Manes",
        "alt_names": ["Di Manes", "Shades"],
        "rank": "Deified Dead Spirits",
        "domain": "Death, Ancestors, Underworld",
        "legions": "All dead",
        "tradition": "Roman Mythology",
        "superior": "None (collective)",
        "subordinates": "Individual shades",
        "symbols": "Graves, tombs, underworld",
        "description": "Deified souls of the dead, especially ancestors. 'Di Manes' means 'divine shades.' Not necessarily evil but powerful. Required offerings and respect. Could become vengeful if neglected. Inscribed on tombs as 'D.M.' Protection of graves."
    },
    
    # GNOSTIC ARCHONS & DEMONS
    "yaldabaoth": {
        "name": "Yaldabaoth",
        "alt_names": ["Demiurge", "Saklas", "Samael"],
        "rank": "Demiurge/Chief Archon",
        "domain": "Material World, Ignorance, False Creation",
        "legions": "All Archons",
        "tradition": "Gnosticism",
        "superior": "None in material realm",
        "subordinates": "12 Archons, material world",
        "symbols": "Lion-headed serpent",
        "description": "False god who created material world in ignorance. Chief Archon with lion head and serpent body. Believes himself the only god. Traps divine sparks in matter. Opposed by true spiritual realm. Rules through 12 Archons (planetary rulers)."
    },
    
    "abraxas": {
        "name": "Abraxas",
        "alt_names": ["Abrasax"],
        "rank": "Archon/Aeon",
        "domain": "365 Heavens, Duality",
        "legions": "365 spirits",
        "tradition": "Gnosticism, Hermeticism",
        "superior": "Ambiguous (good/evil/both)",
        "subordinates": "365 spirits of days",
        "symbols": "Rooster head, human body, serpent legs, whip/shield",
        "description": "Complex deity/archon embodying good and evil. Head of rooster, human body, serpent legs. Holds whip and shield. Name's letters equal 365 in Greek numerology (days/heavens). Neither wholly good nor evil but beyond morality. Generator of 365 spheres."
    },
    
    "archons": {
        "name": "The Seven Archons",
        "alt_names": ["Planetary Rulers", "Rulers of This World"],
        "rank": "Archon Group",
        "domain": "Seven Planets, Material Bondage",
        "legions": "Various demons",
        "tradition": "Gnosticism",
        "superior": "Yaldabaoth",
        "subordinates": "Demons of material world",
        "symbols": "Seven planets, chains",
        "description": "Seven rulers of planetary spheres serving Yaldabaoth. Keep divine sparks trapped in material world. Each rules a planet and aspect of material bondage. Names vary by text but include Yao, Sabaoth, Adonai, Eloai, Orai, Astaphai. Ignorant, jealous beings."
    },
    
    # BIBLICAL DEMONS NOT YET LISTED
    "azazel": {
        "name": "Azazel (Apocalypse)",
        "alt_names": ["Unclean Bird"],
        "rank": "Fallen Angel",
        "domain": "Temptation, Preventing Visions",
        "legions": "Unknown",
        "tradition": "Apocalypse of Abraham",
        "superior": "Among chief fallen",
        "subordinates": "Demons of temptation",
        "symbols": "Unclean bird, corruption",
        "description": "In Apocalypse of Abraham, appears as unclean bird trying to prevent Abraham's vision of God. Represents temptation and corruption. Angel Yahoel drives him away. Associated with sacrifices and scapegoat traditions."
    },
    
    "gadreel": {
        "name": "Gadreel (Biblical)",
        "alt_names": ["Wall of God", "Deceiver of Eve"],
        "rank": "Fallen Angel",
        "domain": "Weapons, Deception",
        "legions": "Unknown",
        "tradition": "Book of Enoch, Extra-biblical",
        "superior": "Among Watchers",
        "subordinates": "Demons of warfare",
        "symbols": "Weapons, serpent (as Eden serpent)",
        "description": "Watcher who taught making of weapons and warfare. In some traditions, he was the serpent who deceived Eve in Eden (not Satan). Introduced mankind to instruments of death. Name means 'Wall of God' or 'God is my helper' (ironic)."
    },
    
    "dagon": {
        "name": "Dagon (Biblical)",
        "alt_names": ["Fish God", "Grain God"],
        "rank": "False God/Demon",
        "domain": "Philistine Worship, Fish/Grain",
        "legions": "Unknown",
        "tradition": "Hebrew Bible (Judges, Samuel)",
        "superior": "None among Philistines",
        "subordinates": "Philistine demons",
        "symbols": "Fish body, hands falling off statue",
        "description": "Chief god of Philistines in Bible. Temple collapsed when Ark of Covenant placed there; statue's hands broke off. Samson destroyed temple of Dagon, killing thousands. Fish-god (or grain god). Humiliated by Yahweh multiple times."
    },
    
    # HAITIAN VODOU DEMONS/LOA (PETRO)
    "baron samedi": {
        "name": "Baron Samedi",
        "alt_names": ["Baron Saturday", "Baron La Croix"],
        "rank": "Loa of Death",
        "domain": "Death, Graves, Resurrection, Obscenity",
        "legions": "Guede spirits",
        "tradition": "Haitian Vodou",
        "superior": "Leader of Guede",
        "subordinates": "All Guede (death spirits)",
        "symbols": "Top hat, skull face, purple/black, cigars, rum",
        "description": "Loa of death and resurrection. Appears in top hat, skull face, dark glasses. Stands at crossroads where souls pass. Extremely obscene and sexual. Drinks rum with hot peppers, smokes cigars. Can heal or deny death. Guards graves."
    },
    
    "baron criminel": {
        "name": "Baron Criminel",
        "alt_names": ["Baron of the Cemetery"],
        "rank": "Petro Loa",
        "domain": "Crime, Judgment of Dead",
        "legions": "Criminal spirits",
        "tradition": "Haitian Vodou",
        "superior": "One of Guede family",
        "subordinates": "Spirits of criminals",
        "symbols": "Red, judgment",
        "description": "Loa who judges criminal dead. Violent aspect of Baron family. Associated with crime and punishment. More aggressive than Baron Samedi. Patron of criminals and justice for victims. Part of Guede (death spirit) family."
    },
    
    "kalfu": {
        "name": "Kalfu",
        "alt_names": ["Carrefour", "Master of Crossroads"],
        "rank": "Petro Loa",
        "domain": "Evil Magic, Crossroads, Malevolence",
        "legions": "Evil spirits",
        "tradition": "Haitian Vodou",
        "superior": "Controls evil magic",
        "subordinates": "Malevolent spirits",
        "symbols": "Crossroads, moon, dark side",
        "description": "Dark counterpart to Legba. Controls the malevolent forces and evil magic. Guards crossroads at night (Legba guards by day). Allows evil spirits to enter world. Petro (hot) aspect. Works with dark magic and curses."
    },
    
    "marinette": {
        "name": "Marinette",
        "alt_names": ["Marinette Bwa Chech", "Marinette Pied Cheche"],
        "rank": "Petro Loa",
        "domain": "Fire, Freedom, Revenge, Screech Owls",
        "legions": "Fire spirits",
        "tradition": "Haitian Vodou",
        "superior": "Petro nation leader",
        "subordinates": "Angry spirits",
        "symbols": "Screech owl, fire, dry wood",
        "description": "Fierce loa of fire and freedom. Screech owl form. Name means 'dry arms' - reference to fire. Extremely dangerous and violent. Associated with Haitian Revolution. Drinks flames, served with fire. Punishes with burning. Werewolf form in some traditions."
    },
    
    "ti-jean petro": {
        "name": "Ti-Jean Petro",
        "alt_names": ["Little John Petro"],
        "rank": "Petro Loa",
        "domain": "Rage, Serpents, Lightning",
        "legions": "Serpent spirits",
        "tradition": "Haitian Vodou",
        "superior": "Major Petro loa",
        "subordinates": "Serpent spirits",
        "symbols": "Serpent, lightning, rage",
        "description": "Dangerous serpent loa of rage and fire. Throws lightning. One-footed serpent form. Violent and unpredictable. Part of Petro (hot) nation of loa. Must be approached with caution. Associated with Dan Petro serpent."
    },
    
    # CANAANITE/PHOENICIAN DEMONS
    "mot": {
        "name": "Mot",
        "alt_names": ["Maweth", "Death"],
        "rank": "God of Death",
        "domain": "Death, Underworld, Drought, Sterility",
        "legions": "Death spirits",
        "tradition": "Canaanite/Ugaritic",
        "superior": "None (primordial)",
        "subordinates": "Dead spirits",
        "symbols": "Death, drought, underworld",
        "description": "God of death and sterility in Canaanite myth. Eternal enemy of Baal. Devours Baal causing drought. Eventually defeated by Anat who cuts him with sword. Represents death and barren land. Mouth stretches from earth to heaven, swallowing all."
    },
    
    "yam": {
        "name": "Yam",
        "alt_names": ["Yamm", "Judge River", "Prince Sea"],
        "rank": "God of Chaos/Sea",
        "domain": "Sea, Rivers, Chaos, Floods",
        "legions": "Sea monsters",
        "tradition": "Canaanite/Ugaritic",
        "superior": "None (primordial)",
        "subordinates": "Sea serpents, Leviathan",
        "symbols": "Sea, chaos, serpents",
        "description": "God of sea and chaos, enemy of Baal. Represents untamed waters and primordial chaos. Demands tribute, wants to rule gods. Defeated by Baal with magic clubs. Associated with Leviathan and sea serpents. Parallel to Tiamat."
    },
    
    "resheph": {
        "name": "Resheph",
        "alt_names": ["Reshef", "God of Plague"],
        "rank": "God of Plague/War",
        "domain": "Plague, War, Fire",
        "legions": "Plague spirits",
        "tradition": "Canaanite/Egyptian",
        "superior": "None",
        "subordinates": "Spirits of disease",
        "symbols": "Gazelle horns, arrows, plague",
        "description": "God of plague and war with gazelle horns. Shoots arrows of plague and fire. Spreads disease and pestilence. Also associated with lightning. Adopted into Egyptian pantheon. Name means 'flame' or 'burning.' Bringer of death through disease."
    },
    
    # ADDITIONAL ENOCHIAN WATCHERS
    "shamsiel": {
        "name": "Shamsiel",
        "alt_names": ["Sun of God"],
        "rank": "Watcher",
        "domain": "Signs of the Sun",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Among 200 Watchers",
        "subordinates": "None specified",
        "symbols": "Sun, signs",
        "description": "Watcher who taught signs of the sun. Name means 'Sun of God.' One of leaders of 200 Watchers who descended to Mount Hermon. Taught forbidden solar knowledge and divination by sun signs."
    },
    
    "turel": {
        "name": "Turel",
        "alt_names": ["Rock of God"],
        "rank": "Watcher",
        "domain": "Unknown Forbidden Knowledge",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Among 200 Watchers",
        "subordinates": "None specified",
        "symbols": "Mountains, rock",
        "description": "One of 200 Watchers led by Semyaza. Name means 'Rock of God' or 'Mountain of God.' Specific teachings not detailed but participated in corruption of humanity. Bound until Day of Judgment."
    },
    
    "ananiel": {
        "name": "Ananiel",
        "alt_names": ["Cloud of God"],
        "rank": "Watcher",
        "domain": "Signs, Sorcery",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Among 200 Watchers",
        "subordinates": "None specified",
        "symbols": "Clouds, signs",
        "description": "Watcher who taught signs and sorcery. Name means 'Cloud of God.' One of chiefs among fallen Watchers. Taught interpretation of omens and weather signs."
    },
    
    # MODERN OCCULT/CHAOS MAGIC ENTITIES
    "choronzon": {
        "name": "Choronzon",
        "alt_names": ["Demon of Dispersion", "333"],
        "rank": "Demon of Abyss",
        "domain": "Chaos, Dispersion, Dissolution of Ego",
        "legions": "None (chaos itself)",
        "tradition": "Thelema, Enochian Magic",
        "superior": "Guardian of Abyss",
        "subordinates": "None",
        "symbols": "333, dispersion, chaos",
        "description": "Demon of the Abyss in Thelemic tradition. Dweller on threshold between material and spiritual. Disperses and confuses. Number 333. Aleister Crowley claimed contact. Represents dissolution of ego required to cross Abyss. Pure chaos without form."
    },
    
    "coronzon": {
        "name": "Coronzon",
        "alt_names": ["Demon of Crossing"],
        "rank": "Archdemonic Intelligence",
        "domain": "Obstacles, Dispersion",
        "legions": "Unknown",
        "tradition": "Enochian Magic, John Dee",
        "superior": "None",
        "subordinates": "None specified",
        "symbols": "Crossing, barriers",
        "description": "Demon encountered in Enochian magic workings. Related or identical to Choronzon in some systems. Represents barriers and obstacles to spiritual attainment. Mentioned in John Dee's Enochian system."
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
    
    # ADDITIONAL DEMONS FROM VARIOUS TRADITIONS
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
    },
    
    # ADDITIONAL WATCHERS
    "baraqiel": {
        "name": "Baraqiel",
        "alt_names": ["Barakel", "Lightning of God"],
        "rank": "Watcher",
        "domain": "Astrology, Lightning",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Lightning, stars",
        "description": "Watcher who taught astrology. Name means 'Lightning of God.' One of the leaders of the 200 Watchers who descended to breed with human women."
    },
    
    "armaros": {
        "name": "Armaros",
        "alt_names": ["Arazyal"],
        "rank": "Watcher",
        "domain": "Resolving Enchantments",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Enchantments, counter-spells",
        "description": "Watcher who taught the resolving of enchantments. One of the 200 fallen angels who taught forbidden knowledge to humanity."
    },
    
    "penemue": {
        "name": "Penemue",
        "alt_names": ["Penemu"],
        "rank": "Watcher",
        "domain": "Writing, Wisdom",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Tablet, stylus, bitter wisdom",
        "description": "Watcher who taught humans writing with ink and paper. Taught bitter and sweet wisdom. Led many into error through his teachings."
    },
    
    "gadreel": {
        "name": "Gadreel",
        "alt_names": ["Wall of God"],
        "rank": "Watcher",
        "domain": "Warfare, Deception",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Weapons of war",
        "description": "Watcher who taught the making of weapons of war and instruments of death. Led Eve astray according to some traditions. Introduced warfare and killing to humanity."
    },
    
    "sariel": {
        "name": "Sariel",
        "alt_names": ["Suriel", "Prince of God"],
        "rank": "Watcher/Archangel",
        "domain": "Moon, Lunar cycles",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Ambiguous (both angelic and fallen)",
        "subordinates": "None specified",
        "symbols": "Moon, lunar knowledge",
        "description": "Taught the course of the moon. Listed among both holy angels and fallen Watchers in different texts. Name means 'Prince of God' or 'Command of God.'"
    },
    
    "tamiel": {
        "name": "Tamiel",
        "alt_names": ["Kasdaye", "Perfection of God"],
        "rank": "Watcher",
        "domain": "Demon conjuration",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Summoning, spirits",
        "description": "Watcher who taught humans how to conjure demons and evil spirits. Showed humanity various strikes and blows. Name means 'Perfection of God.'"
    },
    
    "yeqon": {
        "name": "Yeqon",
        "alt_names": [],
        "rank": "Watcher",
        "domain": "Seduction, Leading astray",
        "legions": "Unknown",
        "tradition": "Book of Enoch",
        "superior": "Semyaza",
        "subordinates": "None specified",
        "symbols": "Seduction",
        "description": "Watcher who led astray the sons of God (angels) and brought them down to Earth to breed with human women. Instrumental in the initial corruption of the Watchers."
    },
    
    # ADDITIONAL NOTABLE DEMONS
    "moloch": {
        "name": "Moloch",
        "alt_names": ["Molech", "Molekh"],
        "rank": "Prince/Demon God",
        "domain": "Child Sacrifice, Fire",
        "legions": "Unknown",
        "tradition": "Hebrew Bible, Christian",
        "superior": "Various (associated with Thaumiel)",
        "subordinates": "Demons of cruelty",
        "symbols": "Bronze statue, fire, bull head",
        "description": "Ancient Canaanite deity associated with child sacrifice. Children were burned alive in his bronze statue. Mentioned multiple times in Hebrew Bible as abomination. Associated with Satan in Milton's Paradise Lost."
    },
    
    "dagon": {
        "name": "Dagon",
        "alt_names": ["Dagan"],
        "rank": "Demon Prince",
        "domain": "Sea, Fish, Grain",
        "legions": "Unknown",
        "tradition": "Philistine, Hebrew Bible",
        "superior": "Various",
        "subordinates": "Sea demons",
        "symbols": "Fish body, grain",
        "description": "Philistine deity, god of grain and fish. Depicted as merman. Temple collapsed when Ark of Covenant was placed there. Chief deity of Philistines mentioned in Judges and Samuel."
    },
    
    "chemosh": {
        "name": "Chemosh",
        "alt_names": [],
        "rank": "Demon God",
        "domain": "War, Moabites",
        "legions": "Unknown",
        "tradition": "Hebrew Bible, Moabite",
        "superior": "Various",
        "subordinates": "Demons of war",
        "symbols": "War, destruction",
        "description": "National god of Moabites. Associated with human sacrifice. Mentioned in Hebrew Bible as abomination. Solomon built high place for Chemosh. Rival to Yahweh in ancient Near East."
    },
    
    "baal": {
        "name": "Baal",
        "alt_names": ["Baal Hadad", "Lord"],
        "rank": "Demon Prince/God",
        "domain": "Storms, Fertility, False Worship",
        "legions": "Various",
        "tradition": "Canaanite, Hebrew Bible",
        "superior": "Becomes demon in Judeo-Christian tradition",
        "subordinates": "Various Baalim",
        "symbols": "Bull, lightning, storm",
        "description": "Chief Canaanite deity meaning 'Lord.' Storm and fertility god. Major rival to Yahweh worship. Became demon in Judeo-Christian tradition. Elijah challenged prophets of Baal on Mount Carmel."
    },
    
    "astaroth": {
        "name": "Astaroth",
        "alt_names": ["Astarte", "Ashtoreth", "Ishtar"],
        "rank": "Great Duke",
        "domain": "Knowledge, Secrets, Past/Future",
        "legions": "40",
        "tradition": "Phoenician goddess, Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "40 legions",
        "symbols": "Star, evening star",
        "description": "Originally Phoenician/Canaanite fertility goddess Astarte. Became great duke of hell. Appears riding dragon, holding viper. Answers questions, reveals secrets. Dangerous breath requires magical defense."
    },
    
    "adramelech": {
        "name": "Adramelech",
        "alt_names": ["King of Fire"],
        "rank": "Grand Chancellor of Hell",
        "domain": "Fire, Pride, Clothing",
        "legions": "Unknown",
        "tradition": "Assyrian, Christian Demonology",
        "superior": "High-ranking infernal nobility",
        "subordinates": "Various demons",
        "symbols": "Peacock, mule, human upper body",
        "description": "Assyrian sun god who became Grand Chancellor of Hell. President of the High Council of Devils. Appears as peacock or mule with human upper body. Associated with fire worship and child sacrifice."
    },
    
    "lucifuge rofocale": {
        "name": "Lucifuge Rofocale",
        "alt_names": ["Focalor variant"],
        "rank": "Prime Minister of Hell",
        "domain": "Wealth, Pacts, Avoidance of Light",
        "legions": "Unknown",
        "tradition": "Grimorium Verum, Grand Grimoire",
        "superior": "Lucifer",
        "subordinates": "Manages infernal contracts",
        "symbols": "Fleeing light, contracts",
        "description": "Prime Minister of Hell in grimoire tradition. Name means 'He who flees light.' Controls wealth and treasures of the world. Manages pacts between demons and humans. Appears in Grand Grimoire."
    },
    
    "mephistopheles": {
        "name": "Mephistopheles",
        "alt_names": ["Mephisto"],
        "rank": "Demon",
        "domain": "Pacts, Souls, Deception",
        "legions": "Unknown",
        "tradition": "German Folklore, Faust Legend",
        "superior": "Lucifer (in most versions)",
        "subordinates": "Various",
        "symbols": "Pact, quill, Faust",
        "description": "Demon from Faust legend who makes pact for Doctor Faustus's soul. Sophisticated, cultured demon. Name possibly from Hebrew 'mephir' (destroyer) and 'tophel' (liar). Made famous by Marlowe and Goethe."
    },
    
    "eurynome": {
        "name": "Eurynome",
        "alt_names": ["Prince of Death"],
        "rank": "Superior Demon",
        "domain": "Death, Corpses, Teeth",
        "legions": "Unknown",
        "tradition": "Christian Demonology",
        "superior": "Lucifer",
        "subordinates": "Demons of death",
        "symbols": "Rotting corpse, long teeth, fox pelt",
        "description": "Prince of Death with hideously long teeth. Feeds on corpses. Appears covered in fox pelts. Name from Greek mythology (a different entity). Demon of horrible appearance who presides over death."
    },
    
    "leonard": {
        "name": "Leonard",
        "alt_names": ["Master Leonard"],
        "rank": "Grand Master of Sabbaths",
        "domain": "Witches' Sabbaths, Black Magic",
        "legions": "Unknown",
        "tradition": "European Witchcraft, Inquisition Records",
        "superior": "Satan",
        "subordinates": "Witches, minor demons",
        "symbols": "Black goat, three horns",
        "description": "Inspector General of Black Magic and Grand Master of Nocturnal Orgies. Appears as large black goat with three horns. Presides over witches' sabbaths. Mentioned in witch trial records."
    },
    
    "buer": {
        "name": "Buer",
        "alt_names": [],
        "rank": "President",
        "domain": "Healing, Philosophy, Herbs",
        "legions": "50",
        "tradition": "Ars Goetia",
        "superior": "Lucifer",
        "subordinates": "50 legions",
        "symbols": "Star/wheel with five goat legs, lion head",
        "description": "President of Hell appearing as five-rayed star with lion head in center and goat legs. Teaches philosophy, natural and moral logic. Heals all diseases, provides good familiars. One of few healing demons."
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

def get_entities_by_tradition(tradition):
    """Get all entities from a specific tradition"""
    results = []
    tradition_lower = tradition.lower()
    
    for key, entity in HIERARCHY_DB.items():
        if tradition_lower in entity["tradition"].lower():
            results.append((key, entity))
    
    return results

def get_entities_by_rank(rank):
    """Get all entities of a specific rank"""
    results = []
    rank_lower = rank.lower()
    
    for key, entity in HIERARCHY_DB.items():
        if rank_lower in entity["rank"].lower():
            results.append((key, entity))
    
    return results

def get_goetia_spirits():
    """Get all 72 Goetia spirits in order"""
    goetia_order = [
        "bael", "agares", "vassago", "samigina", "marbas", "valefor", "amon", "barbatos", 
        "paimon", "buer", "gusion", "sitri", "beleth", "leraje", "eligos", "zepar", 
        "botis", "bathin", "sallos", "purson", "marax", "ipos", "aim", "naberius", 
        "glasya-labolas", "bune", "ronove", "berith", "astaroth", "forneus", "foras", 
        "asmoday", "gaap", "furfur", "marchosias", "stolas", "phenex", "halphas", 
        "malphas", "raum", "focalor", "vepar", "sabnock", "shax", "vine", "bifrons", 
        "uvall", "haagenti", "crocell", "furcas", "balam", "alloces", "caim", "murmur", 
        "orobas", "gremory", "ose", "amy", "orias", "vapula", "zagan", "volac", 
        "andras", "haures", "andrealphus", "kimaris", "amdusias", "belial", "decarabia", 
        "seere", "dantalion", "andromalius"
    ]
    
    return [(key, HIERARCHY_DB[key]) for key in goetia_order if key in HIERARCHY_DB]

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
   ├─ Semyaza - Leader (200 Watchers)
   ├─ Azazel - Forbidden Knowledge
   ├─ Kokabiel - Astrology
   ├─ Baraqiel - Lightning/Astrology
   ├─ Armaros - Enchantments
   ├─ Penemue - Writing
   ├─ Gadreel - Warfare
   ├─ Sariel - Moon
   ├─ Tamiel - Demon Conjuration
   └─ Yeqon - Seduction

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗡️ ARS GOETIA (72 Demons) - NOW COMPLETE!
   
   Kings (9): Bael, Paimon, Beleth, Purson,
             Asmoday, Vine, Balam, Zagan, Belial
   
   Dukes (26): Agares, Valefor, Barbatos, Gusion,
              Eligos, Zepar, Bathin, Sallos, Astaroth,
              and 17 more...
   
   Princes (11): Vassago, Sitri, Ipos, Gaap,
                Stolas, Orobas, Seere, and 4 more...
   
   Marquises (17): Samigina, Leraje, Naberius,
                   Ronove, Forneus, Marchosias,
                   Phenex, and 10 more...
   
   Counts/Presidents/Knights: 9 more spirits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌑 QLIPHOTH (Kabbalah Shadow Tree)
   ├─ Thaumiel - Duality (Satan & Moloch)
   ├─ Ghagiel - Hindrance (Beelzebub)
   ├─ Satariel - Concealment (Lucifuge)
   └─ Gamchicoth - Disruption (Astaroth)

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

📜 OTHER NOTABLE DEMONS
   ├─ Abaddon/Apollyon - Angel of the Abyss
   ├─ Moloch - Child Sacrifice
   ├─ Dagon - Philistine Sea God
   ├─ Baal - Storm God/False Worship
   ├─ Adramelech - Grand Chancellor
   ├─ Lucifuge Rofocale - Prime Minister
   ├─ Mephistopheles - Soul Pacts
   └─ Mastema - Chief of Evil Spirits

Use .hierarchy [name] for detailed info
Use .hierarchy random for random entity
Use .hierarchy search [keyword] to find entities
Use .hierarchy goetia for all 72 spirits
Use .hierarchy tradition [name] for tradition-specific
"""
    return chart