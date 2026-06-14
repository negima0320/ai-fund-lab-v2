from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable

PHASE = "Phase5-K"
READY_FOR_PHASE5L_COMPLETION_AUDIT = "READY_FOR_PHASE5L_COMPLETION_AUDIT"
NEEDS_PHASE5J_REVIEW = "NEEDS_PHASE5J_REVIEW"

DEFAULT_PHASE5J_DIR = Path("reports/opportunity_ai/phase5j")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5k")

CALIBRATION_METRICS_FILENAME = "calibration_metrics.json"
CALIBRATION_AUDIT_FILENAME = "calibration_audit.json"
CALIBRATION_BY_STRATEGY_FILENAME = "calibration_by_strategy.csv"
RECOMMENDED_POLICY_FILENAME = "recommended_policy.json"

SUMMARY_FILENAME = "policy_finalization_summary.json"
AUDIT_FILENAME = "policy_finalization_audit.json"
SCHEMA_FILENAME = "final_opportunity_output_schema.json"
POLICY_CANDIDATES_FILENAME = "final_policy_candidates.csv"

FINAL_OUTPUT_COLUMNS = [
    "target_date",
    "code",
    "expected_edge_score",
    "buy_rank",
    "expected_return_horizon",
    "downside_risk_score",
    "buy_reason",
    "no_buy_reason",
    "candidate_score",
    "candidate_rank",
    "model_version",
    "feature_version",
    "inference_run_id",
    "created_at",
    "is_top5",
    "is_top10",
    "is_top20",
    "risk_guard_status",
    "calibration_policy_name",
]


@dataclass(frozen=True)
class PolicyFinalizationResult:
    summary: dict[str, Any]
    audit: dict[str, Any]
    output_schema: dict[str, Any]
    policy_candidates: pd.DataFrame


def finalize_opportunity_policy(
    *,
    phase5j_dir: Path = DEFAULT_PHASE5J_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> PolicyFinalizationResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = phase5j_paths(phase5j_dir)
    output_paths = {
        "summary": output_dir / SUMMARY_FILENAME,
        "audit": output_dir / AUDIT_FILENAME,
        "schema": output_dir / SCHEMA_FILENAME,
        "policy_candidates": output_dir / POLICY_CANDIDATES_FILENAME,
    }
    missing_inputs = [str(path) for path in paths.values() if not path.is_file()]
    if missing_inputs:
        audit = build_blocked_audit(created_at=created_at, missing_inputs=missing_inputs, reason="Phase5-J artifacts are missing.")
        summary = build_summary_shell(created_at=created_at, readiness_status=NEEDS_PHASE5J_REVIEW, status="BLOCKED", output_paths=output_paths, audit=audit)
        schema = build_final_output_schema(created_at=created_at)
        candidates = pd.DataFrame()
        write_outputs(output_paths, summary, audit, schema, candidates)
        return PolicyFinalizationResult(summary, audit, schema, candidates)

    calibration_metrics = read_json(paths["metrics"])
    calibration_audit = read_json(paths["audit"])
    recommended_policy = read_json(paths["recommended_policy"])
    by_strategy = pd.read_csv(paths["by_strategy"])

    schema = build_final_output_schema(created_at=created_at)
    candidates = build_policy_candidates(by_strategy)
    risk_guard_policy = build_risk_guard_policy(recommended_policy, candidates)
    final_recommendation = build_final_recommendation(candidates, recommended_policy, risk_guard_policy)
    safety = build_safety_rules()
    audit = build_audit(
        created_at=created_at,
        calibration_metrics=calibration_metrics,
        calibration_audit=calibration_audit,
        recommended_policy=recommended_policy,
        policy_candidates=candidates,
        schema=schema,
        risk_guard_policy=risk_guard_policy,
    )
    readiness_status = resolve_readiness(audit)
    audit["readiness_status"] = readiness_status
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY_FOR_PHASE5L_COMPLETION_AUDIT else "REVIEW_REQUIRED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "phase5j_artifacts": {name: str(path) for name, path in paths.items()},
        "output_paths": {name: str(path) for name, path in output_paths.items()},
        "promotion_ready": False,
        "opportunity_ai_final_role": "20-business-day expected-value ranking AI for Candidate Top50.",
        "scope_boundary": {
            "does_rank_candidate_top50": True,
            "does_define_ranking_policy_candidates": True,
            "does_decide_purchase_count": False,
            "does_allocate_capital": False,
            "does_manage_positions": False,
            "does_place_orders": False,
            "does_promote_model": False,
            "does_switch_readers": False,
        },
        "final_output_schema_columns": FINAL_OUTPUT_COLUMNS,
        "policy_candidates": candidates.to_dict("records"),
        "risk_guard_policy": risk_guard_policy,
        "top6_10_tail_conclusion": {
            "status": "TAIL_DILUTION_CONFIRMED",
            "fixed_top10_policy": "not_finalized_as_fixed_purchase_count",
            "phase5_policy_position": "Top10 should remain a ranking band with score gap, risk guard, or variable-count handling.",
            "phase_boundary": "The actual number of shares or names to buy belongs to later Capital Allocation / operational policy phases.",
        },
        "final_recommendation": final_recommendation,
        "safety_and_source_of_truth": safety,
        "phase5l_handoff": {
            "next_phase": "Phase5-L Completion Audit",
            "inputs": [
                str(output_paths["summary"]),
                str(output_paths["audit"]),
                str(output_paths["schema"]),
                str(output_paths["policy_candidates"]),
            ],
            "expected_completion_audit_focus": [
                "Phase5 scope boundary",
                "leakage and forbidden feature checks",
                "promotion_ready remains false",
                "final schema consistency",
                "policy candidate documentation completeness",
            ],
        },
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-L Completion Audit."
            if readiness_status == READY_FOR_PHASE5L_COMPLETION_AUDIT
            else "Review Phase5-J artifacts and policy finalization blockers."
        ),
    }
    write_outputs(output_paths, summary, audit, schema, candidates)
    return PolicyFinalizationResult(summary, audit, schema, candidates)


