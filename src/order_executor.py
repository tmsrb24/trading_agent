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

    def get_open_stop_loss_order_id(self, symbol):
        """
        Finds the ID of the open stop-loss order for a given symbol.
        """
        try:
            open_orders = self.api.list_orders(status='open', symbols=[symbol])
            for order in open_orders:
                if order.type == 'stop':
                    return order.id
            return None
        except Exception as e:
            print(f"Error getting open stop-loss order for {symbol}: {e}")
            return None

    def replace_stop_loss(self, order_id, new_stop_price):
        """
        Replaces an existing stop-loss order with a new stop price.
        """
        try:
            self.api.replace_order(
                order_id=order_id,
                stop_price=new_stop_price
            )
            print(f"SUCCESS: Replaced stop-loss for order {order_id} to {new_stop_price}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to replace stop-loss for order {order_id}: {e}")
            return False

    def place_order_with_sl(self, symbol, qty, side, stop_loss_price):
        """
        Places a market order with an attached stop-loss.
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

    def close_position(self, symbol):
        """Closes the entire open position for the given symbol."""
        print(f"\n--- Closing Position for {symbol} ---")
        try:
            # Alpaca API requires symbol without '/' for closing positions by symbol
            symbol_for_api = symbol.replace('/', '')
            closed_order = self.api.close_position(symbol_for_api)
            print(f"SUCCESS: Position close order submitted. Order ID: {closed_order.id}")
            return closed_order
        except Exception as e:
            print(f"ERROR: Failed to close position for {symbol}: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancels a specific order by its ID."""
        print(f"\n--- Cancelling Order {order_id} ---")
        try:
            self.api.cancel_order(order_id)
            print(f"SUCCESS: Order {order_id} cancelled.")
            return True
        except Exception as e:
            print(f"ERROR: Failed to cancel order {order_id}: {e}")
            return False

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
