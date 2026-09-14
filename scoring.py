from config import (
    DD100_LEVELS,
    DD60_LEVELS,
    DD20_LEVELS,
    RSI_LEVELS,
    TREND_BONUS,
    TREND_PENALTY,
    STRONG_BUY_SCORE,
    BUY_SCORE,
    WATCH_SCORE,
)


def _threshold_points(value: float, levels: list[tuple[float, int]]) -> int:
    """Return the highest point tier reached by an indicator."""
    points = 0
    for threshold, tier_points in levels:
        if value <= threshold:
            points = tier_points
    return points


def score_stock(row: dict) -> tuple[int, str]:
    """Score a dividend-dip setup using multiple independent signals.

    V1.3 avoids treating a large 100-day drawdown alone as a strong buy.
    The score combines 100/60/20-day drawdowns, RSI and 200DMA trend.
    """
    dd100 = row["drawdown_100d"]
    dd60 = row["drawdown_60d"]
    dd20 = row["drawdown_20d"]
    rsi = row["rsi_14"]

    points = _threshold_points(dd100, DD100_LEVELS)
    points += _threshold_points(dd60, DD60_LEVELS)
    points += _threshold_points(dd20, DD20_LEVELS)

    if rsi == rsi:  # NaN-safe
        points += _threshold_points(rsi, RSI_LEVELS)

    above_200dma = row.get("above_200dma")
    if above_200dma is True:
        points += TREND_BONUS
    elif above_200dma is False:
        points += TREND_PENALTY

    if points >= STRONG_BUY_SCORE:
        signal = "STRONG BUY CANDIDATE"
    elif points >= BUY_SCORE:
        signal = "BUY CANDIDATE"
    elif points >= WATCH_SCORE:
        signal = "WATCH"
    else:
        signal = "HOLD"

    return points, signal
