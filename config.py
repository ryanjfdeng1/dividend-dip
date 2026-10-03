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

FINANCIALS = {"JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SPGI", "MCO", "ICE", "CME", "AON", "MMC", "CB", "PGR", "ALL", "TRV"}
BANKS = {"JPM", "BAC", "WFC", "C", "GS", "MS"}

LOOKBACK_DAYS = 100
LOOKBACK_60D = 60
LOOKBACK_20D = 20
LOOKBACK_252D = 252
SMA_LONG = 200
RSI_PERIOD = 14
WATCH_SCORE = 45
BUY_SCORE = 60
STRONG_BUY_SCORE = 75
MIN_DIP_FOR_CANDIDATE = -0.10

# Reporting taxonomy for the fixed US large-cap universe.
# Sector follows broad GICS-style sectors; industry is a practical screening
# label. Kept local so the scanner does not need 117 extra API calls.
SECTOR_MAP = {
    "MSFT": "Information Technology", "AAPL": "Information Technology",
    "GOOGL": "Communication Services", "GOOG": "Communication Services",
    "META": "Communication Services", "AVGO": "Information Technology",
    "ORCL": "Information Technology", "CSCO": "Information Technology",
    "IBM": "Information Technology", "ACN": "Information Technology",
    "ADBE": "Information Technology", "CRM": "Information Technology",
    "QCOM": "Information Technology", "TXN": "Information Technology",
    "AMAT": "Information Technology", "ADI": "Information Technology",
    "INTU": "Information Technology", "NOW": "Information Technology",
    "INTC": "Information Technology", "MU": "Information Technology",
    "LRCX": "Information Technology", "KLAC": "Information Technology",
    "AMZN": "Consumer Discretionary", "NFLX": "Communication Services",
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials",
    "C": "Financials", "GS": "Financials", "MS": "Financials",
    "BLK": "Financials", "SPGI": "Financials", "MCO": "Financials",
    "ICE": "Financials", "CME": "Financials", "AON": "Financials",
    "MMC": "Financials", "CB": "Financials", "PGR": "Financials",
    "ALL": "Financials", "TRV": "Financials",
    "UNH": "Health Care", "JNJ": "Health Care", "ABBV": "Health Care",
    "ABT": "Health Care", "MRK": "Health Care", "AMGN": "Health Care",
    "LLY": "Health Care", "BMY": "Health Care", "TMO": "Health Care",
    "DHR": "Health Care", "MDT": "Health Care", "SYK": "Health Care",
    "BSX": "Health Care", "ELV": "Health Care", "GILD": "Health Care",
    "CVS": "Health Care",
    "WMT": "Consumer Staples", "COST": "Consumer Staples",
    "HD": "Consumer Discretionary", "LOW": "Consumer Discretionary",
    "MCD": "Consumer Discretionary", "SBUX": "Consumer Discretionary",
    "NKE": "Consumer Discretionary", "TGT": "Consumer Discretionary",
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "CL": "Consumer Staples", "PM": "Consumer Staples", "MO": "Consumer Staples",
    "KMB": "Consumer Staples", "GIS": "Consumer Staples",
    "CAT": "Industrials", "DE": "Industrials", "HON": "Industrials",
    "GE": "Industrials", "RTX": "Industrials", "LMT": "Industrials",
    "ETN": "Industrials", "EMR": "Industrials", "MMM": "Industrials",
    "UPS": "Industrials", "UNP": "Industrials", "CSX": "Industrials",
    "WM": "Industrials", "ITW": "Industrials", "ADP": "Industrials",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "EOG": "Energy", "PSX": "Energy", "MPC": "Energy", "VLO": "Energy",
    "LIN": "Materials", "APD": "Materials", "SHW": "Materials", "NEM": "Materials",
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities", "D": "Utilities",
    "AEP": "Utilities", "AMT": "Real Estate", "PLD": "Real Estate", "O": "Real Estate",
    "DIS": "Communication Services", "CMCSA": "Communication Services",
    "V": "Financials", "MA": "Financials", "PYPL": "Financials",
    "SYY": "Consumer Staples", "FDX": "Industrials", "ORLY": "Consumer Discretionary",
    "AZO": "Consumer Discretionary",
}

