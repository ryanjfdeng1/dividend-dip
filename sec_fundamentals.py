import json
import os
import time
from datetime import date
from pathlib import Path

import requests

SEC_DATA_URL = "https://data.sec.gov"
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

SEC_CACHE_DAYS = int(os.getenv("SEC_CACHE_DAYS", "7"))
FUNDAMENTALS_VERSION = "2.1"
SEC_DELAY = float(os.getenv("SEC_REQUEST_DELAY", "0.15"))

# Freshness is based on the period covered by the financial data, not merely
# the filing date. This keeps an old annual number from looking "fresh".
FRESH_A_DAYS = int(os.getenv("SEC_FRESH_A_DAYS", "120"))
FRESH_B_DAYS = int(os.getenv("SEC_FRESH_B_DAYS", "210"))
FRESH_C_DAYS = int(os.getenv("SEC_FRESH_C_DAYS", "365"))
FRESH_MAX_DAYS = int(os.getenv("SEC_MAX_FUNDAMENTAL_AGE_DAYS", "450"))

_TICKER_MAP = None


def _headers():
    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent:
        user_agent = "QualityDipScanner/1.9 research contact=your-email@example.com"
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}


def _cache_path(symbol):
    return CACHE_DIR / f"{symbol.upper()}_sec_fundamentals.json"


def _read_cache(symbol):
    path = _cache_path(symbol)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
        cached_on = payload.get("_cached_on")
        if cached_on:
            age = (date.today() - date.fromisoformat(cached_on)).days
            # V1.9 caches are refreshed once so the new TTM/quarterly logic is used.
            if (
                age <= SEC_CACHE_DAYS
                and payload.get("fundamentals_version") == FUNDAMENTALS_VERSION
                and "shares_outstanding" in payload
                and "latest_quarter_date" in payload
            ):
                payload["fundamentals_source"] = "SEC_CACHE"
                return payload
    except Exception:
        pass
    return None


def _save_cache(symbol, payload):
    payload["_cached_on"] = date.today().isoformat()
    payload["fundamentals_version"] = FUNDAMENTALS_VERSION
    _cache_path(symbol).write_text(json.dumps(payload))


def _get_ticker_map():
    global _TICKER_MAP
    if _TICKER_MAP is not None:
        return _TICKER_MAP
    response = requests.get(SEC_TICKER_URL, headers=_headers(), timeout=30)
    response.raise_for_status()
    raw = response.json()
    _TICKER_MAP = {
        item["ticker"].upper(): str(item["cik_str"]).zfill(10)
        for item in raw.values()
    }
    return _TICKER_MAP


def _request_companyfacts(symbol):
    cik = _get_ticker_map().get(symbol.upper())
    if not cik:
        raise RuntimeError(f"SEC CIK not found for {symbol}")
    response = requests.get(
        f"{SEC_DATA_URL}/api/xbrl/companyfacts/CIK{cik}.json",
        headers=_headers(),
        timeout=30,
    )
    if response.status_code == 429:
        raise RuntimeError("SEC rate limited (429)")
    response.raise_for_status()
    time.sleep(SEC_DELAY)
    return response.json()


def _units(fact):
    units = fact.get("units", {})
    if not units:
        return []
    for unit in ("USD", "shares", "pure", "USD/shares"):
        if unit in units:
            return units[unit]
    return next(iter(units.values()))


def _facts(companyfacts, tags):
    facts = companyfacts.get("facts", {})
    for tag in tags:
        if ":" in tag:
            taxonomy, concept = tag.split(":", 1)
        else:
            taxonomy, concept = "us-gaap", tag
        fact = facts.get(taxonomy, {}).get(concept)
        if fact:
            return _units(fact)
    return []


def _annual_series(companyfacts, tags):
    rows = _facts(companyfacts, tags)
    candidates = []
    for row in rows:
        if row.get("form") not in ("10-K", "20-F", "40-F"):
            continue
        if row.get("val") is None:
            continue
        start, end = row.get("start"), row.get("end")
        if not start or not end:
            continue
        try:
            days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        except ValueError:
            continue
        if 300 <= days <= 430:
            candidates.append(row)

    result = {}
    for row in candidates:
        key = row["end"]
        old = result.get(key)
        if old is None or row.get("filed", "") > old.get("filed", ""):
            result[key] = row
    return sorted(result.values(), key=lambda x: x["end"])


