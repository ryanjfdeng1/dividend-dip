import json
import os
import time
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://api.tiingo.com/tiingo/fundamentals"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

# Fundamentals change much more slowly than prices.
# Default: refresh every 30 days.
FUNDAMENTAL_TTL_DAYS = int(os.getenv("FUNDAMENTAL_TTL_DAYS", "30"))
RATE_STATE = CACHE_DIR / ".tiingo_rate_state.json"
TIINGO_HOURLY_BUDGET = int(os.getenv("TIINGO_HOURLY_BUDGET", "45"))

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


def _load_rate_state() -> dict:
    try:
        state = json.loads(RATE_STATE.read_text())
        if state.get("hour") == int(time.time() // 3600):
            return state
    except Exception:
        pass
    return {"hour": int(time.time() // 3600), "requests": 0}


def _consume_request() -> None:
    state = _load_rate_state()
    if state["requests"] >= TIINGO_HOURLY_BUDGET:
        raise RuntimeError(
            f"Tiingo hourly safety budget reached ({TIINGO_HOURLY_BUDGET}). "
            "Cached fundamentals will still be used; rerun after the next hour."
        )
    state["requests"] += 1
    RATE_STATE.write_text(json.dumps(state))


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
    _consume_request()
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 429:
            raise RuntimeError("Tiingo rate limited (429)")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Tiingo request failed: {exc}") from exc


def _read_cache(path: Path):
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
        cached_on = payload.get("_cached_on")
        if not cached_on:
            return None
        age = (date.today() - date.fromisoformat(cached_on)).days
        if age <= FUNDAMENTAL_TTL_DAYS:
            return payload
    except Exception:
        return None
    return None


def _save_cache(path: Path, payload: dict) -> None:
    payload["_cached_on"] = date.today().isoformat()
    path.write_text(json.dumps(payload))


def get_fundamentals(symbol: str) -> dict:
    """Return cached fundamentals for 30 days; refresh only when stale."""
    path = _cache_path(symbol)
    cached = _read_cache(path)
    if cached is not None:
        cached.pop("_cached_on", None)
        cached["fundamentals_source"] = "cache"
        return cached

    try:
        payload = _request(
            f"{BASE_URL}/{symbol}/statements",
            {"token": _token()},
        )
    except Exception as exc:
        return {
            "fundamentals_available": False,
            "fundamentals_error": str(exc),
        }

    if not isinstance(payload, list) or not payload:
        return {
            "fundamentals_available": False,
            "fundamentals_error": "No statement data returned",
        }

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
        "fundamentals_source": "tiingo",
    }

    # PE is price-sensitive, so refresh it separately only when the
    # fundamental cache itself is refreshed. If the daily endpoint is
    # unavailable, keep the rest of the statement data.
    try:
        daily = _request(
            f"{BASE_URL}/{symbol}/daily",
            {"token": _token(), "columns": "date,peRatio"},
        )
        if isinstance(daily, list) and daily:
            result["pe"] = daily[-1].get("peRatio")
    except Exception as exc:
        result["fundamentals_error"] = str(exc)

    _save_cache(path, result)
    return result
