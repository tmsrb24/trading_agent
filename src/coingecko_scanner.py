from pycoingecko import CoinGeckoAPI
from logger import logger

class CoinGeckoScanner:
    def __init__(self, client):
        self.client = client
        self.cg = CoinGeckoAPI()
        # Mapping from CoinGecko ID to Alpaca Symbol
        self.id_to_symbol_map = {
            'bitcoin': 'BTC/USD', 'ethereum': 'ETH/USD', 'solana': 'SOL/USD',
            'ripple': 'XRP/USD', 'dogecoin': 'DOGE/USD', 'aave': 'AAVE/USD',
            'uniswap': 'UNI/USD', 'chainlink': 'LINK/USD', 'cardano': 'ADA/USD',
            'litecoin': 'LTC/USD', 'bitcoin-cash': 'BCH/USD', 'stellar': 'XLM/USD',
            'shiba-inu': 'SHIB/USD', 'matic-network': 'MATIC/USD', 'avalanche-2': 'AVAX/USD',
            'tron': 'TRX/USD', 'polkadot': 'DOT/USD', 'sui': 'SUI/USD', 'zcash': 'ZEC/USD',
            'dash': 'DASH/USD', 'firo': 'FIRO/USD', 'monero': 'XMR/USD'
        }

    def scan(self):
        """
        Finds trending coins on CoinGecko and returns the Alpaca-tradable symbols.
        """
        logger.info("--- Starting CoinGecko Trending Scan ---")
        try:
            trending_data = self.cg.get_search_trending()
            
            if not trending_data or 'coins' not in trending_data:
                logger.warning("Could not fetch trending data from CoinGecko.")
                return []

            trending_ids = [coin['item']['id'] for coin in trending_data['coins']]
            
            # Map trending IDs to Alpaca symbols
            tradable_trending = []
            for cg_id in trending_ids:
                if cg_id in self.id_to_symbol_map:
                    tradable_trending.append(self.id_to_symbol_map[cg_id])
            
            logger.info(f"CoinGecko Trending Scan complete. Found: {', '.join(tradable_trending)}")
            return tradable_trending
        except Exception as e:
            logger.error(f"An error occurred during CoinGecko scan: {e}")
            return []
