import math


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def score_stock(row: dict) -> tuple:
    """V1.5: identify quality dips and filter likely value traps.

    Maximum = 100:
      Dip 0-30, Dividend 0-15, Quality 0-30, Valuation 0-15, Trend 0-10.

    The score is deliberately conservative when fundamentals are missing.
    """
    dd100 = _num(row.get("drawdown_100d"))
    dd60 = _num(row.get("drawdown_60d"))
    dd20 = _num(row.get("drawdown_20d"))
    rsi = _num(row.get("rsi_14"))

    # 0-30: depth + short-term oversold condition.
    dip = 0
    if dd100 is not None:
        if dd100 <= -0.25: dip += 16
        elif dd100 <= -0.20: dip += 14
        elif dd100 <= -0.15: dip += 11
        elif dd100 <= -0.10: dip += 7
    if dd60 is not None:
        if dd60 <= -0.20: dip += 8
        elif dd60 <= -0.15: dip += 6
        elif dd60 <= -0.10: dip += 4
        elif dd60 <= -0.05: dip += 2
    if rsi is not None and rsi <= 35:
        dip += 6
    elif rsi is not None and rsi <= 40:
        dip += 3
    dip = min(30, dip)

    # 0-15: sustainable dividend rather than yield alone.
    dividend = 0
    yield_ = _num(row.get("dividend_yield"))
    growth = _num(row.get("dividend_growth"))
    payout = _num(row.get("payout_ratio"))
    if yield_ is not None:
        if yield_ >= 0.05: dividend += 7
        elif yield_ >= 0.04: dividend += 6
        elif yield_ >= 0.03: dividend += 5
        elif yield_ >= 0.02: dividend += 3
    if growth is not None:
        if growth >= 0.08: dividend += 5
        elif growth >= 0.04: dividend += 4
        elif growth >= 0: dividend += 2
    if payout is not None and payout > 0.80:
        dividend = max(0, dividend - 3)
    dividend = min(15, dividend)

    # 0-30: business quality.
    quality = 0
    eps = _num(row.get("eps"))
    fcf = _num(row.get("free_cash_flow"))
    roe = _num(row.get("roe"))
    revenue_growth = _num(row.get("revenue_growth"))
    eps_growth = _num(row.get("eps_growth"))

    if eps is not None and eps > 0: quality += 5
    if fcf is not None and fcf > 0: quality += 6
    if roe is not None:
        if roe >= 0.25: quality += 8
        elif roe >= 0.20: quality += 7
        elif roe >= 0.15: quality += 5
        elif roe >= 0.10: quality += 3
    if revenue_growth is not None:
        if revenue_growth >= 0.05: quality += 4
        elif revenue_growth >= 0: quality += 2
    if eps_growth is not None:
        if eps_growth >= 0.05: quality += 4
        elif eps_growth >= 0: quality += 2
    if payout is not None and 0 <= payout <= 0.70: quality += 2
    quality = min(30, quality)

    # 0-15: valuation. P/E is now material, but extreme/negative P/E gets no credit.
    valuation = 0
    pe = _num(row.get("pe"))
    if pe is not None and pe > 0:
        if pe <= 12: valuation = 15
        elif pe <= 15: valuation = 13
        elif pe <= 18: valuation = 11
        elif pe <= 22: valuation = 8
        elif pe <= 27: valuation = 5
        elif pe <= 35: valuation = 2

    # 0-10: trend confirmation. Being below 200DMA is not an automatic rejection.
    trend = 0
    if row.get("above_200dma") is True:
        trend = 10
    elif row.get("above_200dma") is False:
        trend = 4

    total = min(100, dip + dividend + quality + valuation + trend)

    fundamentals_available = bool(row.get("fundamentals_available"))
    risk_flags = []
    if fundamentals_available:
        if eps is not None and eps <= 0: risk_flags.append("NEGATIVE_EPS")
        if fcf is not None and fcf <= 0: risk_flags.append("NEGATIVE_FCF")
        if payout is not None and payout > 1.0: risk_flags.append("PAYOUT_GT_100")
        if eps_growth is not None and eps_growth < -0.10: risk_flags.append("EPS_DECLINE")
        if revenue_growth is not None and revenue_growth < -0.10: risk_flags.append("REVENUE_DECLINE")

    # Classify the reason for the drawdown.
    if not fundamentals_available:
        dip_type = "UNKNOWN"
    elif risk_flags:
        dip_type = "FUNDAMENTAL_RISK"
    elif dd100 is not None and dd100 <= -0.15 and quality >= 20:
        dip_type = "QUALITY_DIP"
    elif dd100 is not None and dd100 <= -0.10:
        dip_type = "NORMAL_DIP"
    else:
        dip_type = "NO_DIP"

    # Staged entry based on distance from the 100D high.
    if dd100 is None or dd100 > -0.10:
        buy_stage = "OBSERVE"
    elif dd100 > -0.15:
        buy_stage = "WATCH_10%"
    elif dd100 > -0.20:
        buy_stage = "BUY_1"
    elif dd100 > -0.25:
        buy_stage = "BUY_2"
    elif dd100 > -0.30:
        buy_stage = "BUY_3"
    else:
        buy_stage = "DEEP_DIP_REVIEW"

    if not fundamentals_available:
        signal = "DATA INCOMPLETE"
    elif "FUNDAMENTAL_RISK" == dip_type:
        signal = "RISK / PASS"
    elif total >= 70:
        signal = "STRONG BUY CANDIDATE"
    elif total >= 55:
        signal = "BUY CANDIDATE"
    elif total >= 40:
        signal = "WATCH"
    else:
        signal = "HOLD"

    return (
        total, signal, dip, dividend, quality, valuation, trend,
        dip_type, buy_stage, ",".join(risk_flags)
    )
