from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.dataset_builder import read_table
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.inference import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    MODEL_VERSION,
    READY_FOR_PHASE6_VALIDATION,
    audit_position_feature_frame,
    build_position_management_output,
)

PHASE = "Phase6-B"
FEATURE_VERSION = "position_management_feature_phase6b_v1"
READY_FOR_PHASE6C_VALIDATION_DESIGN = "READY_FOR_PHASE6C_VALIDATION_DESIGN"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/position_management_ai/phase6b_position_feature_dry_run.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/position_management_ai/phase6b_position_feature_dry_run.json")

REQUIRED_FEATURE_COLUMNS = (
    "entry_price",
    "current_price",
    "holding_days",
    "unrealized_return",
    "peak_return",
    "drawdown_from_peak",
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_ratio_5d",
    "volume_ratio_20d",
    "close_over_ma_5d",
    "close_over_ma_20d",
    "ma_5_20_ratio",
    "ma_20_60_ratio",
    "volatility_20d",
    "trend_strength_score",
    "expected_edge_score",
    "buy_rank",
    "downside_risk_score",
    "risk_guard_status",
)

TECHNICAL_FEATURE_COLUMNS = (
    "return_1d",
    "return_5d",
    "return_20d",
    "volume_ratio_5d",
    "volume_ratio_20d",
    "close_over_ma_5d",
    "close_over_ma_20d",
    "ma_5_20_ratio",
    "ma_20_60_ratio",
    "volatility_20d",
    "trend_strength_score",
)


@dataclass(frozen=True)
class Phase6BDryRunResult:
    feature_frame: pd.DataFrame
    inference_output: pd.DataFrame
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_phase6b_position_feature_dry_run(
    *,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    quote_path: Path | None = None,
    opportunity_path: Path | None = None,
    created_at: str | None = None,
) -> Phase6BDryRunResult:
    created_at = created_at or now_utc()
    if quote_path and quote_path.is_file() and opportunity_path and opportunity_path.is_file():
        quote_frame = read_table(quote_path)
        opportunity_frame = read_table(opportunity_path)
        position_frame = build_historical_position_fixture_from_quotes(
            quote_frame=quote_frame,
            scenarios=sample_scenarios_from_quotes(quote_frame, max_rows=12),
        )
    else:
        quote_frame = fixture_quote_frame()
        opportunity_frame = fixture_opportunity_frame()
        position_frame = fixture_position_scenarios()

    feature_frame = build_position_features_from_quotes(
        position_frame=position_frame,
        quote_frame=quote_frame,
        opportunity_frame=opportunity_frame,
        created_at=created_at,
    )
    inference_frame = to_phase6_inference_frame(feature_frame)
    audit = audit_position_feature_frame(inference_frame, input_holding_count=len(feature_frame), created_at=created_at)
    audit = {**audit, "phase": PHASE}
    if audit["leakage_audit_status"] != "OK":
        summary = build_phase6b_summary(
            feature_frame=feature_frame,
            inference_output=pd.DataFrame(),
            audit=audit,
            output_csv_path=output_csv_path,
            output_json_path=output_json_path,
            created_at=created_at,
            readiness_status=BLOCKED_BY_LEAKAGE_AUDIT,
        )
        write_json(output_json_path, summary)
        return Phase6BDryRunResult(feature_frame=feature_frame, inference_output=pd.DataFrame(), summary=summary, audit=audit)

    inference_output = build_position_management_output(
        inference_frame,
        created_at=created_at,
        inference_run_id=f"phase6b_{created_at.replace(':', '').replace('+', 'Z')}",
    )
    dry_run_frame = feature_frame.merge(
        inference_output[
            [
                "target_date",
                "code",
                "action",
                "hold_score",
                "exit_score",
                "add_score",
                "reduce_score",
                "continue_holding",
                "exit_candidate",
                "add_candidate",
                "reduce_candidate",
                "action_reason",
                "exit_reason",
            ]
        ],
        on=["target_date", "code"],
        how="left",
        validate="one_to_one",
    )
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    dry_run_frame.to_csv(output_csv_path, index=False)
    summary = build_phase6b_summary(
        feature_frame=dry_run_frame,
        inference_output=inference_output,
        audit={**audit, **action_counts(inference_output), "readiness_status": READY_FOR_PHASE6C_VALIDATION_DESIGN},
        output_csv_path=output_csv_path,
        output_json_path=output_json_path,
        created_at=created_at,
        readiness_status=READY_FOR_PHASE6C_VALIDATION_DESIGN,
    )
    write_json(output_json_path, summary)
    return Phase6BDryRunResult(feature_frame=dry_run_frame, inference_output=inference_output, summary=summary, audit=summary["audit"])


