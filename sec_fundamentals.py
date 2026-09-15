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
SEC_DELAY = float(os.getenv("SEC_REQUEST_DELAY", "0.15"))

_TICKER_MAP = None


def _headers():
    # SEC asks automated users to declare a descriptive User-Agent with contact info.
    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent:
        user_agent = "QualityDipScanner/1.7 research contact=your-email@example.com"
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
            if age <= SEC_CACHE_DAYS:
                payload["fundamentals_source"] = "SEC_CACHE"
                return payload
    except Exception:
        pass
    return None


def _save_cache(symbol, payload):
    payload["_cached_on"] = date.today().isoformat()
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
    # Prefer USD, shares, or pure. The caller can select the relevant unit.
    for unit in ("USD", "shares", "pure", "USD/shares"):
        if unit in units:
            return units[unit]
    return next(iter(units.values()))


def _facts(companyfacts, tags):
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        fact = gaap.get(tag)
        if fact:
            return _units(fact)
    return []


def _annual_series(companyfacts, tags):
    rows = _facts(companyfacts, tags)
    candidates = []
    for row in rows:
        if row.get("form") not in ("10-K", "20-F", "40-F"):
            continue
        if row.get("fp") not in (None, "FY"):
            continue
        if row.get("val") is None:
            continue
        start = row.get("start")
        end = row.get("end")
        if not start or not end:
            continue
        try:
            days = (
                date.fromisoformat(end) - date.fromisoformat(start)
            ).days
        except ValueError:
            continue
        if 300 <= days <= 430:
            candidates.append(row)
    candidates.sort(key=lambda x: x.get("end", ""))
    # Deduplicate by fiscal year/end date, keeping the latest filed fact.
    result = {}
    for row in candidates:
        result[row["end"]] = row
    return list(sorted(result.values(), key=lambda x: x["end"]))


def _latest_instant(companyfacts, tags):
    rows = _facts(companyfacts, tags)
    candidates = []
    for row in rows:
        if row.get("val") is not None and row.get("end"):
            candidates.append(row)
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
    latest = float(rows[-1]["val"])
    prior = float(rows[-2]["val"])
    if prior == 0:
        return None
    return latest / prior - 1


def _ttm_eps(companyfacts):
    # Prefer Diluted EPS annual facts. Companyfacts commonly reports this in USD/share.
    rows = _annual_series(companyfacts, [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasic",
    ])
    if rows:
        return float(rows[-1]["val"])

    return None


def get_sec_fundamentals(symbol, force_refresh=False):
    cached = None if force_refresh else _read_cache(symbol)
    if cached is not None:
        return cached

    try:
        facts = _request_companyfacts(symbol)

        revenue = _latest_annual_value(
            facts, ["RevenueFromContractWithCustomerExcludingAssessedTax",
                    "Revenues", "SalesRevenueNet"]
        )
        net_income = _latest_annual_value(
            facts, ["NetIncomeLoss", "ProfitLoss"]
        )
        equity = _latest_instant(
            facts, ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
        )
        assets = _latest_instant(facts, ["Assets"])
        cfo = _latest_annual_value(
            facts, ["NetCashProvidedByUsedInOperatingActivities"]
        )
        capex = _latest_annual_value(
            facts, ["PaymentsToAcquirePropertyPlantAndEquipment",
                    "PaymentsToAcquireProductiveAssets"]
        )
        debt_current = _latest_instant(
            facts, ["LongTermDebtCurrent", "LongTermDebtAndFinanceLeaseObligationsCurrent"]
        )
        debt_long = _latest_instant(
            facts, ["LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"]
        )

        eps = _ttm_eps(facts)
        if eps is None and net_income is not None:
            shares = _latest_annual_value(
                facts, ["WeightedAverageNumberOfDilutedSharesOutstanding",
                        "WeightedAverageNumberOfSharesOutstandingBasic"]
            )
            if shares and shares > 0:
                eps = net_income / shares

        fcf = None
        if cfo is not None:
            # SEC reports capex as a positive cash outflow for this tag.
            fcf = cfo - abs(capex or 0)

        roe = None
        if net_income is not None and equity and equity.get("val"):
            equity_value = float(equity["val"])
            if equity_value > 0:
                roe = net_income / equity_value

        debt = None
        if debt_current or debt_long:
            debt = float((debt_current or {}).get("val", 0)) + float((debt_long or {}).get("val", 0))

        result = {
            "fundamentals_available": bool(revenue is not None or net_income is not None or eps is not None),
            "eps": eps,
            "free_cash_flow": fcf,
            "roe": roe,
            "payout_ratio": None,
            "pe": None,
            "revenue_growth": _growth(
                facts, ["RevenueFromContractWithCustomerExcludingAssessedTax",
                        "Revenues", "SalesRevenueNet"]
            ),
            "eps_growth": _growth(
                facts, ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
            ),
            "revenue": revenue,
            "net_income": net_income,
            "total_assets": float(assets["val"]) if assets else None,
            "equity": float(equity["val"]) if equity else None,
            "debt": debt,
            "fundamental_date": (revenue and _annual_series(
                facts, ["RevenueFromContractWithCustomerExcludingAssessedTax",
                        "Revenues", "SalesRevenueNet"]
            )[-1].get("end")) or None,
            "fundamentals_source": "SEC_XBRL",
            "data_quality": "B",
        }

        _save_cache(symbol, result)
        return result

    except Exception as exc:
        return {
            "fundamentals_available": False,
            "fundamentals_source": "SEC_ERROR",
            "fundamentals_error": str(exc),
            "data_quality": "D",
        }
