# Dividend Dip V1.5

Manual dividend-stock dip scanner for long-term investors.

## V1.5 objective

V1.5 focuses on finding a **quality dip**, not simply the stock with the largest decline.

The model combines:

- **Dip Score (0-30):** 100D/60D drawdown + RSI
- **Dividend Score (0-15):** yield + dividend growth, with a payout penalty
- **Quality Score (0-30):** EPS, free cash flow, ROE, revenue growth, EPS growth and payout
- **Valuation Score (0-15):** P/E
- **Trend Score (0-10):** price versus 200DMA

Total = **100 points**.

## V1.5 signals

- **70+** → STRONG BUY CANDIDATE
- **55-69** → BUY CANDIDATE
- **40-54** → WATCH
- **<40** → HOLD
- Missing fundamentals → **DATA INCOMPLETE**
- Major fundamental deterioration → **RISK / PASS**

## Drawdown classification

V1.5 also reports the reason for the dip:

- **QUALITY_DIP** — at least 15% below the 100-day high while business quality remains strong
- **NORMAL_DIP** — a meaningful price decline without enough evidence of high quality
- **FUNDAMENTAL_RISK** — negative EPS/FCF, severe earnings/revenue decline, or excessive payout
- **UNKNOWN** — fundamentals unavailable
- **NO_DIP** — less than 10% below the 100-day high

## Staged entry

- <10% → OBSERVE
- 10-15% → WATCH_10%
- 15-20% → BUY_1
- 20-25% → BUY_2
- 25-30% → BUY_3
- 30%+ → DEEP_DIP_REVIEW

The staged entry is a research aid, not a trading instruction.

## Data

V1.5 prefers Tiingo EOD. Tiingo provides raw/adjusted OHLCV, dividends and splits for historical analysis. citeturn0search1

Tiingo currently lists 50 hourly requests and 1,000 daily requests for its free individual plan. Fundamental API access is a separate add-on, and free/evaluation fundamental coverage is limited. citeturn0search0turn0search3

The program uses local caching and retry/backoff for transient 429 errors.

Alpha Vantage remains available as a fallback when Tiingo is not configured.

## Setup

Create `.env` locally:

TIINGO_API_KEY=YOUR_TIINGO_TOKEN
ALPHAVANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY

Do not commit `.env`.

## Run

source .venv/bin/activate
pip install -r requirements.txt
python scanner.py

Outputs:

- `scan_results.csv`
- `scan_errors.csv` when symbols fail
- cached price/fundamental data under `data/`

## Important

The score is a research heuristic, **not a validated investment strategy**. A high score does not mean a stock will rise.

The next major upgrade is **V1.6 historical backtesting**: test whether 55+, 70+ and QUALITY_DIP signals actually outperform after 1, 3, 6 and 12 months, including dividends.

No automatic trading is implemented.