def build_position_features_from_quotes(
    *,
    position_frame: pd.DataFrame,
    quote_frame: pd.DataFrame,
    opportunity_frame: pd.DataFrame,
    created_at: str | None = None,
) -> pd.DataFrame:
    created_at = created_at or now_utc()
    positions = normalize_position_scenarios(position_frame)
    quotes = normalize_quote_frame(quote_frame)
    opportunity = normalize_opportunity_frame(opportunity_frame)
    rows: list[dict[str, Any]] = []
    for position in positions.to_dict("records"):
        code = str(position["code"])
        entry_date = str(position["entry_date"])
        target_date = str(position["target_date"])
        history = quotes[(quotes["code"] == code) & (quotes["target_date"] <= target_date)].sort_values("target_date")
        holding_window = history[(history["target_date"] >= entry_date) & (history["target_date"] <= target_date)].copy()
        if history.empty or holding_window.empty:
            continue
        current_row = history.iloc[-1]
        entry_candidates = holding_window[holding_window["target_date"] == entry_date]
        entry_row = entry_candidates.iloc[0] if not entry_candidates.empty else holding_window.iloc[0]
        entry_price = float(entry_row["Close"])
        current_price = float(current_row["Close"])
        peak_price = float(holding_window["High"].max()) if "High" in holding_window.columns else float(holding_window["Close"].max())
        unrealized_return = safe_return(current_price, entry_price)
        peak_return = safe_return(peak_price, entry_price)
        technicals = calculate_technical_features(history)
        rows.append(
            {
                "target_date": target_date,
                "entry_date": entry_date,
                "code": code,
                "entry_price": round_float(entry_price),
                "current_price": round_float(current_price),
                "holding_days": int(len(holding_window) - 1),
                "position_size": float(position.get("position_size", 100.0)),
                "unrealized_return": round_float(unrealized_return),
                "current_return": round_float(unrealized_return),
                "peak_return": round_float(peak_return),
                "drawdown_from_peak": round_float(unrealized_return - peak_return),
                **technicals,
                "feature_version": FEATURE_VERSION,
                "created_at": created_at,
            }
        )
    features = pd.DataFrame(rows)
    if features.empty:
        return features
    features = features.merge(opportunity, on=["target_date", "code"], how="left", validate="one_to_one")
    features["expected_edge_score"] = pd.to_numeric(features.get("expected_edge_score", 0.0), errors="coerce").fillna(0.0)
    features["buy_rank"] = pd.to_numeric(features.get("buy_rank", 999), errors="coerce").fillna(999).astype(int)
    features["downside_risk_score"] = pd.to_numeric(features.get("downside_risk_score", 0.50), errors="coerce").fillna(0.50)
    features["risk_guard_status"] = features.get("risk_guard_status", "unknown").fillna("unknown").astype(str)
    ordered_columns = [
        "target_date",
        "entry_date",
        "code",
        *REQUIRED_FEATURE_COLUMNS,
        "position_size",
        "current_return",
        "feature_version",
        "created_at",
    ]
    optional_columns = [column for column in ("candidate_score", "candidate_rank") if column in features.columns]
    return features[ordered_columns + optional_columns]


