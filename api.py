"""
External API functions for Discord Bot
Handles API calls to third-party services
"""

import aiohttp
import asyncio
import logging
import random
from config import SERPAPI_KEY, OPENCAGE_KEY, GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Global reference to bot session (will be set from main.py)
bot_session = None


def set_bot_session(session):
    """Set the persistent aiohttp session"""
    global bot_session
    bot_session = session


# ============================================================
# GOOGLE LENS API (via SerpApi)
# ============================================================


async def google_lens_fetch_results(image_url: str, limit: int = 3):
    """Fetch reverse image search results from Google Lens via SerpApi"""
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY environment variable not set")

    search_url = "https://serpapi.com/search.json"
    params = {"engine": "google_lens", "url": image_url, "api_key": SERPAPI_KEY}

    session = bot_session
    if session is None:
        import aiohttp

        session = aiohttp.ClientSession()
        should_close = True
    else:
        should_close = False

    try:
        async with session.get(search_url, params=params, timeout=30) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(
                    f"SerpApi returned HTTP {resp.status}: {error_text[:200]}"
                )
            data = await resp.json()
    except asyncio.TimeoutError:
        raise RuntimeError("Request to SerpApi timed out")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Network error: {e}")
    finally:
        if should_close and session:
            await session.close()

    results = []
    visual_matches = data.get("visual_matches", [])

    for match in visual_matches[:limit]:
        results.append(
            {
                "title": match.get("title", "Untitled"),
                "link": match.get("link", ""),
                "thumbnail": match.get("thumbnail", ""),
                "source": match.get("source", "Unknown source"),
            }
        )

    search_metadata = data.get("search_metadata", {})
    search_page = search_metadata.get("google_lens_url", "")

    return {"results": results, "search_page": search_page}


async def lookup_location(query):
    """Lookup timezone and city from location query using OpenCage API"""
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": query, "key": OPENCAGE_KEY}

    session = bot_session
    if session is None:
        import aiohttp

        session = aiohttp.ClientSession()
        should_close = True
    else:
        should_close = False

    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                logger.error(f"OpenCage API returned {resp.status}")
                return None, None
            data = await resp.json()
    except asyncio.TimeoutError:
        logger.error("OpenCage API timeout")
        return None, None
    except Exception as e:
        logger.error(f"OpenCage API error: {e}")
        return None, None
    finally:
        if should_close and session:
            await session.close()

    if data.get("results"):
        first = data["results"][0]
        timezone_name = first["annotations"]["timezone"]["name"]
        components = first["components"]
        city = (
            components.get("city")
            or components.get("town")
            or components.get("village")
            or components.get("state")
            or query
        )
        return timezone_name, city
    return None, None


# ============================================================
# OPENCAGE GEOCODING API
# ============================================================


async def lookup_location(query):
    """Lookup timezone and city from location query using OpenCage API"""
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": query, "key": OPENCAGE_KEY}

    try:
        async with bot_session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                logger.error(f"OpenCage API returned {resp.status}")
                return None, None
            data = await resp.json()
    except asyncio.TimeoutError:
        logger.error("OpenCage API timeout")
        return None, None
    except Exception as e:
        logger.error(f"OpenCage API error: {e}")
        return None, None

    if data.get("results"):
        first = data["results"][0]
        timezone_name = first["annotations"]["timezone"]["name"]
        components = first["components"]
        city = (
            components.get("city")
            or components.get("town")
            or components.get("village")
            or components.get("state")
            or query
        )
        return timezone_name, city
    return None, None


# ============================================================
# URBAN DICTIONARY API
# ============================================================


async def urban_dictionary_lookup(term):
    """Look up a term on Urban Dictionary"""
    url = "https://api.urbandictionary.com/v0/define"

    # Safety check - if bot_session is None, create a temporary one
    session = bot_session
    if session is None:
        import aiohttp

        session = aiohttp.ClientSession()
        should_close = True
    else:
        should_close = False

    try:
        async with session.get(url, params={"term": term}, timeout=15) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data
    except asyncio.TimeoutError:
        logger.error("Urban Dictionary API timeout")
        return None
    except Exception as e:
        logger.error(f"Urban Dictionary API error: {e}")
        return None
    finally:
        if should_close and session:
            await session.close()

# ============================================================
# POLLINATIONS.AI IMAGE GENERATION
# ============================================================

import urllib.parse

async def pollinations_generate_image(prompt: str):
    """
    Generate an image based on a prompt using Pollinations.ai.
    Fetches raw bytes to ensure reliability in Discord.
    """
    import aiohttp
    
    # URL Sanitization
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 999999)
    
    # gen.pollinations.ai is the newer direct endpoint
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    
    session = bot_session
    created_session = False
    if session is None:
        session = aiohttp.ClientSession()
        created_session = True

    try:
        async with session.get(image_url, timeout=60) as resp:
            if resp.status != 200:
                logger.error(f"Pollinations error {resp.status}")
                return None, f"Mirror error: {resp.status}"
            
            image_bytes = await resp.read()
            if not image_bytes or len(image_bytes) < 1000:
                return None, "Received invalid image data."
                
            return image_bytes, None
    except Exception as e:
        logger.error(f"Pollinations fetch failed: {e}")
        return None, f"Connection failed: {str(e)[:50]}"
    finally:
        if created_session:
            await session.close()


# ============================================================
# GOOGLE IMAGEN (AI STUDIO / GEMINI API)
# ============================================================

async def google_generate_image(prompt: str):
    """
    Generate an image using Google's Imagen 3 model via AI Studio.
    Returns (image_bytes, error_message).
    """
    if not GOOGLE_API_KEY:
        return None, "GOOGLE_API_KEY is missing from environment."

    try:
        from google import genai
        from google.genai import types
        
        # Initialize client with API KEY (AI Studio mode)
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        def generate():
            # Use the AI Studio / Gemini API endpoint model
            response = client.models.generate_images(
                model='imagen-3.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    include_rai_reason=True,
                    output_mime_type='image/png'
                )
            )
            if not response.generated_images:
                return None
            return response.generated_images[0].image_bytes

        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(None, generate)
        if not image_bytes:
            return None, "Google returned no image data."
        return image_bytes, None

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error in google_generate_image: {err_msg}", exc_info=True)
        return None, f"API Error: {err_msg[:100]}"
