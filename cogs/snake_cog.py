import discord
from discord.ext import commands
import random
import logging
import urllib.parse

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
            }
        ]

    @commands.command(name="snake")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def snake_command(self, ctx):
        """Draw a random snake from the compendium with a high-quality visualization."""
        snake = random.choice(self.snakes)
        
        # Generate image prompt
        prompt = f"Hi-quality realistic photography of a {snake['name']} ({snake['scientific']}) in its natural habitat, {snake['origin']}, dark cinematic lighting, extremely detailed scales and eyes, 8k resolution, National Geographic style."
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}"
        
        embed = discord.Embed(
            title=f"🐍 {snake['name']}",
            description=f"*{snake['scientific']}*",
            color=discord.Color.dark_green()
        )
        
        embed.set_image(url=image_url)
        embed.add_field(name="🌎 Origin", value=snake['origin'], inline=True)
        embed.add_field(name="⚠️ Danger", value=snake['danger'], inline=False)
        embed.add_field(name="✨ Traits", value=snake['traits'], inline=False)
        
        footer_text = "Drawn from the Great Serpent Compendium."
        embed.set_footer(text=footer_text)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SnakeCog(bot))
