# V1.6 universe: quality-first US large caps.
# This is a curated research universe, not a claim that every constituent is
# currently "high quality". The scanner decides quality from fundamentals.
STOCKS = [
    # Technology / communication
    "MSFT", "AAPL", "GOOGL", "GOOG", "META", "AVGO", "ORCL", "CSCO",
    "IBM", "ACN", "ADBE", "CRM", "QCOM", "TXN", "AMAT", "ADI", "INTU",
    "NOW", "INTC", "MU", "LRCX", "KLAC", "AMZN", "NFLX",

    # Financials
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SPGI", "MCO",
    "ICE", "CME", "AON", "MMC", "CB", "PGR", "ALL", "TRV",

    # Healthcare
    "UNH", "JNJ", "ABBV", "ABT", "MRK", "AMGN", "LLY", "BMY",
    "TMO", "DHR", "MDT", "SYK", "BSX", "ELV", "GILD", "CVS",

    # Consumer
    "WMT", "COST", "HD", "LOW", "MCD", "SBUX", "NKE", "TGT",
    "PG", "KO", "PEP", "CL", "PM", "MO", "KMB", "GIS",

    # Industrials
    "CAT", "DE", "HON", "GE", "RTX", "LMT", "ETN", "EMR", "MMM",
    "UPS", "UNP", "CSX", "WM", "ITW", "ADP",

    # Energy / materials
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO",
    "LIN", "APD", "SHW", "NEM",

    # Utilities / REITs
    "NEE", "DUK", "SO", "D", "AEP", "AMT", "PLD", "O",

    # Additional established companies
    "DIS", "CMCSA", "V", "MA", "PYPL", "SYY", "FDX", "ORLY", "AZO",
]

LOOKBACK_DAYS = 100
LOOKBACK_60D = 60
LOOKBACK_20D = 20
SMA_LONG = 200
RSI_PERIOD = 14

# V1.6 score thresholds
WATCH_SCORE = 45
BUY_SCORE = 60
STRONG_BUY_SCORE = 75
MIN_DIP_FOR_CANDIDATE = -0.10
