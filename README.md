# Quality Dip Scanner V1.6

A manual research scanner for finding high-quality US companies after meaningful price drawdowns.

## Strategy

V1.6 is no longer a high-dividend strategy.

The core idea is:

> Quality company + reasonable valuation + meaningful dip = candidate

Dividend yield is only a small optional bonus. A low-yield quality growth stock can score highly if its fundamentals and valuation are strong.

## Universe

The default universe is a curated list of about 120 established US large-cap companies across technology, communication, financials, healthcare, consumer, industrials, energy, materials, utilities and REITs.

The universe is deliberately broad. It is a research universe, not a claim that every stock is high quality.

## V1.6 score

| Component | Weight | Purpose |
|---|---:|---|
| Quality | 45 | Profitability, cash flow and growth |
| Valuation | 20 | Avoid buying an expensive dip |
| Dip | 30 | Identify meaningful drawdowns |
| Dividend | 5 | Optional shareholder-return bonus |
| Total | 100 | |

Quality uses EPS, free cash flow, ROE, revenue growth, EPS growth and payout ratio when available.

Valuation currently uses P/E. Negative or extreme P/E receives no valuation points.

Dip uses 100-day, 60-day and 20-day drawdowns plus RSI(14).

Dividend yield and dividend growth are a small bonus, not a requirement.

## Signals

- 75+ → STRONG BUY CANDIDATE
- 60-74 → BUY CANDIDATE
- 45-59 → WATCH
- <45 → HOLD
- Missing fundamentals → DATA INCOMPLETE
- Major deterioration → RISK / PASS
- Less than 10% below 100-day high → NO DIP

## Dip stages

- <10% → OBSERVE
- 10-15% → WATCH_10%
- 15-20% → BUY_1
- 20-25% → BUY_2
- 25-30% → BUY_3
- 30%+ → DEEP_DIP_REVIEW

These are research labels, not automatic trading instructions.

## Data

Tiingo is preferred for EOD price data when TIINGO_API_KEY is configured. Local caching and retry/backoff reduce unnecessary API requests.

Alpha Vantage remains available as a fallback.

Fundamental coverage depends on the Tiingo account/API entitlement. If fundamentals cannot be verified, the scanner deliberately avoids issuing a BUY signal.

## Setup

Create .env locally:

TIINGO_API_KEY=YOUR_TIINGO_TOKEN
ALPHAVANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY

Never commit .env.

## Run

source .venv/bin/activate
pip install -r requirements.txt
python scanner.py

Outputs:

- scan_results.csv
- scan_errors.csv when symbols fail
- cached data under data/

## Next step: V1.7 backtest

Before treating the score as an investment signal, test it historically.

The preferred next upgrade is to measure forward 1M / 3M / 6M / 12M total returns for score >= 60, score >= 75, QUALITY_DIP, and different drawdown levels.

This will tell us whether the scoring model has genuine predictive value rather than merely looking sensible.

No automatic trading is implemented.
