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
# V1.3 scores the quality of a dip using multiple price/RSI signals.
LOOKBACK_DAYS = 100
LOOKBACK_60D = 60
LOOKBACK_20D = 20
SMA_LONG = 200
RSI_PERIOD = 14

# V1.3 scoring tiers. Lower (more negative) drawdown and lower RSI
# indicate a deeper/possibly oversold dip.
DD100_LEVELS = [(-0.10, 10), (-0.15, 15), (-0.20, 20)]
DD60_LEVELS = [(-0.05, 5), (-0.10, 10), (-0.15, 15)]
DD20_LEVELS = [(-0.05, 5), (-0.10, 10)]
RSI_LEVELS = [(40, 10), (35, 15), (30, 20)]

# Long-term trend confirmation.
TREND_BONUS = 10
TREND_PENALTY = -10

WATCH_SCORE = 25
BUY_SCORE = 40
STRONG_BUY_SCORE = 55
