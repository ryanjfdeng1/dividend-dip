# V1.6 universe: quality-first US large caps.
STOCKS = [
    "MSFT", "AAPL", "GOOGL", "GOOG", "META", "AVGO", "ORCL", "CSCO", "IBM", "ACN", "ADBE", "CRM", "QCOM", "TXN", "AMAT", "ADI", "INTU", "NOW", "INTC", "MU", "LRCX", "KLAC", "AMZN", "NFLX",
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SPGI", "MCO", "ICE", "CME", "AON", "MMC", "CB", "PGR", "ALL", "TRV",
    "UNH", "JNJ", "ABBV", "ABT", "MRK", "AMGN", "LLY", "BMY", "TMO", "DHR", "MDT", "SYK", "BSX", "ELV", "GILD", "CVS",
    "WMT", "COST", "HD", "LOW", "MCD", "SBUX", "NKE", "TGT", "PG", "KO", "PEP", "CL", "PM", "MO", "KMB", "GIS",
    "CAT", "DE", "HON", "GE", "RTX", "LMT", "ETN", "EMR", "MMM", "UPS", "UNP", "CSX", "WM", "ITW", "ADP",
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "LIN", "APD", "SHW", "NEM",
    "NEE", "DUK", "SO", "D", "AEP", "AMT", "PLD", "O",
    "DIS", "CMCSA", "V", "MA", "PYPL", "SYY", "FDX", "ORLY", "AZO",
]

# Companies whose cash-flow statements are not comparable to ordinary
# industrial/consumer companies for FCF scoring.
FINANCIALS = {"JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SPGI", "MCO", "ICE", "CME", "AON", "MMC", "CB", "PGR", "ALL", "TRV"}
BANKS = {"JPM", "BAC", "WFC", "C", "GS", "MS"}

LOOKBACK_DAYS = 100
LOOKBACK_60D = 60
LOOKBACK_20D = 20
SMA_LONG = 200
RSI_PERIOD = 14
WATCH_SCORE = 45
BUY_SCORE = 60
STRONG_BUY_SCORE = 75
MIN_DIP_FOR_CANDIDATE = -0.10
