import time
import sys
import os
import pandas as pd

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from api_client import AlpacaAPIClient
from strategy import PullbackStrategy
from risk_manager import RiskManager
from order_executor import OrderExecutor
from logger import TradeLogger
from scanner import Scanner
from sentiment_analyzer import SentimentAnalyzer
from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit

def main():
    """
    Main function for the advanced trading agent.
    """
    print("--- Starting Advanced Trading Agent ---")

    # --- Configuration ---
    TIMEFRAME = TimeFrame(5, TimeFrameUnit.Minute)
    POLL_INTERVAL_SECONDS = 60 * 5
    
    STRATEGY_PARAMS = {
        'ema_fast_len': 20, 'ema_slow_len': 50, 'ema_trend_len': 200,
        'atr_len': 14, 'adx_len': 14, 'rsi_len': 14,
        'adx_threshold': 20, 'rsi_overbought': 60, 'rsi_oversold': 40,
        'sentiment_threshold': 0.2, # Require a moderately positive/negative sentiment
    }
    
    # Mapping from Alpaca symbol to Santiment slug
    SYMBOL_SLUG_MAP = {
        'BTC/USD': 'bitcoin',
        'ETH/USD': 'ethereum',
        'SOL/USD': 'solana',
        'XRP/USD': 'ripple',
        'DOGE/USD': 'dogecoin',
    }
    RISK_PARAMS = {
        'risk_per_trade': 0.05, 'max_trade_value': 500.0,
    }
    RR_RATIO = 3.0

    # --- Initialization ---
    client = AlpacaAPIClient()
    risk_manager = RiskManager(client, **RISK_PARAMS)
    executor = OrderExecutor(client)
    logger = TradeLogger()
    scanner = Scanner(client)
    sentiment_analyzer = SentimentAnalyzer()

    # --- Main Loop ---
    while True:
        try:
            print(f"\n--- New Cycle: {pd.Timestamp.now(tz='UTC')} ---")
            
            top_symbols = scanner.find_trending_coins()
            
            if not top_symbols:
                print("Scanner found no opportunities. Waiting for next cycle.")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if not risk_manager.can_open_new_trade():
                print("Portfolio risk limits reached. Waiting for next cycle.")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            for symbol in top_symbols:
                if not risk_manager.can_open_new_trade():
                    print("Portfolio risk limits reached during cycle. Stopping analysis.")
                    break

                position = client.get_position(symbol)
                if position:
                    print(f"Holding position in {symbol}. Skipping entry logic.")
                    continue
                
                print(f"Analyzing {symbol} for new entry...")
                end_date = pd.Timestamp.now(tz='UTC')
                start_date = end_date - pd.Timedelta(days=3) # Fetch 3 days for 5m TF
                data = client.get_crypto_bars([symbol], TIMEFRAME, start_date.isoformat(), end_date.isoformat())

                if data is None or data.empty:
                    print(f"Could not fetch data for {symbol}. Skipping.")
                    continue
                
                # Add slug to params for this specific symbol
                current_strategy_params = STRATEGY_PARAMS.copy()
                current_strategy_params['slug'] = SYMBOL_SLUG_MAP.get(symbol)

                strategy = PullbackStrategy(data[data['symbol'] == symbol], current_strategy_params, sentiment_analyzer)
                
                if strategy.df.empty:
                    print(f"Not enough data for {symbol} to calculate indicators. Skipping.")
                    continue

                signal = strategy.generate_signal()
                
                last_row = strategy.df.iloc[-1]
                print(
                    f"  Signal for {symbol}: {signal}\n"
                    f"    Close={last_row['close']:.2f}, EMA_F={last_row.get('ema_fast', 0):.2f}, "
                    f"EMA_S={last_row.get('ema_slow', 0):.2f}, ADX={last_row.get('adx', 0):.2f}, "
                    f"RSI={last_row.get('rsi', 0):.2f}"
                )

                if signal == 'BUY':
                    print(f"!!! {signal} SIGNAL DETECTED for {symbol} !!!")
                    last_atr = strategy.df['atr'].iloc[-1]
                    entry_price = strategy.df['close'].iloc[-1]
                    
                    stop_loss_price = entry_price - (1.5 * last_atr)
                    take_profit_price = entry_price + (RR_RATIO * (entry_price - stop_loss_price))
                    
                    quantity = risk_manager.calculate_position_size(entry_price, stop_loss_price)

                    if quantity > 0:
                        order = executor.place_order_with_sl(symbol, quantity, 'buy', f"{stop_loss_price:.2f}")
                        if order:
                            logger.log_trade(symbol, 'buy', quantity, entry_price, stop_loss_price, take_profit_price)
            
            print("\nCycle complete. Waiting for next scan.")
            time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n--- Shutting down Trading Agent ---")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == '__main__':
    main()
