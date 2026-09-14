import os
import time
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import requests

ALPHA_URL = "https://www.alphavantage.co/query"
TIINGO_URL = "https://api.tiingo.com/tiingo/daily"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)


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


def _request_tiingo(symbol: str):
    start = date.today() - timedelta(days=800)
    last = None
    for attempt in range(4):
        try:
            response = requests.get(
                f"{TIINGO_URL}/{symbol}/prices",
                params={"startDate": start.isoformat(), "token": _tiingo_key()},
                timeout=30,
            )
            if response.status_code == 429:
                last = RuntimeError(f"Tiingo rate limited (429) for {symbol}")
                time.sleep(2 ** attempt * 2)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise last or RuntimeError(f"Tiingo request failed for {symbol}")


def _get_tiingo_history(symbol: str) -> pd.DataFrame:
    cached = _read_cache(symbol)

    # Refresh when the cache does not contain a recent trading-day observation.
    today = pd.Timestamp(date.today())
    if not cached.empty and cached.index.max() >= today - pd.Timedelta(days=4) and len(cached) >= 200:
        return cached

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
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df.to_csv(_cache_path(symbol))
    time.sleep(0.25)
    return df


def _get_alpha_history(symbol: str) -> pd.DataFrame:
    cached = _read_cache(symbol)
    if not cached.empty:
        return cached

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
    df.to_csv(_cache_path(symbol))
    time.sleep(1.2)
    return df


def get_daily_history(symbol: str, use_cache: bool = True) -> pd.DataFrame:
    """Prefer Tiingo; use cached data and retry on transient rate limits."""
    if os.getenv("TIINGO_API_KEY"):
        return _get_tiingo_history(symbol)
    return _get_alpha_history(symbol)
