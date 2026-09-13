STOCKS = [
    "KO", "PG", "PEP", "MCD", "WMT",
    "JNJ", "ABBV", "ABT", "MRK", "AMGN",
    "XOM", "CVX", "COP",
    "JPM", "MS", "C", "BLK",
    "CAT", "EMR", "UPS", "ADP",
    "IBM", "CSCO", "AVGO",
    "VZ", "T", "HD", "UNH", "O", "MO",
]

# Alpha Vantage free daily endpoint returns a compact recent window.
# V1.2 therefore uses the 100-trading-day high as the temporary dip reference.
LOOKBACK_DAYS = 100
LOOKBACK_60D = 60
LOOKBACK_20D = 20
SMA_LONG = 200
RSI_PERIOD = 14

WATCH_DRAWDOWN = 0.10
BUY_DRAWDOWN = 0.15
STRONG_BUY_DRAWDOWN = 0.20
