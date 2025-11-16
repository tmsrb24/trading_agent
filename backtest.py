import pandas as pd
import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from api_client import AlpacaAPIClient
from strategy import SmaCrossoverStrategy
from risk_manager import RiskManager
from alpaca_trade_api.rest import TimeFrame

def run_backtest(symbol, start_date, end_date, sma_short, sma_long, initial_capital=100000.0, risk_per_trade=0.02):
    """
    Runs a more accurate backtest for the SMA Crossover strategy.
    """
    print("--- Starting Backtest ---")
    
    # 1. Fetch Data & Initialize Components
    client = AlpacaAPIClient()
    risk_manager = RiskManager(client, risk_per_trade=risk_per_trade)
    bars = client.get_crypto_bars([symbol], TimeFrame.Day, start_date, end_date)
    if bars is None or bars.empty:
        print("Could not fetch data for backtest. Aborting.")
        return

    data = bars[bars['symbol'] == symbol]

    # 2. Generate Signals
    strategy = SmaCrossoverStrategy(symbol, data, sma_short, sma_long)
    signals = strategy.generate_signals()

    # 3. Simulate Portfolio
    portfolio = pd.DataFrame(index=signals.index)
    portfolio['quantity'] = 0.0  # Quantity of the asset held
    portfolio['cash'] = initial_capital
    portfolio['total'] = initial_capital
    portfolio['positions'] = signals['positions']

    for i in range(1, len(portfolio)):
        price = data['close'].iloc[i]
        
        # Carry over values from the previous day
        portfolio.loc[portfolio.index[i], 'quantity'] = portfolio.loc[portfolio.index[i-1], 'quantity']
        portfolio.loc[portfolio.index[i], 'cash'] = portfolio.loc[portfolio.index[i-1], 'cash']

        # Buy signal
        if portfolio['positions'].iloc[i] == 2.0:
            # Use RiskManager to calculate position size
            quantity_to_buy = risk_manager.calculate_position_size(symbol, price)
            cost = quantity_to_buy * price

            if portfolio['cash'].iloc[i-1] > cost: # Check if we have enough cash
                portfolio.loc[portfolio.index[i], 'quantity'] += quantity_to_buy
                portfolio.loc[portfolio.index[i], 'cash'] -= cost
                print(f"{portfolio.index[i].date()}: BUY {quantity_to_buy:.4f} {symbol} at ${price:,.2f}")

        # Sell signal
        elif portfolio['positions'].iloc[i] == -2.0:
            if portfolio['quantity'].iloc[i-1] > 0: # Check if we have assets to sell
                quantity_to_sell = portfolio['quantity'].iloc[i-1]
                cash_received = quantity_to_sell * price
                portfolio.loc[portfolio.index[i], 'cash'] += cash_received
                portfolio.loc[portfolio.index[i], 'quantity'] = 0.0
                print(f"{portfolio.index[i].date()}: SELL {quantity_to_sell:.4f} {symbol} at ${price:,.2f}")
            
        # Update total portfolio value based on current price
        current_holdings_value = portfolio['quantity'].iloc[i] * price
        portfolio.loc[portfolio.index[i], 'total'] = portfolio['cash'].iloc[i] + current_holdings_value

    # 4. Calculate Performance
    final_value = portfolio['total'].iloc[-1]
    total_return = (final_value / initial_capital - 1) * 100
    
    print("\n--- Backtest Results ---")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Total Return: {total_return:.2f}%")
    
    return portfolio

if __name__ == '__main__':
    run_backtest(
        symbol='BTC/USD',
        start_date='2021-01-01',
        end_date='2023-01-01',
        sma_short=20,
        sma_long=50
    )
