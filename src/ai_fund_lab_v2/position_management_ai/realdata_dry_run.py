from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.dataset_builder import read_table
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable
from ai_fund_lab_v2.position_management_ai.alignment_audit import (
    action_distribution,
    alignment_metrics,
    build_alignment_table,
    dataset_to_inference_frame,
    extract_mismatches,
    label_distribution,
)
from ai_fund_lab_v2.position_management_ai.calibration import (
    CALIBRATED_MODEL_VERSION,
    apply_calibrated_baseline_to_label_dataset,
)
from ai_fund_lab_v2.position_management_ai.feature_builder import (
    build_position_features_from_quotes,
    calculate_technical_features,
    fixture_opportunity_frame,
    fixture_position_scenarios,
    fixture_quote_frame,
    normalize_quote_frame,
    round_float,
)
from ai_fund_lab_v2.position_management_ai.inference import audit_position_feature_frame
from ai_fund_lab_v2.position_management_ai.label_dataset import audit_position_label_dataset, build_position_label_dataset_frame

PHASE = "Phase6-F"
READY_FOR_PHASE6G_POLICY_EXPANSION = "READY_FOR_PHASE6G_POLICY_EXPANSION"
BLOCKED_BY_REALDATA_DRY_RUN = "BLOCKED_BY_REALDATA_DRY_RUN"

DEFAULT_QUOTE_PATH = Path(".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet")
DEFAULT_FEATURE_OUTPUT_PATH = Path("reports/position_management_ai/phase6f_realdata_position_features.csv")
DEFAULT_LABEL_OUTPUT_PATH = Path("reports/position_management_ai/phase6f_realdata_label_dataset.csv")
DEFAULT_ALIGNMENT_OUTPUT_PATH = Path("reports/position_management_ai/phase6f_realdata_alignment.csv")
DEFAULT_AUDIT_OUTPUT_PATH = Path("reports/position_management_ai/phase6f_realdata_audit.json")


@dataclass(frozen=True)
class Phase6FRealDataDryRunResult:
    feature_frame: pd.DataFrame
    label_dataset: pd.DataFrame
    alignment: pd.DataFrame
    audit: dict[str, Any]


def run_phase6f_realdata_position_dry_run(
    *,
    quote_path: Path = DEFAULT_QUOTE_PATH,
    feature_output_path: Path = DEFAULT_FEATURE_OUTPUT_PATH,
    label_output_path: Path = DEFAULT_LABEL_OUTPUT_PATH,
    alignment_output_path: Path = DEFAULT_ALIGNMENT_OUTPUT_PATH,
    audit_output_path: Path = DEFAULT_AUDIT_OUTPUT_PATH,
    max_codes: int = 12,
    max_target_dates: int = 3,
    created_at: str | None = None,
) -> Phase6FRealDataDryRunResult:
    created_at = created_at or now_utc()
    data_source = "normalized_daily_quotes"
    opportunity_signal_source = "proxy_from_normalized_quotes"
    if quote_path.is_file():
        quote_frame = read_table(quote_path)
    else:
        quote_frame = fixture_quote_frame()
        data_source = "phase6b_fixture_fallback"
        opportunity_signal_source = "phase6b_fixture_opportunity"

    quotes = normalize_quote_frame(quote_frame)
    scenarios = build_realdata_position_scenarios(quotes, max_codes=max_codes, max_target_dates=max_target_dates)
    if scenarios.empty:
        quotes = fixture_quote_frame()
        scenarios = fixture_position_scenarios()
        opportunity_frame = fixture_opportunity_frame()
        data_source = "phase6b_fixture_fallback"
        opportunity_signal_source = "phase6b_fixture_opportunity"
    else:
        opportunity_frame = build_proxy_opportunity_signals(quotes, scenarios)

    feature_frame = build_position_features_from_quotes(
        position_frame=scenarios,
        quote_frame=quotes,
        opportunity_frame=opportunity_frame,
        created_at=created_at,
    )
    label_dataset = build_position_label_dataset_frame(
        feature_frame=feature_frame,
        quote_frame=quotes,
        created_at=created_at,
    )
    calibrated_frame = apply_calibrated_baseline_to_label_dataset(label_dataset, created_at=created_at)
    alignment = build_alignment_table(calibrated_frame)
    mismatches = extract_mismatches(calibrated_frame)
    label_audit = audit_position_label_dataset(label_dataset, created_at=created_at)
    feature_audit = audit_position_feature_frame(dataset_to_inference_frame(label_dataset), input_holding_count=len(label_dataset), created_at=created_at)
    readiness_status = (
        READY_FOR_PHASE6G_POLICY_EXPANSION
        if label_audit["label_leakage_audit_status"] == "OK" and feature_audit["leakage_audit_status"] == "OK"
        else BLOCKED_BY_REALDATA_DRY_RUN
    )
    audit = build_phase6f_audit(
        quotes=quotes,
        scenarios=scenarios,
        feature_frame=feature_frame,
        label_dataset=label_dataset,
        calibrated_frame=calibrated_frame,
        alignment=alignment,
        mismatches=mismatches,
        label_audit=label_audit,
        feature_audit=feature_audit,
        quote_path=quote_path,
        feature_output_path=feature_output_path,
        label_output_path=label_output_path,
        alignment_output_path=alignment_output_path,
        audit_output_path=audit_output_path,
        data_source=data_source,
        opportunity_signal_source=opportunity_signal_source,
        readiness_status=readiness_status,
        created_at=created_at,
    )

    feature_output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_frame.to_csv(feature_output_path, index=False)
    label_dataset.to_csv(label_output_path, index=False)
    alignment.to_csv(alignment_output_path, index=False)
    write_json(audit_output_path, audit)
    return Phase6FRealDataDryRunResult(feature_frame=feature_frame, label_dataset=label_dataset, alignment=alignment, audit=audit)


