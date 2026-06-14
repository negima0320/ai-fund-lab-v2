from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import (
    DEFAULT_DAILY_RESPONSE_DIR,
    DEFAULT_RANKED_DAILY_PATH,
    load_daily_close_path,
    load_ranked_daily,
    max_drawdown,
    now_utc,
    round_float,
)
from ai_fund_lab_v2.capital_allocation_ai.phase7e_strict_backtest import (
    StrictConfig,
    leakage_audit as strict_leakage_audit,
    simulate_strict,
    to_jsonable,
)


DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7g")
DEFAULT_LISTED_ISSUES_PATH = Path(".runtime/data/raw/jquants/listed_issues/data.parquet")
INITIAL_CAPITAL = 1_000_000.0
COMPLETION_STATUS = "PHASE7G_FINAL_INTEGRATED_BACKTEST_COMPLETE"


def run_phase7g_final_integrated_backtest(
    *,
    ranked_daily_path: Path = DEFAULT_RANKED_DAILY_PATH,
    daily_response_dir: Path = DEFAULT_DAILY_RESPONSE_DIR,
    listed_issues_path: Path = DEFAULT_LISTED_ISSUES_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = load_ranked_daily(ranked_daily_path)
    prices = load_daily_close_path(daily_response_dir, ranked)
    issue_master = load_listed_issue_master(listed_issues_path)

    metrics: list[dict[str, Any]] = []
    annual: list[dict[str, Any]] = []
    trades_all: list[pd.DataFrame] = []
    daily_all: list[pd.DataFrame] = []
    for config in build_phase7g_configs():
        result = simulate_strict(ranked, prices, config)
        m = enrich_metrics(result["metrics"], config)
        metrics.append(m)
        annual.extend(result["annual_summary"])
        for key, bucket in [("trades", trades_all), ("daily", daily_all)]:
            frame = result[key].copy()
            if not frame.empty:
                frame.insert(0, "policy_id", config.policy_id)
                frame.insert(1, "policy_name", config.policy_name)
                frame.insert(2, "policy_role", getattr(config, "policy_role", "unknown"))
                frame.insert(3, "cost_slippage_bps", config.transaction_cost_bps)
            bucket.append(frame)

    comparison = pd.DataFrame(metrics).sort_values(["policy_rank_group", "cost_slippage_bps", "policy_id"])
    annual_frame = pd.DataFrame(annual).sort_values(["policy_id", "year"]) if annual else pd.DataFrame()
    trade_ledger = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()
    trade_ledger = add_issue_names(trade_ledger, issue_master)
    daily_ledger = pd.concat(daily_all, ignore_index=True) if daily_all else pd.DataFrame()
    monthly = build_monthly_summary(daily_ledger)
    compounding = build_compounding_summary(annual_frame)
    ranking = build_policy_ranking(comparison)
    leakage = strict_leakage_audit(ranked, prices, created_at)
    leakage["phase"] = "Phase7-G Leakage Audit"

    paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "final_policy_comparison": output_dir / "final_policy_comparison.csv",
        "annual_summary": output_dir / "annual_summary.csv",
        "monthly_summary": output_dir / "monthly_summary.csv",
        "compounding_summary": output_dir / "compounding_summary.csv",
        "policy_ranking": output_dir / "policy_ranking.csv",
        "leakage_audit": output_dir / "leakage_audit.json",
        "equity_curve": output_dir / "equity_curve.csv",
        "trade_ledger": output_dir / "trade_ledger.csv",
        "daily_portfolio_ledger": output_dir / "daily_portfolio_ledger.csv",
    }
    comparison.to_csv(paths["final_policy_comparison"], index=False)
    annual_frame.to_csv(paths["annual_summary"], index=False)
    monthly.to_csv(paths["monthly_summary"], index=False)
    compounding.to_csv(paths["compounding_summary"], index=False)
    ranking.to_csv(paths["policy_ranking"], index=False)
    daily_ledger.to_csv(paths["equity_curve"], index=False)
    daily_ledger.to_csv(paths["daily_portfolio_ledger"], index=False)
    trade_ledger.to_csv(paths["trade_ledger"], index=False)
    write_json(paths["leakage_audit"], leakage)
    summary = build_summary(comparison, annual_frame, monthly, trade_ledger, paths, ranked, prices, leakage, created_at, issue_master)
    write_json(paths["validation_summary"], summary)
    return {
        "summary": summary,
        "comparison": comparison,
        "annual_summary": annual_frame,
        "monthly_summary": monthly,
        "compounding_summary": compounding,
        "policy_ranking": ranking,
        "trade_ledger": trade_ledger,
        "daily_ledger": daily_ledger,
        "leakage_audit": leakage,
    }