def _quarterly_series(companyfacts, tags):
    """Return standalone quarter observations from 10-Q/10-K facts."""
    rows = _facts(companyfacts, tags)
    candidates = []
    for row in rows:
        if row.get("form") not in ("10-Q", "10-K"):
            continue
        if row.get("val") is None:
            continue
        start, end = row.get("start"), row.get("end")
        if not start or not end:
            continue
        try:
            days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        except ValueError:
            continue
        # Standalone quarterly income/cash-flow facts are normally ~3 months.
        if 70 <= days <= 120:
            candidates.append(row)

    result = {}
    for row in candidates:
        key = row["end"]
        old = result.get(key)
        if old is None or row.get("filed", "") > old.get("filed", ""):
            result[key] = row
    return sorted(result.values(), key=lambda x: x["end"])


def _ttm_value(companyfacts, tags):
    rows = _quarterly_series(companyfacts, tags)
    if len(rows) < 4:
        return None, None
    latest = rows[-4:]
    return sum(float(row["val"]) for row in latest), latest[-1]["end"]


def _ttm_growth(companyfacts, tags):
    rows = _quarterly_series(companyfacts, tags)
    if len(rows) < 8:
        return None
    latest = sum(float(row["val"]) for row in rows[-4:])
    prior = sum(float(row["val"]) for row in rows[-8:-4])
    return None if prior == 0 else latest / prior - 1


def _latest_instant(companyfacts, tags):
    rows = _facts(companyfacts, tags)
    candidates = [r for r in rows if r.get("val") is not None and r.get("end")]
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x.get("end", ""), x.get("filed", "")))
    return candidates[-1]


def _latest_annual_value(companyfacts, tags):
    rows = _annual_series(companyfacts, tags)
    return float(rows[-1]["val"]) if rows else None


def _growth(companyfacts, tags):
    rows = _annual_series(companyfacts, tags)
    if len(rows) < 2:
        return None
    latest, prior = float(rows[-1]["val"]), float(rows[-2]["val"])
    return None if prior == 0 else latest / prior - 1


def _freshness(fundamental_date):
    if not fundamental_date:
        return "D", "MISSING_FUNDAMENTAL_DATE", None
    try:
        age = (date.today() - date.fromisoformat(fundamental_date)).days
    except ValueError:
        return "D", "INVALID_FUNDAMENTAL_DATE", None

    if age <= FRESH_A_DAYS:
        return "A", "", age
    if age <= FRESH_B_DAYS:
        return "B", "AGING_FUNDAMENTALS", age
    if age <= FRESH_C_DAYS:
        return "C", "STALE_FUNDAMENTALS", age
    if age <= FRESH_MAX_DAYS:
        return "D", "VERY_STALE_FUNDAMENTALS", age
    return "E", "VERY_STALE_FUNDAMENTALS", age



def _cagr_from_annual(rows, years):
    if len(rows) < years + 1:
        return None
    latest = float(rows[-1]["val"])
    base = float(rows[-(years + 1)]["val"])
    if base <= 0 or latest <= 0:
        return None
    return (latest / base) ** (1 / years) - 1


def _trend_change(rows, years):
    if len(rows) < years + 1:
        return None
    latest = float(rows[-1]["val"])
    base = float(rows[-(years + 1)]["val"])
    if base == 0:
        return None
    return latest / base - 1