INDUSTRY_MAP = {
    "MSFT": "Software", "AAPL": "Technology Hardware",
    "GOOGL": "Interactive Media & Services", "GOOG": "Interactive Media & Services",
    "META": "Interactive Media & Services", "AVGO": "Semiconductors",
    "ORCL": "Software", "CSCO": "Communications Equipment", "IBM": "IT Services",
    "ACN": "IT Services", "ADBE": "Software", "CRM": "Software",
    "QCOM": "Semiconductors", "TXN": "Semiconductors", "AMAT": "Semiconductor Equipment",
    "ADI": "Semiconductors", "INTU": "Software", "NOW": "Software",
    "INTC": "Semiconductors", "MU": "Semiconductors", "LRCX": "Semiconductor Equipment",
    "KLAC": "Semiconductor Equipment", "AMZN": "Broadline Retail", "NFLX": "Entertainment",
    "JPM": "Banks", "BAC": "Banks", "WFC": "Banks", "C": "Banks",
    "GS": "Capital Markets", "MS": "Capital Markets", "BLK": "Capital Markets",
    "SPGI": "Financial Data & Exchanges", "MCO": "Financial Data & Exchanges",
    "ICE": "Financial Data & Exchanges", "CME": "Financial Data & Exchanges",
    "AON": "Insurance Brokers", "MMC": "Insurance Brokers",
    "CB": "Property & Casualty Insurance", "PGR": "Property & Casualty Insurance",
    "ALL": "Property & Casualty Insurance", "TRV": "Property & Casualty Insurance",
    "UNH": "Health Care Providers & Services", "JNJ": "Pharmaceuticals",
    "ABBV": "Biotechnology", "ABT": "Health Care Equipment", "MRK": "Pharmaceuticals",
    "AMGN": "Biotechnology", "LLY": "Pharmaceuticals", "BMY": "Pharmaceuticals",
    "TMO": "Life Sciences Tools & Services", "DHR": "Life Sciences Tools & Services",
    "MDT": "Health Care Equipment", "SYK": "Health Care Equipment",
    "BSX": "Health Care Equipment", "ELV": "Health Care Providers & Services",
    "GILD": "Biotechnology", "CVS": "Health Care Providers & Services",
    "WMT": "Consumer Staples Distribution & Retail", "COST": "Consumer Staples Distribution & Retail",
    "HD": "Broadline Retail", "LOW": "Broadline Retail",
    "MCD": "Hotels, Restaurants & Leisure", "SBUX": "Hotels, Restaurants & Leisure",
    "NKE": "Textiles, Apparel & Luxury Goods", "TGT": "Consumer Staples Distribution & Retail",
    "PG": "Household Products", "KO": "Beverages", "PEP": "Beverages",
    "CL": "Personal Care Products", "PM": "Tobacco", "MO": "Tobacco",
    "KMB": "Household Products", "GIS": "Food Products",
    "CAT": "Machinery", "DE": "Machinery", "HON": "Industrial Conglomerates",
    "GE": "Aerospace & Defense", "RTX": "Aerospace & Defense", "LMT": "Aerospace & Defense",
    "ETN": "Electrical Equipment", "EMR": "Electrical Equipment",
    "MMM": "Industrial Conglomerates", "UPS": "Air Freight & Logistics",
    "UNP": "Ground Transportation", "CSX": "Ground Transportation",
    "WM": "Commercial Services & Supplies", "ITW": "Machinery", "ADP": "Professional Services",
    "XOM": "Oil, Gas & Consumable Fuels", "CVX": "Oil, Gas & Consumable Fuels",
    "COP": "Oil, Gas & Consumable Fuels", "SLB": "Energy Equipment & Services",
    "EOG": "Oil, Gas & Consumable Fuels", "PSX": "Oil, Gas & Consumable Fuels",
    "MPC": "Oil, Gas & Consumable Fuels", "VLO": "Oil, Gas & Consumable Fuels",
    "LIN": "Chemicals", "APD": "Chemicals", "SHW": "Chemicals", "NEM": "Metals & Mining",
    "NEE": "Electric Utilities", "DUK": "Electric Utilities", "SO": "Electric Utilities",
    "D": "Electric Utilities", "AEP": "Electric Utilities",
    "AMT": "Specialized REITs", "PLD": "Industrial REITs", "O": "Retail REITs",
    "DIS": "Entertainment", "CMCSA": "Media", "V": "Financial Services",
    "MA": "Financial Services", "PYPL": "Financial Services",
    "SYY": "Consumer Staples Distribution & Retail", "FDX": "Air Freight & Logistics",
    "ORLY": "Specialty Retail", "AZO": "Specialty Retail",
}


# Company groups prevent multiple share classes occupying multiple primary slots.
COMPANY_GROUP_MAP = {"GOOG": "Alphabet", "GOOGL": "Alphabet"}

# Optional local portfolio metadata; tickers are supplied through .env, not stored here.
PORTFOLIO_TICKER_SECTOR_MAP = {
    "NVDA": "Information Technology", "TSM": "Information Technology",
    "SMH": "Information Technology", "QQQ": "Information Technology",
    "VYM": "Financials", "SCHD": "Financials", "JEPQ": "Information Technology",
    "XLI": "Industrials", "XLV": "Health Care", "EWT": "Information Technology",
    "EWY": "Information Technology",
}
