import pandas as pd
import numpy as np
import indicators as ind

class BaseStrategy:
    """
    Base class for all trading strategies.
    """
    def generate_signal(self):
        raise NotImplementedError("Should implement generate_signal()")

class PullbackStrategy(BaseStrategy):
    """
    Intraday trend-following strategy on pullbacks to a moving average, with sentiment filter.
    """
    def __init__(self, data, params, sentiment_analyzer):
        self.params = params
        self.sentiment_analyzer = sentiment_analyzer
        self._calculate_indicators(data)

    def _calculate_indicators(self, data):
        """Calculates and attaches all required indicators to the DataFrame."""
        self.df = data.copy()
        self.df['ema_fast'] = ind.calculate_ema(self.df['close'], length=self.params['ema_fast_len'])
        self.df['ema_slow'] = ind.calculate_ema(self.df['close'], length=self.params['ema_slow_len'])
        self.df['ema_trend'] = ind.calculate_ema(self.df['close'], length=self.params['ema_trend_len'])
        self.df['atr'] = ind.calculate_atr(self.df['high'], self.df['low'], self.df['close'], length=self.params['atr_len'])
        self.df['adx'], _, _ = ind.calculate_adx(self.df['high'], self.df['low'], self.df['close'], length=self.params['adx_len'])
        self.df['rsi'] = ind.calculate_rsi(self.df['close'], length=self.params['rsi_len'])
        
        # Drop rows with NaN values created by indicators
        self.df.dropna(inplace=True)

    def generate_signal(self):
        """
        Generates a single trade signal ('BUY', 'SELL', or 'HOLD') based on the last two candles.
        """
        if len(self.df) < 2:
            return 'HOLD'

        last_candle = self.df.iloc[-1]
        prev_candle = self.df.iloc[-2]

        # --- LONG SIGNAL ---
        # 1. Trend Filters
        # --- LONG SIGNAL ---
        # 1. Trend Filters (Loosened as per analysis)
        long_trend_ok = (last_candle['close'] > last_candle['ema_trend']) and \
                        (last_candle['ema_fast'] > last_candle['ema_slow'])
        
        trend_strength_ok = last_candle['adx'] > self.params['adx_threshold']
        
        # 2. Entry Trigger (Pullback & Confirmation)
        pullback_entry_ok = (prev_candle['low'] <= prev_candle['ema_fast']) and \
                            (last_candle['close'] > last_candle['ema_fast'])
        
        rsi_ok_long = last_candle['rsi'] < self.params['rsi_overbought']

        if long_trend_ok and trend_strength_ok and pullback_entry_ok and rsi_ok_long:
            # --- Final Sentiment Check ---
            symbol_slug = self.params.get('slug')
            if symbol_slug:
                sentiment = self.sentiment_analyzer.get_sentiment_score(symbol_slug)
                print(f"  Sentiment score for {symbol_slug}: {sentiment:.2f}")
                if sentiment >= self.params['sentiment_threshold']:
                    return 'BUY'
            else: # If no slug, trade without sentiment
                return 'BUY'

        # --- SHORT SIGNAL ---
        # 1. Trend Filters (Loosened)
        short_trend_ok = (last_candle['close'] < last_candle['ema_trend']) and \
                         (last_candle['ema_fast'] < last_candle['ema_slow'])

        # 2. Entry Trigger (Pullback & Confirmation)
        pullback_entry_ok_short = (prev_candle['high'] >= prev_candle['ema_fast']) and \
                                  (last_candle['close'] < last_candle['ema_fast'])
        
        rsi_ok_short = last_candle['rsi'] > self.params['rsi_oversold']

        if short_trend_ok and trend_strength_ok and pullback_entry_ok_short and rsi_ok_short:
            # --- Final Sentiment Check ---
            symbol_slug = self.params.get('slug')
            if symbol_slug:
                sentiment = self.sentiment_analyzer.get_sentiment_score(symbol_slug)
                print(f"  Sentiment score for {symbol_slug}: {sentiment:.2f}")
                if sentiment <= -self.params['sentiment_threshold']:
                    return 'SELL'
            else: # If no slug, trade without sentiment
                return 'SELL'

        return 'HOLD'

if __name__ == '__main__':
    # Example Usage and Testing
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.api_client import AlpacaAPIClient
    from alpaca_trade_api.rest import TimeFrame

    # --- Parameters ---
    strategy_params = {
        'ema_fast_len': 20,
        'ema_slow_len': 50,
        'ema_trend_len': 200,
        'atr_len': 14,
        'adx_len': 14,
        'rsi_len': 14,
        'adx_threshold': 25,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
    }

    client = AlpacaAPIClient()
    bars = client.get_crypto_bars(['BTC/USD'], TimeFrame.Hour, "2023-01-01", "2023-06-01")

    if bars is not None:
        btc_bars = bars[bars['symbol'] == 'BTC/USD']
        
        strategy = PullbackStrategy(btc_bars, strategy_params)
        signal = strategy.generate_signal()

        print("--- Pullback Strategy Test ---")
        print(f"Data has {len(strategy.df)} candles after indicator calculation.")
        print("\nLast 5 candles with indicators:")
        print(strategy.df.tail())
        print(f"\nFinal Signal: {signal}")


class AlwaysBuyStrategy(BaseStrategy):
    """A dummy strategy that always returns a BUY signal for testing."""
    def __init__(self, data, params=None):
        # This strategy doesn't need data or params, but keeps the interface consistent.
        pass
    
    def generate_signal(self):
        return 'BUY'
