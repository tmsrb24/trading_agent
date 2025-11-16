import pandas as pd
from pycoingecko import CoinGeckoAPI

class Scanner:
    """
    Scans the market for trending coins using the CoinGecko API.
    """
    def __init__(self, api_client):
        self.api_client = api_client
        self.coingecko = CoinGeckoAPI()

    def find_trending_coins(self):
        """
        Finds trending coins from CoinGecko and filters them against tradable assets in Alpaca.
        
        :return: A list of tradable symbols (e.g., ['BTC/USD', 'ETH/USD']).
        """
        print("\n--- Scanning Market for Trending Coins (via CoinGecko) ---")
        try:
            # 1. Get trending coins from CoinGecko
            trending_data = self.coingecko.get_search_trending()
            if not trending_data or 'coins' not in trending_data:
                print("Could not fetch trending data from CoinGecko.")
                return self._fallback()

            # Extract symbols (e.g., 'BTC', 'ETH')
            trending_symbols = [coin['item']['symbol'].upper() for coin in trending_data['coins']]
            print(f"CoinGecko trending: {trending_symbols}")

            # 2. Get tradable assets from Alpaca
            tradable_assets = self.api_client.get_tradable_crypto_assets()
            if not tradable_assets:
                return self._fallback()
            
            tradable_symbols_base = {asset.symbol.split('/')[0] for asset in tradable_assets}

            # 3. Find the intersection
            final_candidates = []
            for symbol in trending_symbols:
                if symbol in tradable_symbols_base:
                    # Assume we are trading against USD
                    final_candidates.append(f"{symbol}/USD")
            
            if not final_candidates:
                print("No overlap between CoinGecko trending and Alpaca tradable assets.")
                return self._fallback()

            print(f"Found {len(final_candidates)} tradable trending coins: {final_candidates}")
            return final_candidates

        except Exception as e:
            print(f"An error occurred during scanning: {e}")
            return self._fallback()

    def _fallback(self):
        """Returns a default list of major coins if scanning fails."""
        print("Falling back to default symbol list.")
        return ['BTC/USD', 'ETH/USD']

if __name__ == '__main__':
    # Example Usage and Testing
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from api_client import AlpacaAPIClient

    client = AlpacaAPIClient()
    scanner = Scanner(client)
    top_coins = scanner.find_trending_coins()
    
    print("\nScanner returned:", top_coins)
