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
    if avg_loss.iloc[-1] == 0 and avg_gain.iloc[-1] > 0:
        return 100.0
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if pd.notna(value) else np.nan


def calculate_dividend_metrics(history: pd.DataFrame, current: float) -> dict:
    dividends = history.get("Dividend")
    if dividends is None:
        return {"dividend_yield": np.nan, "dividend_growth": np.nan, "annual_dividend": np.nan}

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
        "annual_dividend": float(last_year),
    }


def calculate_metrics(history: pd.DataFrame, fundamentals: Optional[dict] = None) -> dict:
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if len(close) < max(RSI_PERIOD + 1, LOOKBACK_20D):
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

    fundamentals = fundamentals or {}
    result.update({
        "fundamentals_available": bool(fundamentals.get("fundamentals_available")),
        "fundamentals_source": fundamentals.get("fundamentals_source"),
        "data_quality": fundamentals.get("data_quality"),
        "fundamentals_error": fundamentals.get("fundamentals_error"),
        "eps": fundamentals.get("eps", np.nan),
        "free_cash_flow": fundamentals.get("free_cash_flow", np.nan),
        "roe": fundamentals.get("roe", np.nan),
        "payout_ratio": fundamentals.get("payout_ratio", np.nan),
        "pe": fundamentals.get("pe", np.nan),
        "revenue_growth": fundamentals.get("revenue_growth", np.nan),
        "eps_growth": fundamentals.get("eps_growth", np.nan),
        "revenue": fundamentals.get("revenue", np.nan),
        "net_income": fundamentals.get("net_income", np.nan),
        "total_assets": fundamentals.get("total_assets", np.nan),
        "equity": fundamentals.get("equity", np.nan),
        "debt": fundamentals.get("debt", np.nan),
        "shares_outstanding": fundamentals.get("shares_outstanding", np.nan),
        "fundamental_date": fundamentals.get("fundamental_date"),
        "fundamental_age_days": fundamentals.get("fundamental_age_days", np.nan),
        "latest_quarter_date": fundamentals.get("latest_quarter_date"),
        "latest_filing_date": fundamentals.get("latest_filing_date"),
        "revenue_cagr_3y": fundamentals.get("revenue_cagr_3y", np.nan),
        "revenue_cagr_5y": fundamentals.get("revenue_cagr_5y", np.nan),
        "eps_cagr_3y": fundamentals.get("eps_cagr_3y", np.nan),
        "eps_cagr_5y": fundamentals.get("eps_cagr_5y", np.nan),
        "fcf_cagr_3y": fundamentals.get("fcf_cagr_3y", np.nan),
        "fcf_cagr_5y": fundamentals.get("fcf_cagr_5y", np.nan),
        "operating_margin": fundamentals.get("operating_margin", np.nan),
        "margin_change_3y": fundamentals.get("margin_change_3y", np.nan),
        "margin_change_5y": fundamentals.get("margin_change_5y", np.nan),
        "debt_change_3y": fundamentals.get("debt_change_3y", np.nan),
        "debt_change_5y": fundamentals.get("debt_change_5y", np.nan),
        "roic_proxy": fundamentals.get("roic_proxy", np.nan),
    })

    # V1.9 valuation metrics. FCF yield is only used for non-financials;
    # bank/financial cash-flow structures are not comparable to industrial FCF.
    shares = result["shares_outstanding"]
    fcf = result["free_cash_flow"]
    if pd.notna(shares) and shares > 0 and pd.notna(fcf) and fcf > 0:
        market_cap = current * shares
        if market_cap > 0:
            result["fcf_yield"] = float(fcf / market_cap)
    else:
        result["fcf_yield"] = np.nan

    # Derive payout ratio from SEC EPS + trailing annual dividends when the
    # provider does not supply it directly.
    eps = result["eps"]
    annual_dividend = result["annual_dividend"]
    if pd.isna(result["payout_ratio"]) and pd.notna(eps) and eps > 0 and pd.notna(annual_dividend):
        result["payout_ratio"] = float(annual_dividend / eps)

    # Current P/E is intentionally calculated from price and annual EPS.
    if pd.isna(result["pe"]) and pd.notna(eps) and eps > 0:
        result["pe"] = float(current / eps)

    return result
