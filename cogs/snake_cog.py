import discord
from discord.ext import commands
import random
import logging
import io
import asyncio
from api import pollinations_generate_image

logger = logging.getLogger(__name__)

class SnakeCog(commands.Cog):
    """Snake Compendium - A collection of the world's most exotic and dangerous snakes."""
    
    def __init__(self, bot):
        self.bot = bot
        self.snakes = [
            {
                "name": "King Cobra",
                "scientific": "Ophiophagus hannah",
                "origin": "Southeast Asia & India",
                "danger": "Maximum. The world's longest venomous snake. Can deliver enough neurotoxin to kill an elephant in one bite.",
                "traits": "Highly intelligent, hooded neck, bird-eating habits."
            },
            {
                "name": "Inland Taipan",
                "scientific": "Oxyuranus microlepidotus",
                "origin": "Central East Australia",
                "danger": "Lethal. Often cited as the most venomous snake on Earth. One bite contains enough toxin to kill 100 men.",
                "traits": "Shy but strike-ready, color-changing scales, swift-moving."
            },
            {
                "name": "Black Mamba",
                "scientific": "Dendroaspis polylepis",
                "origin": "Sub-Saharan Africa",
                "danger": "Severe. Fast, aggressive, and highly venomous. Known as the 'Shadow of Death'.",
                "traits": "Ink-black mouth, incredible speed (up to 12mph), coffin-shaped head."
            },
            {
                "name": "Gaboon Viper",
                "scientific": "Bitis gabonica",
                "origin": "Rainforests of Africa",
                "danger": "High. Possesses the longest fangs (up to 2 inches) and highest venom yield of any snake.",
                "traits": "Deep-leaf camouflage, heavy-bodied, massive triangular head."
            },
            {
                "name": "Blue Insularis",
                "scientific": "Trimeresurus insularis",
                "origin": "Lesser Sunda Islands, Indonesia",
                "danger": "Moderate. A rare, striking blue variant of the White-lipped Pit Viper.",
                "traits": "Neon blue color, prehensile tail, arboreal hunter."
            },
            {
                "name": "Emerald Tree Boa",
                "scientific": "Corallus caninus",
                "origin": "Amazon Basin",
                "danger": "Non-venomous (Constrictor). Known for massive teeth and powerful coils.",
                "traits": "Vibrant green with white lightning bolts, nocturnal, lightning-fast strike."
            },
            {
                "name": "King Brown Snake",
                "scientific": "Pseudechis australis",
                "origin": "Australia",
                "danger": "Extreme. Heavy-duty venom and large body. Not actually a brown snake, but a member of the black snake family.",
                "traits": "Aggressive, wide distribution, eats other snakes."
            },
            {
                "name": "Dragon-Headed Pit Viper",
                "scientific": "Protobothrops mangshanensis",
                "origin": "Mt. Mang, China",
                "danger": "High. A rare, ancient-looking giant known as the 'Mangshan Pit Viper'.",
                "traits": "Mossy camouflage, massive size (up to 2m), dragon-like facial features."
            },
            {
                "name": "Bushmaster",
                "scientific": "Lachesis muta",  
                "origin": "Central and South America",
                "danger": "High. The longest pit viper in the world. Shy but extremely dangerous if disturbed.",
                "traits": "Egg-laying, rough scales, lives in primary rainforests."
            },
            {
                "name": "Sea Krait",
                "scientific": "Laticauda colubrina",
                "origin": "Indo-Pacific Waters",
                "danger": "Lethal. More venomous than cobras but generally non-aggressive to humans.",
                "traits": "Banded blue/black, amphibious, lethal neurotoxicity."
            },
             {
                "name": "Malayan Pit Viper",
                "scientific": "Calloselasma rhodostoma",
                "origin": "Southeast Asia",
                "danger": "High. Responsible for more bites than almost any other snake in its range.",
                "traits": "Triangular patterns, sedentary, heat-sensing pits."
            },
             {
                "name": "Reticulated Python",
                "scientific": "Malayopython reticulatus",
                "origin": "Southeast Asia",
                "danger": "Maximum (Constrictor). The world's longest snake. Large individuals are known to eat humans.",
                "traits": "Geometric patterns, aquatic proficiency, massive muscular force."
            },
            {
                "name": "Saw-scaled Viper",
                "scientific": "Echis carinatus",
                "origin": "Middle East & Central Asia",
                "danger": "High. Small but incredibly aggressive. Responsible for more human deaths than any other snake species.",
                "traits": "Sizzling sound from scale-rubbing, lightning-fast strike, highly potent hemotoxin."
            },
            {
                "name": "Boomslang",
                "scientific": "Dispholidus typus",
                "origin": "Sub-Saharan Africa",
                "danger": "Severe. A rear-fanged snake with hemotoxic venom that causes internal bleeding from every orifice.",
                "traits": "Large emerald eyes, incredible camouflage, shy tree-dweller."
            },
            {
                "name": "Eastern Brown Snake",
                "scientific": "Pseudonaja textilis",
                "origin": "Australia",
                "danger": "Lethal. Responsible for the most snakebite deaths in Australia. Known for its speed and aggression.",
                "traits": "Slim body, highly variable color, 'S' shaped defensive posture."
            },
            {
                "name": "Russell's Viper",
                "scientific": "Daboia russelii",
                "origin": "Asia",
                "danger": "Maximum. One of the 'Big Four' venomous snakes in India. Extremely irritable and loud-hissing.",
                "traits": "Chain-like patterns, powerful strike, highly destructive venom."
            },
            {
                "name": "Fer-de-lance",
                "scientific": "Bothrops asper",
                "origin": "Central & South America",
                "danger": "Severe. Highly irritable and fast. Known as the 'Ultimate Pit Viper'.",
                "traits": "Triangular head, defensive 'tail vibrating', large size."
            },
            {
                "name": "Common Krait",
                "scientific": "Bungarus caeruleus",
                "origin": "Indian Subcontinent",
                "danger": "Lethal. Nocturnal hunter with a bite that is often painless, yet deadly within hours.",
                "traits": "Polished black scales with white bands, docile by day, aggressive by night."
            },
            {
                "name": "Tiger Snake",
                "scientific": "Notechis scutatus",
                "origin": "Australia",
                "danger": "Extreme. Highly venomous with a potent mix of neurotoxins, hemolysins, and coagulants.",
                "traits": "Dark bands like a tiger, flattened neck when threatened, semi-aquatic."
            },
            {
                "name": "Mozambique Spitting Cobra",
                "scientific": "Naja mossambica",
                "origin": "Eastern & Southern Africa",
                "danger": "High. Can accurately spit venom into eyes from up to 8 feet away.",
                "traits": "Salmon-colored throat, highly nervous, unique defensive spitting."
            },
            {
                "name": "Eastern Coral Snake",
                "scientific": "Micrurus fulvius",
                "origin": "Southeastern United States",
                "danger": "Severe. Possesses one of the most potent neurotoxins in the Americas.",
                "traits": "Vibrant red, yellow, and black rings, shy and reclusive, stays underground."
            },
            {
                "name": "Death Adder",
                "scientific": "Acanthophis antarcticus",
                "origin": "Australia & New Guinea",
                "danger": "Lethal. Master of ambush. Possesses the fastest strike of any snake in the world.",
                "traits": "Short body, leaf-litter camouflage, lures prey with a worm-like tail tip."
            },
            {
                "name": "Sidewinder",
                "scientific": "Crotalus cerastes",
                "origin": "Southwestern US & Mexico",
                "danger": "Moderate. A specialized desert rattlesnake with a unique locomotion.",
                "traits": "Horn-like scales above eyes, J-shaped scent trails, rapid desert movement."
            },
            {
                "name": "Rhinoceros Viper",
                "scientific": "Bitis nasicornis",
                "origin": "Central African Rainforests",
                "danger": "High. A massive, slow-moving heavy-hitter with incredible patterns.",
                "traits": "Horns on snout, stunning geometric colors, loud 'hissing' like a bellows."
            },
            {
                "name": "Cape Cobra",
                "scientific": "Naja nivea",
                "origin": "Southern Africa",
                "danger": "Extreme. Considered the most dangerous cobra in Africa due to its potent neurotoxic venom.",
                "traits": "Yellow to copper scales, diurnal hunter, highly aggressive defensive hood."
            }
        ]

    @commands.command(name="snake")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def snake_command(self, ctx):
        """Draw a random snake from the compendium with a high-quality visualization."""
        snake = random.choice(self.snakes)
        
        # 2. Get Image Bytes via API
        prompt = f"Hi-quality realistic photography of a {snake['name']} ({snake['scientific']}) in its natural habitat, {snake['origin']}, dark cinematic lighting, extremely detailed scales and eyes, 8k resolution, National Geographic style."
        
        try:
            image_bytes, error_msg = await pollinations_generate_image(prompt)
            
            if not image_bytes:
                return

            # 3. Prepare File & Embed
            file = discord.File(io.BytesIO(image_bytes), filename="snake.png")
            embed = discord.Embed(
                title=f"🐍 {snake['name']}",
                description=f"*{snake['scientific']}*",
                color=discord.Color.dark_green()
            )
            
            embed.set_image(url="attachment://snake.png")
            embed.add_field(name="🌎 Origin", value=snake['origin'], inline=True)
            embed.add_field(name="⚠️ Danger", value=snake['danger'], inline=False)
            embed.add_field(name="✨ Traits", value=snake['traits'], inline=False)
            
            footer_text = "Snake"
            embed.set_footer(text=footer_text)
            
            # 4. Final delivery
            await ctx.send(embed=embed, file=file)

        except Exception as e:
            logger.error(f"Error in .snake command: {e}", exc_info=True)
            return

async def setup(bot):
    await bot.add_cog(SnakeCog(bot))
