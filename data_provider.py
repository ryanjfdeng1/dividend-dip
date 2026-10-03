import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ALPHA_URL = "https://www.alphavantage.co/query"
TIINGO_URL = "https://api.tiingo.com/tiingo/daily"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)

# Keep a safety margin below Tiingo Starter's published 50 requests/hour.
# See: https://www.tiingo.com/account/billing/pricing
TIINGO_HOURLY_BUDGET = int(os.getenv("TIINGO_HOURLY_BUDGET", "45"))
RATE_STATE = CACHE_DIR / ".tiingo_rate_state.json"


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}_price.csv"


def _alpha_key() -> str:
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY is not set.")
    return key


def _tiingo_key() -> str:
    key = os.getenv("TIINGO_API_KEY")
    if not key:
        raise RuntimeError("TIINGO_API_KEY is not set.")
    return key


def _read_cache(symbol: str) -> pd.DataFrame:
    path = _cache_path(symbol)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        return df.sort_index()
    except Exception:
        return pd.DataFrame()


def _load_rate_state() -> dict:
    try:
        state = json.loads(RATE_STATE.read_text())
        if state.get("hour") == int(time.time() // 3600):
            return state
    except Exception:
        pass
    return {"hour": int(time.time() // 3600), "requests": 0}


def _consume_tiingo_request() -> None:
    state = _load_rate_state()
    if state["requests"] >= TIINGO_HOURLY_BUDGET:
        raise RuntimeError(
            f"Tiingo hourly safety budget reached ({TIINGO_HOURLY_BUDGET}). "
            "Cached data will still be used; rerun after the next hour."
        )
    state["requests"] += 1
    RATE_STATE.write_text(json.dumps(state))


def _request_tiingo(symbol: str):
    start = date.today() - timedelta(days=1200)
    _consume_tiingo_request()

    try:
        response = requests.get(
            f"{TIINGO_URL}/{symbol}/prices",
            params={
                "startDate": start.isoformat(),
                "token": _tiingo_key(),
                "format": "json",
            },
            timeout=30,
        )
        if response.status_code == 429:
            raise RuntimeError(f"Tiingo rate limited (429) for {symbol}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Tiingo request failed for {symbol}: {exc}") from exc


def _apply_split_adjustment(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize historical OHLC prices to the latest share basis.

    Tiingo provides splitFactor on the ex-date. A forward split such as
    KLAC's 10-for-1 split has splitFactor=10, so prices before that date
    must be divided by 10 for a continuous price series.
    """
    df = df.copy()
    if "SplitFactor" not in df.columns:
        df["SplitFactor"] = 1.0

    factors = pd.to_numeric(df["SplitFactor"], errors="coerce").fillna(1.0)
    factors = factors.where(factors > 0, 1.0)

    # Product of all split factors strictly after each observation.
    # This keeps the ex-date itself on the new share basis.
    future_factor = factors.iloc[::-1].cumprod().iloc[::-1] / factors
    future_factor = future_factor.replace([float("inf"), -float("inf")], 1.0)

    df["CloseRaw"] = pd.to_numeric(df["Close"], errors="coerce")
    df["SplitAdjustmentFactor"] = future_factor

    for column in ("Open", "High", "Low", "Close"):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            df[column] = values / future_factor

    df["SplitAdjusted"] = future_factor.ne(1.0)
    return df


def _get_tiingo_history(symbol: str) -> pd.DataFrame:
    cached = _read_cache(symbol)

    # Price history is refreshed at most once per trading day.
    today = pd.Timestamp(date.today())
    if (
        not cached.empty
        and cached.index.max() >= today - pd.Timedelta(days=4)
        and len(cached) >= 700
        and "SplitFactor" in cached.columns
    ):
        return _apply_split_adjustment(cached)

    payload = _request_tiingo(symbol)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"No Tiingo daily data returned for {symbol}")

    rows = []
    for item in payload:
        rows.append({
            "Date": item["date"][:10],
            "Open": float(item["open"]),
            "High": float(item["high"]),
            "Low": float(item["low"]),
            "Close": float(item["close"]),
            "Volume": int(item["volume"]),
            "AdjClose": float(item.get("adjClose", item["close"])),
            "Dividend": float(item.get("divCash", 0) or 0),
            "SplitFactor": float(item.get("splitFactor", 1.0) or 1.0),
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df = _apply_split_adjustment(df)
    df.to_csv(_cache_path(symbol))
    return df


def _get_alpha_history(symbol: str) -> pd.DataFrame:
    cached = _read_cache(symbol)
    if not cached.empty:
        if "SplitFactor" in cached.columns:
            return _apply_split_adjustment(cached)
        raise RuntimeError(
            f"Cached Alpha Vantage history for {symbol} has no split metadata. "
            "Use Tiingo price data for split-safe historical calculations."
        )

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "full",
        "apikey": _alpha_key(),
    }
    response = requests.get(ALPHA_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if "Note" in payload:
        raise RuntimeError(f"Alpha Vantage rate limit: {payload['Note']}")
    if "Information" in payload:
        raise RuntimeError(f"Alpha Vantage response: {payload['Information']}")
    if "Error Message" in payload:
        raise RuntimeError(f"Alpha Vantage error: {payload['Error Message']}")

    series = payload.get("Time Series (Daily)")
    if not series:
        raise RuntimeError(f"No daily data returned for {symbol}")

    rows = [{
        "Date": date_,
        "Open": float(v["1. open"]),
        "High": float(v["2. high"]),
        "Low": float(v["3. low"]),
        "Close": float(v["4. close"]),
        "Volume": int(v["5. volume"]),
    } for date_, v in series.items()]

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    raise RuntimeError(
        f"Alpha Vantage daily data for {symbol} lacks split metadata. "
        "Use Tiingo price data for split-safe historical calculations."
    )


def get_daily_history(symbol: str, use_cache: bool = True) -> pd.DataFrame:
    """Return a split-normalized price series; Tiingo is required."""
    if os.getenv("TIINGO_API_KEY"):
        return _get_tiingo_history(symbol)

    raise RuntimeError(
        "Split-safe price history requires TIINGO_API_KEY. "
        "Alpha Vantage TIME_SERIES_DAILY does not provide split metadata."
    )
