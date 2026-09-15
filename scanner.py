import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from config import STOCKS, FINANCIALS
from data_provider import get_daily_history
from fundamentals import get_fundamentals as get_tiingo_fundamentals
from sec_fundamentals import get_sec_fundamentals
from indicators import calculate_metrics
from scoring import score_stock

load_dotenv()


def _has_usable_fundamentals(data: dict) -> bool:
    return bool(data.get("fundamentals_available")) and (
        data.get("eps") is not None
        or data.get("free_cash_flow") is not None
        or data.get("revenue") is not None
    )


def get_fundamentals(symbol: str) -> dict:
    # V1.7: SEC XBRL is the primary source and requires no API key.
    sec = get_sec_fundamentals(symbol)
    if _has_usable_fundamentals(sec):
        return sec

    # Keep Tiingo as a fallback for accounts that already have Fundamentals
    # access. This prevents a temporary SEC/API problem from blocking a scan.
    if os.getenv("TIINGO_API_KEY"):
        tiingo = get_tiingo_fundamentals(symbol)
        if _has_usable_fundamentals(tiingo):
            tiingo["data_quality"] = "B"
            return tiingo

    sec["data_quality"] = sec.get("data_quality", "D")
    return sec


def scan_one(symbol: str) -> dict:
    history = get_daily_history(symbol, use_cache=True)
    fundamentals = get_fundamentals(symbol)
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
            "Missing price-data API key. Set TIINGO_API_KEY or "
            "ALPHAVANTAGE_API_KEY in .env."
        )

    rows, errors = [], []
    price_provider = "Tiingo" if os.getenv("TIINGO_API_KEY") else "Alpha Vantage"

    print(f"Quality Dip Scanner V1.9 | {len(STOCKS)} stocks")
    print(f"Price data: {price_provider} | Fundamentals: SEC XBRL -> Tiingo fallback")
    print("Price cache: refresh at most once per trading day")
    print("SEC fundamentals cache: refresh every 7 days")
    print("=" * 155)

    for symbol in STOCKS:
        try:
            row = scan_one(symbol)
            rows.append(row)

            fundamental_status = row.get("fundamentals_error", "")
            sector = "FIN" if symbol in FINANCIALS else "NON-FIN"
            status = row.get("data_quality") or "D"
            source = row.get("fundamentals_source") or "NONE"
            if fundamental_status:
                fundamental_status = f" | {fundamental_status[:45]}"

            print(
                f"OK   {symbol:5s} | DD100={_fmt(row['drawdown_100d'] * 100):>6s}% | "
                f"RSI={_fmt(row['rsi_14']):>5s} | PE={_fmt(row['pe']):>5s} | FCFY={_fmt(row.get('fcf_yield') * 100 if pd.notna(row.get('fcf_yield')) else None):>5s}% | "
                f"Q={row['quality_score']:2d}/45 | V={row['valuation_score']:2d}/30 | "
                f"D={row['dip_score']:2d}/20 | Div={row['dividend_score']:1d}/5 | "
                f"Score={row['score']:3d} | {status}/{source} | {sector} | {row['signal']}"
                f"{fundamental_status}"
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
        "eps", "free_cash_flow", "fcf_yield", "shares_outstanding", "roe", "payout_ratio", "pe",
        "revenue", "net_income", "total_assets", "equity", "debt",
        "revenue_growth", "eps_growth", "dividend_yield", "dividend_growth",
        "fundamental_date", "fundamental_age_days", "fundamentals_source", "data_quality",
        "fundamentals_error", "quality_score", "valuation_score",
        "dip_score", "dividend_score", "score", "dip_type",
        "buy_stage", "risk_flags", "signal",
    ]
    columns = [c for c in columns if c in df.columns]

    print("\nTop candidates")
    print("-" * 200)
    print(df[columns].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    df.to_csv("scan_results.csv", index=False)

    if errors:
        pd.DataFrame(errors).to_csv("scan_errors.csv", index=False)
        print(f"\n{len(errors)} symbols failed. See scan_errors.csv")

    print("\nSaved: scan_results.csv")


if __name__ == "__main__":
    main()
