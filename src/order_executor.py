class OrderExecutor:
    """
    Handles the execution of trades via the Alpaca API.
    """
    def __init__(self, api_client):
        """
        Initializes the Order Executor.
        
        :param api_client: An instance of the AlpacaAPIClient.
        """
        self.api_client = api_client
        self.api = api_client.api

    def place_order_with_sl(self, symbol, qty, side, stop_loss_price):
        """
        Places a market order with an attached stop-loss.
        NOTE: Alpaca does not support bracket orders for crypto. This is the next best thing.
        
        :param symbol: The symbol to trade.
        :param qty: The quantity to trade.
        :param side: 'buy' or 'sell'.
        :param stop_loss_price: The stop price for the stop-loss order.
        :return: The order object if successful, None otherwise.
        """
        print("\n--- Placing Order with Stop-Loss ---")
        print(f"  Symbol: {symbol}")
        print(f"  Quantity: {qty}")
        print(f"  Side: {side}")
        print(f"  Stop Loss: {stop_loss_price}")
        
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc',
                stop_loss={
                    'stop_price': stop_loss_price
                }
            )
            print(f"SUCCESS: Order with SL placed. Order ID: {order.id}")
            return order
        except Exception as e:
            print(f"ERROR: Failed to place order: {e}")
            return None

if __name__ == '__main__':
    # Example Usage and Testing
    # WARNING: This will place a REAL order on your paper trading account.
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.api_client import AlpacaAPIClient

    print("--- Order Executor Test ---")
    client = AlpacaAPIClient()
    executor = OrderExecutor(client)

    # Example: Place a small market buy order for BTC/USD
    # We use a very small quantity for testing purposes.
    test_symbol = 'BTC/USD'
    test_qty = 0.0001 
    
    print(f"This script will attempt to place a {test_qty} {test_symbol} BUY order.")
    # Uncomment the lines below to run a test order with SL
    # sl_price = 24900
    # executor.place_order_with_sl(test_symbol, test_qty, 'buy', sl_price)