def phase5j_paths(phase5j_dir: Path) -> dict[str, Path]:
    return {
        "metrics": phase5j_dir / CALIBRATION_METRICS_FILENAME,
        "audit": phase5j_dir / CALIBRATION_AUDIT_FILENAME,
        "by_strategy": phase5j_dir / CALIBRATION_BY_STRATEGY_FILENAME,
        "recommended_policy": phase5j_dir / RECOMMENDED_POLICY_FILENAME,
    }


def build_policy_candidates(by_strategy: pd.DataFrame) -> pd.DataFrame:
    candidate_names = {
        "current_model_top5": {
            "policy_label": "Current model Top5 ranking band",
            "policy_family": "current_model",
            "phase5_position": "candidate",
            "risk_guard_requirement": "recommended",
            "notes": "Top5 quality is promising, but test mean return was slightly below CandidateTop50 while max-return and risk metrics improved.",
        },
        "current_model_top10": {
            "policy_label": "Current model fixed Top10 ranking band",
            "policy_family": "current_model",
            "phase5_position": "caution",
            "risk_guard_requirement": "required",
            "notes": "Fixed Top10 remains affected by Top6-10 tail dilution and should not be treated as a fixed purchase count.",
        },
        "current_model_top20": {
            "policy_label": "Current model Top20 ranking band",
            "policy_family": "current_model",
            "phase5_position": "conservative_fallback",
            "risk_guard_requirement": "recommended",
            "notes": "Top20 is more stable than fixed Top10 in full-history validation, but it is a ranking band for downstream phases.",
        },
        "simple_rule_top5": {
            "policy_label": "Simple-rule-informed Top5 candidate",
            "policy_family": "simple_rule",
            "phase5_position": "risk_guard_candidate",
            "risk_guard_requirement": "required",
            "notes": "Return, future max return, and top-decile capture are strong; downside_bad_rate worsens, so promotion is not allowed as-is.",
        },
        "top10_gap_threshold_policy": {
            "policy_label": "Variable Top10 with score-gap threshold",
            "policy_family": "variable_top10",
            "phase5_position": "candidate",
            "risk_guard_requirement": "recommended",
            "notes": "Addresses fixed Top10 tail dilution better than fixed Top10 on test, using score-gap filtering.",
        },
        "risk_adjusted_model_top5": {
            "policy_label": "Risk-adjusted model Top5",
            "policy_family": "risk_adjusted_blend",
            "phase5_position": "conservative_candidate",
            "risk_guard_requirement": "built_in_and_recommended",
            "notes": "Lower downside_bad and better drawdown profile; return lift is smaller than simple-rule candidates.",
        },
        "simple_rule_blend_model_top5": {
            "policy_label": "Simple-rule/model blend Top5",
            "policy_family": "blend",
            "phase5_position": "balanced_candidate",
            "risk_guard_requirement": "recommended",
            "notes": "Keeps much of the simple-rule return lift while reducing downside_bad deterioration versus pure simple_rule_top5.",
        },
    }
    rows: list[dict[str, Any]] = []
    for strategy, metadata in candidate_names.items():
        split_rows = {row["split"]: row for row in by_strategy[by_strategy["strategy"] == strategy].to_dict("records")}
        validation = split_rows.get("validation", {})
        test = split_rows.get("test", {})
        rows.append(
            {
                "policy_name": strategy,
                **metadata,
                "validation_mean_future_return_20d": round_float(validation.get("mean_future_return_20d")),
                "validation_mean_future_max_return_20d": round_float(validation.get("mean_future_max_return_20d")),
                "validation_top_decile_rate_20d": round_float(validation.get("top_decile_rate_20d")),
                "validation_downside_bad_rate_20d": round_float(validation.get("downside_bad_rate_20d")),
                "validation_lift_vs_candidate_top50_future_return": round_float(validation.get("lift_vs_candidate_top50_future_return")),
                "test_mean_future_return_20d": round_float(test.get("mean_future_return_20d")),
                "test_mean_future_max_return_20d": round_float(test.get("mean_future_max_return_20d")),
                "test_top_decile_rate_20d": round_float(test.get("top_decile_rate_20d")),
                "test_downside_bad_rate_20d": round_float(test.get("downside_bad_rate_20d")),
                "test_downside_bad_delta_vs_candidate_top50": round_float(test.get("downside_bad_delta_vs_candidate_top50")),
                "test_lift_vs_candidate_top50_future_return": round_float(test.get("lift_vs_candidate_top50_future_return")),
                "finalization_status": "not_promoted_policy_candidate",
            }
        )
    return pd.DataFrame(rows)


