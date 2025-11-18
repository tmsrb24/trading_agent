import pandas as pd
import sys
import os
import numpy as np

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from api_client import AlpacaAPIClient
from strategy import PullbackStrategy
from risk_manager import RiskManager
from sentiment_analyzer import SentimentAnalyzer
from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit

def run_backtest(symbol, start_date, end_date, strategy_params, risk_params, rr_ratio, initial_capital=10000.0):
    """
    Runs a backtest for the PullbackStrategy.
    """
    print(f"--- Starting Backtest for {symbol} from {start_date} to {end_date} ---")

    # 1. Fetch Data & Initialize Components
    client = AlpacaAPIClient()
    sentiment_analyzer = SentimentAnalyzer() # Needed for the strategy
    
    # The RiskManager needs an account object, we can simulate one for backtesting
    class SimulatedAccount:
        def __init__(self, equity):
            self.equity = equity

    client.account = SimulatedAccount(initial_capital) # Monkey-patch a simulated account
    risk_manager = RiskManager(client, **risk_params)

    bars = client.get_crypto_bars([symbol], TimeFrame.Day, start_date, end_date)
    if bars is None or bars.empty:
        print("Could not fetch data for backtest. Aborting.")
        return

    data = bars[bars['symbol'] == symbol]

    # Calculate average ATR for dynamic position sizing
    # We need to calculate ATR for the entire dataset first
    import src.indicators as ind
    data['atr'] = ind.calculate_atr(data['high'], data['low'], data['close'], length=strategy_params['atr_len'])
    average_atr = data['atr'].mean()
    print(f"Calculated Average ATR: {average_atr:.2f}")

    # --- Macro Market Filter (BTC 200-day EMA) ---
    # btc_end_date = data.index[-1]
    # btc_start_date = btc_end_date - pd.Timedelta(days=200 * 1.5) # Fetch enough data for 200-day EMA
    # btc_data = client.get_crypto_bars(['BTC/USD'], TimeFrame(1, TimeFrameUnit.Day), btc_start_date.isoformat(), btc_end_date.isoformat())

    # macro_trend_bullish = True
    # if btc_data is not None and not btc_data.empty:
    #     btc_close_prices = btc_data[btc_data['symbol'] == 'BTC/USD']['close']
    #     btc_ema_200 = ind.calculate_ema(btc_close_prices, length=200).iloc[-1]
    #     if btc_close_prices.iloc[-1] < btc_ema_200:
    #         macro_trend_bullish = False
    #         print(f"Macro Market Filter: BTC price (${btc_close_prices.iloc[-1]:.2f}) is below 200-day EMA (${btc_ema_200:.2f}). Skipping BUY signals.")

    # 2. Simulate Portfolio and Trades
    portfolio = pd.DataFrame(index=data.index)
    portfolio['cash'] = initial_capital
    portfolio['position_value'] = 0.0
    portfolio['total'] = initial_capital
    
    trades = []
    active_trade = None

    # 3. Main Backtest Loop
    for i in range(strategy_params['ema_trend_len'], len(data)): # Start after longest EMA period
        
        # --- Carry over values ---
        if i > 0:
            portfolio.loc[data.index[i], 'cash'] = portfolio.loc[data.index[i-1], 'cash']
            portfolio.loc[data.index[i], 'position_value'] = portfolio.loc[data.index[i-1], 'position_value']

        current_price = data['close'].iloc[i]
        
        # --- Update Active Trade ---
        if active_trade:
            active_trade['pnl'] = (current_price - active_trade['entry_price']) * active_trade['quantity']
            portfolio.loc[data.index[i], 'position_value'] = (current_price * active_trade['quantity'])

            # Check for Stop-Loss or Take-Profit
            if current_price <= active_trade['stop_loss'] or current_price >= active_trade['take_profit']:
                exit_price = active_trade['stop_loss'] if current_price <= active_trade['stop_loss'] else active_trade['take_profit']
                pnl = (exit_price - active_trade['entry_price']) * active_trade['quantity']
                
                portfolio.loc[data.index[i], 'cash'] += (active_trade['quantity'] * exit_price)
                portfolio.loc[data.index[i], 'position_value'] = 0
                
                active_trade['exit_price'] = exit_price
                active_trade['exit_date'] = data.index[i]
                active_trade['pnl'] = pnl
                trades.append(active_trade)
                
                print(f"{data.index[i].date()}: EXIT {symbol} at ${exit_price:.2f}, PnL: ${pnl:.2f}")
                active_trade = None

        # --- Check for New Entry Signal ---
        if not active_trade:
            # We need a rolling window of data to calculate indicators for each step
            rolling_data = data.iloc[:i+1]
            strategy = PullbackStrategy(rolling_data, strategy_params, sentiment_analyzer)
            
            if not strategy.df.empty:
                signal = strategy.generate_signal()
                
                # Apply macro market filter to BUY signals
                # if signal == 'BUY' and not macro_trend_bullish:
                #     print(f"Skipping BUY signal for {symbol} due to bearish macro trend.")
                #     continue

                if signal == 'BUY':
                    entry_price = current_price
                    last_atr = strategy.df['atr'].iloc[-1]
                    stop_loss_price = entry_price - (1.5 * last_atr)
                    take_profit_price = entry_price + (rr_ratio * (entry_price - stop_loss_price))
                    
                    # Update simulated account equity for risk manager
                    client.account.equity = portfolio['cash'].iloc[i-1] + portfolio['position_value'].iloc[i-1]
                    quantity = risk_manager.calculate_position_size(entry_price, stop_loss_price, current_atr=last_atr, average_atr=average_atr)

                    if quantity > 0 and portfolio['cash'].iloc[i] > (quantity * entry_price):
                        active_trade = {
                            'symbol': symbol,
                            'entry_date': data.index[i],
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'stop_loss': stop_loss_price,
                            'take_profit': take_profit_price,
                        }
                        portfolio.loc[data.index[i], 'cash'] -= (quantity * entry_price)
                        portfolio.loc[data.index[i], 'position_value'] = (quantity * entry_price)
                        print(f"{data.index[i].date()}: ENTRY {symbol} ({quantity:.4f}) at ${entry_price:.2f}")

        # Update total portfolio value
        portfolio.loc[data.index[i], 'total'] = portfolio['cash'].iloc[i] + portfolio['position_value'].iloc[i]

    # 4. Calculate Performance
    portfolio.dropna(inplace=True)
    final_value = portfolio['total'].iloc[-1]
    total_return = (final_value / initial_capital - 1) * 100
    
    trades_df = pd.DataFrame(trades)
    win_rate = 0
    avg_profit = 0
    avg_loss = 0
    if len(trades_df) > 0:
        win_rate = len(trades_df[trades_df['pnl'] > 0]) / len(trades_df)
        if len(trades_df[trades_df['pnl'] > 0]) > 0:
            avg_profit = trades_df[trades_df['pnl'] > 0]['pnl'].mean()
        if len(trades_df[trades_df['pnl'] <= 0]) > 0:
            avg_loss = trades_df[trades_df['pnl'] <= 0]['pnl'].mean()
    
    print("\n--- Backtest Results ---")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Average Profit: ${avg_profit:,.2f}")
    print(f"Average Loss: ${avg_loss:,.2f}")
    
    return portfolio, trades_df

if __name__ == '__main__':
    # Use the same parameters as in main.py for consistency
    strategy_params = {
        'ema_fast_len': 20, 'ema_slow_len': 50, 'ema_trend_len': 200,
        'atr_len': 14, 'adx_len': 14, 'rsi_len': 14,
        'adx_threshold': 25, # Let's test with a non-zero ADX threshold
        'rsi_overbought': 70, 
        'rsi_oversold': 30,
        'sentiment_threshold': 0.1,
        'slug': 'bitcoin', # Slug for sentiment analysis
        'use_sentiment': False # Disable sentiment for backtesting due to API limitations
    }
    risk_params = {
        'risk_per_trade': 0.05,
    }
    rr_ratio = 3.0

    run_backtest(
        symbol='BTC/USD',
        start_date='2022-01-01',
        end_date='2023-09-01',
        strategy_params=strategy_params,
        risk_params=risk_params,
        rr_ratio=rr_ratio
    )