def build_historical_position_fixture_from_quotes(*, quote_frame: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    quotes = normalize_quote_frame(quote_frame)
    scenarios = normalize_position_scenarios(scenarios)
    valid_rows: list[dict[str, Any]] = []
    for scenario in scenarios.to_dict("records"):
        code = str(scenario["code"])
        entry_date = str(scenario["entry_date"])
        target_date = str(scenario["target_date"])
        window = quotes[(quotes["code"] == code) & (quotes["target_date"] >= entry_date) & (quotes["target_date"] <= target_date)]
        if not window.empty:
            valid_rows.append(scenario)
    return pd.DataFrame(valid_rows)


def to_phase6_inference_frame(feature_frame: pd.DataFrame) -> pd.DataFrame:
    frame = feature_frame.copy()
    rename_map = {column: f"feature__{column}" for column in TECHNICAL_FEATURE_COLUMNS if column in frame.columns}
    frame = frame.rename(columns=rename_map)
    return frame


def calculate_technical_features(history: pd.DataFrame) -> dict[str, float]:
    close = pd.to_numeric(history["Close"], errors="coerce")
    volume = pd.to_numeric(history["Volume"], errors="coerce")
    current_close = float(close.iloc[-1])
    ma5 = float(close.tail(5).mean())
    ma20 = float(close.tail(20).mean())
    ma60 = float(close.tail(60).mean())
    volume5 = float(volume.tail(5).mean())
    volume20 = float(volume.tail(20).mean())
    returns = close.pct_change()
    return_1d = safe_return(current_close, float(close.iloc[-2])) if len(close) >= 2 else 0.0
    return_5d = safe_return(current_close, float(close.iloc[-6])) if len(close) >= 6 else 0.0
    return_20d = safe_return(current_close, float(close.iloc[-21])) if len(close) >= 21 else 0.0
    volatility_20d = float(returns.tail(20).std()) if len(returns.dropna()) >= 2 else 0.0
    close_over_ma_5d = safe_ratio(current_close, ma5, default=1.0)
    close_over_ma_20d = safe_ratio(current_close, ma20, default=1.0)
    ma_5_20_ratio = safe_ratio(ma5, ma20, default=1.0)
    ma_20_60_ratio = safe_ratio(ma20, ma60, default=1.0)
    trend_strength_score = (
        0.35 * normalize_scalar(close_over_ma_20d - 1.0, -0.08, 0.12)
        + 0.25 * normalize_scalar(ma_5_20_ratio - 1.0, -0.05, 0.08)
        + 0.25 * normalize_scalar(return_20d, -0.15, 0.25)
        + 0.15 * normalize_scalar(safe_ratio(volume5, volume20, default=1.0) - 1.0, -0.50, 1.50)
    )
    return {
        "return_1d": round_float(return_1d),
        "return_5d": round_float(return_5d),
        "return_20d": round_float(return_20d),
        "volume_ratio_5d": round_float(safe_ratio(volume5, volume20, default=1.0)),
        "volume_ratio_20d": 1.0,
        "close_over_ma_5d": round_float(close_over_ma_5d),
        "close_over_ma_20d": round_float(close_over_ma_20d),
        "ma_5_20_ratio": round_float(ma_5_20_ratio),
        "ma_20_60_ratio": round_float(ma_20_60_ratio),
        "volatility_20d": round_float(volatility_20d),
        "trend_strength_score": round_float(trend_strength_score),
    }


def fixture_quote_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2026-03-02", periods=75)
    scenarios = {
        "2001": {"base": 100.0, "daily": 0.0040, "shock": 0.00, "volume": 100000.0},
        "2002": {"base": 120.0, "daily": -0.0035, "shock": -0.06, "volume": 90000.0},
        "2003": {"base": 90.0, "daily": 0.0030, "shock": -0.10, "volume": 110000.0},
        "2004": {"base": 80.0, "daily": 0.0015, "shock": 0.00, "volume": 80000.0},
        "2005": {"base": 70.0, "daily": -0.0010, "shock": 0.00, "volume": 70000.0},
        "2006": {"base": 105.0, "daily": 0.0020, "shock": -0.04, "volume": 95000.0},
    }
    rows: list[dict[str, Any]] = []
    for code, config in scenarios.items():
        close = float(config["base"])
        for index, date in enumerate(dates):
            close *= 1.0 + float(config["daily"])
            if index == 68:
                close *= 1.0 + float(config["shock"])
            volume = float(config["volume"]) * (1.0 + (index % 7) * 0.04)
            rows.append(
                {
                    "target_date": date.strftime("%Y-%m-%d"),
                    "Date": date.strftime("%Y-%m-%d"),
                    "code": code,
                    "Code": code,
                    "Open": round_float(close * 0.995),
                    "High": round_float(close * 1.015),
                    "Low": round_float(close * 0.985),
                    "Close": round_float(close),
                    "Volume": round_float(volume),
                }
            )
    return pd.DataFrame(rows)


def fixture_position_scenarios() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "entry_date": "2026-05-08", "code": "2001", "position_size": 100},
            {"target_date": "2026-06-12", "entry_date": "2026-05-15", "code": "2002", "position_size": 100},
            {"target_date": "2026-06-12", "entry_date": "2026-04-24", "code": "2003", "position_size": 100},
            {"target_date": "2026-06-12", "entry_date": "2026-05-29", "code": "2004", "position_size": 100},
            {"target_date": "2026-06-12", "entry_date": "2026-05-22", "code": "2005", "position_size": 100},
            {"target_date": "2026-06-12", "entry_date": "2026-05-01", "code": "2006", "position_size": 100},
        ]
    )


def fixture_opportunity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "2001", "expected_edge_score": 0.18, "buy_rank": 2, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "2002", "expected_edge_score": -0.06, "buy_rank": 42, "downside_risk_score": 0.82, "risk_guard_status": "bad"},
            {"target_date": "2026-06-12", "code": "2003", "expected_edge_score": 0.08, "buy_rank": 7, "downside_risk_score": 0.68, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "2004", "expected_edge_score": 0.04, "buy_rank": 14, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "2005", "expected_edge_score": -0.02, "buy_rank": 31, "downside_risk_score": 0.55, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "2006", "expected_edge_score": 0.06, "buy_rank": 9, "downside_risk_score": 0.62, "risk_guard_status": "ok"},
        ]
    )


