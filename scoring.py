import math

from config import FINANCIALS, BANKS


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def score_stock(row: dict) -> tuple:
    """V1.9 Quality Dip score. Maximum 100: Quality 45, Valuation 30, Dip 20, Dividend 5."""
    eps = _num(row.get("eps"))
    fcf = _num(row.get("free_cash_flow"))
    symbol = str(row.get("ticker", "")).upper()
    is_financial = symbol in FINANCIALS
    is_bank = symbol in BANKS
    roe = _num(row.get("roe"))
    revenue_growth = _num(row.get("revenue_growth"))
    eps_growth = _num(row.get("eps_growth"))
    payout = _num(row.get("payout_ratio"))
    pe = _num(row.get("pe"))
    fcf_yield = _num(row.get("fcf_yield"))
    data_quality = row.get("data_quality")
    fundamental_age = _num(row.get("fundamental_age_days"))
    dd100 = _num(row.get("drawdown_100d"))
    dd60 = _num(row.get("drawdown_60d"))
    rsi = _num(row.get("rsi_14"))
    yield_ = _num(row.get("dividend_yield"))
    div_growth = _num(row.get("dividend_growth"))

    quality = 0
    if eps is not None and eps > 0: quality += 7
    if not is_financial and fcf is not None and fcf > 0: quality += 8
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
    if payout is not None and 0 <= payout <= 0.70: quality += 3
    quality = min(45, quality)

    # V1.9: valuation gets 30 points. Non-financials use PE + FCF yield;
    # financials use PE only because industrial FCF yield is not meaningful.
    valuation = 0
    if pe is not None and pe > 0:
        if pe <= 12: valuation += 15
        elif pe <= 15: valuation += 13
        elif pe <= 18: valuation += 11
        elif pe <= 22: valuation += 9
        elif pe <= 27: valuation += 6
        elif pe <= 35: valuation += 3

    if is_financial:
        # Give financials the full valuation weight through PE/PB-style
        # earnings valuation rather than a misleading FCF yield.
        valuation = min(30, valuation * 2)
    elif fcf_yield is not None and fcf_yield > 0:
        if fcf_yield >= 0.08: valuation += 15
        elif fcf_yield >= 0.06: valuation += 13
        elif fcf_yield >= 0.05: valuation += 11
        elif fcf_yield >= 0.04: valuation += 9
        elif fcf_yield >= 0.03: valuation += 6
        elif fcf_yield >= 0.02: valuation += 3
    valuation = min(30, valuation)

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
    dip = min(20, round(dip * 20 / 30))

    dividend = 0
    if yield_ is not None:
        if yield_ >= 0.04: dividend += 2
        elif yield_ >= 0.02: dividend += 1
    if div_growth is not None:
        if div_growth >= 0.05: dividend += 2
        elif div_growth >= 0: dividend += 1
    dividend = min(5, dividend)

    # V1.9 freshness: recent quarterly data keeps full scoring power;
    # aging data is progressively discounted so stale fundamentals cannot
    # produce a high-quality candidate merely because the old numbers were good.
    freshness_factor = 1.0
    if fundamental_age is None:
        freshness_factor = 0.0
    elif fundamental_age > 365:
        freshness_factor = 0.0
    elif fundamental_age > 270:
        freshness_factor = 0.50
    elif fundamental_age > 210:
        freshness_factor = 0.75
    elif fundamental_age > 120:
        freshness_factor = 0.90

    quality = round(quality * freshness_factor)
    valuation = round(valuation * freshness_factor)

    fundamentals_verified = bool(row.get("fundamentals_available")) and data_quality in ("A", "B", "C", "D") and freshness_factor > 0
    if data_quality in ("D", "E") or freshness_factor == 0:
        fundamentals_verified = False

    total = min(100, quality + valuation + dip + dividend)

    risk_flags = []
    if fundamentals_verified:
        if eps is not None and eps <= 0: risk_flags.append("NEGATIVE_EPS")
        if not is_financial and fcf is not None and fcf <= 0: risk_flags.append("NEGATIVE_FCF")
        if payout is not None and payout > 1.0: risk_flags.append("PAYOUT_GT_100")
        if eps_growth is not None and eps_growth < -0.10: risk_flags.append("EPS_DECLINE")
        if revenue_growth is not None and revenue_growth < -0.10: risk_flags.append("REVENUE_DECLINE")
    if fundamental_age is not None and fundamental_age > 450:
        risk_flags.append("STALE_FUNDAMENTALS")

    if not fundamentals_verified:
        dip_type = "UNKNOWN"
    elif risk_flags:
        dip_type = "FUNDAMENTAL_RISK"
    elif dd100 is not None and dd100 <= -0.15 and quality >= 30:
        dip_type = "QUALITY_DIP"
    elif dd100 is not None and dd100 <= -0.10:
        dip_type = "NORMAL_DIP"
    else:
        dip_type = "NO_DIP"

    if dd100 is None or dd100 > -0.10: buy_stage = "OBSERVE"
    elif dd100 > -0.15: buy_stage = "WATCH_10%"
    elif dd100 > -0.20: buy_stage = "BUY_1"
    elif dd100 > -0.25: buy_stage = "BUY_2"
    elif dd100 > -0.30: buy_stage = "BUY_3"
    else: buy_stage = "DEEP_DIP_REVIEW"

    if not fundamentals_verified:
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

    return (total, signal, dip, dividend, quality, valuation, dip_type, buy_stage, ",".join(risk_flags))
