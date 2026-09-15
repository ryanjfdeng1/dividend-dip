import math


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def score_stock(row: dict) -> tuple:
    """V1.8 Quality Dip score.

    Maximum = 100:
      Quality 45, Valuation 20, Dip 30, Dividend 5.

    Dividend is an optional bonus; a low-yield company can still score highly.
    Missing fundamentals prevent a BUY signal because quality cannot be verified.
    """
    eps = _num(row.get("eps"))
    fcf = _num(row.get("free_cash_flow"))
    roe = _num(row.get("roe"))
    revenue_growth = _num(row.get("revenue_growth"))
    eps_growth = _num(row.get("eps_growth"))
    payout = _num(row.get("payout_ratio"))
    pe = _num(row.get("pe"))
    data_quality = row.get("data_quality")
    fundamental_age = _num(row.get("fundamental_age_days"))
    dd100 = _num(row.get("drawdown_100d"))
    dd60 = _num(row.get("drawdown_60d"))
    dd20 = _num(row.get("drawdown_20d"))
    rsi = _num(row.get("rsi_14"))
    yield_ = _num(row.get("dividend_yield"))
    div_growth = _num(row.get("dividend_growth"))

    # Quality: 45
    quality = 0
    if eps is not None:
        quality += 7 if eps > 0 else 0
    if fcf is not None:
        quality += 8 if fcf > 0 else 0

    if roe is not None:
        if roe >= 0.25: quality += 10
        elif roe >= 0.20: quality += 8
        elif roe >= 0.15: quality += 6
        elif roe >= 0.10: quality += 3

    if revenue_growth is not None:
        if revenue_growth >= 0.10: quality += 7
        elif revenue_growth >= 0.05: quality += 6
        elif revenue_growth >= 0: quality += 3

    if eps_growth is not None:
        if eps_growth >= 0.10: quality += 7
        elif eps_growth >= 0.05: quality += 6
        elif eps_growth >= 0: quality += 3

    if payout is not None and 0 <= payout <= 0.70:
        quality += 3
    quality = min(45, quality)

    # Valuation: 20. Low P/E is useful, but avoid rewarding negative/extreme P/E.
    valuation = 0
    if pe is not None and pe > 0:
        if pe <= 12: valuation = 20
        elif pe <= 15: valuation = 17
        elif pe <= 18: valuation = 14
        elif pe <= 22: valuation = 11
        elif pe <= 27: valuation = 7
        elif pe <= 35: valuation = 3

    # Dip: 30. Depth is combined with evidence of short-term selling pressure.
    dip = 0
    if dd100 is not None:
        if dd100 <= -0.30: dip += 15
        elif dd100 <= -0.25: dip += 14
        elif dd100 <= -0.20: dip += 12
        elif dd100 <= -0.15: dip += 9
        elif dd100 <= -0.10: dip += 6

    if dd60 is not None:
        if dd60 <= -0.20: dip += 7
        elif dd60 <= -0.15: dip += 6
        elif dd60 <= -0.10: dip += 4
        elif dd60 <= -0.05: dip += 2

    if rsi is not None:
        if rsi <= 30: dip += 8
        elif rsi <= 35: dip += 6
        elif rsi <= 40: dip += 3
    dip = min(30, dip)

    # Dividend: 5-point bonus only.
    dividend = 0
    if yield_ is not None:
        if yield_ >= 0.04: dividend += 2
        elif yield_ >= 0.02: dividend += 1
    if div_growth is not None and div_growth >= 0.05:
        dividend += 2
    elif div_growth is not None and div_growth >= 0:
        dividend += 1
    dividend = min(5, dividend)

    # Freshness guard: verified fundamentals must be current enough to support a BUY.\n    if fundamental_age is not None and fundamental_age > 450:\n        quality = 0\n        valuation = 0\n    total = min(100, quality + valuation + dip + dividend)

    fundamentals_available = bool(row.get("fundamentals_available"))
    risk_flags = []
    if fundamentals_available:
        if eps is not None and eps <= 0: risk_flags.append("NEGATIVE_EPS")
        if fcf is not None and fcf <= 0: risk_flags.append("NEGATIVE_FCF")
        if payout is not None and payout > 1.0: risk_flags.append("PAYOUT_GT_100")
        if eps_growth is not None and eps_growth < -0.10: risk_flags.append("EPS_DECLINE")
        if revenue_growth is not None and revenue_growth < -0.10: risk_flags.append("REVENUE_DECLINE")

    if not fundamentals_available:
        dip_type = "UNKNOWN"
    elif risk_flags:
        dip_type = "FUNDAMENTAL_RISK"
    elif dd100 is not None and dd100 <= -0.15 and quality >= 30:
        dip_type = "QUALITY_DIP"
    elif dd100 is not None and dd100 <= -0.10:
        dip_type = "NORMAL_DIP"
    else:
        dip_type = "NO_DIP"

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
    elif dip_type == "FUNDAMENTAL_RISK":
        signal = "RISK / PASS"
    elif dd100 is None or dd100 > -0.10:
        signal = "NO DIP"
    elif total >= 75:
        signal = "STRONG BUY CANDIDATE"
    elif total >= 60:
        signal = "BUY CANDIDATE"
    elif total >= 45:
        signal = "WATCH"
    else:
        signal = "HOLD"

    return (
        total, signal, dip, dividend, quality, valuation,
        dip_type, buy_stage, ",".join(risk_flags)
    )
