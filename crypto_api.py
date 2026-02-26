import aiohttp
import logging

logger = logging.getLogger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"


async def fetch_crypto_prices(session: aiohttp.ClientSession, limit: int = 5) -> list:
    """
    Fetches the top N cryptocurrencies sorted by market cap in USD using aiohttp.
    """
    headers = {
        "User-Agent": "ApeBot/1.0 (Discord Bot; contact: your_email@example.com)",
        "accept": "application/json"
    }

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }

    try:
        async with session.get(COINGECKO_API_URL, params=params, headers=headers, timeout=10) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"CoinGecko API error: {response.status} - {error_text}")
                return []
            
            data = await response.json()

            results = []
            for coin in data:
                results.append(
                    {
                        "name": coin.get("name", "N/A"),
                        "symbol": coin.get("symbol", "N/A").upper(),
                        "price": coin.get("current_price"),
                        "change_24h": coin.get("price_change_percentage_24h_in_currency"),
                    }
                )
            return results

    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error from CoinGecko: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during crypto fetch: {e}", exc_info=True)
        return []
