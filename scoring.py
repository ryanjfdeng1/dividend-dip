import math


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def score_stock(row: dict) -> tuple:
    """V1.4: score dip, dividend quality, business quality and valuation.

    Maximum = 100:
      Dip 0-30, Dividend 0-20, Quality 0-30, Valuation 0-10, Trend 0-10.
    Missing fundamentals are never treated as a positive signal.
    """
    dip = 0
    dd100 = _num(row.get("drawdown_100d"))
    dd60 = _num(row.get("drawdown_60d"))
    dd20 = _num(row.get("drawdown_20d"))
    rsi = _num(row.get("rsi_14"))

    if dd100 is not None:
        if dd100 <= -0.20: dip += 15
        elif dd100 <= -0.15: dip += 12
        elif dd100 <= -0.10: dip += 8
    if dd60 is not None:
        if dd60 <= -0.15: dip += 8
        elif dd60 <= -0.10: dip += 6
        elif dd60 <= -0.05: dip += 3
    if dd20 is not None and dd20 <= -0.05:
        dip += 3
    if rsi is not None and rsi <= 35:
        dip += 4

    dividend = 0
    yield_ = _num(row.get("dividend_yield"))
    growth = _num(row.get("dividend_growth"))
    if yield_ is not None:
        if yield_ >= 0.04: dividend += 10
        elif yield_ >= 0.03: dividend += 8
        elif yield_ >= 0.02: dividend += 5
    if growth is not None:
        if growth >= 0.08: dividend += 10
        elif growth >= 0.04: dividend += 7
        elif growth >= 0: dividend += 4

    quality = 0
    eps = _num(row.get("eps"))
    fcf = _num(row.get("free_cash_flow"))
    roe = _num(row.get("roe"))
    payout = _num(row.get("payout_ratio"))
    revenue_growth = _num(row.get("revenue_growth"))
    eps_growth = _num(row.get("eps_growth"))

    if eps is not None and eps > 0:
        quality += 5
    if fcf is not None and fcf > 0:
        quality += 5
    if roe is not None:
        if roe >= 0.20: quality += 8
        elif roe >= 0.15: quality += 6
        elif roe >= 0.10: quality += 3
    if payout is not None and 0 <= payout <= 0.70:
        quality += 5
    if revenue_growth is not None and revenue_growth > 0:
        quality += 3
    if eps_growth is not None and eps_growth > 0:
        quality += 4

    valuation = 0
    pe = _num(row.get("pe"))
    if pe is not None and pe > 0:
        if pe <= 15: valuation += 10
        elif pe <= 20: valuation += 7
        elif pe <= 25: valuation += 4

    trend = 0
    if row.get("above_200dma") is True:
        trend = 10
    elif row.get("above_200dma") is False:
        trend = 3

    total = min(100, dip + dividend + quality + valuation + trend)

    fundamentals_available = bool(row.get("fundamentals_available"))
    if not fundamentals_available:
        signal = "DATA INCOMPLETE"
    elif total >= 70:
        signal = "STRONG BUY CANDIDATE"
    elif total >= 55:
        signal = "BUY CANDIDATE"
    elif total >= 40:
        signal = "WATCH"
    else:
        signal = "HOLD"

    return total, signal, dip, dividend, quality, valuation, trend
