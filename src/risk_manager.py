import pandas as pd
from datetime import datetime, timedelta
from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit

class RiskManager:
    """
    Manages risk for the trading agent, including position sizing.
    """
    def __init__(self, api_client, config):
        """
        Initializes the Risk Manager using a config object.
        """
        self.api_client = api_client
        self.config = config
        self.account = self.api_client.get_account_info()

        # Parse values from the config object
        self.risk_per_trade = self.config.getfloat('risk', 'risk_per_trade', fallback=0.01)
        self.max_trade_value = self.config.getfloat('main', 'max_trade_value', fallback=500.0)
        self.max_open_trades = self.config.getint('risk', 'max_open_trades', fallback=3)
        self.daily_loss_limit_pct = self.config.getfloat('risk', 'daily_loss_limit_pct', fallback=0.03)
        self.consecutive_loss_limit = self.config.getint('risk', 'consecutive_loss_limit', fallback=3)

        # State tracking
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_reset_date = pd.Timestamp.now(tz='UTC').date()

    def reset_daily_stats_if_needed(self):
        """
        Resets daily PnL and loss counters if a new day has started.
        """
        today = pd.Timestamp.now(tz='UTC').date()
        if today > self.last_reset_date:
            print("--- New Day --- Resetting daily risk stats.")
            self.daily_pnl = 0.0
            self.consecutive_losses = 0 # Or maybe not reset this one daily? For now, we do.
            self.last_reset_date = today

    def can_open_new_trade(self):
        """
        Checks if all portfolio-level risk rules allow opening a new trade.
        """
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
        """
        Records the PnL of a closed trade and updates loss counters.
        """
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def check_correlation(self, symbol, open_positions_symbols, correlation_threshold=0.7):
        """
        Checks if the given symbol is highly correlated with any existing open positions.
        
        :param symbol: The symbol to check for correlation.
        :param open_positions_symbols: A list of symbols of currently open positions.
        :param correlation_threshold: The correlation threshold above which a trade is disallowed.
        :return: True if no high correlation is found, False otherwise.
        """
        if not open_positions_symbols:
            return True # No open positions to check against

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30) # Look back 30 days for correlation
            timeframe = TimeFrame(1, TimeFrameUnit.Day)

            all_symbols = [symbol] + open_positions_symbols
            all_data = self.api_client.get_crypto_bars(all_symbols, timeframe, start_date.isoformat(), end_date.isoformat())

            if all_data is None or all_data.empty:
                print("Could not fetch data for correlation check. Skipping correlation.")
                return True # Fail safe, allow trade

            # Pivot data to have symbols as columns and close prices as values
            close_prices = all_data.pivot_table(index='timestamp', columns='symbol', values='close')
            
            if symbol not in close_prices.columns:
                print(f"Data for {symbol} not found for correlation check. Skipping correlation.")
                return True

            for open_symbol in open_positions_symbols:
                if open_symbol not in close_prices.columns:
                    print(f"Data for open position {open_symbol} not found for correlation check. Skipping correlation for this pair.")
                    continue

                correlation = close_prices[symbol].corr(close_prices[open_symbol])
                if pd.isna(correlation):
                    print(f"Could not calculate correlation between {symbol} and {open_symbol}. Skipping correlation for this pair.")
                    continue

                if abs(correlation) >= correlation_threshold:
                    print(f"RISK CHECK FAILED: {symbol} is highly correlated ({correlation:.2f}) with open position {open_symbol}.")
                    return False
            
            return True
        except Exception as e:
            print(f"Error during correlation check: {e}")
            return True # Fail safe, allow trade

    def calculate_position_size(self, entry_price, stop_loss_price, current_atr=None, average_atr=None):
        """
        Calculates position size based on SL distance and max risk.
        
        :param entry_price: The price at which the trade will be entered.
        :param stop_loss_price: The price at which the stop-loss will be set.
        :param current_atr: The current Average True Range.
        :param average_atr: The average ATR over a longer period.
        :return: The quantity (float) to trade. Returns 0 if invalid.
        """
        if self.account is None or entry_price <= 0 or stop_loss_price <= 0:
            return 0

        try:
            equity = float(self.account.equity)
            
            # Determine dynamic risk_per_trade if ATRs are provided
            effective_risk_per_trade = self.risk_per_trade
            if current_atr is not None and average_atr is not None and average_atr > 0:
                # If current volatility is higher, reduce risk_per_trade
                # If current volatility is lower, increase risk_per_trade
                volatility_ratio = current_atr / average_atr
                # Inverse relationship: higher volatility_ratio -> lower effective_risk_per_trade
                effective_risk_per_trade = self.risk_per_trade / volatility_ratio
                
                # Clamp effective_risk_per_trade to reasonable bounds
                effective_risk_per_trade = max(0.01, min(0.10, effective_risk_per_trade))

            # 1. Determine max cash to risk based on % of equity
            cash_to_risk = equity * effective_risk_per_trade
            
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
            print(f"  Effective Risk per Trade: {effective_risk_per_trade * 100:.2f}%")
            print(f"  Cash to Risk ({effective_risk_per_trade * 100:.2f}%): ${cash_to_risk:,.2f}")
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
        risk_manager = RiskManager(client, risk_per_trade=0.05, max_trade_value=500.0) # Using $500 as per user request
        
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

        # --- Simulation 3: Dynamic risk with higher volatility ---
        print("\n--- Simulation 3: Dynamic Risk (Higher Volatility) ---")
        entry = 25000
        sl = 24500
        current_atr = 1000 # Higher volatility
        average_atr = 500
        risk_manager.calculate_position_size(entry, sl, current_atr, average_atr)

        # --- Simulation 4: Dynamic risk with lower volatility ---
        print("\n--- Simulation 4: Dynamic Risk (Lower Volatility) ---")
        entry = 25000
        sl = 24500
        current_atr = 250 # Lower volatility
        average_atr = 500
        risk_manager.calculate_position_size(entry, sl, current_atr, average_atr)
