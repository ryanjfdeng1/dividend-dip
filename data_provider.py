import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.alphavantage.co/query"
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)


def _api_key() -> str:
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise RuntimeError(
            "ALPHAVANTAGE_API_KEY is not set. "
            "Create a .env file or export the variable before running."
        )
    return key


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}.csv"


def get_daily_history(symbol: str, use_cache: bool = True) -> pd.DataFrame:
    """Get daily OHLCV data from Alpha Vantage and cache it locally."""
    path = _cache_path(symbol)

    if use_cache and path.exists():
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        if not df.empty:
            return df.sort_index()

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",
        "apikey": _api_key(),
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
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
        raise RuntimeError(f"No daily data returned for {symbol}: {payload}")

    rows = []
    for date, values in series.items():
        rows.append({
            "Date": date,
            "Open": float(values["1. open"]),
            "High": float(values["2. high"]),
            "Low": float(values["3. low"]),
            "Close": float(values["4. close"]),
            "Volume": int(values["5. volume"]),
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    df.to_csv(path)

    # Be conservative with a free API when scanning multiple symbols manually.
    time.sleep(1.2)
    return df
