# Dividend Dip V1.4

Manual dividend-stock dip scanner for long-term investors.

## What V1.4 does

V1.4 ranks a stock from 0-100 using five components:

- **Dip Score (0-30):** 100D/60D/20D drawdowns + RSI
- **Dividend Score (0-20):** trailing dividend yield + dividend growth
- **Quality Score (0-30):** EPS, free cash flow, ROE, payout ratio and growth
- **Valuation Score (0-10):** P/E
- **Trend Score (0-10):** price vs 200DMA

Signals:

- **70+** → STRONG BUY CANDIDATE
- **55-69** → BUY CANDIDATE
- **40-54** → WATCH
- **<40** → HOLD

If fundamental data is unavailable, the scanner reports **DATA INCOMPLETE** rather than pretending that the stock is investable.

## Data source

V1.4 prefers **Tiingo EOD** when TIINGO_API_KEY is configured. Tiingo provides adjusted and raw prices plus dividend cash distributions, which lets the scanner calculate dividend yield/growth and a true 200DMA when enough history is available.

Tiingo fundamentals are optional because fundamental coverage depends on the account/entitlement. The scanner falls back gracefully when a ticker has no fundamental access.

Alpha Vantage remains supported as a fallback for price history when only ALPHAVANTAGE_API_KEY is configured.

## Setup

Create .env locally:

TIINGO_API_KEY=YOUR_TIINGO_TOKEN
ALPHAVANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY

For V1.4, Tiingo is recommended.

Never commit .env to GitHub. It is already included in .gitignore.

## Run

source .venv/bin/activate
pip install -r requirements.txt
python scanner.py

The scanner caches price and fundamental responses under data/ to reduce repeated API calls.

## Important

The score is a research heuristic, **not a validated investment strategy**. A high score does not mean a stock will rise.

The next major upgrade should be **historical backtesting**: measure how stocks scoring 55/70/80+ actually performed after 1, 3, 6 and 12 months, including dividends.

No automatic trading is implemented.