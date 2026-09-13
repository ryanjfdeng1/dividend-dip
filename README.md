# Dividend Dip V1.2

Manual dividend-stock dip scanner.

## Data source

V1.2 uses Alpha Vantage's official `TIME_SERIES_DAILY` endpoint with the free/compact daily data window.

Because the compact response is only about 100 trading days, V1.2 temporarily uses:

- 100-day high instead of 52-week high
- 60-day high
- 20-day high

A true 200-day moving average is calculated only if sufficient history is available; with the free compact response it will normally be unavailable.

## Setup

Create `.env`:

```text
ALPHAVANTAGE_API_KEY=YOUR_KEY
```

Never commit `.env` to GitHub. It is already included in `.gitignore`.

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
python scanner.py
```

The first run downloads each ticker and saves it under `data/`.
Later runs reuse the local cache.

## Signals

Initial research rules:

- 10%+ pullback → WATCH
- 15%+ pullback → BUY CANDIDATE
- 20%+ pullback → STRONG BUY CANDIDATE

These thresholds are hypotheses, not validated investment rules.

## Next version

V2 should add:
- reliable dividend yield/history
- EPS growth
- free cash flow
- payout ratio
- debt/EBITDA
- valuation
- dividend-cut detection
- historical backtesting

No automatic trading is implemented.
