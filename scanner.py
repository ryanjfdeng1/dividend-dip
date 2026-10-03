import os
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from dotenv import load_dotenv

from config import STOCKS, FINANCIALS, SECTOR_MAP, INDUSTRY_MAP, COMPANY_GROUP_MAP, PORTFOLIO_TICKER_SECTOR_MAP
from data_provider import get_daily_history
from fundamentals import get_fundamentals as get_tiingo_fundamentals
from sec_fundamentals import get_sec_fundamentals
from indicators import calculate_metrics
from scoring import score_stock

load_dotenv()


def _has_usable_fundamentals(data: dict) -> bool:
    """Return True only when at least one core fundamental is a real number."""
    if not bool(data.get("fundamentals_available")):
        return False
    for key in ("eps", "free_cash_flow", "revenue"):
        value = data.get(key)
        try:
            if value is not None and pd.notna(value) and float(value) == float(value):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _normalize_data_status(data: dict) -> dict:
    """V2.3.1: never report OK when fundamentals are not actually usable."""
    if _has_usable_fundamentals(data):
        if data.get("data_status") is None:
            data["data_status"] = "OK"
        return data

    if data.get("fundamentals_source") == "SEC_ERROR":
        data["data_status"] = "ERROR"
    elif data.get("data_quality") == "E":
        data["data_status"] = "STALE"
    else:
        data["data_status"] = "INCOMPLETE"
    return data


def get_fundamentals(symbol: str) -> dict:
    sec = _normalize_data_status(get_sec_fundamentals(symbol))
    if _has_usable_fundamentals(sec):
        return sec

    if os.getenv("TIINGO_API_KEY"):
        tiingo = _normalize_data_status(get_tiingo_fundamentals(symbol))
        if _has_usable_fundamentals(tiingo):
            tiingo["data_quality"] = "B"
            tiingo["data_status"] = "OK"
            return tiingo

    return _normalize_data_status(sec)


def _company_group(symbol: str) -> str:
    return COMPANY_GROUP_MAP.get(symbol, symbol)


def _portfolio_tickers() -> set[str]:
    raw = os.getenv("DIVIDEND_DIP_PORTFOLIO_TICKERS", "")
    return {item.strip().upper() for item in raw.split(",") if item.strip()}


def _portfolio_overlap(symbol: str) -> tuple[str, int]:
    tickers = _portfolio_tickers()
    if not tickers:
        return "UNKNOWN", 0
    target_sector = SECTOR_MAP.get(symbol)
    target_industry = INDUSTRY_MAP.get(symbol)
    count = 0
    best = "LOW"
    for held in tickers:
        if held == symbol:
            return "HIGH", count + 1
        held_sector = SECTOR_MAP.get(held) or PORTFOLIO_TICKER_SECTOR_MAP.get(held)
        held_industry = INDUSTRY_MAP.get(held)
        if target_industry and held_industry and target_industry == held_industry:
            count += 1
            best = "HIGH"
        elif target_sector and held_sector and target_sector == held_sector:
            count += 1
            if best != "HIGH":
                best = "MEDIUM"
    return best, count