def build_realdata_position_scenarios(
    quotes: pd.DataFrame,
    *,
    max_codes: int,
    max_target_dates: int,
) -> pd.DataFrame:
    dates = sorted(quotes["target_date"].astype(str).unique().tolist())
    if len(dates) < 35:
        return pd.DataFrame()
    candidate_target_dates = dates[-30:-5:8]
    target_dates = candidate_target_dates[:max_target_dates]
    codes = sorted(quotes["code"].astype(str).unique().tolist())[:max_codes]
    rows: list[dict[str, Any]] = []
    for target_date in target_dates:
        target_index = dates.index(target_date)
        entry_offsets = (20, 12, 6)
        for code_index, code in enumerate(codes):
            offset = entry_offsets[code_index % len(entry_offsets)]
            if target_index - offset < 0:
                continue
            rows.append(
                {
                    "target_date": target_date,
                    "entry_date": dates[target_index - offset],
                    "code": code,
                    "position_size": 100,
                }
            )
    return pd.DataFrame(rows)


def build_proxy_opportunity_signals(quotes: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios.to_dict("records"):
        target_date = str(scenario["target_date"])
        code = str(scenario["code"])
        history = quotes[(quotes["code"] == code) & (quotes["target_date"] <= target_date)].sort_values("target_date")
        if history.empty:
            continue
        technicals = calculate_technical_features(history)
        trend_component = (technicals["close_over_ma_20d"] - 1.0) * 0.8 + (technicals["ma_5_20_ratio"] - 1.0) * 0.6
        momentum_component = 0.6 * technicals["return_20d"] + 0.3 * technicals["return_5d"]
        risk_component = min(max(technicals["volatility_20d"] / 0.08, 0.0), 1.0)
        expected_edge_score = round_float(momentum_component + trend_component - 0.05 * risk_component)
        downside_risk_score = round_float(
            min(
                max(
                    0.35
                    + 0.40 * risk_component
                    + 0.20 * max(0.0, 1.0 - technicals["close_over_ma_20d"])
                    + 0.20 * max(0.0, 1.0 - technicals["ma_5_20_ratio"]),
                    0.0,
                ),
                1.0,
            )
        )
        rows.append(
            {
                "target_date": target_date,
                "code": code,
                "expected_edge_score": expected_edge_score,
                "downside_risk_score": downside_risk_score,
                "risk_guard_status": "bad" if downside_risk_score >= 0.75 else "ok",
            }
        )
    opportunity = pd.DataFrame(rows)
    if opportunity.empty:
        return opportunity
    opportunity = opportunity.sort_values(["target_date", "expected_edge_score", "code"], ascending=[True, False, True]).copy()
    opportunity["buy_rank"] = opportunity.groupby("target_date")["expected_edge_score"].rank(method="first", ascending=False).astype(int)
    return opportunity


def build_phase6f_audit(
    *,
    quotes: pd.DataFrame,
    scenarios: pd.DataFrame,
    feature_frame: pd.DataFrame,
    label_dataset: pd.DataFrame,
    calibrated_frame: pd.DataFrame,
    alignment: pd.DataFrame,
    mismatches: pd.DataFrame,
    label_audit: dict[str, Any],
    feature_audit: dict[str, Any],
    quote_path: Path,
    feature_output_path: Path,
    label_output_path: Path,
    alignment_output_path: Path,
    audit_output_path: Path,
    data_source: str,
    opportunity_signal_source: str,
    readiness_status: str,
    created_at: str,
) -> dict[str, Any]:
    target_dates = sorted(label_dataset["target_date"].astype(str).unique().tolist()) if "target_date" in label_dataset.columns else []
    codes = sorted(label_dataset["code"].astype(str).unique().tolist()) if "code" in label_dataset.columns else []
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE6G_POLICY_EXPANSION else "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "quote_path": str(quote_path),
        "data_source": data_source,
        "opportunity_signal_source": opportunity_signal_source,
        "calibrated_model_version": CALIBRATED_MODEL_VERSION,
        "feature_output_path": str(feature_output_path),
        "label_output_path": str(label_output_path),
        "alignment_output_path": str(alignment_output_path),
        "audit_output_path": str(audit_output_path),
        "quote_date_min": str(quotes["target_date"].min()) if not quotes.empty else "",
        "quote_date_max": str(quotes["target_date"].max()) if not quotes.empty else "",
        "quote_row_count": int(len(quotes)),
        "quote_code_count": int(quotes["code"].nunique()) if "code" in quotes.columns else 0,
        "scenario_row_count": int(len(scenarios)),
        "feature_row_count": int(len(feature_frame)),
        "label_row_count": int(len(label_dataset)),
        "alignment_row_count": int(len(alignment)),
        "target_date_count": len(target_dates),
        "target_dates": target_dates,
        "code_count": len(codes),
        "codes": codes,
        "action_distribution": action_distribution(calibrated_frame),
        "label_distribution": label_distribution(calibrated_frame),
        "alignment_metrics": alignment_metrics(calibrated_frame),
        "mismatch_count": int(len(mismatches)),
        "add_loss_position_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["feature__unrealized_return"] <= 0)).sum()),
        "add_exit_label_overlap_count": int(((calibrated_frame["action"] == "ADD") & (calibrated_frame["label__label_exit_before_drawdown"])).sum()),
        "exit_continue_winner_count": int(((calibrated_frame["action"] == "EXIT") & (calibrated_frame["label__label_continue_winner"])).sum()),
        "forbidden_feature_audit_status": "OK" if feature_audit["leakage_audit_status"] == "OK" and label_audit["forbidden_feature_audit_status"] == "OK" else "ERROR",
        "leakage_audit_status": "OK" if feature_audit["leakage_audit_status"] == "OK" and label_audit["label_leakage_audit_status"] == "OK" else "ERROR",
        "feature_audit": feature_audit,
        "label_audit": label_audit,
        "training_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def action_distribution(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty or "action" not in frame.columns:
        return {}
    return {str(action): int(count) for action, count in frame["action"].value_counts().sort_index().items()}


def label_distribution(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    labels = (
        "label__label_continue_winner",
        "label__label_exit_before_drawdown",
        "label__label_add_candidate",
        "label__label_reduce_candidate",
    )
    distribution: dict[str, dict[str, int]] = {}
    for label in labels:
        if label not in frame.columns:
            continue
        counts = frame[label].astype(bool).value_counts().to_dict()
        distribution[label] = {"true": int(counts.get(True, 0)), "false": int(counts.get(False, 0))}
    return distribution


def alignment_metrics(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "hold_continue_winner_rate": action_label_rate(frame, "HOLD", "label__label_continue_winner"),
        "hold_exit_label_rate": action_label_rate(frame, "HOLD", "label__label_exit_before_drawdown"),
        "exit_exit_label_rate": action_label_rate(frame, "EXIT", "label__label_exit_before_drawdown"),
        "exit_continue_winner_rate": action_label_rate(frame, "EXIT", "label__label_continue_winner"),
        "add_add_label_rate": action_label_rate(frame, "ADD", "label__label_add_candidate"),
        "add_exit_label_rate": action_label_rate(frame, "ADD", "label__label_exit_before_drawdown"),
        "reduce_reduce_label_rate": action_label_rate(frame, "REDUCE", "label__label_reduce_candidate"),
        "reduce_continue_winner_rate": action_label_rate(frame, "REDUCE", "label__label_continue_winner"),
    }


def action_label_rate(frame: pd.DataFrame, action: str, label: str) -> float:
    group = frame[frame["action"] == action] if "action" in frame.columns else pd.DataFrame()
    if group.empty or label not in group.columns:
        return 0.0
    return round(float(group[label].astype(bool).mean()), 6)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
