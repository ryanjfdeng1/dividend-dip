import numpy as np
import pandas as pd
from typing import Optional

from config import LOOKBACK_DAYS, LOOKBACK_60D, LOOKBACK_20D, LOOKBACK_252D, SMA_LONG, RSI_PERIOD


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
    high_20d = float(close.tail(LOOKBACK_20D).max())
    high_60d = float(close.tail(LOOKBACK_60D).max())
    high_100d = float(close.tail(LOOKBACK_DAYS).max())
    high_252d = float(close.tail(LOOKBACK_252D).max())

    lookback_3y = min(len(close), 756)
    high_3y = float(close.tail(lookback_3y).max())
    price_3y_ago = float(close.iloc[-lookback_3y])
    drawdown_3y = current / high_3y - 1
    return_3y = current / price_3y_ago - 1
    if return_3y <= -0.30:
        trend_regime = "MULTI_YEAR_DECLINE"
    elif return_3y < 0:
        trend_regime = "LONG_TERM_DOWNTREND"
    elif drawdown_3y <= -0.20:
        trend_regime = "NORMAL_CORRECTION"
    else:
        trend_regime = "HEALTHY_TREND"

    sma_200 = np.nan
    if len(close) >= SMA_LONG:
        sma_200 = float(close.rolling(SMA_LONG).mean().iloc[-1])

    result = {
        "price": current,
        "high_20d": high_20d,
        "high_60d": high_60d,
        "high_100d": high_100d,
        "high_252d": high_252d,
        "drawdown_20d": current / high_20d - 1,
        "drawdown_60d": current / high_60d - 1,
        "drawdown_100d": current / high_100d - 1,
        "drawdown_252d": current / high_252d - 1,
        "high_3y": high_3y,
        "drawdown_3y": drawdown_3y,
        "return_3y": return_3y,
        "trend_regime": trend_regime,
        "sma_200": sma_200,
        "above_200dma": bool(current > sma_200) if pd.notna(sma_200) else None,
        "distance_200dma": (current / sma_200 - 1) if pd.notna(sma_200) and sma_200 > 0 else np.nan,
        "split_adjusted": bool(history.get("SplitAdjusted", pd.Series(False, index=history.index)).any()),
        "split_adjustment_factor": float(history.get("SplitAdjustmentFactor", pd.Series(1.0, index=history.index)).iloc[0]),
        "rsi_14": calculate_rsi(close),
        **calculate_dividend_metrics(history, current),
    }

    fundamentals = fundamentals or {}
    result.update({
        "fundamentals_available": bool(fundamentals.get("fundamentals_available")),
        "fundamentals_source": fundamentals.get("fundamentals_source"),
        "data_quality": fundamentals.get("data_quality"),
        "data_status": fundamentals.get("data_status"),
        "fundamentals_error": fundamentals.get("fundamentals_error"),
        "eps": fundamentals.get("eps", np.nan),
        "free_cash_flow": fundamentals.get("free_cash_flow", np.nan),
        "roe": fundamentals.get("roe", np.nan),
        "payout_ratio": fundamentals.get("payout_ratio", np.nan),
        "pe": fundamentals.get("pe", np.nan),
        "revenue_growth": fundamentals.get("revenue_growth", np.nan),
        "eps_growth": fundamentals.get("eps_growth", np.nan),
        "fcf_growth": fundamentals.get("fcf_growth", np.nan),
        "revenue": fundamentals.get("revenue", np.nan),
        "net_income": fundamentals.get("net_income", np.nan),
        "total_assets": fundamentals.get("total_assets", np.nan),
        "equity": fundamentals.get("equity", np.nan),
        "debt": fundamentals.get("debt", np.nan),
        "debt_to_equity": fundamentals.get("debt_to_equity", np.nan),
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

    shares = result["shares_outstanding"]
    fcf = result["free_cash_flow"]
    if pd.notna(shares) and shares > 0 and pd.notna(fcf) and fcf > 0:
        market_cap = current * shares
        if market_cap > 0:
            result["fcf_yield"] = float(fcf / market_cap)
    else:
        result["fcf_yield"] = np.nan

    debt = result["debt"]
    equity = result["equity"]
    if pd.isna(result["debt_to_equity"]) and pd.notna(debt) and pd.notna(equity) and equity > 0:
        result["debt_to_equity"] = float(debt / equity)

    eps = result["eps"]
    annual_dividend = result["annual_dividend"]
    if pd.isna(result["payout_ratio"]) and pd.notna(eps) and eps > 0 and pd.notna(annual_dividend):
        result["payout_ratio"] = float(annual_dividend / eps)

    # FCF is a company-level amount while annual_dividend is per share.
    # Convert dividends to total cash paid before calculating FCF payout.
    shares = result["shares_outstanding"]
    if (
        pd.notna(fcf)
        and fcf > 0
        and pd.notna(annual_dividend)
        and pd.notna(shares)
        and shares > 0
    ):
        total_dividends = annual_dividend * shares
        result["fcf_payout_ratio"] = float(total_dividends / fcf)
    else:
        result["fcf_payout_ratio"] = np.nan

    payout = result["payout_ratio"]
    fcf_payout = result["fcf_payout_ratio"]
    div_growth = result["dividend_growth"]
    if pd.notna(payout) and payout <= 0.60 and pd.notna(fcf_payout) and fcf_payout <= 0.60:
        result["dividend_safety"] = "STRONG"
    elif pd.notna(payout) and payout <= 0.80 and (pd.isna(fcf_payout) or fcf_payout <= 0.80):
        result["dividend_safety"] = "OK"
    elif (pd.notna(payout) and payout > 1.00) or (pd.notna(fcf_payout) and fcf_payout > 1.00):
        result["dividend_safety"] = "REVIEW"
    elif pd.notna(div_growth) and div_growth < -0.05:
        result["dividend_safety"] = "REVIEW"
    else:
        result["dividend_safety"] = "UNKNOWN"

    if pd.isna(result["pe"]) and pd.notna(eps) and eps > 0:
        result["pe"] = float(current / eps)

    return result
