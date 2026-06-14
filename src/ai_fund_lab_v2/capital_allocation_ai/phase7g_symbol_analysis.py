from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import round_float
from ai_fund_lab_v2.capital_allocation_ai.phase7g_final_integrated_backtest import (
    DEFAULT_LISTED_ISSUES_PATH,
    DEFAULT_OUTPUT_DIR,
    display_stock_code,
    normalize_jquants_code,
)


DEFAULT_POLICY_ID = "CAP5_0BPS"
UNRESOLVED_REASON = "not_found_in_2026_06_01_listed_issue_master_or_delisted"


def run_phase7g_symbol_analysis(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    listed_issues_path: Path = DEFAULT_LISTED_ISSUES_PATH,
    policy_id: str = DEFAULT_POLICY_ID,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trades = pd.read_csv(output_dir / "trade_ledger.csv")
    daily = pd.read_csv(output_dir / "daily_portfolio_ledger.csv")
    issue_master = load_issue_master(listed_issues_path)
    trades = enrich_trades(trades, issue_master)
    sells = trades[(trades["policy_id"] == policy_id) & (trades["action"] == "SELL")].copy()
    daily_policy = daily[daily["policy_id"] == policy_id].copy()

    top_profit = build_symbol_summary(sells, ascending=False, value_column="profit_amount").head(20)
    top_loss = build_symbol_summary(sells, ascending=True, value_column="loss_amount").head(20)
    top_wins = build_trade_extremes(sells, ascending=False).head(20)
    top_losses = build_trade_extremes(sells, ascending=True).head(20)
    yearly_best, yearly_worst = build_yearly_symbol_summaries(sells)
    sector_summary = build_sector_summary(sells)
    market_summary = build_market_summary(sells)
    resolution_audit = build_resolution_audit(sells)
    cash_summary, cash_by_year = build_cash_summary(daily_policy)
    loss_sell_summary = build_loss_sell_summary(sells)

    paths = {
        "top_profit_contributing_symbols_named": output_dir / "top_profit_contributing_symbols_named.csv",
        "top_loss_contributing_symbols_named": output_dir / "top_loss_contributing_symbols_named.csv",
        "top_winning_trades_named": output_dir / "top_winning_trades_named.csv",
        "top_losing_trades_named": output_dir / "top_losing_trades_named.csv",
        "yearly_best_symbols_named": output_dir / "yearly_best_symbols_named.csv",
        "yearly_worst_symbols_named": output_dir / "yearly_worst_symbols_named.csv",
        "sector_profit_summary": output_dir / "sector_profit_summary.csv",
        "sector_loss_summary": output_dir / "sector_loss_summary.csv",
        "market_segment_summary": output_dir / "market_segment_summary.csv",
        "symbol_resolution_audit": output_dir / "symbol_resolution_audit.csv",
        "symbol_analysis_summary": output_dir / "symbol_analysis_summary.json",
    }

    top_profit.to_csv(paths["top_profit_contributing_symbols_named"], index=False)
    top_loss.to_csv(paths["top_loss_contributing_symbols_named"], index=False)
    top_wins.to_csv(paths["top_winning_trades_named"], index=False)
    top_losses.to_csv(paths["top_losing_trades_named"], index=False)
    yearly_best.to_csv(paths["yearly_best_symbols_named"], index=False)
    yearly_worst.to_csv(paths["yearly_worst_symbols_named"], index=False)
    sector_summary.sort_values("net_profit", ascending=False).to_csv(paths["sector_profit_summary"], index=False)
    sector_summary.sort_values("loss_amount", ascending=True).to_csv(paths["sector_loss_summary"], index=False)
    market_summary.to_csv(paths["market_segment_summary"], index=False)
    resolution_audit.to_csv(paths["symbol_resolution_audit"], index=False)

    resolved = int((~resolution_audit["name_unresolved"]).sum())
    total = int(len(resolution_audit))
    summary = {
        "policy_id": policy_id,
        "listed_issues_source": str(listed_issues_path),
        "master_date": issue_master["master_date"].dropna().max() if not issue_master.empty else "",
        "code_format": {
            "trade_ledger_code": "J-Quants 5-character issue code such as 93670 or 148A0",
            "report_display_code": "Drop trailing exchange digit 0 when present, e.g. 93670 -> 9367, 148A0 -> 148A",
        },
        "symbol_resolution": {
            "unique_symbols": total,
            "resolved_symbol_count": resolved,
            "unresolved_symbol_count": total - resolved,
            "name_unresolved_count": total - resolved,
            "symbol_resolution_rate": round_float(resolved / total) if total else 0,
        },
        "cash_summary": cash_summary,
        "cash_ratio_by_year": cash_by_year,
        "loss_sell_summary": loss_sell_summary,
        "audit": {
            "new_jquants_api_fetch_executed": False,
            "broker_api_executed": False,
            "paper_trading_executed": False,
            "order_executed": False,
            "live_order_executed": False,
            "tachibana_api_called": False,
            "existing_artifacts_only": True,
        },
        "outputs": {name: str(path) for name, path in paths.items() if name != "symbol_analysis_summary"},
    }
    paths["symbol_analysis_summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "summary": summary,
        "top_profit": top_profit,
        "top_loss": top_loss,
        "top_wins": top_wins,
        "top_losses": top_losses,
        "yearly_best": yearly_best,
        "yearly_worst": yearly_worst,
        "sector_summary": sector_summary,
        "market_summary": market_summary,
        "resolution_audit": resolution_audit,
    }


def load_issue_master(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=master_columns())
    raw = pd.read_parquet(path)
    if raw.empty or "Code" not in raw.columns:
        return pd.DataFrame(columns=master_columns())
    out = pd.DataFrame(
        {
            "jquants_code": raw["Code"].map(normalize_jquants_code),
            "code_normalized": raw["Code"].map(display_stock_code),
            "company_name": raw.get("CoName", pd.Series([""] * len(raw))).fillna("").astype(str),
            "sector": raw.get("S17Nm", pd.Series([""] * len(raw))).fillna("").astype(str),
            "industry": raw.get("S33Nm", pd.Series([""] * len(raw))).fillna("").astype(str),
            "market_segment": raw.get("MktNm", pd.Series([""] * len(raw))).fillna("").astype(str),
            "master_date": raw.get("Date", pd.Series([""] * len(raw))).fillna("").astype(str),
        }
    )
    return out[out["jquants_code"] != ""].drop_duplicates("jquants_code", keep="last")


def master_columns() -> list[str]:
    return ["jquants_code", "code_normalized", "company_name", "sector", "industry", "market_segment", "master_date"]


def enrich_trades(trades: pd.DataFrame, issue_master: pd.DataFrame) -> pd.DataFrame:
    out = trades.copy()
    out["code_original"] = out["code"].map(normalize_jquants_code)
    out["code_normalized"] = out["code_original"].map(display_stock_code)
    if issue_master.empty:
        for col in ["company_name", "sector", "industry", "market_segment", "master_date"]:
            out[col] = ""
        out["name_unresolved"] = True
        out["name_unresolved_reason"] = "listed_issue_master_not_available"
        return out
    out = out.drop(columns=[c for c in ["company_name", "sector", "industry", "market_segment", "master_date"] if c in out.columns])
    merged = out.merge(issue_master, how="left", left_on="code_original", right_on="jquants_code", suffixes=("", "_master"))
    merged["code_normalized"] = merged["code_normalized_master"].fillna(merged["code_normalized"])
    for col in ["company_name", "sector", "industry", "market_segment", "master_date"]:
        merged[col] = merged[col].fillna("").astype(str)
    merged["name_unresolved"] = merged["company_name"].astype(str).str.strip().eq("")
    merged["name_unresolved_reason"] = merged["name_unresolved"].map(lambda x: UNRESOLVED_REASON if x else "")
    return merged.drop(columns=[c for c in ["jquants_code", "code_normalized_master"] if c in merged.columns])


def build_symbol_summary(sells: pd.DataFrame, *, ascending: bool, value_column: str) -> pd.DataFrame:
    group_cols = ["code_original", "code_normalized", "company_name", "sector", "industry", "market_segment", "name_unresolved", "name_unresolved_reason"]
    rows = []
    for keys, group in sells.groupby(group_cols, dropna=False, sort=False):
        total = float(group["realized_pnl"].sum())
        returns = group["net_return_after_cost"].dropna()
        rows.append(
            dict(
                zip(group_cols, keys),
                profit_amount=round_float(total),
                loss_amount=round_float(total),
                win_rate=round_float((group["realized_pnl"] > 0).mean()),
                trade_count=int(len(group)),
                average_holding_days=round_float(group["holding_days"].mean()),
                best_trade_return=round_float(returns.max()) if not returns.empty else 0,
                worst_trade_return=round_float(returns.min()) if not returns.empty else 0,
            )
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(value_column, ascending=ascending).reset_index(drop=True)


def build_trade_extremes(sells: pd.DataFrame, *, ascending: bool) -> pd.DataFrame:
    cols = [
        "code_original",
        "code_normalized",
        "company_name",
        "sector",
        "industry",
        "market_segment",
        "entry_date",
        "exit_date",
        "net_return_after_cost",
        "realized_pnl",
        "holding_days",
        "exit_reason",
        "name_unresolved",
        "name_unresolved_reason",
    ]
    out = sells.sort_values("realized_pnl", ascending=ascending)[cols].copy()
    return out.rename(
        columns={
            "entry_date": "buy_date",
            "exit_date": "sell_date",
            "net_return_after_cost": "return_pct",
            "realized_pnl": "profit_or_loss_amount",
        }
    ).reset_index(drop=True)


def build_yearly_symbol_summaries(sells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = []
    for year, year_group in sells.groupby("year", sort=True):
        frame = build_symbol_summary(year_group, ascending=False, value_column="profit_amount")
        if frame.empty:
            continue
        frame.insert(0, "year", int(year))
        frame["profit_or_loss"] = frame["profit_amount"]
        summaries.append(frame)
    all_years = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    if all_years.empty:
        return all_years, all_years
    best = all_years.sort_values(["year", "profit_or_loss"], ascending=[True, False]).groupby("year", as_index=False).head(10)
    worst = all_years.sort_values(["year", "profit_or_loss"], ascending=[True, True]).groupby("year", as_index=False).head(10)
    keep = [
        "year",
        "code_original",
        "code_normalized",
        "company_name",
        "sector",
        "industry",
        "market_segment",
        "profit_or_loss",
        "trade_count",
        "win_rate",
        "average_holding_days",
        "name_unresolved",
        "name_unresolved_reason",
    ]
    return best[keep].reset_index(drop=True), worst[keep].reset_index(drop=True)


def build_sector_summary(sells: pd.DataFrame) -> pd.DataFrame:
    return build_group_summary(sells, ["sector", "industry"]).sort_values("net_profit", ascending=False).reset_index(drop=True)


def build_market_summary(sells: pd.DataFrame) -> pd.DataFrame:
    return build_group_summary(sells, ["market_segment"]).sort_values("net_profit", ascending=False).reset_index(drop=True)


def build_group_summary(sells: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    frame = sells.copy()
    for col in group_cols:
        frame[col] = frame[col].fillna("").astype(str).replace("", "名称未取得")
    for keys, group in frame.groupby(group_cols, dropna=False, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        pnl = group["realized_pnl"]
        rows.append(
            dict(
                zip(group_cols, keys),
                profit_amount=round_float(pnl[pnl > 0].sum()),
                loss_amount=round_float(pnl[pnl < 0].sum()),
                net_profit=round_float(pnl.sum()),
                win_rate=round_float((pnl > 0).mean()),
                trade_count=int(len(group)),
                average_holding_days=round_float(group["holding_days"].mean()),
            )
        )
    return pd.DataFrame(rows)


def build_resolution_audit(sells: pd.DataFrame) -> pd.DataFrame:
    cols = ["code_original", "code_normalized", "company_name", "sector", "industry", "market_segment", "name_unresolved", "name_unresolved_reason"]
    audit = sells.groupby(cols, dropna=False, as_index=False).agg(trade_count=("realized_pnl", "size"), net_profit=("realized_pnl", "sum"))
    audit["net_profit"] = audit["net_profit"].map(round_float)
    return audit.sort_values(["name_unresolved", "code_original"], ascending=[False, True]).reset_index(drop=True)


def build_cash_summary(daily: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if daily.empty:
        return {}, []
    frame = daily.copy()
    frame["cash_ratio"] = frame["cash"] / frame["total_assets_net"]
    frame["target_date"] = pd.to_datetime(frame["target_date"])
    frame["year"] = frame["target_date"].dt.year
    summary = {
        "average_cash_ratio": round_float(frame["cash_ratio"].mean()),
        "median_cash_ratio": round_float(frame["cash_ratio"].median()),
        "min_cash_ratio": round_float(frame["cash_ratio"].min()),
        "max_cash_ratio": round_float(frame["cash_ratio"].max()),
        "average_capital_utilization": round_float(frame["capital_utilization"].mean()),
        "cash_drag": round_float(frame["cash_ratio"].mean()),
        "days_cash_ratio_over_30pct": int((frame["cash_ratio"] > 0.30).sum()),
        "days_cash_ratio_over_50pct": int((frame["cash_ratio"] > 0.50).sum()),
    }
    by_year = []
    for year, group in frame.groupby("year", sort=True):
        by_year.append(
            {
                "year": int(year),
                "average_cash_ratio": round_float(group["cash_ratio"].mean()),
                "median_cash_ratio": round_float(group["cash_ratio"].median()),
                "average_capital_utilization": round_float(group["capital_utilization"].mean()),
            }
        )
    return summary, by_year


def build_loss_sell_summary(sells: pd.DataFrame) -> dict[str, Any]:
    if sells.empty:
        return {}
    pnl = sells["realized_pnl"]
    returns = sells["net_return_after_cost"]
    losing = sells[pnl < 0]
    winning = sells[pnl > 0]
    return {
        "total_sells": int(len(sells)),
        "profitable_sells": int(len(winning)),
        "losing_sells": int(len(losing)),
        "losing_sell_rate": round_float(len(losing) / len(sells)),
        "average_profit_sell_return": round_float(winning["net_return_after_cost"].mean()) if not winning.empty else 0,
        "average_loss_sell_return": round_float(losing["net_return_after_cost"].mean()) if not losing.empty else 0,
        "median_loss_sell_return": round_float(losing["net_return_after_cost"].median()) if not losing.empty else 0,
        "worst_loss_sell_return": round_float(returns.min()) if not returns.empty else 0,
    }
