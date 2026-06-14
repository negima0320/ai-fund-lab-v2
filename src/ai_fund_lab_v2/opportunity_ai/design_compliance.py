from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.policy_finalization import FINAL_OUTPUT_COLUMNS
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable

PHASE = "Phase5-M"
PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS = "PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS"
PHASE5_DESIGN_NON_COMPLIANT = "PHASE5_DESIGN_NON_COMPLIANT"

DEFAULT_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_PHASE5L_SUMMARY_PATH = Path("reports/opportunity_ai/phase5l/completion_summary.json")
DEFAULT_PHASE5L_AUDIT_PATH = Path("reports/opportunity_ai/phase5l/completion_audit.json")
DEFAULT_PHASE5I_AUDIT_PATH = Path("reports/opportunity_ai/phase5i/full_history_audit.json")
DEFAULT_PHASE5K_SCHEMA_PATH = Path("reports/opportunity_ai/phase5k/final_opportunity_output_schema.json")
DEFAULT_PHASE5K_AUDIT_PATH = Path("reports/opportunity_ai/phase5k/policy_finalization_audit.json")
DEFAULT_PHASE5J_AUDIT_PATH = Path("reports/opportunity_ai/phase5j/calibration_audit.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5m")

REVIEW_FILENAME = "design_compliance_review.json"
FEATURE_COVERAGE_FILENAME = "design_compliance_feature_coverage.csv"
AUDIT_FILENAME = "design_compliance_audit.json"

FORBIDDEN_FEATURE_TERMS = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "trade_result",
    "trade_profit",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "backtest",
    "pm_multiplier",
    "paper_trading",
    "expected_edge_score",
    "buy_rank",
    "opportunity_output",
)


@dataclass(frozen=True)
class DesignComplianceResult:
    review: dict[str, Any]
    audit: dict[str, Any]
    feature_coverage: pd.DataFrame


