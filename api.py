"""
External API functions for Discord Bot
Handles API calls to third-party services
"""

import aiohttp
import asyncio
import logging
import random
import os
import json
import urllib.parse
from config import SERPAPI_KEY, OPENCAGE_KEY, GOOGLE_API_KEY, GOOGLE_CREDENTIALS_PATH

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
# ============================================================
# POLLINATIONS.AI IMAGE MIRROR (FALLBACK)
# ============================================================

async def pollinations_generate_image(prompt: str):
    """
    Generate an image based on a prompt using Pollinations.ai.
    Uses a robust retry loop and model failover for reliability.
    """
    import aiohttp
    
    encoded_prompt = urllib.parse.quote(prompt)
    models = ["flux", "turbo"] 
    max_retries = 3
    
    session = bot_session
    created_session = False
    if session is None:
        session = aiohttp.ClientSession()
        created_session = True

    try:
        for model in models:
            for attempt in range(max_retries):
                seed = random.randint(1, 999999)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&model={model}&nologo=true"
                try:
                    async with session.get(image_url, timeout=120) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            if image_bytes and len(image_bytes) > 2000:
                                return image_bytes, None
                except Exception:
                    pass
                await asyncio.sleep(1)
        return None, "All manifestation mirrors are dark."
    finally:
        if created_session:
            await session.close()


# ============================================================
# GOOGLE IMAGEN (AI STUDIO / GEMINI API)
# ============================================================

async def google_generate_image(prompt: str):
    """
    Generate an image using Google's Imagen 3 model.
    Pivots between Vertex AI (Service Account) or AI Studio (API Key).
    """
    if not GOOGLE_API_KEY and not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        return None, "Google credentials (JSON or API Key) are missing."

    try:
        from google import genai
        from google.genai import types
        from google.oauth2 import service_account
        
        # DEBUG: Check exactly where we are looking
        logger.info(f"Checking for credentials at: {GOOGLE_CREDENTIALS_PATH}")
        file_exists = os.path.exists(GOOGLE_CREDENTIALS_PATH)
        logger.info(f"Credentials file exists: {file_exists}")

        if file_exists:
            # Explicit Service Account loading for Vertex AI
            with open(GOOGLE_CREDENTIALS_PATH, 'r') as f:
                creds_info = json.load(f)
                project_id = creds_info.get('project_id')
            
            logger.info(f"Manifesting via Vertex AI (Project: {project_id})")
            
            creds = service_account.Credentials.from_service_account_info(creds_info)
            client = genai.Client(
                vertexai=True,
                project=project_id,
                credentials=creds,
                location='us-central1'
            )
            model_name = 'imagen-3.0-generate-001'
        else:
            # Fallback to AI Studio Mode
            logger.warning("No Service Account found. Falling back to AI Studio (API Key).")
            client = genai.Client(api_key=GOOGLE_API_KEY)
            model_name = 'imagen-3.0-generate-002'
            
        def generate():
            response = client.models.generate_images(
                model=model_name,
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
        if "401" in err_msg:
            return None, "Google Auth Error (401). Ensure Vertex AI API is enabled in project."
        if "403" in err_msg:
            return None, "Google Permission Error (403). Check Service Account roles."
        return None, f"Google Error: {err_msg[:100]}"
