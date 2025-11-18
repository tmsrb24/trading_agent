import pandas as pd
import src.indicators as ind

class ScalpingStrategy:
    def __init__(self, data, params):
        self.df = data.copy()
        self.params = params
        self._calculate_indicators()

    def _calculate_indicators(self):
        """Calculates and adds all necessary indicators to the DataFrame."""
        try:
            # Moving Averages
            self.df['ema_fast'] = ind.calculate_ema(self.df['close'], length=self.params['ema_fast_len'])
            self.df['ema_slow'] = ind.calculate_ema(self.df['close'], length=self.params['ema_slow_len'])

            # Stochastic Oscillator
            self.df['stoch_k'], self.df['stoch_d'] = ind.calculate_stoch(
                self.df['high'], self.df['low'], self.df['close'],
                k=self.params['stoch_k'],
                d=self.params['stoch_d'],
                smooth_k=self.params['stoch_smooth_k']
            )
            
            # ATR for stop-loss calculation
            self.df['atr'] = ind.calculate_atr(
                self.df['high'], self.df['low'], self.df['close'], 
                length=self.params['atr_len']
            )

            self.df.dropna(inplace=True)
        except Exception as e:
            print(f"Error calculating indicators for scalping strategy: {e}")
            self.df = pd.DataFrame() # Clear dataframe on error

    def generate_signal(self, position=None):
        """
        Generates aggressive scalping signals.
        - Entry: Buys dips in an uptrend, sells rallies in a downtrend.
        - Exit: Exits when the trend reverses (EMA crossover).
        """
        if len(self.df) < 2:
            return 'HOLD'

        latest = self.df.iloc[-1]
        second_latest = self.df.iloc[-2]

        # --- Trend & Crossover Conditions ---
        is_uptrend = latest['ema_fast'] > latest['ema_slow']
        is_downtrend = latest['ema_fast'] < latest['ema_slow']
        bearish_crossover = (second_latest['ema_fast'] > second_latest['ema_slow'] and 
                             latest['ema_fast'] < latest['ema_slow'])
        bullish_crossover = (second_latest['ema_fast'] < second_latest['ema_slow'] and 
                             latest['ema_fast'] > latest['ema_slow'])

        # --- Logic for Open Positions (Exit on Trend Reversal) ---
        if position:
            if position.side == 'long' and bearish_crossover:
                return 'EXIT_LONG'
            if position.side == 'short' and bullish_crossover:
                return 'EXIT_SHORT'
            return 'HOLD_POSITION'

        # --- Logic for No Position (Aggressive Entry) ---
        else:
            # BUY signal: Trend is up and stochastic is oversold (a dip)
            is_oversold = latest['stoch_k'] < self.params['stoch_oversold']
            if is_uptrend and is_oversold:
                return 'BUY'
            
            # SELL signal: Trend is down and stochastic is overbought (a rally)
            is_overbought = latest['stoch_k'] > self.params['stoch_overbought']
            if is_downtrend and is_overbought:
                return 'SELL'

        return 'HOLD'
