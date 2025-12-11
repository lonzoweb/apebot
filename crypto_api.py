# --- crypto_api.py ---
import requests
import logging

logger = logging.getLogger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"


def fetch_crypto_prices(limit: int = 5) -> list:
    """
    Fetches the top N cryptocurrencies sorted by market cap in USD.
    This function is synchronous and should be run in an executor thread.
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
        response = requests.get(COINGECKO_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

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

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to fetch crypto prices from CoinGecko: {e}", exc_info=True
        )
        return []
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during crypto fetch: {e}", exc_info=True
        )
        return []