def build_risk_guard_policy(recommended_policy: dict[str, Any], candidates: pd.DataFrame) -> dict[str, Any]:
    simple_rule = lookup_policy(candidates, "simple_rule_top5")
    return {
        "risk_guard_required": True,
        "required_for_policy": recommended_policy.get("policy_name"),
        "simple_rule_top5_status": "requires_risk_guard_before_any_future_promotion",
        "simple_rule_top5_return_strength": {
            "test_mean_future_return_20d": simple_rule.get("test_mean_future_return_20d", 0.0),
            "test_mean_future_max_return_20d": simple_rule.get("test_mean_future_max_return_20d", 0.0),
            "test_top_decile_rate_20d": simple_rule.get("test_top_decile_rate_20d", 0.0),
        },
        "simple_rule_top5_risk_issue": {
            "test_downside_bad_rate_20d": simple_rule.get("test_downside_bad_rate_20d", 0.0),
            "test_downside_bad_delta_vs_candidate_top50": simple_rule.get("test_downside_bad_delta_vs_candidate_top50", 0.0),
            "conclusion": "downside_bad_rate worsens versus CandidateTop50, so pure simple_rule_top5 is not promotion-ready.",
        },
        "risk_guard_conditions": [
            "risk_guard_status must be emitted for every inference row.",
            "downside_risk_score must remain part of the Opportunity output contract.",
            "no_buy_reason should explain high-risk or weak-tail candidates even when expected_edge_score is high.",
            "Top10 should be handled as a ranking band or variable set using score-gap/risk filters, not as a fixed buy count.",
            "Capital Allocation and Position Management decide how to consume the ranking; Phase5 does not decide actual purchase count or order size.",
        ],
    }


def build_final_recommendation(
    candidates: pd.DataFrame,
    recommended_policy: dict[str, Any],
    risk_guard_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "primary_phase5_policy_candidate": recommended_policy.get("policy_name"),
        "primary_policy_status": "risk_guard_candidate_not_promoted",
        "ranking_policy_candidates": candidates["policy_name"].tolist(),
        "conservative_fallback": "current_model_top20",
        "risk_adjusted_fallback": "risk_adjusted_model_top5",
        "variable_top10_candidate": "top10_gap_threshold_policy",
        "promotion_ready": False,
        "phase5_does_not_decide_purchase_count": True,
        "summary": [
            "Opportunity AI remains a 20-business-day expected-value ranking AI.",
            "Candidate Top50 should be ranked by expected_edge_score and explained with downside_risk_score, buy_reason, and no_buy_reason.",
            "Top5 quality is promising, but Top10 needs tail dilution controls.",
            "simple_rule_top5 is strong on return but requires risk guard because downside_bad_rate worsened.",
            "Downstream phases decide capital allocation, position management, and execution policy.",
        ],
        "risk_guard_required": risk_guard_policy["risk_guard_required"],
    }