def run_design_compliance_review(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    phase5l_summary_path: Path = DEFAULT_PHASE5L_SUMMARY_PATH,
    phase5l_audit_path: Path = DEFAULT_PHASE5L_AUDIT_PATH,
    phase5i_audit_path: Path = DEFAULT_PHASE5I_AUDIT_PATH,
    phase5k_schema_path: Path = DEFAULT_PHASE5K_SCHEMA_PATH,
    phase5k_audit_path: Path = DEFAULT_PHASE5K_AUDIT_PATH,
    phase5j_audit_path: Path = DEFAULT_PHASE5J_AUDIT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> DesignComplianceResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / REVIEW_FILENAME
    coverage_path = output_dir / FEATURE_COVERAGE_FILENAME
    audit_path = output_dir / AUDIT_FILENAME

    inputs = {
        "dataset": dataset_path,
        "model": model_path,
        "phase5l_summary": phase5l_summary_path,
        "phase5l_audit": phase5l_audit_path,
        "phase5i_audit": phase5i_audit_path,
        "phase5k_schema": phase5k_schema_path,
        "phase5k_audit": phase5k_audit_path,
        "phase5j_audit": phase5j_audit_path,
    }
    missing_inputs = [str(path) for path in inputs.values() if not path.is_file()]
    if missing_inputs:
        audit = build_blocked_audit(created_at, missing_inputs)
        review = build_review_shell(created_at, PHASE5_DESIGN_NON_COMPLIANT, audit, review_path, coverage_path, audit_path)
        coverage = pd.DataFrame()
        write_outputs(review_path, coverage_path, audit_path, review, coverage, audit)
        return DesignComplianceResult(review=review, audit=audit, feature_coverage=coverage)

    dataset = pd.read_parquet(dataset_path)
    model_payload = load_model_payload(model_path)
    phase5l_summary = read_json(phase5l_summary_path)
    phase5l_audit = read_json(phase5l_audit_path)
    phase5i_audit = read_json(phase5i_audit_path)
    phase5k_schema = read_json(phase5k_schema_path)
    phase5k_audit = read_json(phase5k_audit_path)
    phase5j_audit = read_json(phase5j_audit_path)

    feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in dataset.columns if str(c).startswith("feature__")))
    label_columns = sorted(c for c in dataset.columns if str(c).startswith("label__"))
    feature_coverage = build_feature_coverage(feature_columns)
    category_counts = build_category_counts(feature_coverage)
    role_audit = audit_role_scope(phase5l_summary, phase5l_audit, phase5k_audit)
    source_audit = audit_source_of_truth(feature_columns)
    forbidden_audit = audit_forbidden_features(feature_columns, phase5j_audit, phase5k_audit)
    label_audit = audit_labels(label_columns)
    schema_audit = audit_output_schema(phase5k_schema)
    full_history_audit = audit_full_history(phase5i_audit, phase5l_summary)
    quality_audit = audit_quality_calibration(phase5j_audit, phase5k_audit)
    safety_audit = audit_safety(phase5l_summary, phase5l_audit)
    known_gaps = build_known_gaps(feature_coverage)
    readiness_status = resolve_readiness(
        role_audit=role_audit,
        source_audit=source_audit,
        forbidden_audit=forbidden_audit,
        label_audit=label_audit,
        schema_audit=schema_audit,
        full_history_audit=full_history_audit,
        quality_audit=quality_audit,
        safety_audit=safety_audit,
    )
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "promotion_ready": False,
        "actual_feature_count": len(feature_columns),
        "actual_feature_columns": feature_columns,
        "label_column_count": len(label_columns),
        "label_columns": label_columns,
        "category_feature_counts": category_counts,
        "role_scope_audit": role_audit,
        "source_of_truth_audit": source_audit,
        "forbidden_feature_audit": forbidden_audit,
        "label_compliance_audit": label_audit,
        "output_schema_audit": schema_audit,
        "full_history_audit": full_history_audit,
        "quality_calibration_audit": quality_audit,
        "safety_audit": safety_audit,
        "known_gaps": known_gaps,
        "design_compliant": readiness_status == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS,
    }
    review = {
        "phase": PHASE,
        "status": "OK" if readiness_status == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS else "NON_COMPLIANT",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "review_path": str(review_path),
        "audit_path": str(audit_path),
        "feature_coverage_path": str(coverage_path),
        "promotion_ready": False,
        "phase5_completion_status": phase5l_summary.get("readiness_status"),
        "phase5_complete": phase5l_summary.get("phase5_complete"),
        "phase6_handoff_ready": phase5l_summary.get("phase6_handoff_ready"),
        "actual_feature_count": len(feature_columns),
        "actual_feature_columns": feature_columns,
        "category_feature_counts": category_counts,
        "unused_designed_features": known_gaps["unused_designed_features"],
        "unused_feature_count": known_gaps["unused_feature_count"],
        "known_gap_count": known_gaps["known_gap_count"],
        "role_scope_audit": role_audit,
        "source_of_truth_audit": source_audit,
        "forbidden_feature_audit": forbidden_audit,
        "label_compliance_audit": label_audit,
        "output_schema_audit": schema_audit,
        "full_history_audit": full_history_audit,
        "quality_calibration_audit": quality_audit,
        "safety_audit": safety_audit,
        "design_review_conclusion": build_conclusion(readiness_status, known_gaps),
        "recommended_next_action": (
            "Proceed to Phase6 with known feature coverage gaps documented."
            if readiness_status == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS
            else "Resolve non-compliance before Phase6."
        ),
    }
    write_outputs(review_path, coverage_path, audit_path, review, feature_coverage, audit)
    return DesignComplianceResult(review=review, audit=audit, feature_coverage=feature_coverage)


