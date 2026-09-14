# Quality Dip Scanner V1.6.1

A manual research scanner for finding high-quality US companies after meaningful price drawdowns.

## Strategy

V1.6 is no longer a high-dividend strategy.

The core idea is:

> Quality company + reasonable valuation + meaningful dip = candidate

Dividend yield is only a small optional bonus.

## V1.6 score

| Component | Weight |
|---|---:|
| Quality | 45 |
| Valuation | 20 |
| Dip | 30 |
| Dividend | 5 |
| **Total** | **100** |

## V1.6.1 data architecture

The scanner is designed around Tiingo's Starter API limits.

Tiingo currently publishes 50 requests/hour, 1,000 requests/day and 500 unique symbols/month for the Starter plan. Fundamental data through the API is an add-on, while the DOW 30 are available for evaluation. See Tiingo's current pricing and fundamentals documentation.

The program now:

1. Caches daily price history locally and refreshes it at most once per trading day.
2. Caches fundamental data locally for 30 days by default.
3. Uses a persistent local hourly request budget of 45 requests, leaving a safety margin below Tiingo's 50/hour limit.
4. Stops making new Tiingo requests after the hourly safety budget is reached; cached data can still be used.
5. Records fundamental API errors separately instead of silently treating them as poor fundamentals.
6. Keeps all market-data caches under data/, which is ignored by Git.

This means repeated daily scans should consume far fewer API calls after the initial cache has been populated.

## Important limitation

If your Tiingo account does not have fundamental-data access for a ticker, the scanner cannot manufacture the missing data. Such stocks remain DATA INCOMPLETE rather than being treated as low-quality companies.

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
- scan_errors.csv
- local price/fundamental caches under data/

## Dip stages

- <10% → OBSERVE
- 10-15% → WATCH_10%
- 15-20% → BUY_1
- 20-25% → BUY_2
- 25-30% → BUY_3
- 30%+ → DEEP_DIP_REVIEW

These are research labels, not automatic trading instructions.

## Next step: V1.7 backtest

Once the data pipeline is stable, test forward 1M / 3M / 6M / 12M returns for different score and drawdown thresholds.

No automatic trading is implemented.