def build_final_output_schema(*, created_at: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "schema_version": "opportunity_inference_output_phase5k_v1",
        "output_columns": FINAL_OUTPUT_COLUMNS,
        "columns": {
            "target_date": {"type": "date/string", "required": True, "description": "Candidate snapshot date."},
            "code": {"type": "string", "required": True, "description": "J-Quants listed issue code."},
            "expected_edge_score": {"type": "float", "required": True, "description": "Opportunity expected-value ranking score."},
            "buy_rank": {"type": "integer", "required": True, "description": "Rank within Candidate Top50 by expected_edge_score or calibrated policy score."},
            "expected_return_horizon": {"type": "string", "required": True, "description": "Expected return horizon, fixed to 20 business days for Phase5."},
            "downside_risk_score": {"type": "float", "required": True, "description": "Risk score used for explanation and risk guard handling."},
            "buy_reason": {"type": "string", "required": True, "description": "Positive ranking explanation."},
            "no_buy_reason": {"type": "string", "required": True, "description": "Risk or weak-rank explanation; can be empty when not applicable."},
            "candidate_score": {"type": "float", "required": True, "description": "Candidate AI prior score."},
            "candidate_rank": {"type": "integer", "required": True, "description": "Candidate AI rank within Top50."},
            "model_version": {"type": "string", "required": True, "description": "Opportunity model/calibration version."},
            "feature_version": {"type": "string", "required": True, "description": "Feature schema version."},
            "inference_run_id": {"type": "string", "required": True, "description": "Inference run identifier."},
            "created_at": {"type": "timestamp/string", "required": True, "description": "Artifact creation timestamp."},
            "is_top5": {"type": "boolean", "required": True, "description": "Ranking-band flag only, not a buy-count decision."},
            "is_top10": {"type": "boolean", "required": True, "description": "Ranking-band flag only, not a buy-count decision."},
            "is_top20": {"type": "boolean", "required": True, "description": "Ranking-band flag only, not a buy-count decision."},
            "risk_guard_status": {"type": "string", "required": True, "description": "Risk guard status such as PASS, WATCH, BLOCKED_BY_RISK, or WEAK_TAIL."},
            "calibration_policy_name": {"type": "string", "required": True, "description": "Calibration/ranking policy candidate name used to produce ranking context."},
        },
        "non_goals": [
            "purchase count decision",
            "purchase amount decision",
            "share quantity decision",
            "portfolio allocation",
            "position management",
            "order execution",
        ],
    }


def build_safety_rules() -> dict[str, Any]:
    return {
        "feature_source_of_truth": "J-Quants API data and J-Quants-derived features only.",
        "future_columns": "future_return_*, future_max_return_*, future_max_drawdown_*, downside_bad_*, top_decile_* are label/evaluation only.",
        "forbidden_features": [
            "trade_result",
            "trade_profit",
            "selected",
            "bought",
            "sold",
            "cash",
            "portfolio",
            "annual_return",
            "final_assets",
            "backtest-derived columns",
            "Paper Trading outputs",
            "PM multiplier",
            "past AI decision outputs",
        ],
        "disallowed_actions_in_phase5k": [
            "promotion",
            "reader switch",
            "Broker API",
            "Paper Trading",
            "order placement",
            "capital allocation",
            "deciding actual number of names to buy",
        ],
    }


