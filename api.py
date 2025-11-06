"""
External API functions for Discord Bot
Handles API calls to third-party services
"""

import aiohttp
import asyncio
import logging
from config import SERPAPI_KEY, OPENCAGE_KEY

logger = logging.getLogger(__name__)

# ============================================================
# GOOGLE LENS API (via SerpApi)
# ============================================================

async def google_lens_fetch_results(image_url: str, limit: int = 3):
    """Fetch reverse image search results from Google Lens via SerpApi"""
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY environment variable not set")

    search_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": SERPAPI_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"SerpApi returned HTTP {resp.status}: {error_text[:200]}")
                data = await resp.json()
    except asyncio.TimeoutError:
        raise RuntimeError("Request to SerpApi timed out")
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Network error: {e}")

    results = []
    visual_matches = data.get("visual_matches", [])
    
    for match in visual_matches[:limit]:
        results.append({
            "title": match.get("title", "Untitled"),
            "link": match.get("link", ""),
            "thumbnail": match.get("thumbnail", ""),
            "source": match.get("source", "Unknown source")
        })

    search_metadata = data.get("search_metadata", {})
    search_page = search_metadata.get("google_lens_url", "")

    return {
        "results": results,
        "search_page": search_page
    }

# ============================================================
# OPENCAGE GEOCODING API
# ============================================================

async def lookup_location(query):
    """Lookup timezone and city from location query using OpenCage API"""
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"q": query, "key": OPENCAGE_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
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
        
    if data.get("results"):
        first = data["results"][0]
        timezone_name = first["annotations"]["timezone"]["name"]
        components = first["components"]
        city = (components.get("city") or components.get("town") or 
                components.get("village") or components.get("state") or query)
        return timezone_name, city
    return None, None

# ============================================================
# URBAN DICTIONARY API
# ============================================================

async def urban_dictionary_lookup(term):
    """Look up a term on Urban Dictionary"""
    url = "https://api.urbandictionary.com/v0/define"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"term": term}, timeout=10) as resp:
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
