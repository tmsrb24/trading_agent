import pandas as pd
import numpy as np

def calculate_ema(series, length):
    """Calculates the Exponential Moving Average (EMA)."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_atr(high, low, close, length):
    """Calculates the Average True Range (ATR)."""
    tr = pd.DataFrame({
        'h-l': high - low,
        'h-pc': abs(high - close.shift()),
        'l-pc': abs(low - close.shift())
    }).max(axis=1)
    atr = tr.ewm(span=length, adjust=False).mean()
    return atr

def calculate_adx(high, low, close, length):
    """
    Calculates the Average Directional Index (ADX).
    Simplified implementation for core ADX value.
    """
    # Calculate True Range (TR)
    tr = pd.DataFrame({
        'h-l': high - low,
        'h-pc': abs(high - close.shift()),
        'l-pc': abs(low - close.shift())
    }).max(axis=1)
    atr = tr.ewm(span=length, adjust=False).mean()

    # Calculate Directional Movement (DM)
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    # Handle cases where -DM > +DM
    plus_dm[plus_dm > minus_dm] = plus_dm
    minus_dm[minus_dm > plus_dm] = minus_dm

    plus_di = (plus_dm.ewm(span=length, adjust=False).mean() / atr) * 100
    minus_di = (minus_dm.ewm(span=length, adjust=False).mean() / atr) * 100

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    adx = dx.ewm(span=length, adjust=False).mean()
    return adx

def calculate_rsi(series, length):
    """Calculates the Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(span=length, adjust=False).mean()
    avg_loss = loss.ewm(span=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_stoch(high, low, close, k, d, smooth_k):
    """
    Calculates the Stochastic Oscillator (%K and %D).
    """
    lowest_low = low.rolling(window=k).min()
    highest_high = high.rolling(window=k).max()

    percent_k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    percent_d = percent_k.rolling(window=d).mean()
    
    # Smooth %K with smooth_k (often 3)
    percent_k_smoothed = percent_k.ewm(span=smooth_k, adjust=False).mean()

    return percent_k_smoothed, percent_d
