import pandas as pd
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.enums import AssetClass
from logger import logger

class TechnicalScanner:
    def __init__(self, client, volume_threshold_usd=1_000, top_n=25):
        """
        Initializes the Scanner.
        :param client: The AlpacaAPIClient instance.
        :param volume_threshold_usd: Minimum 24h trading volume in USD to consider a coin.
        :param top_n: Number of top coins by volume to return.
        """
        self.client = client
        self.volume_threshold_usd = volume_threshold_usd
        self.top_n = top_n

    def scan(self):
        """
        Scans for cryptocurrencies with high trading volume on Alpaca.
        1. Fetches all tradable crypto assets.
        2. Fetches their latest 24h volume data.
        3. Filters out coins below the volume threshold.
        4. Sorts by volume and returns the top N symbols.
        """
        logger.info("--- Starting High Volume Scan ---")
        try:
            # 1. Get all tradable crypto assets from Alpaca
            assets = self.client.api.list_assets(status='active', asset_class=AssetClass.CRYPTO)
            tradable_assets = [a for a in assets if a.tradable and a.symbol.endswith('USD')]
            
            if not tradable_assets:
                logger.warning("Could not find any tradable crypto assets.")
                return []

            symbols = [a.symbol for a in tradable_assets]
            logger.info(f"Found {len(symbols)} tradable crypto assets. Fetching volume data...")

            # 2. Fetch latest daily bar to check volume
            end_date = pd.Timestamp.now(tz='UTC')
            start_date = end_date - pd.Timedelta(days=2)
            
            # Correctly format dates to YYYY-MM-DD string format
            bars = self.client.get_crypto_bars(
                symbols,
                TimeFrame(1, TimeFrameUnit.Day),
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if bars is None or bars.empty:
                logger.error("Could not fetch any bar data for volume scan.")
                return []

            # 3. Calculate 24h volume in USD and filter
            latest_bars = bars.groupby('symbol').last()
            latest_bars['volume_usd'] = latest_bars['close'] * latest_bars['volume']
            
            high_volume_bars = latest_bars[latest_bars['volume_usd'] >= self.volume_threshold_usd]
            
            if high_volume_bars.empty:
                logger.info(f"No coins met the ${self.volume_threshold_usd:,.0f} volume threshold.")
                return []

            # 4. Sort by volume and return top N
            sorted_bars = high_volume_bars.sort_values(by='volume_usd', ascending=False)
            top_symbols = list(sorted_bars.head(self.top_n).index)
            
            logger.info(f"Scan complete. Top {len(top_symbols)} coins by volume: {', '.join(top_symbols)}")
            return top_symbols

        except Exception as e:
            logger.error(f"An error occurred during the volume scan: {e}")
            return []
