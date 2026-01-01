import aiohttp
import logging

logger = logging.getLogger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"


async def fetch_crypto_prices(session: aiohttp.ClientSession, limit: int = 5) -> list:
    """
    Fetches the top N cryptocurrencies sorted by market cap in USD using aiohttp.
    """
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h",
    }

    try:
        async with session.get(COINGECKO_API_URL, params=params, timeout=10) as response:
            response.raise_for_status()
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