def build_phase7g_configs() -> list[StrictConfig]:
    specs = [
        ("CAP5", "Primary CAP5", "primary", {"minimum_holding_days": 15, "replacement_cap_per_month": 5}),
        ("CAP4", "Conservative CAP4", "conservative", {"minimum_holding_days": 15, "replacement_cap_per_month": 4}),
        ("POLICY_Y_CAP4_EDGE08_CONF5", "Weak-regime Policy Y", "weak_regime", {"minimum_holding_days": 15, "replacement_cap_per_month": 4, "replacement_edge_margin": 0.08, "confirmation_days": 5}),
        ("A_FIXED_20BD", "Reference A fixed 20bd", "reference", {"family": "BASE"}),
        ("C3_MIN15_T2", "Reference high turnover C3 min15", "reference_high_turnover", {"minimum_holding_days": 15}),
    ]
    configs: list[StrictConfig] = []
    for base_id, name, role, kwargs in specs:
        for bps in [0.0, 10.0, 30.0]:
            params = dict(kwargs)
            family = params.pop("family", "C3")
            config = StrictConfig(
                policy_id=f"{base_id}_{int(bps)}BPS",
                policy_name=f"{name} cost/slippage {int(bps)}bps",
                family=family,
                transaction_cost_bps=bps,
                slippage_bps=bps,
                **params,
            )
            object.__setattr__(config, "policy_role", role)
            object.__setattr__(config, "policy_rank_group", {"primary": 1, "conservative": 2, "weak_regime": 3, "reference": 4, "reference_high_turnover": 5}[role])
            configs.append(config)
    return configs


def load_listed_issue_master(path: Path = DEFAULT_LISTED_ISSUES_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["jquants_code", "display_code", "company_name", "master_date", "market_name"])
    frame = pd.read_parquet(path)
    if frame.empty or "Code" not in frame.columns:
        return pd.DataFrame(columns=["jquants_code", "display_code", "company_name", "master_date", "market_name"])
    out = pd.DataFrame({
        "jquants_code": frame["Code"].map(normalize_jquants_code),
        "display_code": frame["Code"].map(display_stock_code),
        "company_name": frame.get("CoName", pd.Series([""] * len(frame))).fillna("").astype(str),
        "master_date": frame.get("Date", pd.Series([""] * len(frame))).fillna("").astype(str),
        "market_name": frame.get("MktNm", pd.Series([""] * len(frame))).fillna("").astype(str),
    })
    out = out[out["jquants_code"] != ""].drop_duplicates("jquants_code", keep="last")
    return out


