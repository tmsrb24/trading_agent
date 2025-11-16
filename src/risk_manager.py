import pandas as pd

class RiskManager:
    """
    Manages risk for the trading agent, including position sizing.
    """
    def __init__(self, api_client, risk_per_trade=0.02, max_trade_value=5000.0):
        """
        Initializes the Risk Manager.
        
        :param api_client: An instance of the AlpacaAPIClient.
        :param risk_per_trade: The fraction of the portfolio to risk on a single trade (e.g., 0.02 for 2%).
        :param max_trade_value: The maximum value in USD for a single trade.
        """
        self.api_client = api_client
        self.risk_per_trade = risk_per_trade
        self.max_trade_value = max_trade_value
        self.account = self.api_client.get_account_info()

        # Portfolio-level risk settings
        self.max_open_trades = 3
        self.daily_loss_limit_pct = 0.03 # 3% of equity
        self.consecutive_loss_limit = 3

        # State tracking
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_reset_date = pd.Timestamp.now(tz='UTC').date()

    def reset_daily_stats_if_needed(self):
        """Resets daily PnL and loss counters if a new day has started."""
        today = pd.Timestamp.now(tz='UTC').date()
        if today > self.last_reset_date:
            print("--- New Day --- Resetting daily risk stats.")
            self.daily_pnl = 0.0
            self.consecutive_losses = 0 # Or maybe not reset this one daily? For now, we do.
            self.last_reset_date = today

    def can_open_new_trade(self):
        """Checks if all portfolio-level risk rules allow opening a new trade."""
        self.reset_daily_stats_if_needed()
        
        try:
            open_positions = self.api_client.api.list_positions()
            if len(open_positions) >= self.max_open_trades:
                print(f"RISK CHECK FAILED: Max open trades ({self.max_open_trades}) limit reached.")
                return False
        except Exception as e:
            print(f"Could not get open positions to check risk: {e}")
            return False # Fail safe
        
        if self.consecutive_losses >= self.consecutive_loss_limit:
            print("RISK CHECK FAILED: Consecutive loss limit reached for the day.")
            return False

        if self.account:
            equity = float(self.account.equity)
            daily_loss_limit_usd = equity * self.daily_loss_limit_pct
            if self.daily_pnl <= -daily_loss_limit_usd:
                print("RISK CHECK FAILED: Daily loss limit reached.")
                return False
        
        return True

    def record_trade_close(self, pnl):
        """Records the PnL of a closed trade and updates loss counters."""
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        Calculates position size based on SL distance and max risk.
        
        :param entry_price: The price at which the trade will be entered.
        :param stop_loss_price: The price at which the stop-loss will be set.
        :return: The quantity (float) to trade. Returns 0 if invalid.
        """
        if self.account is None or entry_price <= 0 or stop_loss_price <= 0:
            return 0

        try:
            equity = float(self.account.equity)
            
            # 1. Determine max cash to risk based on % of equity
            cash_to_risk = equity * self.risk_per_trade
            
            # 2. Calculate SL distance per unit of the asset
            sl_distance_per_unit = abs(entry_price - stop_loss_price)
            if sl_distance_per_unit == 0:
                return 0

            # 3. Calculate quantity based on risk and SL distance
            quantity = cash_to_risk / sl_distance_per_unit
            
            # 4. Check against the hard cap for position value (e.g., $5000)
            position_value = quantity * entry_price
            if position_value > self.max_trade_value:
                quantity = self.max_trade_value / entry_price
                position_value = self.max_trade_value

            print(f"Risk Manager Calculation:")
            print(f"  Portfolio Equity: ${equity:,.2f}")
            print(f"  Cash to Risk ({self.risk_per_trade * 100}%): ${cash_to_risk:,.2f}")
            print(f"  Entry Price: ${entry_price:,.2f}")
            print(f"  Stop-Loss Price: ${stop_loss_price:,.2f}")
            print(f"  SL Distance: ${sl_distance_per_unit:,.2f}")
            print(f"  Calculated Quantity (before cap): {cash_to_risk / sl_distance_per_unit:.6f}")
            print(f"  Max Position Value: ${self.max_trade_value:,.2f}")
            print(f"  Final Quantity (after cap): {quantity:.6f}")
            print(f"  Final Position Value: ${position_value:,.2f}")
            
            return quantity
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return 0

if __name__ == '__main__':
    # Example Usage and Testing
    import sys
    import os
    # Add the parent directory to the Python path to find the 'api_client' module
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.api_client import AlpacaAPIClient

    # This test assumes you have a valid API connection
    client = AlpacaAPIClient()
    
    if client.get_account_info():
        # Test with a max trade value of $5000 and 1% risk
        risk_manager = RiskManager(client, risk_per_trade=0.01, max_trade_value=500.0) # Using $500 as per user request
        
        # --- Simulation 1: Normal trade ---
        print("\n--- Simulation 1: Normal Trade ---")
        entry = 25000
        sl = 24500 # $500 SL distance
        risk_manager.calculate_position_size(entry, sl)

        # --- Simulation 2: Trade that hits the $500 cap ---
        print("\n--- Simulation 2: Trade Capped by Value ---")
        entry = 25000
        sl = 24950 # Very tight $50 SL distance
        risk_manager.calculate_position_size(entry, sl)
