import os
import san
from dotenv import load_dotenv
from datetime import datetime, timedelta

class SentimentAnalyzer:
    def __init__(self):
        """Initializes the sentiment analyzer and sets the Santiment API key."""
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=dotenv_path)
        
        api_key = os.getenv('SANTIMENT_API_KEY')
        if not api_key or api_key == "YOUR_SANTIMENT_API_KEY":
            print("WARNING: SANTIMENT_API_KEY is not set. Sentiment analysis will be skipped.")
            self.enabled = False
        else:
            san.ApiConfig.api_key = api_key
            self.enabled = True

    def get_sentiment_score(self, symbol_slug):
        """
        Fetches the weighted sentiment score from Santiment.
        The score typically ranges from -3 (very bearish) to 3 (very bullish).
        We will normalize it to a -1 to 1 range.
        
        :param symbol_slug: The slug for the crypto asset (e.g., 'bitcoin', 'ethereum').
        :return: A normalized sentiment score from -1.0 to 1.0, or 0 if unavailable.
        """
        if not self.enabled:
            return 0 # Return neutral if disabled

        try:
            # Workaround for Santiment FREE plan data lag.
            # Fetch the latest available data instead of "now".
            to_date = datetime.now() - timedelta(days=30)
            from_date = to_date - timedelta(days=2)

            data = san.get(
                f"sentiment_balance_total/{symbol_slug}",
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d'),
                interval="1d"
            )
            if not data.empty:
                # Get the latest score and normalize it (assuming a typical range of -3 to 3)
                latest_score = data['value'].iloc[-1]
                normalized_score = latest_score / 3.0 
                return max(-1.0, min(1.0, normalized_score)) # Clamp between -1 and 1
            return 0
        except Exception as e:
            print(f"Could not fetch sentiment for {symbol_slug}: {e}")
            return 0 # Return neutral on error

if __name__ == '__main__':
    # Example Usage:
    # Make sure to set your SANTIMENT_API_KEY in the .env file
    analyzer = SentimentAnalyzer()
    if analyzer.enabled:
        btc_slug = "bitcoin"
        eth_slug = "ethereum"
        
        print(f"Fetching sentiment for {btc_slug}...")
        btc_score = analyzer.get_sentiment_score(btc_slug)
        print(f"  -> Normalized Score: {btc_score:.2f}")

        print(f"Fetching sentiment for {eth_slug}...")
        eth_score = analyzer.get_sentiment_score(eth_slug)
        print(f"  -> Normalized Score: {eth_score:.2f}")
