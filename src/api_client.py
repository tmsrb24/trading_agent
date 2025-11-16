import os
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv

class AlpacaAPIClient:
    """
    A client for interacting with the Alpaca API.
    Handles authentication and provides methods for API calls.
    """
    def __init__(self):
        """
        Initializes the API client and authenticates with Alpaca.
        """
        # Load environment variables from .env file in the parent directory
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path=dotenv_path)

        self.api_key = os.getenv('API_KEY')
        self.secret_key = os.getenv('SECRET_KEY')
        self.base_url = "https://paper-api.alpaca.markets"

        if not self.api_key or not self.secret_key:
            raise ValueError("API_KEY and SECRET_KEY must be set in the .env file.")

        self.api = tradeapi.REST(self.api_key, self.secret_key, self.base_url, api_version='v2')

    def get_account_info(self):
        """
        Retrieves and returns account information.
        """
        try:
            account = self.api.get_account()
            print("Successfully connected to Alpaca.")
            print(f"Account Number: {account.account_number}")
            print(f"Portfolio Value: {account.portfolio_value}")
            print(f"Buying Power: {account.buying_power}")
            return account
        except Exception as e:
            print(f"Failed to connect to Alpaca: {e}")
            return None

    def get_crypto_bars(self, symbols, timeframe, start, end):
        """
        Fetches historical crypto data for the given symbols.
        
        :param symbols: A list of symbols to fetch data for (e.g., ['BTC/USD'])
        :param timeframe: The timeframe for the bars (e.g., TimeFrame.Day)
        :param start: Start date in ISO format (e.g., '2022-01-01')
        :param end: End date in ISO format (e.g., '2023-01-01')
        :return: A pandas DataFrame with the bar data.
        """
        try:
            from alpaca_trade_api.rest import TimeFrame
            
            bar_data = self.api.get_crypto_bars(symbols, timeframe, start, end).df
            print(f"Successfully fetched {len(bar_data)} bars for {symbols}")
            return bar_data
        except Exception as e:
            print(f"Failed to fetch crypto bars: {e}")
            return None

    def get_position(self, symbol):
        """
        Retrieves the current open position for a given symbol.
        Returns the position object if it exists, otherwise None.
        """
        try:
            position = self.api.get_position(symbol)
            return position
        except Exception as e:
            # The API throws an error if there is no open position.
            return None

    def get_tradable_crypto_assets(self):
        """
        Fetches a list of all tradable crypto assets.
        """
        try:
            assets = self.api.list_assets(status='active', asset_class='crypto')
            tradable_assets = [a for a in assets if a.tradable]
            print(f"Found {len(tradable_assets)} tradable crypto assets.")
            return tradable_assets
        except Exception as e:
            print(f"Failed to get tradable assets: {e}")
            return []

if __name__ == '__main__':
    # Example usage:
    # This block will run when the script is executed directly.
    # It's useful for testing the connection and data fetching.
    client = AlpacaAPIClient()
    account = client.get_account_info()

    if account:
        # Test fetching tradable assets
        assets = client.get_tradable_crypto_assets()
        if assets:
            print(f"Sample of tradable assets:")
            for asset in assets[:5]:
                print(f"  - {asset.symbol}")
