# Quality Dip Scanner V1.9

A manual research scanner for finding high-quality US companies after meaningful price drawdowns.

## Strategy

> Quality company + reasonable valuation + meaningful dip = candidate

Dividend yield is only a small optional bonus.

## Score

| Component | Weight |
|---|---:|
| Quality | 45 |
| Valuation | 20 |
| Dip | 30 |
| Dividend | 5 |
| **Total** | **100** |

## V1.9 fundamental-data architecture

V1.7 changes the fundamental-data pipeline:

**SEC EDGAR XBRL → Tiingo fallback**

The SEC's `data.sec.gov` APIs provide company submissions and extracted XBRL financial-statement data without API keys. The Company Facts endpoint can return standardized XBRL facts for a company in one API call.

The scanner uses SEC Company Facts as its primary source. V1.9 prefers the latest four standalone quarterly observations to build TTM revenue, net income, EPS and cash flow metrics when sufficient XBRL data is available. It falls back to annual data when quarterly observations are insufficient. The scanner also records the latest quarter and filing dates.

- Revenue
- Net income
- EPS
- Operating cash flow
- Capital expenditure
- Free cash flow
- ROE
- Revenue growth
- EPS growth
- Debt
- Equity
- Assets

Current P/E is calculated from the latest annual EPS and current market price. Payout ratio is derived from trailing annual dividends / EPS when possible.

If SEC data is temporarily unavailable or insufficient and Tiingo Fundamentals access is configured, Tiingo is used as a fallback.

### Data quality

- **B / SEC_XBRL** — fundamental data successfully obtained from SEC.
- **B / Tiingo** — SEC was insufficient, but Tiingo supplied usable fundamentals.
- **D / SEC_ERROR** — fundamental data could not be obtained.
- `DATA INCOMPLETE` means the program cannot verify the company's fundamentals; it does **not** mean the company has poor fundamentals.

SEC fundamental caches are kept locally for 7 days by default. This prevents repeated scans from downloading the same Company Facts JSON every day.

## SEC User-Agent

Set a descriptive SEC User-Agent in your local `.env` file. For example:

```
SEC_USER_AGENT=QualityDipScanner/1.7 your-email@example.com
```

Do not commit `.env`.

## Setup

Create `.env` locally:

```
TIINGO_API_KEY=YOUR_TIINGO_TOKEN
ALPHAVANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY
SEC_USER_AGENT=QualityDipScanner/1.7 your-email@example.com
```

The price-data provider remains Tiingo when `TIINGO_API_KEY` is configured, otherwise Alpha Vantage is used.

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
python scanner.py
```

Outputs:

- `scan_results.csv`
- `scan_errors.csv`
- local price and SEC fundamental caches under `data/`

## Why Alpha Vantage remains useful

Alpha Vantage also provides standardized fundamental endpoints for company overview, income statement, balance sheet, cash flow, shares outstanding, and earnings history. It is therefore a good future validation/secondary provider, but V1.7 does not spend an Alpha Vantage request for every stock when SEC data is available.

## Dip stages

- <10% → OBSERVE
- 10-15% → WATCH_10%
- 15-20% → BUY_1
- 20-25% → BUY_2
- 25-30% → BUY_3
- 30%+ → DEEP_DIP_REVIEW

These are research labels, not automatic trading instructions.

## V1.9 freshness rules

Fundamental freshness now affects scoring:
- <=120 days: full quality/valuation weight
- 121-210 days: 90%
- 211-270 days: 75%
- 271-365 days: 50%
- >365 days: fundamentals are not verified and the stock cannot receive a BUY CANDIDATE signal

The scanner also emits `fundamental_age_days`, `latest_quarter_date`, and `latest_filing_date` so stale inputs are visible in the CSV.

## Next step: V2.0
Validate SEC-derived metrics against a second provider for a sample of stocks, then add margins, leverage and ROIC where the data is sufficiently reliable.

No automatic trading is implemented.
