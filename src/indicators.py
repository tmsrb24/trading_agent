import pandas as pd
import numpy as np

def calculate_ema(series, length):
    """Calculates the Exponential Moving Average (EMA)."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_atr(high, low, close, length=14):
    """Calculates the Average True Range (ATR)."""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    tr = pd.DataFrame({'h_l': high_low, 'h_c': high_close, 'l_c': low_close}).max(axis=1)
    return calculate_ema(tr, length)

def calculate_rsi(series, length=14):
    """Calculates the Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_adx(high, low, close, length=14):
    """Calculates the Average Directional Index (ADX)."""
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.DataFrame({'h_l': high - low, 'h_c': np.abs(high - close.shift()), 'l_c': np.abs(low - close.shift())}).max(axis=1)
    atr = calculate_ema(tr, length)
    
    plus_di = 100 * (calculate_ema(plus_dm, length) / atr)
    minus_di = 100 * (np.abs(calculate_ema(minus_dm, length)) / atr)
    
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = calculate_ema(dx, length)
    
    return adx, plus_di, minus_di

if __name__ == '__main__':
    # Simple test with dummy data
    data = {
        'open': [10, 11, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10],
        'high': [11, 12, 13, 12, 11, 12, 13, 14, 15, 16, 15, 14, 13, 12, 11],
        'low': [9, 10, 11, 10, 9, 10, 11, 12, 13, 14, 13, 12, 11, 10, 9],
        'close': [11, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9],
        'volume': [100]*15
    }
    df = pd.DataFrame(data)

    print("--- Testing Indicators ---")
    df['ema_10'] = calculate_ema(df['close'], length=10)
    df['atr_14'] = calculate_atr(df['high'], df['low'], df['close'], length=14)
    df['rsi_14'] = calculate_rsi(df['close'], length=14)
    df['adx_14'], _, _ = calculate_adx(df['high'], df['low'], df['close'], length=14)

    print(df[['close', 'ema_10', 'atr_14', 'rsi_14', 'adx_14']].tail())