def scan_one(symbol: str) -> dict:
    history = get_daily_history(symbol, use_cache=True)
    fundamentals = get_fundamentals(symbol)
    data = calculate_metrics(history, fundamentals)
    data["ticker"] = symbol
    data["date"] = datetime.now().date().isoformat()
    data = _normalize_data_status(data)

    (
        total, signal, dip, dividend, quality, valuation,
        trend_score, structural_penalty, value_trap_risk, dip_type, buy_stage,
        risk_flags, structural_flags, research_flags,
        research_score, research_signal, research_confidence,
        recent_fundamental_score, recent_fundamental_data_quality,
        structural_risk_multiplier, dip_quality, candidate_score, candidate_signal,
        fundamental_confidence
    ) = score_stock(data)

    data.update({
        "sector": SECTOR_MAP.get(symbol, "Unknown"),
        "industry": INDUSTRY_MAP.get(symbol, "Unknown"),
        "company_group": _company_group(symbol),
        "portfolio_overlap": _portfolio_overlap(symbol)[0],
        "portfolio_overlap_count": _portfolio_overlap(symbol)[1],
        "data_status": data.get("data_status") or "INCOMPLETE",
        "score_status": "SCORED" if total is not None else "UNSCORED",
        "score": total,
        "signal": signal,
        "dip_score": dip,
        "dividend_score": dividend,
        "quality_score": quality,
        "valuation_score": valuation,
        "trend_score": trend_score,
        "structural_penalty": structural_penalty,
        "value_trap_risk": value_trap_risk,
        "structural_flags": structural_flags,
        "research_flags": research_flags,
        "research_score": research_score,
        "research_signal": research_signal,
        "research_confidence": research_confidence,
        "recent_fundamental_score": recent_fundamental_score,
        "recent_fundamental_data_quality": recent_fundamental_data_quality,
        "fundamental_confidence": fundamental_confidence,
        "structural_risk_multiplier": structural_risk_multiplier,
        "dip_quality": dip_quality,
        "candidate_score": candidate_score,
        "candidate_signal": candidate_signal,
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
    if not os.getenv("TIINGO_API_KEY"):
        raise RuntimeError(
            "TIINGO_API_KEY is required for split-safe historical prices. "
            "Add TIINGO_API_KEY to .env. Alpha Vantage TIME_SERIES_DAILY "
            "does not provide split metadata."
        )

    rows, errors = [], []
    price_provider = "Tiingo (split-normalized)"

    print(f"Quality Dip Scanner V2.7 | {len(STOCKS)} stocks")
    print(f"Price data: {price_provider} | Fundamentals: SEC XBRL -> Tiingo fallback")
    print("Price cache: refresh at most once per trading day | Corporate actions: split-normalized")
    print("SEC fundamentals cache: refresh every 7 days | TTM + 3/5-year trend metrics")
    print("Data quality: OK scored | STALE/ERROR/INCOMPLETE excluded from ranking")
    print("=" * 155)

    for symbol in STOCKS:
        try:
            row = scan_one(symbol)
            rows.append(row)

            fundamental_status = row.get("fundamentals_error", "")
            sector = row.get("sector", "Unknown")
            industry = row.get("industry", "Unknown")
            status = row.get("data_quality") or "D"
            source = row.get("fundamentals_source") or "NONE"
            if fundamental_status:
                fundamental_status = f" | {fundamental_status[:45]}"

            print(
                f"{row.get('data_status', 'INCOMPLETE'):10s} {symbol:5s} | DD20={_fmt(row['drawdown_20d'] * 100):>6s}% | DD60={_fmt(row['drawdown_60d'] * 100):>6s}% | "
                f"DD100={_fmt(row['drawdown_100d'] * 100):>6s}% | DD252={_fmt(row['drawdown_252d'] * 100):>6s}% | "
                f"RSI={_fmt(row['rsi_14']):>5s} | 200DMA={_fmt(row.get('distance_200dma') * 100 if pd.notna(row.get('distance_200dma')) else None):>6s}% | PE={_fmt(row['pe']):>5s} | FCFY={_fmt(row.get('fcf_yield') * 100 if pd.notna(row.get('fcf_yield')) else None):>5s} | "
                f"Q={row['quality_score']:2d}/30 | T={row['trend_score']:2d}/15 | V={row['valuation_score']:2d}/30 | "
                f"D={row['dip_score']:2d}/20 | Div={row['dividend_score']:1d}/5 | "
                f"Score={_fmt(row['score'], 0):>3s} | Trap={row.get('value_trap_risk', 'UNKNOWN'):7s} | "
                f"Penalty={row.get('structural_penalty', 0):2d} | {status}/{source}/{row.get('data_status', 'INCOMPLETE')} | "
                f"{sector} / {industry} | {row['signal']}"
                f"{fundamental_status}"
            )
        except Exception as exc:
            errors.append({"ticker": symbol, "error": str(exc)})
            print(f"ERROR {symbol:5s} | {exc}")

    if not rows:
        raise RuntimeError("No stocks could be scanned.")

    df = pd.DataFrame(rows)

    # Research ranking is independent from the legacy score.
    df["research_rank"] = pd.NA
    research_mask = df["research_score"].notna()
    if research_mask.any():
        ranked = df.loc[research_mask].sort_values(
            ["research_score", "research_confidence", "score"],
            ascending=[False, False, False],
            na_position="last",
        )
        df.loc[ranked.index, "research_rank"] = range(1, len(ranked) + 1)

    
    # Candidate ranking is the intersection of verified research quality and
    # a meaningful 100-day drawdown. Stocks without a qualifying dip are not
    # ranked as candidates.
    df["candidate_rank"] = pd.NA
    df["candidate_group_rank"] = pd.NA
    candidate_mask = df["candidate_score"].notna()
    if candidate_mask.any():
        ranked = df.loc[candidate_mask].sort_values(
            ["candidate_score", "research_score", "drawdown_100d"],
            ascending=[False, False, True],
            na_position="last",
        )
        seen_groups = set()
        primary_rank = 1
        group_counts = {}
        for idx, row in ranked.iterrows():
            group = row.get("company_group", row.get("ticker"))
            group_counts[group] = group_counts.get(group, 0) + 1
            df.loc[idx, "candidate_group_rank"] = group_counts[group]
            if group not in seen_groups:
                df.loc[idx, "candidate_rank"] = primary_rank
                seen_groups.add(group)
                primary_rank += 1

    # Explain why a stock is not a candidate instead of leaving Candidate Score blank.
    def candidate_eligibility_reason(row):
        if pd.notna(row.get("candidate_score")) and pd.notna(row.get("candidate_group_rank")) and row.get("candidate_group_rank") > 1:
            return "SAME_COMPANY_DUPLICATE"
        if pd.notna(row.get("candidate_score")):
            return "ELIGIBLE"
        if row.get("data_status") != "OK" or row.get("score_status") != "SCORED":
            return "FUNDAMENTALS_UNVERIFIED"
        if pd.isna(row.get("research_score")):
            return "RESEARCH_INCOMPLETE"
        if row.get("research_score") < 65:
            return "RESEARCH_TOO_LOW"
        if pd.isna(row.get("research_confidence")) or row.get("research_confidence") < 75:
            return "RESEARCH_CONFIDENCE_LOW"
        if pd.isna(row.get("drawdown_100d")) or row.get("drawdown_100d") > -0.10:
            return "DIP_TOO_SMALL"
        if row.get("fundamental_age_days") is not None and row.get("fundamental_age_days") > 120:
            return "FUNDAMENTALS_TOO_OLD"
        if row.get("trend_regime") not in ("HEALTHY_TREND", "NORMAL_CORRECTION"):
            return "LONG_TERM_TREND_RISK"
        if row.get("revenue_growth") is not None and row.get("revenue_growth") < -0.05:
            return "RECENT_REVENUE_WEAK"
        if row.get("eps_growth") is not None and row.get("eps_growth") < -0.10:
            return "RECENT_EPS_WEAK"
        if row.get("fcf_growth") is not None and row.get("fcf_growth") < -0.15:
            return "RECENT_FCF_WEAK"
        if row.get("value_trap_risk") == "HIGH":
            return "HIGH_VALUE_TRAP"
        if row.get("value_trap_risk") == "MEDIUM":
            return "MEDIUM_STRUCTURAL_RISK"
        if row.get("trend_regime") in ("LONG_TERM_DOWNTREND", "MULTI_YEAR_DECLINE"):
            return "LONG_TERM_TREND_RISK"
        if row.get("recent_fundamental_data_quality") == "LIMITED":
            return "FUNDAMENTAL_DATA_LIMITED"
        return "NOT_ELIGIBLE"

    df["candidate_eligibility_reason"] = df.apply(candidate_eligibility_reason, axis=1)

    # Export order follows the scanner's primary decision hierarchy:
    # eligible candidates first by Candidate Rank, then non-candidates by
    # Research Rank / Research Score. This makes the CSV useful at first glance.
    df["_candidate_sort"] = df["candidate_rank"].notna().map({True: 0, False: 1})
    df["_candidate_rank_sort"] = df["candidate_rank"].fillna(float("inf"))
    df["_candidate_group_sort"] = df["candidate_group_rank"].fillna(float("inf"))
    df["_research_rank_sort"] = df["research_rank"].fillna(float("inf"))
    df = df.sort_values(
        ["_candidate_sort", "_candidate_rank_sort", "_candidate_group_sort", "_research_rank_sort",
         "research_score", "score", "ticker"],
        ascending=[True, True, True, False, False, True],
        na_position="last",
    ).drop(columns=["_candidate_sort", "_candidate_rank_sort", "_candidate_group_sort", "_research_rank_sort"])

    # Human-first column order: put the five key decision dimensions together
    # at the far left so the CSV can be understood immediately in Excel/Numbers:
    # Candidate Score -> Dip Quality -> Structural Risk -> Fundamental Data Quality
    # -> Research Score. Supporting market/research fields follow, then legacy
    # score components and raw data.
    columns = [
        # ===== PRIMARY DECISION PANEL =====
        "candidate_rank", "ticker", "company_group", "price",
        "candidate_score", "candidate_signal", "candidate_eligibility_reason",
        "portfolio_overlap", "portfolio_overlap_count", "candidate_group_rank",
        "dip_quality",
        "value_trap_risk", "structural_risk_multiplier",
        "fundamental_confidence", "recent_fundamental_data_quality",
        "research_score", "research_signal", "research_confidence", "research_rank",
        # ===== SUPPORTING MARKET / DIP CONTEXT =====
        "drawdown_100d", "drawdown_60d", "drawdown_20d", "drawdown_252d",
        "drawdown_3y", "return_3y", "trend_regime",
        "rsi_14", "distance_200dma", "pe", "fcf_yield", "dividend_yield",
        "sector", "industry",
        # ===== FUNDAMENTAL / RISK DETAIL =====
        "recent_fundamental_score", "dip_type", "buy_stage",
        "structural_flags", "research_flags", "risk_flags",
        "dividend_safety", "fcf_payout_ratio", "roic_proxy", "debt_to_equity",
        "revenue_cagr_5y", "eps_cagr_5y", "fcf_cagr_5y", "margin_change_5y",
        # ===== LEGACY SCORE =====
        "score", "signal", "quality_score", "trend_score", "valuation_score",
        "dip_score", "dividend_score", "structural_penalty",
        # ===== DATA STATUS =====
        "data_status", "data_quality", "fundamentals_source",
        "fundamental_date", "fundamental_age_days", "latest_quarter_date", "latest_filing_date",
        "fundamentals_error", "score_status",
        # ===== RAW MARKET DATA =====
        "high_20d", "high_60d", "high_100d", "high_252d", "sma_200", "above_200dma",
        "split_adjusted", "split_adjustment_factor",
        # ===== RAW FUNDAMENTALS =====
        "eps", "free_cash_flow", "shares_outstanding", "roe", "payout_ratio",
        "revenue", "net_income", "total_assets", "equity", "debt",
        "revenue_growth", "eps_growth", "fcf_growth", "dividend_growth",
        "revenue_cagr_3y", "eps_cagr_3y", "fcf_cagr_3y", "operating_margin",
        "margin_change_3y", "debt_change_3y", "debt_change_5y",
    ]
    columns = [c for c in columns if c in df.columns]

    status_counts = df["data_status"].fillna("INCOMPLETE").value_counts().to_dict()
    scoreable = int(df["score"].notna().sum())
    print("\nData quality summary")
    print("-" * 80)
    for status in ("OK", "STALE", "ERROR", "INCOMPLETE"):
        print(f"{status:10s}: {int(status_counts.get(status, 0)):3d}")
    print(f"{'SCORED':10s}: {scoreable:3d}")
    print(f"{'ERRORS':10s}: {len(errors):3d}")

    print("\nTop candidates")
    print("-" * 200)
    print(df[columns].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Keep scan_results.csv machine-friendly (raw numeric values) and also
    # provide a human-readable version for opening directly in Excel/Numbers.
    df[columns].to_csv("scan_results.csv", index=False)

    readable = df[columns].copy()
    percent_columns = {
        "drawdown_100d", "drawdown_60d", "drawdown_20d", "drawdown_252d",
        "distance_200dma", "fcf_yield", "dividend_yield", "fcf_payout_ratio",
        "revenue_cagr_5y", "eps_cagr_5y", "fcf_cagr_5y", "margin_change_5y",
        "revenue_growth", "eps_growth", "fcf_growth", "dividend_growth", "operating_margin",
        "revenue_cagr_3y", "eps_cagr_3y", "fcf_cagr_3y",
        "margin_change_3y", "debt_change_3y", "debt_change_5y",
        "roe", "payout_ratio",
    }
    for column in percent_columns:
        if column in readable.columns:
            readable[column] = readable[column].map(
                lambda x: "" if pd.isna(x) else f"{x * 100:.1f}%"
            )

    rank_columns = {"candidate_rank", "research_rank"}
    for column in rank_columns:
        if column in readable.columns:
            readable[column] = readable[column].map(
                lambda x: "" if pd.isna(x) else str(int(x))
            )

    for column in ("candidate_score", "research_score", "research_confidence", "score"):
        if column in readable.columns:
            readable[column] = readable[column].map(
                lambda x: "" if pd.isna(x) else f"{x:.1f}"
            )

    readable.to_csv("scan_results_readable.csv", index=False)

    # Excel output: freeze the header/left panel, add filters, auto-size columns,
    # and highlight the key decision fields so the first screen is easy to scan.
    excel_path = "scan_results.xlsx"
    readable.to_excel(excel_path, index=False, sheet_name="Scan Results")
    wb = load_workbook(excel_path)
    ws = wb["Scan Results"]
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 30

    fills = {
        "candidate": PatternFill("solid", fgColor="D9EAF7"),
        "quality": PatternFill("solid", fgColor="E2F0D9"),
        "risk": PatternFill("solid", fgColor="FCE4D6"),
        "data": PatternFill("solid", fgColor="FFF2CC"),
        "research": PatternFill("solid", fgColor="E4DFEC"),
    }
    header_map = {cell.value: cell.column for cell in ws[1]}
    groups = {
        "candidate": ["candidate_rank", "candidate_score", "candidate_signal", "candidate_eligibility_reason"],
        "quality": ["dip_quality"],
        "risk": ["value_trap_risk", "structural_risk_multiplier"],
        "data": ["fundamental_confidence", "recent_fundamental_data_quality"],
        "research": ["research_score", "research_signal", "research_confidence", "research_rank"],
    }
    for group, names in groups.items():
        for name in names:
            col = header_map.get(name)
            if col:
                ws.cell(1, col).fill = fills[group]
                ws.cell(1, col).font = Font(bold=True)
                for row in range(2, ws.max_row + 1):
                    ws.cell(row, col).fill = fills[group]

    # Highlight the most useful categorical states in the body.
    if header_map.get("dip_quality"):
        col = header_map["dip_quality"]
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row, col)
            if cell.value in ("HEALTHY_DIP", "DEEP_HEALTHY_DIP"):
                cell.fill = PatternFill("solid", fgColor="C6E0B4")
            elif cell.value in ("STRUCTURAL_RISK_DIP", "LONG_TERM_DECLINE"):
                cell.fill = PatternFill("solid", fgColor="F4B084")
            elif cell.value in ("DATA_REVIEW", "FUNDAMENTAL_REVIEW"):
                cell.fill = PatternFill("solid", fgColor="FFE699")

    if header_map.get("fundamental_confidence"):
        col = header_map["fundamental_confidence"]
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row, col)
            if cell.value == "HIGH":
                cell.fill = PatternFill("solid", fgColor="C6E0B4")
            elif cell.value == "LOW":
                cell.fill = PatternFill("solid", fgColor="F4B084")

    for cell in ws[1]:
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="center")

    # Practical widths: keep the important left panel readable without making
    # the whole workbook excessively wide.
    for column_cells in ws.columns:
        letter = column_cells[0].column_letter
        header = str(column_cells[0].value or "")
        if header in groups["candidate"] + groups["quality"] + groups["risk"] + groups["data"] + groups["research"]:
            width = min(max(len(header) + 2, 14), 28)
        elif header in ("ticker", "price", "sector", "industry", "trend_regime"):
            width = min(max(len(header) + 2, 12), 24)
        else:
            width = min(max(len(header) + 2, 10), 18)
        ws.column_dimensions[letter].width = width

    wb.save(excel_path)

    if errors:
        pd.DataFrame(errors).to_csv("scan_errors.csv", index=False)
        print(f"\n{len(errors)} symbols failed. See scan_errors.csv")

    print("\nSaved: scan_results.csv (raw) and scan_results_readable.csv (human-readable)")


if __name__ == "__main__":
    main()