def build_audit(
    *,
    created_at: str,
    calibration_metrics: dict[str, Any],
    calibration_audit: dict[str, Any],
    recommended_policy: dict[str, Any],
    policy_candidates: pd.DataFrame,
    schema: dict[str, Any],
    risk_guard_policy: dict[str, Any],
) -> dict[str, Any]:
    expected_columns_present = schema.get("output_columns") == FINAL_OUTPUT_COLUMNS
    recommended_supported = recommended_policy.get("policy_name") in set(policy_candidates["policy_name"]) if not policy_candidates.empty else False
    promotion_ready = bool(calibration_metrics.get("promotion_ready", False) or calibration_audit.get("promotion_ready", False) or recommended_policy.get("promotion_ready", False))
    return {
        "phase": PHASE,
        "created_at": created_at,
        "phase5j_artifacts_loaded": True,
        "phase5j_readiness_status": calibration_audit.get("readiness_status", calibration_metrics.get("readiness_status")),
        "phase5j_leakage_status": calibration_audit.get("leakage_status"),
        "policy_candidate_count": int(len(policy_candidates)),
        "policy_candidates_summarized": bool(len(policy_candidates) >= 5),
        "recommended_policy_name": recommended_policy.get("policy_name"),
        "recommended_policy_supported": recommended_supported,
        "simple_rule_top5_requires_risk_guard": risk_guard_policy.get("risk_guard_required", False),
        "top6_10_tail_dilution_status": "TAIL_DILUTION_CONFIRMED",
        "fixed_top10_finalized_as_buy_count": False,
        "phase5_decides_purchase_count": False,
        "final_output_schema_fixed": expected_columns_present,
        "final_output_column_count": len(schema.get("output_columns", [])),
        "risk_guard_requirement_documented": bool(risk_guard_policy.get("risk_guard_conditions")),
        "leakage_status": "OK" if calibration_audit.get("leakage_status") == "OK" else "ERROR",
        "forbidden_feature_column_count": int(calibration_audit.get("forbidden_feature_column_count", 0)),
        "future_feature_column_count": int(calibration_audit.get("future_feature_column_count", 0)),
        "trade_result_feature_column_count": int(calibration_audit.get("trade_result_feature_column_count", 0)),
        "portfolio_feature_column_count": int(calibration_audit.get("portfolio_feature_column_count", 0)),
        "backtest_feature_column_count": int(calibration_audit.get("backtest_feature_column_count", 0)),
        "promotion_ready": promotion_ready,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
    }


def resolve_readiness(audit: dict[str, Any]) -> str:
    severe_issue = (
        not audit["phase5j_artifacts_loaded"]
        or audit["phase5j_readiness_status"] != "READY_FOR_PHASE5K_POLICY_FINALIZATION"
        or audit["leakage_status"] != "OK"
        or not audit["policy_candidates_summarized"]
        or not audit["recommended_policy_supported"]
        or not audit["final_output_schema_fixed"]
        or not audit["risk_guard_requirement_documented"]
        or audit["promotion_ready"]
        or audit["phase5_decides_purchase_count"]
        or audit["promotion_performed"]
        or audit["reader_switch_performed"]
        or audit["paper_trading_executed"]
        or audit["broker_api_executed"]
        or audit["order_executed"]
        or audit["capital_allocation_executed"]
    )
    return NEEDS_PHASE5J_REVIEW if severe_issue else READY_FOR_PHASE5L_COMPLETION_AUDIT


def lookup_policy(candidates: pd.DataFrame, policy_name: str) -> dict[str, Any]:
    matches = candidates[candidates["policy_name"] == policy_name]
    return matches.iloc[0].to_dict() if not matches.empty else {}


def build_blocked_audit(*, created_at: str, missing_inputs: list[str], reason: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "phase5j_artifacts_loaded": False,
        "missing_inputs": missing_inputs,
        "block_reason": reason,
        "policy_candidate_count": 0,
        "policy_candidates_summarized": False,
        "recommended_policy_supported": False,
        "final_output_schema_fixed": False,
        "risk_guard_requirement_documented": False,
        "leakage_status": "NOT_RUN",
        "promotion_ready": False,
        "readiness_status": NEEDS_PHASE5J_REVIEW,
    }


def build_summary_shell(
    *,
    created_at: str,
    readiness_status: str,
    status: str,
    output_paths: dict[str, Path],
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "output_paths": {name: str(path) for name, path in output_paths.items()},
        "promotion_ready": False,
        "audit": audit,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def write_outputs(
    output_paths: dict[str, Path],
    summary: dict[str, Any],
    audit: dict[str, Any],
    schema: dict[str, Any],
    policy_candidates: pd.DataFrame,
) -> None:
    write_json(output_paths["summary"], summary)
    write_json(output_paths["audit"], audit)
    write_json(output_paths["schema"], schema)
    policy_candidates.to_csv(output_paths["policy_candidates"], index=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 6) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
