# Quality Dip Scanner V2.3

A manual research scanner for finding high-quality US companies after meaningful price drawdowns.

## Strategy

> Quality company + reasonable valuation + meaningful dip = candidate

Dividend yield is only a small optional bonus.

## Score

| Component | Weight |
|---|---:|
| Quality | 30 |
| Long-term business trend | 15 |
| Valuation | 30 |
| Dip | 20 |
| Dividend | 5 |
| **Total** | **100** |

## V2.0 fundamental-data architecture

The V1.7+ pipeline uses:

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

- **OK** — fundamentals are sufficiently current and verified; the stock can receive a numeric score.
- **STALE** — fundamentals exist but the underlying reporting period is too old to verify; no numeric score is exposed.
- **ERROR** — SEC/Tiingo retrieval failed; no numeric score is exposed.
- **INCOMPLETE** — insufficient fundamental fields are available; no numeric score is exposed.
- The scanner keeps component values for diagnostics, but only `OK` rows are ranked as scored candidates.
- SEC freshness is based on the **latest usable reporting period**, not the oldest component. A lagging XBRL tag such as capex/EPS must not make an otherwise current TTM dataset appear years old.

SEC fundamental caches are kept locally for 7 days by default. The cache schema/version is refreshed when the fundamental extraction logic changes. This prevents repeated scans from downloading the same Company Facts JSON every day.

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

## V2.0 structural-risk / value-trap detection

V2.0 keeps the original 100-point base score (Quality 45 + Valuation 30 + Dip 20 + Dividend 5), then applies a separate structural-risk penalty of up to 20 points. The report exposes the penalty instead of hiding it.
- <=120 days: full quality/valuation weight
- 121-210 days: 90%
- 211-270 days: 75%
- 271-365 days: 50%
- >365 days: fundamentals are not verified and the stock cannot receive a BUY CANDIDATE signal

The scanner also emits `fundamental_age_days`, `latest_quarter_date`, and `latest_filing_date` so stale inputs are visible in the CSV.

### Structural risk signals
- Revenue TTM decline >5%: structural warning; >10%: stronger warning.
- EPS TTM decline >5%: structural warning; >10%: stronger warning.
- Negative FCF or EPS can add structural risk for non-financial companies.
- High leverage can add structural risk for non-financial companies.
- Structural penalty is capped at 20 points.
- `LOW`, `MEDIUM`, `HIGH`, or `UNKNOWN` is reported as `value_trap_risk`.
- `VALUE TRAP REVIEW` replaces a buy signal when structural risk is high.

These are research flags, not claims that a company is actually a value trap. The scanner is designed to trigger manual review.

## V2.2 multi-horizon price context

V2.2 adds multi-horizon price context without changing the existing 100-point scoring model:
- `DD20`: drawdown from the highest closing price in the last 20 trading days.
- `DD60`: drawdown from the highest closing price in the last 60 trading days.
- `DD100`: drawdown from the highest closing price in the last 100 trading days.
- `DD252`: drawdown from the highest closing price in the last 252 trading days (roughly one trading year).
- `200DMA`: percentage distance between the current close and the 200-day simple moving average.

All drawdown metrics use **closing prices**, not intraday highs. `DD100` remains the primary dip-stage and signal input, so this version does not silently change existing candidate thresholds. `DD252` is a longer-term context metric that helps distinguish a recent pullback from a larger one-year drawdown.

The terminal output now shows DD20/60/100/252 and 200DMA distance, and the CSV includes the corresponding high-water marks and metrics.

## V2.1 long-term business trend

V2.1 keeps the 100-point base score but reallocates it to:
- Quality: 30
- Long-term business trend: 15
- Valuation: 30
- Dip: 20
- Dividend: 5

The long-term trend score uses SEC XBRL history where available:
- 3/5-year revenue CAGR
- 3/5-year EPS CAGR
- 3/5-year FCF CAGR
- operating-margin trend
- debt trend
- ROIC proxy

The ROIC field is explicitly a proxy because there is no single universal ROIC XBRL field across issuers. It uses operating income, estimated tax rate and debt + equity as invested capital.

Long-term deterioration can also add to the separate structural-risk penalty:
- 5-year revenue decline
- 5-year EPS decline
- 5-year FCF decline
- material margin compression
- rapid debt growth

The scanner should treat these as research flags rather than automatic conclusions about a business. SEC Company Facts provides historical XBRL facts through the public data API.