def get_sec_fundamentals(symbol, force_refresh=False):
    cached = None if force_refresh else _read_cache(symbol)
    if cached is not None:
        return cached

    try:
        facts = _request_companyfacts(symbol)

        revenue_tags = [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues", "SalesRevenueNet"
        ]
        eps_tags = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]

        operating_income_tags = ["OperatingIncomeLoss"]
        tax_expense_tags = ["IncomeTaxExpenseBenefit"]
        pretax_income_tags = [
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeTaxExpenseBenefit"
        ]
        net_income_tags = ["NetIncomeLoss", "ProfitLoss"]
        cfo_tags = ["NetCashProvidedByUsedInOperatingActivities"]
        capex_tags = [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets"
        ]

        # V1.9: prefer TTM built from the latest four standalone quarters.
        revenue, revenue_date = _ttm_value(facts, revenue_tags)
        net_income, net_income_date = _ttm_value(facts, net_income_tags)
        cfo, cfo_date = _ttm_value(facts, cfo_tags)
        capex, capex_date = _ttm_value(facts, capex_tags)
        eps, eps_date = _ttm_value(facts, eps_tags)

        # Fallback to annual data when a company does not expose enough
        # standalone quarterly XBRL observations.
        if revenue is None:
            revenue_rows = _annual_series(facts, revenue_tags)
            revenue = float(revenue_rows[-1]["val"]) if revenue_rows else None
            revenue_date = revenue_rows[-1]["end"] if revenue_rows else None

        if net_income is None:
            net_income = _latest_annual_value(facts, net_income_tags)
            annual = _annual_series(facts, net_income_tags)
            net_income_date = annual[-1]["end"] if annual else None

        if cfo is None:
            cfo = _latest_annual_value(facts, cfo_tags)
            annual = _annual_series(facts, cfo_tags)
            cfo_date = annual[-1]["end"] if annual else None

        if capex is None:
            capex = _latest_annual_value(facts, capex_tags)
            annual = _annual_series(facts, capex_tags)
            capex_date = annual[-1]["end"] if annual else None

        if eps is None:
            eps = _latest_annual_value(facts, eps_tags)
            annual = _annual_series(facts, eps_tags)
            eps_date = annual[-1]["end"] if annual else None

        equity = _latest_instant(facts, [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
        ])
        assets = _latest_instant(facts, ["Assets"])
        debt_current = _latest_instant(facts, [
            "LongTermDebtCurrent",
            "LongTermDebtAndFinanceLeaseObligationsCurrent"
        ])
        debt_long = _latest_instant(facts, [
            "LongTermDebtNoncurrent",
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent"
        ])

        if eps is None and net_income is not None:
            shares_weighted = _latest_annual_value(facts, [
                "WeightedAverageNumberOfDilutedSharesOutstanding",
                "WeightedAverageNumberOfSharesOutstandingBasic"
            ])
            if shares_weighted and shares_weighted > 0:
                eps = net_income / shares_weighted

        fcf = cfo - abs(capex or 0) if cfo is not None else None

        revenue_annual = _annual_series(facts, revenue_tags)
        fcf_annual = []
        cfo_annual = _annual_series(facts, cfo_tags)
        capex_annual = _annual_series(facts, capex_tags)
        capex_by_end = {r["end"]: float(r["val"]) for r in capex_annual}
        for r in cfo_annual:
            if r["end"] in capex_by_end:
                fcf_annual.append({"end": r["end"], "val": float(r["val"]) - abs(capex_by_end[r["end"]])})

        operating_income_annual = _annual_series(facts, operating_income_tags)
        debt_annual = _annual_series(facts, ["LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"])
        equity_annual = _annual_series(facts, [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
        ])
        eps_annual = _annual_series(facts, eps_tags)
        revenue_cagr_3y = _cagr_from_annual(revenue_annual, 3)
        revenue_cagr_5y = _cagr_from_annual(revenue_annual, 5)
        eps_cagr_3y = _cagr_from_annual(eps_annual, 3)
        eps_cagr_5y = _cagr_from_annual(eps_annual, 5)
        fcf_cagr_3y = _cagr_from_annual(fcf_annual, 3)
        fcf_cagr_5y = _cagr_from_annual(fcf_annual, 5)

        rev_by_end = {r["end"]: float(r["val"]) for r in revenue_annual}
        margin_history = []
        for r in operating_income_annual:
            rev = rev_by_end.get(r["end"])
            if rev and rev > 0:
                margin_history.append({"end": r["end"], "val": float(r["val"]) / rev})
        margin_change_3y = _trend_change(margin_history, 3)
        margin_change_5y = _trend_change(margin_history, 5)

        debt_change_3y = _trend_change(debt_annual, 3)
        debt_change_5y = _trend_change(debt_annual, 5)

        latest_revenue = float(revenue_annual[-1]["val"]) if revenue_annual else None
        latest_operating_income = float(operating_income_annual[-1]["val"]) if operating_income_annual else None
        operating_margin = (
            latest_operating_income / latest_revenue
            if latest_operating_income is not None and latest_revenue and latest_revenue > 0
            else None
        )

        tax_annual = _annual_series(facts, tax_expense_tags)
        pretax_annual = _annual_series(facts, pretax_income_tags)
        roic_proxy = None
        if operating_income_annual and debt_annual and equity_annual:
            op = float(operating_income_annual[-1]["val"])
            debt_latest = float(debt_annual[-1]["val"])
            equity_latest = float(equity_annual[-1]["val"])
            tax_rate = 0.21
            if tax_annual and pretax_annual:
                tax = float(tax_annual[-1]["val"])
                pretax = float(pretax_annual[-1]["val"])
                if pretax > 0:
                    tax_rate = max(0.0, min(0.35, tax / pretax))
            invested_capital = debt_latest + equity_latest
            if invested_capital > 0:
                roic_proxy = (op * (1 - tax_rate)) / invested_capital


        roe = None
        if net_income is not None and equity and float(equity["val"]) > 0:
            roe = net_income / float(equity["val"])

        shares_row = _latest_instant(facts, [
            "dei:EntityCommonStockSharesOutstanding",
            "us-gaap:CommonStockSharesOutstanding",
        ])
        shares = float(shares_row["val"]) if shares_row else None
        if shares is not None and shares <= 0:
            shares = None

        debt = None
        if debt_current or debt_long:
            debt = float((debt_current or {}).get("val", 0)) + float(
                (debt_long or {}).get("val", 0)
            )

        dates = [d for d in (revenue_date, net_income_date, eps_date, cfo_date, capex_date) if d]
        fundamental_date = min(dates) if dates else None
        latest_quarter_date = max(dates) if dates else None

        data_quality, freshness_flag, age = _freshness(fundamental_date)

        # Revenue/EPS growth is also TTM-vs-prior-TTM when enough quarters exist.
        revenue_growth = _ttm_growth(facts, revenue_tags)
        if revenue_growth is None:
            revenue_growth = _growth(facts, revenue_tags)

        eps_growth = _ttm_growth(facts, eps_tags)
        if eps_growth is None:
            eps_growth = _growth(facts, eps_tags)

        result = {
            "fundamentals_available": bool(revenue is not None or net_income is not None or eps is not None),
            "eps": eps,
            "free_cash_flow": fcf,
            "roe": roe,
            "payout_ratio": None,
            "pe": None,
            "revenue_growth": revenue_growth,
            "eps_growth": eps_growth,
            "revenue": revenue,
            "net_income": net_income,
            "total_assets": float(assets["val"]) if assets else None,
            "equity": float(equity["val"]) if equity else None,
            "debt": debt,
            "shares_outstanding": shares,
            "fundamental_date": fundamental_date,
            "fundamental_age_days": age,
            "latest_quarter_date": latest_quarter_date,
            "latest_filing_date": max(
                [r.get("filed") for tag in revenue_tags for r in _facts(facts, [tag]) if r.get("filed")]
                or [None]
            ),
            "fundamentals_source": "SEC_XBRL_TTM",
            "data_quality": data_quality,
            "fundamentals_error": freshness_flag or None,
            "revenue_cagr_3y": revenue_cagr_3y,
            "revenue_cagr_5y": revenue_cagr_5y,
            "eps_cagr_3y": eps_cagr_3y,
            "eps_cagr_5y": eps_cagr_5y,
            "fcf_cagr_3y": fcf_cagr_3y,
            "fcf_cagr_5y": fcf_cagr_5y,
            "operating_margin": operating_margin,
            "margin_change_3y": margin_change_3y,
            "margin_change_5y": margin_change_5y,
            "debt_change_3y": debt_change_3y,
            "debt_change_5y": debt_change_5y,
            "roic_proxy": roic_proxy,
        }

        # E means the underlying financial period is too old to verify.
        if data_quality == "E":
            result["fundamentals_available"] = False

        _save_cache(symbol, result)
        return result

    except Exception as exc:
        return {
            "fundamentals_available": False,
            "fundamentals_source": "SEC_ERROR",
            "fundamentals_error": str(exc),
            "data_quality": "E",
        }
