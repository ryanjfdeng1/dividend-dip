from config import (
    WATCH_DRAWDOWN,
    BUY_DRAWDOWN,
    STRONG_BUY_DRAWDOWN,
)


def score_stock(row: dict) -> tuple[int, str]:
    points = 0
    dd = row["drawdown_100d"]

    if dd <= -WATCH_DRAWDOWN:
        points += 20
    if dd <= -BUY_DRAWDOWN:
        points += 10
    if dd <= -STRONG_BUY_DRAWDOWN:
        points += 10

    if row["above_200dma"] is True:
        points += 10

    if points >= 40:
        signal = "STRONG BUY CANDIDATE"
    elif points >= 30:
        signal = "BUY CANDIDATE"
    elif points >= 20:
        signal = "WATCH"
    else:
        signal = "HOLD"

    return points, signal
