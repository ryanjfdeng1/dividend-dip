import numpy as np
import pandas as pd
from typing import Optional

from config import LOOKBACK_DAYS, LOOKBACK_60D, LOOKBACK_20D, SMA_LONG, RSI_PERIOD


def calculate_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if pd.notna(value) else np.nan


def calculate_dividend_metrics(history: pd.DataFrame, current: float) -> dict:
    dividends = history.get("Dividend")
    if dividends is None:
        return {"dividend_yield": np.nan, "dividend_growth": np.nan}

    dividends = pd.to_numeric(dividends, errors="coerce").fillna(0)
    dates = dividends.index
    end = dates[-1]
    last_year = dividends[(dates > end - pd.Timedelta(days=365)) & (dates <= end)].sum()
    prior_year = dividends[
        (dates > end - pd.Timedelta(days=730))
        & (dates <= end - pd.Timedelta(days=365))
    ].sum()

    growth = np.nan
    if prior_year > 0:
        growth = float(last_year / prior_year - 1)

    return {
        "dividend_yield": float(last_year / current) if current > 0 else np.nan,
        "dividend_growth": growth,
    }


def calculate_metrics(history: pd.DataFrame, fundamentals: Optional[dict] = None) -> dict:
    close = history["Close"].dropna()

    if len(close) < RSI_PERIOD + 1:
        raise ValueError(f"Not enough price history: {len(close)} trading days")

    current = float(close.iloc[-1])
    high_100d = float(close.tail(LOOKBACK_DAYS).max())
    high_60d = float(close.tail(LOOKBACK_60D).max())
    high_20d = float(close.tail(LOOKBACK_20D).max())

    sma_200 = np.nan
    if len(close) >= SMA_LONG:
        sma_200 = float(close.rolling(SMA_LONG).mean().iloc[-1])

    result = {
        "price": current,
        "high_100d": high_100d,
        "drawdown_100d": current / high_100d - 1,
        "drawdown_60d": current / high_60d - 1,
        "drawdown_20d": current / high_20d - 1,
        "sma_200": sma_200,
        "above_200dma": bool(current > sma_200) if pd.notna(sma_200) else None,
        "rsi_14": calculate_rsi(close),
        **calculate_dividend_metrics(history, current),
    }

    if fundamentals:
        result.update({
            "fundamentals_available": fundamentals.get("fundamentals_available", False),
            "eps": fundamentals.get("eps", np.nan),
            "free_cash_flow": fundamentals.get("free_cash_flow", np.nan),
            "roe": fundamentals.get("roe", np.nan),
            "payout_ratio": fundamentals.get("payout_ratio", np.nan),
            "pe": fundamentals.get("pe", np.nan),
            "revenue_growth": fundamentals.get("revenue_growth", np.nan),
            "eps_growth": fundamentals.get("eps_growth", np.nan),
        })
    else:
        result["fundamentals_available"] = False

    return result