def sample_scenarios_from_quotes(quote_frame: pd.DataFrame, *, max_rows: int) -> pd.DataFrame:
    quotes = normalize_quote_frame(quote_frame)
    rows: list[dict[str, Any]] = []
    for code, group in quotes.groupby("code"):
        dates = sorted(group["target_date"].unique().tolist())
        if len(dates) < 25:
            continue
        rows.append({"target_date": dates[-1], "entry_date": dates[-20], "code": code, "position_size": 100})
        if len(rows) >= max_rows:
            break
    return pd.DataFrame(rows)


def normalize_quote_frame(quote_frame: pd.DataFrame) -> pd.DataFrame:
    quotes = quote_frame.copy()
    if "target_date" not in quotes.columns and "Date" in quotes.columns:
        quotes["target_date"] = quotes["Date"]
    if "code" not in quotes.columns and "Code" in quotes.columns:
        quotes["code"] = quotes["Code"]
    required = {"target_date", "code", "Close", "Volume"}
    missing = sorted(required - set(quotes.columns))
    if missing:
        raise ValueError(f"quote frame is missing required columns: {', '.join(missing)}")
    if "High" not in quotes.columns:
        quotes["High"] = quotes["Close"]
    quotes["target_date"] = quotes["target_date"].astype(str)
    quotes["code"] = quotes["code"].astype(str)
    return quotes.sort_values(["code", "target_date"]).drop_duplicates(["target_date", "code"], keep="first")


def normalize_position_scenarios(position_frame: pd.DataFrame) -> pd.DataFrame:
    positions = position_frame.copy()
    required = {"target_date", "entry_date", "code"}
    missing = sorted(required - set(positions.columns))
    if missing:
        raise ValueError(f"position scenarios are missing required columns: {', '.join(missing)}")
    positions["target_date"] = positions["target_date"].astype(str)
    positions["entry_date"] = positions["entry_date"].astype(str)
    positions["code"] = positions["code"].astype(str)
    if "position_size" not in positions.columns:
        positions["position_size"] = 100.0
    return positions


def normalize_opportunity_frame(opportunity_frame: pd.DataFrame) -> pd.DataFrame:
    opportunity = opportunity_frame.copy()
    required = {"target_date", "code"}
    missing = sorted(required - set(opportunity.columns))
    if missing:
        raise ValueError(f"opportunity frame is missing required columns: {', '.join(missing)}")
    opportunity["target_date"] = opportunity["target_date"].astype(str)
    opportunity["code"] = opportunity["code"].astype(str)
    return opportunity.drop_duplicates(["target_date", "code"], keep="first")


def build_phase6b_summary(
    *,
    feature_frame: pd.DataFrame,
    inference_output: pd.DataFrame,
    audit: dict[str, Any],
    output_csv_path: Path,
    output_json_path: Path,
    created_at: str,
    readiness_status: str,
) -> dict[str, Any]:
    add_loss_count = 0
    if not feature_frame.empty and {"add_candidate", "unrealized_return"}.issubset(feature_frame.columns):
        add_loss_count = int(((feature_frame["add_candidate"]) & (feature_frame["unrealized_return"] <= 0)).sum())
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE6C_VALIDATION_DESIGN else "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "output_csv_path": str(output_csv_path),
        "output_json_path": str(output_json_path),
        "dry_run_row_count": int(len(feature_frame)),
        "required_feature_count": len(REQUIRED_FEATURE_COLUMNS),
        "missing_required_features": sorted(set(REQUIRED_FEATURE_COLUMNS) - set(feature_frame.columns)),
        "action_counts": action_counts(inference_output),
        "add_loss_position_count": add_loss_count,
        "audit": audit,
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def action_counts(output: pd.DataFrame) -> dict[str, int]:
    if output.empty or "action" not in output.columns:
        return {"hold_count": 0, "exit_count": 0, "add_candidate_count": 0, "reduce_count": 0}
    return {
        "hold_count": int((output["action"] == "HOLD").sum()),
        "exit_count": int((output["action"] == "EXIT").sum()),
        "add_candidate_count": int((output["action"] == "ADD").sum()),
        "reduce_count": int((output["action"] == "REDUCE").sum()),
    }


def safe_return(current: float, previous: float) -> float:
    return safe_ratio(current, previous, default=1.0) - 1.0


def safe_ratio(numerator: float, denominator: float, *, default: float) -> float:
    if denominator == 0 or np.isnan(denominator):
        return default
    return float(numerator) / float(denominator)


def normalize_scalar(value: float, lower: float, upper: float) -> float:
    if upper == lower:
        return 0.0
    return max(0.0, min(1.0, (float(value) - lower) / (upper - lower)))


def round_float(value: Any, digits: int = 8) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if np.isnan(numeric) or np.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
