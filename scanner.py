import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from config import STOCKS
from data_provider import get_daily_history
from indicators import calculate_metrics
from scoring import score_stock

load_dotenv()


def scan_one(symbol: str) -> dict:
    history = get_daily_history(symbol, use_cache=True)
    data = calculate_metrics(history)
    data["ticker"] = symbol
    data["date"] = datetime.now().date().isoformat()

    points, signal = score_stock(data)
    data["score"] = points
    data["signal"] = signal
    return data


def main():
    if not os.getenv("ALPHAVANTAGE_API_KEY"):
        raise RuntimeError(
            "Missing ALPHAVANTAGE_API_KEY. "
            "Create .env from .env.example and put your key there."
        )

    rows = []
    errors = []

    print("Dividend Dip Scanner V1.3")
    print("=" * 75)

    for symbol in STOCKS:
        try:
            row = scan_one(symbol)
            rows.append(row)
            print(
                f"OK   {symbol:5s} | "
                f"100D DD={row['drawdown_100d']:.1%} | "
                f"60D DD={row['drawdown_60d']:.1%} | "
                f"20D DD={row['drawdown_20d']:.1%} | "
                f"RSI={row['rsi_14']:.1f} | "
                f"score={row['score']:2d} | {row['signal']}"
            )
        except Exception as exc:
            errors.append({"ticker": symbol, "error": str(exc)})
            print(f"ERROR {symbol:5s} | {exc}")

    if not rows:
        raise RuntimeError("No stocks could be scanned.")

    df = pd.DataFrame(rows).sort_values(
        ["score", "drawdown_100d"],
        ascending=[False, True],
    )

    columns = [
        "ticker", "price", "high_100d",
        "drawdown_100d", "drawdown_60d", "drawdown_20d",
        "sma_200", "above_200dma", "rsi_14",
        "score", "signal",
    ]

    print("\nResults")
    print("-" * 120)
    print(df[columns].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    df.to_csv("scan_results.csv", index=False)

    if errors:
        pd.DataFrame(errors).to_csv("scan_errors.csv", index=False)
        print(f"\n{len(errors)} symbols failed. See scan_errors.csv")

    print("\nSaved: scan_results.csv")


if __name__ == "__main__":
    main()
