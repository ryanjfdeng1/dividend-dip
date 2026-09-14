import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from config import STOCKS
from data_provider import get_daily_history
from fundamentals import get_fundamentals
from indicators import calculate_metrics
from scoring import score_stock

load_dotenv()


def scan_one(symbol: str) -> dict:
    history = get_daily_history(symbol, use_cache=True)
    fundamentals = get_fundamentals(symbol) if os.getenv("TIINGO_API_KEY") else {}
    data = calculate_metrics(history, fundamentals)
    data["ticker"] = symbol
    data["date"] = datetime.now().date().isoformat()

    (
        total, signal, dip, dividend, quality, valuation,
        dip_type, buy_stage, risk_flags
    ) = score_stock(data)

    data.update({
        "score": total,
        "signal": signal,
        "dip_score": dip,
        "dividend_score": dividend,
        "quality_score": quality,
        "valuation_score": valuation,
        "dip_type": dip_type,
        "buy_stage": buy_stage,
        "risk_flags": risk_flags,
    })
    return data


def _fmt(value, digits=1):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}"


def main():
    if not os.getenv("TIINGO_API_KEY") and not os.getenv("ALPHAVANTAGE_API_KEY"):
        raise RuntimeError(
            "Missing API key. Set TIINGO_API_KEY (recommended) or "
            "ALPHAVANTAGE_API_KEY in .env."
        )

    rows, errors = [], []
    provider = "Tiingo" if os.getenv("TIINGO_API_KEY") else "Alpha Vantage"

    print(f"Quality Dip Scanner V1.6 | {len(STOCKS)} stocks | Data: {provider}")
    print("=" * 145)

    for symbol in STOCKS:
        try:
            row = scan_one(symbol)
            rows.append(row)
            print(
                f"OK   {symbol:5s} | DD100={_fmt(row['drawdown_100d'] * 100):>6s}% | "
                f"RSI={_fmt(row['rsi_14']):>5s} | PE={_fmt(row['pe']):>5s} | "
                f"Q={row['quality_score']:2d}/45 | V={row['valuation_score']:2d}/20 | "
                f"D={row['dip_score']:2d}/30 | Div={row['dividend_score']:1d}/5 | "
                f"Score={row['score']:3d} | {row['signal']}"
            )
        except Exception as exc:
            errors.append({"ticker": symbol, "error": str(exc)})
            print(f"ERROR {symbol:5s} | {exc}")

    if not rows:
        raise RuntimeError("No stocks could be scanned.")

    df = pd.DataFrame(rows).sort_values(
        ["score", "quality_score", "drawdown_100d"],
        ascending=[False, False, True],
    )

    columns = [
        "ticker", "price", "high_100d", "drawdown_100d", "drawdown_60d",
        "drawdown_20d", "sma_200", "above_200dma", "rsi_14",
        "eps", "free_cash_flow", "roe", "payout_ratio", "pe",
        "revenue_growth", "eps_growth", "dividend_yield", "dividend_growth",
        "fundamental_date", "quality_score", "valuation_score", "dip_score",
        "dividend_score", "score", "dip_type", "buy_stage", "risk_flags", "signal",
    ]
    columns = [c for c in columns if c in df.columns]

    print("\nTop candidates")
    print("-" * 180)
    print(df[columns].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    df.to_csv("scan_results.csv", index=False)

    if errors:
        pd.DataFrame(errors).to_csv("scan_errors.csv", index=False)
        print(f"\n{len(errors)} symbols failed. See scan_errors.csv")

    print("\nSaved: scan_results.csv")


if __name__ == "__main__":
    main()
