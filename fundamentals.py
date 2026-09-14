import json
import os
import time
from pathlib import Path

import requests

BASE_URL = "https://api.tiingo.com/tiingo/fundamentals"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

ALIASES = {
    "eps": ["eps", "dilutedEPS", "basicEPS"],
    "free_cash_flow": ["freeCashFlow"],
    "roe": ["roe", "returnOnEquity"],
    "payout_ratio": ["payoutRatio", "dividendPayoutRatio"],
    "revenue_growth": ["revenueGrowth"],
    "eps_growth": ["epsGrowth"],
}


def _token() -> str:
    token = os.getenv("TIINGO_API_KEY")
    if not token:
        raise RuntimeError("TIINGO_API_KEY is not set.")
    return token


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}_fundamentals.json"


def _value(statement_data: list, aliases: list):
    values = {}
    for item in statement_data or []:
        code = item.get("dataCode")
        value = item.get("value")
        if code in aliases and value is not None:
            values[code] = value
    for alias in aliases:
        if alias in values:
            try:
                return float(values[alias])
            except (TypeError, ValueError):
                return None
    return None


def _request(url: str, params: dict):
    last = None
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                last = RuntimeError("Tiingo rate limited (429)")
                time.sleep(2 ** attempt * 2)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise last or RuntimeError("Tiingo request failed")


def get_fundamentals(symbol: str) -> dict:
    """Get latest Tiingo fundamentals with local caching and retry handling."""
    path = _cache_path(symbol)
    payload = None

    if path.exists():
        try:
            payload = json.loads(path.read_text())
        except Exception:
            payload = None

    if payload is None:
        try:
            payload = _request(
                f"{BASE_URL}/{symbol}/statements",
                {"token": _token()},
            )
            path.write_text(json.dumps(payload))
        except Exception:
            return {"fundamentals_available": False}

    if not isinstance(payload, list) or not payload:
        return {"fundamentals_available": False}

    latest = payload[0]
    statement_data = []
    for section in (latest.get("statementData") or {}).values():
        if isinstance(section, list):
            statement_data.extend(section)

    result = {
        "fundamentals_available": True,
        "eps": _value(statement_data, ALIASES["eps"]),
        "free_cash_flow": _value(statement_data, ALIASES["free_cash_flow"]),
        "roe": _value(statement_data, ALIASES["roe"]),
        "payout_ratio": _value(statement_data, ALIASES["payout_ratio"]),
        "revenue_growth": _value(statement_data, ALIASES["revenue_growth"]),
        "eps_growth": _value(statement_data, ALIASES["eps_growth"]),
        "pe": None,
        "fundamental_date": latest.get("date"),
    }

    try:
        daily = _request(
            f"{BASE_URL}/{symbol}/daily",
            {"token": _token(), "columns": "date,peRatio"},
        )
        if isinstance(daily, list) and daily:
            latest_daily = daily[-1]
            result["pe"] = latest_daily.get("peRatio")
    except Exception:
        pass

    return result
