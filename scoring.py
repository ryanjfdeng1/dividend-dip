import math

from config import FINANCIALS, BANKS


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def score_stock(row: dict) -> tuple:
    """V2.7 Quality Dip score with explicit fundamental-data verification.

    Base score: Quality 30 + Long-term business trend 15 + Valuation 30
    + Dip 20 + Dividend 5 = 100 points.

    Structural risk is reported separately and can reduce the final score by
    up to 20 points. Only data_status == "OK" rows receive a numeric total.
    """
    eps = _num(row.get("eps"))
    fcf = _num(row.get("free_cash_flow"))
    symbol = str(row.get("ticker", "")).upper()
    is_financial = symbol in FINANCIALS
    roe = _num(row.get("roe"))
    revenue_growth = _num(row.get("revenue_growth"))
    eps_growth = _num(row.get("eps_growth"))
    fcf_growth = _num(row.get("fcf_growth"))
    payout = _num(row.get("payout_ratio"))
    pe = _num(row.get("pe"))
    fcf_yield = _num(row.get("fcf_yield"))
    data_quality = row.get("data_quality")
    data_status = row.get("data_status")
    fundamental_age = _num(row.get("fundamental_age_days"))
    dd100 = _num(row.get("drawdown_100d"))
    dd60 = _num(row.get("drawdown_60d"))
    rsi = _num(row.get("rsi_14"))
    yield_ = _num(row.get("dividend_yield"))
    div_growth = _num(row.get("dividend_growth"))
    debt = _num(row.get("debt"))
    equity = _num(row.get("equity"))
    revenue_cagr_3y = _num(row.get("revenue_cagr_3y"))
    revenue_cagr_5y = _num(row.get("revenue_cagr_5y"))
    eps_cagr_3y = _num(row.get("eps_cagr_3y"))
    eps_cagr_5y = _num(row.get("eps_cagr_5y"))
    fcf_cagr_3y = _num(row.get("fcf_cagr_3y"))
    fcf_cagr_5y = _num(row.get("fcf_cagr_5y"))
    margin_change_3y = _num(row.get("margin_change_3y"))
    margin_change_5y = _num(row.get("margin_change_5y"))
    debt_change_3y = _num(row.get("debt_change_3y"))
    debt_change_5y = _num(row.get("debt_change_5y"))
    roic_proxy = _num(row.get("roic_proxy"))
    debt_to_equity = _num(row.get("debt_to_equity"))
    fcf_payout_ratio = _num(row.get("fcf_payout_ratio"))
    dividend_safety = row.get("dividend_safety")

    quality = 0
    if eps is not None and eps > 0:
        quality += 5
    if not is_financial and fcf is not None and fcf > 0:
        quality += 6
    if roe is not None:
        if roe >= 0.25:
            quality += 5
        elif roe >= 0.20:
            quality += 5
        elif roe >= 0.15:
            quality += 4
        elif roe >= 0.10:
            quality += 2
    if revenue_growth is not None:
        if revenue_growth >= 0.10:
            quality += 7
        elif revenue_growth >= 0.05:
            quality += 6
        elif revenue_growth >= 0:
            quality += 2
    if eps_growth is not None:
        if eps_growth >= 0.10:
            quality += 7
        elif eps_growth >= 0.05:
            quality += 6
        elif eps_growth >= 0:
            quality += 3
    if payout is not None and 0 <= payout <= 0.70:
        quality += 3
    quality = min(30, quality)



    # V2.1 long-term business trend: 15 points.
    # This is deliberately separate from the one-year quality metrics.
    trend_score = 0
    trend_components = []

    def _cagr_points(value, strong, good, neutral):
        if value is None:
            return 0
        if value >= strong:
            return 3
        if value >= good:
            return 2
        if value >= neutral:
            return 1
        return 0

    trend_score += _cagr_points(revenue_cagr_5y, 0.08, 0.03, 0.0)
    trend_score += _cagr_points(eps_cagr_5y, 0.10, 0.05, 0.0)
    trend_score += _cagr_points(fcf_cagr_5y, 0.10, 0.05, 0.0)
    if roic_proxy is not None:
        if roic_proxy >= 0.15:
            trend_score += 3
        elif roic_proxy >= 0.10:
            trend_score += 2
        elif roic_proxy >= 0.06:
            trend_score += 1
    if margin_change_5y is not None:
        if margin_change_5y >= 0.10:
            trend_score += 3
        elif margin_change_5y >= 0:
            trend_score += 2
        elif margin_change_5y > -0.10:
            trend_score += 1

    # Cap at 15. Missing long-term data earns no points rather than a penalty.
    trend_score = min(15, trend_score)

    valuation = 0
    if pe is not None and pe > 0:
        if pe <= 12:
            valuation += 15
        elif pe <= 15:
            valuation += 13
        elif pe <= 18:
            valuation += 11
        elif pe <= 22:
            valuation += 9
        elif pe <= 27:
            valuation += 6
        elif pe <= 35:
            valuation += 3

    if is_financial:
        valuation = min(30, valuation * 2)
    elif fcf_yield is not None and fcf_yield > 0:
        if fcf_yield >= 0.08:
            valuation += 15
        elif fcf_yield >= 0.06:
            valuation += 13
        elif fcf_yield >= 0.05:
            valuation += 11
        elif fcf_yield >= 0.04:
            valuation += 9
        elif fcf_yield >= 0.03:
            valuation += 6
        elif fcf_yield >= 0.02:
            valuation += 3
    valuation = min(30, valuation)

    dip = 0
    if dd100 is not None:
        if dd100 <= -0.30:
            dip += 15
        elif dd100 <= -0.25:
            dip += 14
        elif dd100 <= -0.20:
            dip += 12
        elif dd100 <= -0.15:
            dip += 9
        elif dd100 <= -0.10:
            dip += 6
    if dd60 is not None:
        if dd60 <= -0.20:
            dip += 7
        elif dd60 <= -0.15:
            dip += 6
        elif dd60 <= -0.10:
            dip += 4
        elif dd60 <= -0.05:
            dip += 2
    if rsi is not None:
        if rsi <= 30:
            dip += 8
        elif rsi <= 35:
            dip += 6
        elif rsi <= 40:
            dip += 3
    dip = min(20, round(dip * 20 / 30))

    dividend = 0
    if yield_ is not None:
        if yield_ >= 0.04:
            dividend += 2
        elif yield_ >= 0.02:
            dividend += 1
    if div_growth is not None:
        if div_growth >= 0.05:
            dividend += 2
        elif div_growth >= 0:
            dividend += 1
    dividend = min(5, dividend)

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

    fundamentals_verified = (
        data_status == "OK"
        and bool(row.get("fundamentals_available"))
        and data_quality in ("A", "B", "C", "D")
        and freshness_factor > 0
    )
    if data_quality in ("D", "E") or freshness_factor == 0:
        fundamentals_verified = False

    risk_flags = []
    if fundamentals_verified:
        if eps is not None and eps <= 0:
            risk_flags.append("NEGATIVE_EPS")
        if not is_financial and fcf is not None and fcf <= 0:
            risk_flags.append("NEGATIVE_FCF")
        if payout is not None and payout > 1.0:
            risk_flags.append("PAYOUT_GT_100")

        if eps_growth is not None and eps_growth < -0.10:
            risk_flags.append("EPS_DECLINE")
        elif eps_growth is not None and eps_growth < -0.05:
            risk_flags.append("EPS_SLOWDOWN")

        if revenue_growth is not None and revenue_growth < -0.10:
            risk_flags.append("REVENUE_DECLINE")
        elif revenue_growth is not None and revenue_growth < -0.05:
            risk_flags.append("REVENUE_SLOWDOWN")

        if not is_financial and debt is not None and equity is not None and equity > 0:
            debt_to_equity = debt / equity
            if debt_to_equity > 3.0:
                risk_flags.append("HIGH_LEVERAGE")
            elif debt_to_equity > 2.0:
                risk_flags.append("ELEVATED_LEVERAGE")

    if fundamental_age is not None:
        if fundamental_age > 365:
            risk_flags.append("VERY_STALE_FUNDAMENTALS")
        elif fundamental_age > 270:
            risk_flags.append("STALE_FUNDAMENTALS")
        elif fundamental_age > 210:
            risk_flags.append("AGING_FUNDAMENTALS")

    structural_penalty = 0
    structural_flags = []

    if fundamentals_verified:
        if revenue_growth is not None:
            if revenue_growth < -0.10:
                structural_penalty += 7
                structural_flags.append("REVENUE_TREND")
            elif revenue_growth < -0.05:
                structural_penalty += 4
                structural_flags.append("REVENUE_TREND")

        if eps_growth is not None:
            if eps_growth < -0.10:
                structural_penalty += 7
                structural_flags.append("EPS_TREND")
            elif eps_growth < -0.05:
                structural_penalty += 4
                structural_flags.append("EPS_TREND")

        if not is_financial and fcf is not None and fcf <= 0:
            structural_penalty += 6
            structural_flags.append("FCF_TREND")

        if eps is not None and eps <= 0:
            structural_penalty += 6
            structural_flags.append("EARNINGS_TREND")

        if not is_financial and debt is not None and equity is not None and equity > 0:
            debt_to_equity = debt / equity
            if debt_to_equity > 3.0:
                structural_penalty += 4
                structural_flags.append("LEVERAGE")

        # Long-term deterioration signals. These complement, rather than
        # replace, the existing one-year checks.
        if revenue_cagr_5y is not None and revenue_cagr_5y < -0.02:
            structural_penalty += 4
            structural_flags.append("REVENUE_5Y_DECLINE")
        elif revenue_cagr_3y is not None and revenue_cagr_3y < -0.05:
            structural_penalty += 3
            structural_flags.append("REVENUE_3Y_DECLINE")

        if eps_cagr_5y is not None and eps_cagr_5y < -0.05:
            structural_penalty += 4
            structural_flags.append("EPS_5Y_DECLINE")
        elif eps_cagr_3y is not None and eps_cagr_3y < -0.10:
            structural_penalty += 3
            structural_flags.append("EPS_3Y_DECLINE")

        if fcf_cagr_5y is not None and fcf_cagr_5y < -0.05:
            structural_penalty += 3
            structural_flags.append("FCF_5Y_DECLINE")

        if margin_change_5y is not None and margin_change_5y < -0.15:
            structural_penalty += 3
            structural_flags.append("MARGIN_COMPRESSION")

        if debt_change_5y is not None and debt_change_5y > 0.50:
            structural_penalty += 2
            structural_flags.append("DEBT_GROWTH")

    structural_penalty = min(20, structural_penalty)

    # Research-stage diagnostics. These do not change the existing score.
    research_flags = []
    if fundamentals_verified:
        if debt_to_equity is not None and not is_financial:
            if debt_to_equity > 3.0:
                research_flags.append("HIGH_DEBT_EQUITY")
            elif debt_to_equity > 2.0:
                research_flags.append("ELEVATED_DEBT_EQUITY")
        if fcf_payout_ratio is not None:
            if fcf_payout_ratio > 1.0:
                research_flags.append("DIVIDEND_GT_FCF")
            elif fcf_payout_ratio > 0.80:
                research_flags.append("HIGH_FCF_PAYOUT")
        if dividend_safety == "REVIEW":
            research_flags.append("DIVIDEND_SAFETY_REVIEW")
        elif dividend_safety == "UNKNOWN":
            research_flags.append("DIVIDEND_SAFETY_UNKNOWN")
        if roic_proxy is not None and roic_proxy < 0.06:
            research_flags.append("LOW_ROIC")
        if revenue_cagr_5y is not None and revenue_cagr_5y < 0:
            research_flags.append("REVENUE_5Y_DECLINE")
        if eps_cagr_5y is not None and eps_cagr_5y < 0:
            research_flags.append("EPS_5Y_DECLINE")
        if fcf_cagr_5y is not None and fcf_cagr_5y < 0:
            research_flags.append("FCF_5Y_DECLINE")
        if margin_change_5y is not None and margin_change_5y < -0.10:
            research_flags.append("MARGIN_COMPRESSION")
    else:
        research_flags.append("FUNDAMENTALS_NOT_VERIFIED")

    if not fundamentals_verified:
        value_trap_risk = "UNKNOWN"
    elif structural_penalty >= 12:
        value_trap_risk = "HIGH"
    elif structural_penalty >= 6:
        value_trap_risk = "MEDIUM"
    else:
        value_trap_risk = "LOW"

    # V2.5 independent research ranking. This does not alter the legacy score.
    # Missing metrics are excluded from the denominator and reported via confidence.
    research_points = 0.0
    research_possible = 0.0

    if fundamentals_verified:
        # Dividend safety: 25 points.
        if dividend_safety == "STRONG":
            research_points += 25
            research_possible += 25
        elif dividend_safety == "OK":
            research_points += 18
            research_possible += 25
        elif dividend_safety == "REVIEW":
            research_points += 5
            research_possible += 25
        elif dividend_safety == "UNKNOWN":
            research_possible += 25

        # FCF coverage: 25 points.
        if fcf_payout_ratio is not None:
            research_possible += 25
            if fcf_payout_ratio <= 0.50:
                research_points += 25
            elif fcf_payout_ratio <= 0.70:
                research_points += 21
            elif fcf_payout_ratio <= 0.80:
                research_points += 17
            elif fcf_payout_ratio <= 1.00:
                research_points += 10
            elif fcf_payout_ratio <= 1.20:
                research_points += 4

        # ROIC: 20 points. Financial companies get no generic ROIC penalty
        # when the proxy is unavailable or not economically comparable.
        if roic_proxy is not None:
            research_possible += 20
            if roic_proxy >= 0.20:
                research_points += 20
            elif roic_proxy >= 0.15:
                research_points += 18
            elif roic_proxy >= 0.10:
                research_points += 15
            elif roic_proxy >= 0.06:
                research_points += 10
            elif roic_proxy >= 0:
                research_points += 4

        # Balance sheet: 15 points, omitted for financials.
        if not is_financial and debt_to_equity is not None:
            research_possible += 15
            if debt_to_equity <= 0.75:
                research_points += 15
            elif debt_to_equity <= 1.50:
                research_points += 12
            elif debt_to_equity <= 2.00:
                research_points += 9
            elif debt_to_equity <= 3.00:
                research_points += 4

        # Long-term business trend: 15 points.
        trend_available = 0
        trend_points = 0
        for value, strong, good in (
            (revenue_cagr_5y, 0.08, 0.03),
            (eps_cagr_5y, 0.10, 0.05),
            (fcf_cagr_5y, 0.10, 0.05),
        ):
            if value is not None:
                trend_available += 1
                trend_points += 5 if value >= strong else 3 if value >= good else 1 if value >= 0 else 0
        if margin_change_5y is not None:
            trend_available += 1
            trend_points += 5 if margin_change_5y >= 0.10 else 3 if margin_change_5y >= 0 else 1 if margin_change_5y > -0.10 else 0
        if trend_available:
            research_possible += 15
            research_points += min(15, trend_points * 15 / (trend_available * 5))

    research_score = (
        round(research_points / research_possible * 100, 1)
        if research_possible >= 60
        else None
    )
    research_confidence = (
        round(research_possible / 100 * 100)
        if fundamentals_verified
        else 0
    )

    if research_score is None:
        research_signal = "RESEARCH INCOMPLETE"
    elif research_confidence < 75:
        # Substantial missing inputs should not be presented as a strong
        # research conclusion, even when the normalized score is high.
        research_signal = "RESEARCH REVIEW" if research_score >= 65 else "RESEARCH RISK"
    elif research_confidence < 85:
        # 75-84% coverage is useful for screening, but not enough for the
        # strongest research label.
        research_signal = "RESEARCH PASS" if research_score >= 65 else (
            "RESEARCH REVIEW" if research_score >= 50 else "RESEARCH RISK"
        )
    elif research_score >= 80:
        research_signal = "RESEARCH STRONG"
    elif research_score >= 65:
        research_signal = "RESEARCH PASS"
    elif research_score >= 50:
        research_signal = "RESEARCH REVIEW"
    else:
        research_signal = "RESEARCH RISK"

    # V2.7 candidate layer: target "recent drawdown + fundamentals intact".
    # This is intentionally independent from the legacy score.
    #
    # Candidate eligibility requires:
    #   * verified and recent fundamentals (<=120 days)
    #   * meaningful 100-day drawdown
    #   * healthy long-term price regime (no multi-year downtrend)
    #   * no material recent revenue/EPS deterioration
    #   * adequate research coverage and no HIGH value-trap classification
    #
    # Candidate score (100):
    #   40 research quality + 25 recent fundamental stability
    #   25 drawdown quality + 10 long-term price regime.
    candidate_score = None
    candidate_signal = "NOT_ELIGIBLE"
    recent_fundamental_score = None

    def _growth_points(value, max_points, strong, floor):
        if value is None:
            return None
        if value >= strong:
            return float(max_points)
        if value >= 0:
            return float(max_points) * (0.65 + 0.35 * (value / strong if strong > 0 else 0))
        if value <= floor:
            return 0.0
        return float(max_points) * 0.65 * ((value - floor) / (0 - floor))

    recent_components = []
    for value, points, strong, floor in (
        (revenue_growth, 8, 0.08, -0.05),
        (eps_growth, 8, 0.10, -0.10),
        (fcf_growth, 5, 0.10, -0.15),
        (margin_change_3y, 4, 0.05, -0.10),
    ):
        points_value = _growth_points(value, points, strong, floor)
        if points_value is not None:
            recent_components.append((points_value, points))

    if recent_components:
        earned = sum(value for value, _ in recent_components)
        possible = sum(points for _, points in recent_components)
        recent_fundamental_score = round(earned / possible * 25.0, 1) if possible else None

    # Structural risk is not a hard exclusion unless HIGH, but MEDIUM risk
    # should materially reduce Candidate Score. This prevents a large drawdown
    # from overpowering leverage or other structural warnings.
    structural_risk_multiplier = {
        "LOW": 1.00,
        "MEDIUM": 0.82,
        "HIGH": 0.00,
    }.get(value_trap_risk, 0.90)

    recent_fundamental_data_count = sum(
        value is not None
        for value in (revenue_growth, eps_growth, fcf_growth, margin_change_3y)
    )
    recent_fundamental_data_quality = (
        "COMPLETE" if recent_fundamental_data_count >= 4
        else "PARTIAL" if recent_fundamental_data_count >= 3
        else "LIMITED"
    )

    # Separate data confidence from Candidate Score so incomplete data is
    # visible without changing the scoring model.
    if (
        fundamentals_verified
        and fundamental_age is not None
        and fundamental_age <= 120
        and recent_fundamental_data_count >= 4
    ):
        fundamental_confidence = "HIGH"
    elif (
        fundamentals_verified
        and fundamental_age is not None
        and fundamental_age <= 120
        and recent_fundamental_data_count >= 3
    ):
        fundamental_confidence = "MEDIUM"
    else:
        fundamental_confidence = "LOW"

    recent_fundamental_ok = (
        fundamentals_verified
        and fundamental_age is not None
        and fundamental_age <= 120
        and (revenue_growth is None or revenue_growth >= -0.05)
        and (eps_growth is None or eps_growth >= -0.10)
        and (fcf_growth is None or fcf_growth >= -0.15)
    )
    trend_ok = row.get("trend_regime") in ("HEALTHY_TREND", "NORMAL_CORRECTION")

    if (
        fundamentals_verified
        and fundamental_age is not None
        and fundamental_age <= 120
        and research_score is not None
        and research_score >= 65
        and research_confidence >= 75
        and dd100 is not None
        and dd100 <= -0.10
        and trend_ok
        and recent_fundamental_ok
        and value_trap_risk != "HIGH"
        and recent_fundamental_score is not None
    ):
        # 40 pts research quality.
        quality_component = research_score * 0.40

        # 25 pts recent fundamental stability. Missing inputs no longer
        # silently become a perfect 25/25; the score is capped when coverage
        # is incomplete.
        fundamental_component = recent_fundamental_score
        # Do not let normalized scores hide missing recent metrics.
        if recent_fundamental_data_quality == "PARTIAL":
            fundamental_component = min(fundamental_component, 22.0)
        elif recent_fundamental_data_quality == "LIMITED":
            fundamental_component = min(fundamental_component, 16.0)
        elif recent_fundamental_data_quality == "COMPLETE":
            fundamental_component = min(fundamental_component, 25.0)

        # 25 pts drawdown: 10 pts at -10%, scaling to 25 pts at -30%.
        dip_component = min(
            25.0,
            10.0 + max(0.0, (-dd100 - 0.10) / 0.20) * 15.0,
        )

        # 10 pts long-term price regime. A normal correction is still
        # eligible, but receives less than a healthy long-term trend.
        trend_component = 10.0 if row.get("trend_regime") == "HEALTHY_TREND" else 8.0

        raw_candidate_score = (
            quality_component
            + fundamental_component
            + dip_component
            + trend_component
        )
        candidate_score = round(raw_candidate_score * structural_risk_multiplier, 1)

        if candidate_score >= 82:
            candidate_signal = "HIGH_QUALITY_DIP"
        elif candidate_score >= 70:
            candidate_signal = "QUALITY_DIP"
        elif candidate_score >= 60:
            candidate_signal = "WATCHLIST_DIP"
        else:
            candidate_signal = "WEAK_DIP"


    # Human-readable classification of the drawdown itself.
    if row.get("data_status") != "OK":
        dip_quality = "DATA_REVIEW"
    elif value_trap_risk == "HIGH":
        dip_quality = "STRUCTURAL_RISK_DIP"
    elif row.get("trend_regime") in ("MULTI_YEAR_DECLINE", "LONG_TERM_DOWNTREND"):
        dip_quality = "LONG_TERM_DECLINE"
    elif value_trap_risk == "MEDIUM":
        dip_quality = "STRUCTURAL_RISK_DIP"
    elif recent_fundamental_data_quality == "LIMITED":
        dip_quality = "DATA_REVIEW"
    elif recent_fundamental_ok and row.get("trend_regime") == "HEALTHY_TREND":
        dip_quality = "HEALTHY_DIP" if dd100 > -0.25 else "DEEP_HEALTHY_DIP"
    elif recent_fundamental_ok and row.get("trend_regime") == "NORMAL_CORRECTION":
        dip_quality = "HEALTHY_DIP" if dd100 > -0.25 else "DEEP_HEALTHY_DIP"
    else:
        dip_quality = "FUNDAMENTAL_REVIEW"

    total = max(0, min(100, quality + trend_score + valuation + dip + dividend - structural_penalty))

    # Never expose a misleading total score when fundamentals are stale,
    # unavailable, or errored. Component scores remain diagnostic only.
    if not fundamentals_verified:
        total = None

    if not fundamentals_verified:
        dip_type = "UNKNOWN"
    elif value_trap_risk == "HIGH":
        dip_type = "VALUE_TRAP_REVIEW"
    elif value_trap_risk == "MEDIUM":
        dip_type = "STRUCTURAL_RISK"
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

    if not fundamentals_verified:
        if data_status == "STALE":
            signal = "DATA STALE"
        elif data_status == "ERROR":
            signal = "DATA ERROR"
        else:
            signal = "DATA INCOMPLETE"
    elif value_trap_risk == "HIGH":
        signal = "VALUE TRAP REVIEW"
    elif value_trap_risk == "MEDIUM":
        signal = "RISK / REVIEW"
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
        trend_score, structural_penalty, value_trap_risk, dip_type, buy_stage,
        ",".join(risk_flags), ",".join(structural_flags), ",".join(research_flags),
        research_score, research_signal, research_confidence,
        recent_fundamental_score, recent_fundamental_data_quality,
        structural_risk_multiplier, dip_quality, candidate_score, candidate_signal,
        fundamental_confidence
    )