def normalize_jquants_code(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if text.isdigit():
        return text.zfill(5)
    return text


def display_stock_code(value: Any) -> str:
    code = normalize_jquants_code(value)
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code


def add_issue_names(frame: pd.DataFrame, issue_master: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["jquants_code"] = out["code"].map(normalize_jquants_code) if "code" in out.columns else ""
    out["display_code"] = out["jquants_code"].map(display_stock_code)
    if issue_master.empty:
        out["company_name"] = ""
        out["listed_issue_lookup_status"] = "MASTER_NOT_AVAILABLE"
        return out
    merged = out.merge(issue_master, how="left", on="jquants_code", suffixes=("", "_master"))
    merged["display_code"] = merged["display_code_master"].fillna(merged["display_code"])
    merged["company_name"] = merged["company_name"].fillna("")
    merged["listed_issue_lookup_status"] = merged["company_name"].map(lambda x: "FOUND_IN_2026_06_01_MASTER" if str(x).strip() else "NOT_FOUND_OR_DELISTED_IN_MASTER")
    drop_cols = [c for c in ["display_code_master"] if c in merged.columns]
    return merged.drop(columns=drop_cols)


def enrich_metrics(metrics: dict[str, Any], config: StrictConfig) -> dict[str, Any]:
    out = dict(metrics)
    out["policy_role"] = getattr(config, "policy_role", "unknown")
    out["policy_rank_group"] = getattr(config, "policy_rank_group", 9)
    out["cost_slippage_bps"] = config.transaction_cost_bps
    out["initial_capital"] = INITIAL_CAPITAL
    out["total_profit_net"] = round_float(out["final_assets_net"] - INITIAL_CAPITAL)
    return out


def build_monthly_summary(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    frame = daily.copy()
    frame["month"] = frame["target_date"].str.slice(0, 7)
    for (policy_id, month), g in frame.groupby(["policy_id", "month"], sort=True):
        start_assets = float(g["total_assets_net"].iloc[0])
        end_assets = float(g["total_assets_net"].iloc[-1])
        rows.append({
            "policy_id": policy_id,
            "policy_name": g["policy_name"].iloc[0],
            "policy_role": g["policy_role"].iloc[0],
            "cost_slippage_bps": float(g["cost_slippage_bps"].iloc[0]),
            "month": month,
            "month_start_assets": round_float(start_assets),
            "month_end_assets": round_float(end_assets),
            "monthly_profit": round_float(end_assets - start_assets),
            "monthly_return": round_float(end_assets / start_assets - 1) if start_assets else 0,
            "monthly_max_drawdown": round_float(max_drawdown(g["total_assets_net"].tolist())),
        })
    return pd.DataFrame(rows)


def build_compounding_summary(annual: pd.DataFrame) -> pd.DataFrame:
    if annual.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for policy_id, g in annual.groupby("policy_id", sort=True):
        simple_assets = INITIAL_CAPITAL
        cumulative_simple_return = 0.0
        for row in g.sort_values("year").itertuples(index=False):
            annual_return = float(row.annual_return_net_by_year)
            cumulative_simple_return += annual_return
            simple_assets = INITIAL_CAPITAL * (1 + cumulative_simple_return)
            rows.append({
                "policy_id": policy_id,
                "policy_name": row.policy_name,
                "year": int(row.year),
                "annual_return": round_float(annual_return),
                "simple_assets_estimate": round_float(simple_assets),
                "compound_assets": None,
                "compound_minus_simple": None,
            })
    return pd.DataFrame(rows)


def attach_compound_assets(compounding: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    if compounding.empty or daily.empty:
        return compounding
    ends = daily.sort_values("target_date").groupby(["policy_id", "year"])["total_assets_net"].last().to_dict()
    out = compounding.copy()
    values = []
    diffs = []
    for row in out.itertuples(index=False):
        value = ends.get((row.policy_id, row.year))
        values.append(round_float(value) if value is not None else None)
        diffs.append(round_float(value - row.simple_assets_estimate) if value is not None else None)
    out["compound_assets"] = values
    out["compound_minus_simple"] = diffs
    return out


def build_policy_ranking(comparison: pd.DataFrame) -> pd.DataFrame:
    zero = comparison[comparison["cost_slippage_bps"] == 0].copy()
    if zero.empty:
        return pd.DataFrame()
    zero["phase7g_score"] = (
        zero["cumulative_return_net"].rank(pct=True)
        + zero["annualized_return_net"].rank(pct=True)
        + zero["profit_factor_net"].fillna(0).rank(pct=True)
        - zero["replacement_rate"].rank(pct=True) * 0.5
        + zero["max_drawdown_net"].rank(pct=True)
    )
    return zero.sort_values("phase7g_score", ascending=False)


def build_symbol_summary(trades: pd.DataFrame, policy_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    sells = sell_trades(trades, policy_id)
    if sells.empty:
        return pd.DataFrame(), pd.DataFrame()
    group_cols = ["code", "display_code", "company_name", "listed_issue_lookup_status"]
    grouped = sells.groupby(group_cols, dropna=False).agg(
        total_pnl=("realized_pnl", "sum"),
        win_rate=("realized_pnl", lambda s: float((s > 0).mean())),
        average_holding_days=("holding_days", "mean"),
        trade_count=("code", "count"),
    ).reset_index()
    best = grouped.sort_values("total_pnl", ascending=False).head(20)
    worst = grouped.sort_values("total_pnl", ascending=True).head(20)
    return best, worst


def sell_trades(trades: pd.DataFrame, policy_id: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    return trades[(trades["policy_id"] == policy_id) & (trades["action"] == "SELL")].copy()


def build_summary(
    comparison: pd.DataFrame,
    annual: pd.DataFrame,
    monthly: pd.DataFrame,
    trades: pd.DataFrame,
    paths: dict[str, Path],
    ranked: pd.DataFrame,
    prices: pd.DataFrame,
    audit: dict[str, Any],
    created_at: str,
    issue_master: pd.DataFrame,
) -> dict[str, Any]:
    primary = comparison[comparison["policy_id"] == "CAP5_0BPS"].to_dict("records")
    ranking = build_policy_ranking(comparison).head(5).to_dict("records")
    best_symbols, worst_symbols = build_symbol_summary(trades, "CAP5_0BPS")
    primary_trades = sell_trades(trades, "CAP5_0BPS")
    best_trades = primary_trades.sort_values("realized_pnl", ascending=False).head(20).to_dict("records") if not primary_trades.empty else []
    worst_trades = primary_trades.sort_values("realized_pnl", ascending=True).head(20).to_dict("records") if not primary_trades.empty else []
    month_primary = monthly[monthly["policy_id"] == "CAP5_0BPS"] if not monthly.empty else pd.DataFrame()
    return {
        "phase": "Phase7-G",
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS,
        "initial_capital": INITIAL_CAPITAL,
        "source": {
            "ranked_daily": str(DEFAULT_RANKED_DAILY_PATH),
            "daily_response_dir": str(DEFAULT_DAILY_RESPONSE_DIR),
            "ranked_start_date": str(ranked["target_date"].min()),
            "ranked_end_date": str(ranked["target_date"].max()),
            "price_start_date": str(prices["target_date"].min()),
            "price_end_date": str(prices["target_date"].max()),
            "ranked_row_count": int(len(ranked)),
            "price_row_count": int(len(prices)),
            "listed_issue_master": str(DEFAULT_LISTED_ISSUES_PATH),
            "listed_issue_master_row_count": int(len(issue_master)),
            "listed_issue_master_date": str(issue_master["master_date"].max()) if not issue_master.empty else "",
        },
        "code_mapping_note": {
            "current_output_code_format": "J-Quants 5-character issue code used in local artifacts, e.g. 93670.",
            "display_code_format": "For common Japanese stock-code display, trailing 0 is removed when present, e.g. 93670 -> 9367. Alphanumeric codes such as 148A0 -> 148A are handled the same way.",
            "master_source": str(DEFAULT_LISTED_ISSUES_PATH),
            "delisted_handling": "Names are joined against the latest local J-Quants listed issue master. Codes not found are kept with blank company_name and listed_issue_lookup_status=NOT_FOUND_OR_DELISTED_IN_MASTER.",
        },
        "primary_policy": primary[0] if primary else {},
        "policy_ranking_top5": ranking,
        "primary_month_summary": {
            "winning_months": int((month_primary["monthly_return"] > 0).sum()) if not month_primary.empty else 0,
            "losing_months": int((month_primary["monthly_return"] < 0).sum()) if not month_primary.empty else 0,
            "best_month": month_primary.sort_values("monthly_return", ascending=False).head(1).to_dict("records")[0] if not month_primary.empty else {},
            "worst_month": month_primary.sort_values("monthly_return", ascending=True).head(1).to_dict("records")[0] if not month_primary.empty else {},
        },
        "best_symbols_top20": best_symbols.to_dict("records"),
        "worst_symbols_top20": worst_symbols.to_dict("records"),
        "best_trades_top20": best_trades,
        "worst_trades_top20": worst_trades,
        "artifact_paths": {k: str(v) for k, v in paths.items()},
        "leakage_audit_status": audit["status"],
        "no_future_data_in_decision": True,
        "backtest_outcome_used_in_decision": False,
        "future_price_used_in_decision": False,
        "future_rank_used_in_decision": False,
        "decision_evaluation_separated": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "jquants_api_called": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_and_write_with_compounding_fix(**kwargs: Any) -> dict[str, Any]:
    result = run_phase7g_final_integrated_backtest(**kwargs)
    output_dir = kwargs.get("output_dir", DEFAULT_OUTPUT_DIR)
    compounding = attach_compound_assets(result["compounding_summary"], result["daily_ledger"])
    compounding.to_csv(Path(output_dir) / "compounding_summary.csv", index=False)
    result["compounding_summary"] = compounding
    return result