def build_feature_coverage(feature_columns: list[str]) -> pd.DataFrame:
    actual = set(feature_columns)
    rows = []
    for spec in designed_feature_specs():
        used_columns = [column for column in spec["actual_columns"] if column in actual]
        rows.append(
            {
                "category": spec["category"],
                "design_feature": spec["design_feature"],
                "planned_status": spec["planned_status"],
                "used_in_training": bool(used_columns),
                "actual_feature_columns": ",".join(used_columns),
                "actual_feature_count": len(used_columns),
                "unused_reason": "" if used_columns else spec["unused_reason"],
                "completion_impact": "OK" if used_columns else spec["completion_impact"],
            }
        )
    actual_mapped = {column for spec in designed_feature_specs() for column in spec["actual_columns"] if column in actual}
    for column in sorted(actual - actual_mapped):
        rows.append(
            {
                "category": classify_actual_feature(column),
                "design_feature": column.replace("feature__", ""),
                "planned_status": "implemented_extra_or_data_quality",
                "used_in_training": True,
                "actual_feature_columns": column,
                "actual_feature_count": 1,
                "unused_reason": "",
                "completion_impact": "OK",
            }
        )
    return pd.DataFrame(rows)


def designed_feature_specs() -> list[dict[str, Any]]:
    return [
        spec("Candidate AI output", "candidate_score", ["feature__candidate_score"], "implemented", ""),
        spec("Candidate AI output", "candidate_rank", ["feature__candidate_rank"], "implemented", ""),
        spec("Candidate AI output", "candidate_reason", ["feature__candidate_reason"], "implemented", ""),
        spec("Market data", "close", [], "designed_candidate", "Phase5-C candidate; raw OHLCV not connected as direct feature, derived momentum/trend features used."),
        spec("Market data", "high", [], "designed_candidate", "Phase5-C candidate; high-derived range feature not implemented in Phase5."),
        spec("Market data", "low", [], "designed_candidate", "Phase5-C candidate; low-derived range feature not implemented in Phase5."),
        spec("Market data", "volume", [], "designed_candidate", "Raw volume not used directly; liquidity and volume momentum derivatives are used."),
        spec("Technical: price momentum", "return_5d", ["feature__price_momentum_return_5d"], "implemented", ""),
        spec("Technical: price momentum", "return_20d", ["feature__price_momentum_return_20d"], "implemented", ""),
        spec("Technical: price momentum", "return_60d", ["feature__price_momentum_return_60d"], "implemented", ""),
        spec("Technical: volume momentum", "volume_ratio_5d", ["feature__volume_momentum_ratio_5d"], "implemented", ""),
        spec("Technical: volume momentum", "volume_ratio_1d_20d", ["feature__volume_momentum_ratio_1d_20d"], "implemented", ""),
        spec("Technical: trend", "close_over_ma20", ["feature__trend_close_over_ma_20d"], "implemented", ""),
        spec("Technical: trend", "ma5_over_ma20", ["feature__trend_ma_5_20_ratio"], "implemented", ""),
        spec("Technical: trend", "ma20_over_ma60", ["feature__trend_ma_20_60_ratio"], "implemented", ""),
        spec("Technical: volatility", "return_std_20d", ["feature__volatility_return_std_20d"], "implemented", ""),
        spec("Technical: volatility", "return_std_60d", [], "designed_candidate", "Phase5-C candidate; 60d volatility not connected in Phase5 implementation."),
        spec("Technical: volatility", "high_low_range", [], "designed_candidate", "Phase5-C candidate; high/low range feature not connected."),
        spec("Liquidity", "avg_volume_20d", ["feature__liquidity_avg_volume_20d"], "implemented", ""),
        spec("Liquidity", "avg_trading_value_20d", [], "designed_candidate", "J-Quants-derived candidate; trading value feature not connected."),
        spec("Fundamental", "sales_growth_rate", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "operating_profit_growth_rate", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "ordinary_profit_growth_rate", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "net_income_growth_rate", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "roe", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "equity_ratio", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Fundamental", "operating_margin", [], "known_gap", "J-Quants fins/as_of_date join not connected in Phase5 full-history dataset."),
        spec("Market environment", "TOPIX", [], "known_gap", "J-Quants index/market environment feature join not connected in Phase5 dataset."),
        spec("Market environment", "market_trend", [], "known_gap", "Market trend feature join not connected in Phase5 dataset."),
        spec("Sector strength", "sector_strength", [], "known_gap", "Sector strength feature join not connected in Phase5 dataset."),
    ]


def spec(category: str, design_feature: str, actual_columns: list[str], planned_status: str, unused_reason: str) -> dict[str, Any]:
    return {
        "category": category,
        "design_feature": design_feature,
        "actual_columns": actual_columns,
        "planned_status": planned_status,
        "unused_reason": unused_reason,
        "completion_impact": "known_gap_future_improvement" if unused_reason else "OK",
    }


def build_category_counts(coverage: pd.DataFrame) -> dict[str, Any]:
    result = {}
    for category, group in coverage.groupby("category"):
        result[str(category)] = {
            "designed_feature_count": int(len(group)),
            "used_design_feature_count": int(group["used_in_training"].sum()),
            "actual_feature_column_count": int(group["actual_feature_count"].sum()),
            "unused_design_feature_count": int((~group["used_in_training"]).sum()),
        }
    return result


def build_known_gaps(coverage: pd.DataFrame) -> dict[str, Any]:
    unused = coverage[~coverage["used_in_training"]].copy()
    return {
        "unused_feature_count": int(len(unused)),
        "known_gap_count": int((unused["completion_impact"] == "known_gap_future_improvement").sum()),
        "unused_designed_features": unused[
            ["category", "design_feature", "planned_status", "unused_reason", "completion_impact"]
        ].to_dict("records"),
        "completion_blocking_gap_count": int((unused["completion_impact"] != "known_gap_future_improvement").sum()),
    }


def audit_role_scope(phase5l_summary: dict[str, Any], phase5l_audit: dict[str, Any], phase5k_audit: dict[str, Any]) -> dict[str, Any]:
    scope = phase5l_audit.get("scope_boundary_audit", {})
    return {
        "opportunity_ai_role": "Candidate Top50 20-business-day expected-value ranking AI",
        "ranks_candidate_top50": bool(scope.get("ranks_candidate_top50", True)),
        "candidate_ai_scope_not_invaded": bool(scope.get("does_not_extract_candidates", True)),
        "position_management_not_invaded": bool(scope.get("does_not_manage_positions", True)),
        "capital_allocation_not_invaded": bool(scope.get("does_not_allocate_capital", True)),
        "broker_order_scope_not_invaded": bool(scope.get("does_not_place_orders", True)),
        "buy_count_not_decided": bool(scope.get("does_not_decide_purchase_count", not phase5k_audit.get("phase5_decides_purchase_count", True))),
        "phase5_complete": bool(phase5l_summary.get("phase5_complete", False)),
        "role_compliant": bool(scope.get("scope_ok", False)),
    }


def audit_source_of_truth(feature_columns: list[str]) -> dict[str, Any]:
    non_jquants_or_allowed = []
    for column in feature_columns:
        if column in {"feature__candidate_score", "feature__candidate_rank", "feature__candidate_reason"}:
            continue
        if not column.startswith("feature__"):
            non_jquants_or_allowed.append(column)
    return {
        "source_rule": "J-Quants API-derived features plus current Candidate AI score/rank/reason only.",
        "non_jquants_or_disallowed_feature_columns": non_jquants_or_allowed,
        "source_of_truth_compliant": not non_jquants_or_allowed,
    }


def audit_forbidden_features(feature_columns: list[str], phase5j_audit: dict[str, Any], phase5k_audit: dict[str, Any]) -> dict[str, Any]:
    forbidden_columns = [
        column
        for column in feature_columns
        if any(term in column.lower() for term in FORBIDDEN_FEATURE_TERMS)
    ]
    return {
        "forbidden_feature_columns": forbidden_columns,
        "forbidden_feature_column_count": len(forbidden_columns),
        "phase5j_forbidden_feature_column_count": int(phase5j_audit.get("forbidden_feature_column_count", 0)),
        "phase5j_future_feature_column_count": int(phase5j_audit.get("future_feature_column_count", 0)),
        "phase5k_forbidden_feature_column_count": int(phase5k_audit.get("forbidden_feature_column_count", 0)),
        "phase5k_future_feature_column_count": int(phase5k_audit.get("future_feature_column_count", 0)),
        "forbidden_feature_compliant": (
            not forbidden_columns
            and int(phase5j_audit.get("forbidden_feature_column_count", 0)) == 0
            and int(phase5j_audit.get("future_feature_column_count", 0)) == 0
            and int(phase5k_audit.get("forbidden_feature_column_count", 0)) == 0
            and int(phase5k_audit.get("future_feature_column_count", 0)) == 0
        ),
    }


def audit_labels(label_columns: list[str]) -> dict[str, Any]:
    required = {
        "label__expected_edge_label_20d",
        "label__future_return_20d",
        "label__future_max_return_20d",
        "label__future_max_drawdown_20d",
        "label__downside_bad_20d",
        "label__top_decile_20d",
    }
    missing = sorted(required - set(label_columns))
    non_20d_labels = [column for column in label_columns if column.startswith("label__") and "_20d" not in column]
    return {
        "required_20d_label_columns": sorted(required),
        "actual_label_columns": label_columns,
        "missing_required_label_columns": missing,
        "non_20d_label_columns": non_20d_labels,
        "expected_edge_label_20d_present": "label__expected_edge_label_20d" in label_columns,
        "future_labels_limited_to_label_prefix": all(column.startswith("label__") for column in label_columns),
        "horizon_20d_compliant": not missing and not non_20d_labels,
        "label_compliant": not missing and not non_20d_labels and "label__expected_edge_label_20d" in label_columns,
    }


def audit_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    actual = list(schema.get("output_columns", []))
    missing = [column for column in FINAL_OUTPUT_COLUMNS if column not in actual]
    return {
        "required_columns": FINAL_OUTPUT_COLUMNS,
        "actual_columns": actual,
        "missing_columns": missing,
        "risk_guard_status_present": "risk_guard_status" in actual,
        "calibration_policy_name_present": "calibration_policy_name" in actual,
        "schema_compliant": not missing,
    }


def audit_full_history(phase5i_audit: dict[str, Any], phase5l_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_date_count": int(phase5i_audit.get("target_date_count", 0)),
        "candidate_rows": int(phase5i_audit.get("candidate_rows", 0)),
        "dataset_rows": int(phase5i_audit.get("dataset_rows", 0)),
        "train_rows": int(phase5i_audit.get("train_rows", 0)),
        "validation_rows": int(phase5i_audit.get("validation_rows", 0)),
        "test_rows": int(phase5i_audit.get("test_rows", 0)),
        "leakage_status": phase5i_audit.get("leakage_status"),
        "model_unique_score_count": int(phase5i_audit.get("model_unique_score_count", 0)),
        "all_same_score": bool(phase5i_audit.get("all_same_score", True)),
        "monthly_only_completion": False,
        "phase5l_full_history_ready": bool(phase5l_summary.get("full_history_ready", False)),
        "full_history_compliant": bool(
            phase5i_audit.get("dataset_rows", 0) > 0
            and phase5i_audit.get("candidate_rows", 0) > 0
            and phase5i_audit.get("leakage_status") == "OK"
            and int(phase5i_audit.get("model_unique_score_count", 0)) > 1
            and not bool(phase5i_audit.get("all_same_score", True))
        ),
    }


def audit_quality_calibration(phase5j_audit: dict[str, Any], phase5k_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase5j_strategy_count": int(phase5j_audit.get("strategy_count", 0)),
        "policy_candidate_count": int(phase5k_audit.get("policy_candidate_count", 0)),
        "top6_10_tail_dilution_status": phase5k_audit.get("top6_10_tail_dilution_status"),
        "simple_rule_top5_requires_risk_guard": bool(phase5k_audit.get("simple_rule_top5_requires_risk_guard", False)),
        "fixed_top10_finalized_as_buy_count": bool(phase5k_audit.get("fixed_top10_finalized_as_buy_count", True)),
        "quality_calibration_compliant": bool(
            int(phase5j_audit.get("strategy_count", 0)) >= 10
            and int(phase5k_audit.get("policy_candidate_count", 0)) >= 5
            and phase5k_audit.get("top6_10_tail_dilution_status") == "TAIL_DILUTION_CONFIRMED"
            and phase5k_audit.get("simple_rule_top5_requires_risk_guard") is True
            and phase5k_audit.get("fixed_top10_finalized_as_buy_count") is False
        ),
    }


def audit_safety(phase5l_summary: dict[str, Any], phase5l_audit: dict[str, Any]) -> dict[str, Any]:
    safety = phase5l_audit.get("safety_boundary_audit", {})
    return {
        "broker_api_executed": bool(safety.get("broker_api_executed", phase5l_summary.get("broker_api_executed", False))),
        "paper_trading_executed": bool(safety.get("paper_trading_executed", phase5l_summary.get("paper_trading_executed", False))),
        "order_executed": bool(safety.get("order_executed", phase5l_summary.get("order_executed", False))),
        "capital_allocation_executed": bool(safety.get("capital_allocation_executed", phase5l_summary.get("capital_allocation_executed", False))),
        "promotion_performed": bool(safety.get("promotion_performed", phase5l_summary.get("promotion_performed", False))),
        "reader_switch_performed": bool(safety.get("reader_switch_performed", phase5l_summary.get("reader_switch_performed", False))),
        "phase4_artifact_destroyed_flag": bool(safety.get("phase4_artifact_destroyed_flag", False)),
        "mock_path_overwrite_flag": bool(safety.get("mock_path_overwrite_flag", False)),
        "safety_compliant": bool(safety.get("safety_ok", False)),
    }


def resolve_readiness(
    *,
    role_audit: dict[str, Any],
    source_audit: dict[str, Any],
    forbidden_audit: dict[str, Any],
    label_audit: dict[str, Any],
    schema_audit: dict[str, Any],
    full_history_audit: dict[str, Any],
    quality_audit: dict[str, Any],
    safety_audit: dict[str, Any],
) -> str:
    compliant = (
        role_audit["role_compliant"]
        and source_audit["source_of_truth_compliant"]
        and forbidden_audit["forbidden_feature_compliant"]
        and label_audit["label_compliant"]
        and schema_audit["schema_compliant"]
        and full_history_audit["full_history_compliant"]
        and quality_audit["quality_calibration_compliant"]
        and safety_audit["safety_compliant"]
    )
    return PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS if compliant else PHASE5_DESIGN_NON_COMPLIANT


def build_conclusion(readiness_status: str, known_gaps: dict[str, Any]) -> dict[str, Any]:
    return {
        "judgment": readiness_status,
        "phase6_ready": readiness_status == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS,
        "known_gaps_are_completion_blocking": known_gaps["completion_blocking_gap_count"] > 0,
        "summary": (
            "Phase5 is design-compliant as an Opportunity AI ranking phase, with known feature coverage gaps documented."
            if readiness_status == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS
            else "Phase5 has design compliance blockers that should be resolved before Phase6."
        ),
    }


def classify_actual_feature(column: str) -> str:
    if "missing_flags" in column:
        return "Data quality"
    if "candidate" in column:
        return "Candidate AI output"
    if "price_momentum" in column:
        return "Technical: price momentum"
    if "volume_momentum" in column:
        return "Technical: volume momentum"
    if "trend" in column:
        return "Technical: trend"
    if "volatility" in column:
        return "Technical: volatility"
    if "liquidity" in column:
        return "Liquidity"
    return "Other"


def build_blocked_audit(created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": PHASE5_DESIGN_NON_COMPLIANT,
        "promotion_ready": False,
        "missing_inputs": missing_inputs,
        "design_compliant": False,
    }


def build_review_shell(
    created_at: str,
    readiness_status: str,
    audit: dict[str, Any],
    review_path: Path,
    coverage_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "NON_COMPLIANT",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "review_path": str(review_path),
        "audit_path": str(audit_path),
        "feature_coverage_path": str(coverage_path),
        "promotion_ready": False,
        "audit": audit,
    }


def load_model_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_outputs(
    review_path: Path,
    coverage_path: Path,
    audit_path: Path,
    review: dict[str, Any],
    coverage: pd.DataFrame,
    audit: dict[str, Any],
) -> None:
    write_json(review_path, review)
    write_json(audit_path, audit)
    coverage.to_csv(coverage_path, index=False)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
