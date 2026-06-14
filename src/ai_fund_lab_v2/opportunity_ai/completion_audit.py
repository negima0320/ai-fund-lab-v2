from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.opportunity_ai.policy_finalization import FINAL_OUTPUT_COLUMNS
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable

PHASE = "Phase5-L"
PHASE5_COMPLETE_WITH_PROMOTION_DISABLED = "PHASE5_COMPLETE_WITH_PROMOTION_DISABLED"
PHASE5_NEEDS_REWORK = "PHASE5_NEEDS_REWORK"

DEFAULT_PHASE_REPORTS_DIR = Path("docs/phase_reports")
DEFAULT_AI_DESIGN_DIR = Path("docs/03_ai_design")
DEFAULT_REQUIREMENTS_DIR = Path("docs/01_requirements")
DEFAULT_OPPORTUNITY_REPORTS_DIR = Path("reports/opportunity_ai")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5l")

COMPLETION_AUDIT_FILENAME = "completion_audit.json"
COMPLETION_SUMMARY_FILENAME = "completion_summary.json"

REQUIRED_DOCS = [
    "phase5a_opportunity_ai_design.md",
    "phase5b_opportunity_label_design.md",
    "phase5c_opportunity_feature_design.md",
    "phase5d_opportunity_dataset_builder.md",
    "phase5d2_historical_candidate_top50.md",
    "phase5e_opportunity_training.md",
    "phase5f_opportunity_inference.md",
    "phase5g_opportunity_quality_audit.md",
    "phase5h_combined_validation.md",
    "phase5i_full_history_expansion.md",
    "phase5j_model_improvement_calibration.md",
    "phase5k_policy_finalization.md",
]

REQUIRED_DESIGN_DOCS = [
    "opportunity_ai_design.md",
]

REQUIRED_REQUIREMENT_DOCS = [
    "system_requirements.md",
]

REQUIRED_ARTIFACTS = [
    "phase5d/opportunity_dataset.parquet",
    "phase5d/opportunity_dataset_audit.json",
    "phase5d/opportunity_dataset_summary.json",
    "phase5d2/historical_candidate_top50.parquet",
    "phase5d2/historical_candidate_top50_audit.json",
    "phase5d2/historical_candidate_top50_summary.json",
    "phase5e/opportunity_training_audit.json",
    "phase5e/opportunity_training_metrics.json",
    "phase5f/latest_opportunity_inference.parquet",
    "phase5f/latest_opportunity_top20.csv",
    "phase5f/opportunity_inference_audit.json",
    "phase5f/opportunity_inference_summary.json",
    "phase5g/opportunity_quality_audit.json",
    "phase5g/opportunity_quality_by_split.csv",
    "phase5g/opportunity_quality_metrics.json",
    "phase5h/combined_validation_audit.json",
    "phase5h/combined_validation_by_date.csv",
    "phase5h/combined_validation_by_split.csv",
    "phase5h/combined_validation_metrics.json",
    "phase5i/full_history_audit.json",
    "phase5i/full_history_candidate_top50.parquet",
    "phase5i/full_history_combined_validation_metrics.json",
    "phase5i/full_history_expansion_summary.json",
    "phase5i/full_history_opportunity_dataset.parquet",
    "phase5i/full_history_quality_metrics.json",
    "phase5i/full_history_training_metrics.json",
    "phase5j/calibration_audit.json",
    "phase5j/calibration_by_date.csv",
    "phase5j/calibration_by_strategy.csv",
    "phase5j/calibration_metrics.json",
    "phase5j/recommended_policy.json",
    "phase5k/final_opportunity_output_schema.json",
    "phase5k/final_policy_candidates.csv",
    "phase5k/policy_finalization_audit.json",
    "phase5k/policy_finalization_summary.json",
]


@dataclass(frozen=True)
class CompletionAuditResult:
    summary: dict[str, Any]
    audit: dict[str, Any]


def audit_phase5_completion(
    *,
    phase_reports_dir: Path = DEFAULT_PHASE_REPORTS_DIR,
    ai_design_dir: Path = DEFAULT_AI_DESIGN_DIR,
    requirements_dir: Path = DEFAULT_REQUIREMENTS_DIR,
    opportunity_reports_dir: Path = DEFAULT_OPPORTUNITY_REPORTS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> CompletionAuditResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / COMPLETION_AUDIT_FILENAME
    summary_path = output_dir / COMPLETION_SUMMARY_FILENAME

    docs_audit = audit_docs(
        phase_reports_dir=phase_reports_dir,
        ai_design_dir=ai_design_dir,
        requirements_dir=requirements_dir,
    )
    artifacts_audit = audit_artifacts(opportunity_reports_dir)
    json_payloads = load_key_payloads(opportunity_reports_dir)
    schema_audit = audit_final_schema(json_payloads.get("phase5k_schema", {}))
    leakage_audit = audit_leakage(json_payloads)
    full_history_audit = audit_full_history(json_payloads)
    policy_audit = audit_policy(json_payloads)
    scope_audit = audit_scope(json_payloads)
    safety_audit = audit_safety(json_payloads)
    readiness_status = resolve_readiness(
        docs_audit=docs_audit,
        artifacts_audit=artifacts_audit,
        schema_audit=schema_audit,
        leakage_audit=leakage_audit,
        full_history_audit=full_history_audit,
        policy_audit=policy_audit,
        scope_audit=scope_audit,
        safety_audit=safety_audit,
    )
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": readiness_status,
        "promotion_ready": False,
        "docs_audit": docs_audit,
        "artifact_completeness": artifacts_audit,
        "final_schema_consistency": schema_audit,
        "leakage_forbidden_feature_audit": leakage_audit,
        "full_history_readiness": full_history_audit,
        "calibration_policy_audit": policy_audit,
        "scope_boundary_audit": scope_audit,
        "safety_boundary_audit": safety_audit,
        "phase5_complete": readiness_status == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED,
    }
    summary = build_summary(
        created_at=created_at,
        readiness_status=readiness_status,
        audit_path=audit_path,
        summary_path=summary_path,
        docs_audit=docs_audit,
        artifacts_audit=artifacts_audit,
        schema_audit=schema_audit,
        leakage_audit=leakage_audit,
        full_history_audit=full_history_audit,
        policy_audit=policy_audit,
        scope_audit=scope_audit,
        safety_audit=safety_audit,
    )
    write_json(audit_path, audit)
    write_json(summary_path, summary)
    return CompletionAuditResult(summary=summary, audit=audit)


def audit_docs(*, phase_reports_dir: Path, ai_design_dir: Path, requirements_dir: Path) -> dict[str, Any]:
    phase_paths = [phase_reports_dir / name for name in REQUIRED_DOCS]
    design_paths = [ai_design_dir / name for name in REQUIRED_DESIGN_DOCS]
    requirement_paths = [requirements_dir / name for name in REQUIRED_REQUIREMENT_DOCS]
    all_paths = phase_paths + design_paths + requirement_paths
    missing = [str(path) for path in all_paths if not path.is_file()]
    return {
        "required_doc_count": len(all_paths),
        "existing_doc_count": len(all_paths) - len(missing),
        "missing_docs": missing,
        "docs_complete": not missing,
    }


def audit_artifacts(opportunity_reports_dir: Path) -> dict[str, Any]:
    paths = [opportunity_reports_dir / relative for relative in REQUIRED_ARTIFACTS]
    missing = [str(path) for path in paths if not path.is_file()]
    return {
        "required_artifact_count": len(paths),
        "existing_artifact_count": len(paths) - len(missing),
        "missing_artifacts": missing,
        "artifacts_complete": not missing,
    }


def load_key_payloads(opportunity_reports_dir: Path) -> dict[str, dict[str, Any]]:
    mapping = {
        "phase5d_audit": "phase5d/opportunity_dataset_audit.json",
        "phase5d2_audit": "phase5d2/historical_candidate_top50_audit.json",
        "phase5e_audit": "phase5e/opportunity_training_audit.json",
        "phase5f_audit": "phase5f/opportunity_inference_audit.json",
        "phase5f_summary": "phase5f/opportunity_inference_summary.json",
        "phase5g_audit": "phase5g/opportunity_quality_audit.json",
        "phase5h_audit": "phase5h/combined_validation_audit.json",
        "phase5i_audit": "phase5i/full_history_audit.json",
        "phase5i_metrics": "phase5i/full_history_combined_validation_metrics.json",
        "phase5j_audit": "phase5j/calibration_audit.json",
        "phase5j_metrics": "phase5j/calibration_metrics.json",
        "phase5j_policy": "phase5j/recommended_policy.json",
        "phase5k_audit": "phase5k/policy_finalization_audit.json",
        "phase5k_summary": "phase5k/policy_finalization_summary.json",
        "phase5k_schema": "phase5k/final_opportunity_output_schema.json",
    }
    return {name: read_json_optional(opportunity_reports_dir / relative) for name, relative in mapping.items()}


def audit_final_schema(schema: dict[str, Any]) -> dict[str, Any]:
    columns = list(schema.get("output_columns", []))
    missing_columns = [column for column in FINAL_OUTPUT_COLUMNS if column not in columns]
    extra_required_missing = [column for column in ("risk_guard_status", "calibration_policy_name") if column not in columns]
    return {
        "required_columns": FINAL_OUTPUT_COLUMNS,
        "actual_columns": columns,
        "missing_columns": missing_columns,
        "risk_guard_status_present": "risk_guard_status" in columns,
        "calibration_policy_name_present": "calibration_policy_name" in columns,
        "final_schema_fixed": not missing_columns and not extra_required_missing,
        "schema_version": schema.get("schema_version"),
    }


def audit_leakage(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    audited_payloads = [
        payloads.get("phase5d_audit", {}),
        payloads.get("phase5e_audit", {}),
        payloads.get("phase5f_audit", {}),
        payloads.get("phase5g_audit", {}),
        payloads.get("phase5h_audit", {}),
        payloads.get("phase5i_audit", {}),
        payloads.get("phase5j_audit", {}),
        payloads.get("phase5k_audit", {}),
    ]
    counts = {
        "forbidden_feature_column_count": sum_int(audited_payloads, "forbidden_feature_column_count"),
        "future_feature_column_count": sum_int(audited_payloads, "future_feature_column_count"),
        "trade_result_feature_column_count": sum_int(audited_payloads, "trade_result_feature_column_count"),
        "portfolio_feature_column_count": sum_int(audited_payloads, "portfolio_feature_column_count"),
        "backtest_feature_column_count": sum_int(audited_payloads, "backtest_feature_column_count"),
        "ai_output_feature_column_count": sum_int(audited_payloads, "ai_output_feature_column_count"),
    }
    statuses = [
        payload.get("leakage_status", payload.get("leakage_audit_status", "OK"))
        for payload in audited_payloads
        if payload
    ]
    leakage_ok = all(status == "OK" for status in statuses) and all(value == 0 for value in counts.values())
    return {
        **counts,
        "leakage_statuses": statuses,
        "feature_source_rule": "J-Quants API data or J-Quants-derived features only.",
        "future_columns_rule": "Future columns are label/evaluation only, not features.",
        "forbidden_trade_portfolio_backtest_rule": "trade/backtest/portfolio/PM multiplier/past AI decision outputs are forbidden as features.",
        "leakage_ok": leakage_ok,
    }


def audit_full_history(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    full = payloads.get("phase5i_audit", {})
    metrics = payloads.get("phase5i_metrics", {})
    quality_metrics = metrics.get("quality_metrics", {})
    validation_available = "validation" in quality_metrics
    test_available = "test" in quality_metrics
    return {
        "candidate_rows": int(full.get("candidate_rows", 0)),
        "dataset_rows": int(full.get("dataset_rows", 0)),
        "train_rows": int(full.get("train_rows", 0)),
        "validation_rows": int(full.get("validation_rows", 0)),
        "test_rows": int(full.get("test_rows", 0)),
        "leakage_status": full.get("leakage_status"),
        "model_unique_score_count": int(full.get("model_unique_score_count", 0)),
        "all_same_score": bool(full.get("all_same_score", True)),
        "validation_metrics_available": validation_available,
        "test_metrics_available": test_available,
        "full_history_ready": bool(
            full.get("candidate_rows", 0) > 0
            and full.get("dataset_rows", 0) > 0
            and full.get("leakage_status") == "OK"
            and int(full.get("model_unique_score_count", 0)) > 1
            and not bool(full.get("all_same_score", True))
            and validation_available
            and test_available
        ),
    }


def audit_policy(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    k_audit = payloads.get("phase5k_audit", {})
    k_summary = payloads.get("phase5k_summary", {})
    j_policy = payloads.get("phase5j_policy", {})
    final_recommendation = k_summary.get("final_recommendation", {})
    return {
        "policy_candidate_count": int(k_audit.get("policy_candidate_count", 0)),
        "policy_candidates_documented": int(k_audit.get("policy_candidate_count", 0)) >= 5,
        "recommended_policy_name": k_audit.get("recommended_policy_name", j_policy.get("policy_name")),
        "simple_rule_top5_requires_risk_guard": bool(k_audit.get("simple_rule_top5_requires_risk_guard")),
        "fixed_top10_finalized_as_buy_count": bool(k_audit.get("fixed_top10_finalized_as_buy_count", True)),
        "phase5_decides_purchase_count": bool(k_audit.get("phase5_decides_purchase_count", True)),
        "top6_10_tail_dilution_status": k_audit.get("top6_10_tail_dilution_status"),
        "promotion_ready": bool(k_audit.get("promotion_ready", True) or k_summary.get("promotion_ready", True)),
        "final_recommendation_present": bool(final_recommendation),
        "policy_audit_ok": bool(
            int(k_audit.get("policy_candidate_count", 0)) >= 5
            and k_audit.get("simple_rule_top5_requires_risk_guard") is True
            and k_audit.get("fixed_top10_finalized_as_buy_count") is False
            and k_audit.get("phase5_decides_purchase_count") is False
            and not bool(k_audit.get("promotion_ready", True) or k_summary.get("promotion_ready", True))
        ),
    }


def audit_scope(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    k_summary = payloads.get("phase5k_summary", {})
    scope = k_summary.get("scope_boundary", {})
    return {
        "ranks_candidate_top50": bool(scope.get("does_rank_candidate_top50", True)),
        "does_not_extract_candidates": True,
        "does_not_manage_positions": not bool(scope.get("does_manage_positions", False)),
        "does_not_allocate_capital": not bool(scope.get("does_allocate_capital", False)),
        "does_not_place_orders": not bool(scope.get("does_place_orders", False)),
        "does_not_decide_purchase_count": not bool(scope.get("does_decide_purchase_count", False)),
        "does_not_promote_model": not bool(scope.get("does_promote_model", False)),
        "does_not_switch_readers": not bool(scope.get("does_switch_readers", False)),
        "scope_ok": bool(
            scope.get("does_rank_candidate_top50", True)
            and not scope.get("does_manage_positions", False)
            and not scope.get("does_allocate_capital", False)
            and not scope.get("does_place_orders", False)
            and not scope.get("does_decide_purchase_count", False)
            and not scope.get("does_promote_model", False)
            and not scope.get("does_switch_readers", False)
        ),
    }


def audit_safety(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    audited_payloads = [
        payloads.get("phase5f_summary", {}),
        payloads.get("phase5g_audit", {}),
        payloads.get("phase5h_audit", {}),
        payloads.get("phase5i_audit", {}),
        payloads.get("phase5j_metrics", {}),
        payloads.get("phase5k_summary", {}),
        payloads.get("phase5k_audit", {}),
    ]
    flags = {
        "broker_api_executed": any_bool(audited_payloads, "broker_api_executed"),
        "paper_trading_executed": any_bool(audited_payloads, "paper_trading_executed"),
        "order_executed": any_bool(audited_payloads, "order_executed"),
        "capital_allocation_executed": any_bool(audited_payloads, "capital_allocation_executed"),
        "promotion_performed": any_bool(audited_payloads, "promotion_performed"),
        "reader_switch_performed": any_bool(audited_payloads, "reader_switch_performed"),
        "promotion_ready": any_bool(audited_payloads, "promotion_ready"),
    }
    safety_ok = not any(flags.values())
    return {
        **flags,
        "phase4_artifact_destroyed_flag": False,
        "mock_path_overwrite_flag": False,
        "safety_ok": safety_ok,
    }


def resolve_readiness(
    *,
    docs_audit: dict[str, Any],
    artifacts_audit: dict[str, Any],
    schema_audit: dict[str, Any],
    leakage_audit: dict[str, Any],
    full_history_audit: dict[str, Any],
    policy_audit: dict[str, Any],
    scope_audit: dict[str, Any],
    safety_audit: dict[str, Any],
) -> str:
    complete = (
        docs_audit["docs_complete"]
        and artifacts_audit["artifacts_complete"]
        and schema_audit["final_schema_fixed"]
        and leakage_audit["leakage_ok"]
        and full_history_audit["full_history_ready"]
        and policy_audit["policy_audit_ok"]
        and scope_audit["scope_ok"]
        and safety_audit["safety_ok"]
    )
    return PHASE5_COMPLETE_WITH_PROMOTION_DISABLED if complete else PHASE5_NEEDS_REWORK


def build_summary(
    *,
    created_at: str,
    readiness_status: str,
    audit_path: Path,
    summary_path: Path,
    docs_audit: dict[str, Any],
    artifacts_audit: dict[str, Any],
    schema_audit: dict[str, Any],
    leakage_audit: dict[str, Any],
    full_history_audit: dict[str, Any],
    policy_audit: dict[str, Any],
    scope_audit: dict[str, Any],
    safety_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "OK" if readiness_status == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED else "REWORK_REQUIRED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "audit_path": str(audit_path),
        "summary_path": str(summary_path),
        "promotion_ready": False,
        "phase5_complete": readiness_status == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED,
        "phase5_role": "Opportunity AI expected-value ranking for Candidate Top50.",
        "phase5_non_goals": [
            "candidate extraction",
            "actual buy-count decision",
            "capital allocation",
            "position management",
            "Broker API",
            "Paper Trading",
            "order placement",
            "promotion",
            "reader switch",
        ],
        "docs_complete": docs_audit["docs_complete"],
        "artifacts_complete": artifacts_audit["artifacts_complete"],
        "final_schema_fixed": schema_audit["final_schema_fixed"],
        "final_output_columns": schema_audit["actual_columns"],
        "leakage_ok": leakage_audit["leakage_ok"],
        "full_history_ready": full_history_audit["full_history_ready"],
        "candidate_rows": full_history_audit["candidate_rows"],
        "dataset_rows": full_history_audit["dataset_rows"],
        "model_score_collapse": full_history_audit["all_same_score"],
        "policy_audit_ok": policy_audit["policy_audit_ok"],
        "simple_rule_top5_requires_risk_guard": policy_audit["simple_rule_top5_requires_risk_guard"],
        "fixed_top10_finalized_as_buy_count": policy_audit["fixed_top10_finalized_as_buy_count"],
        "scope_ok": scope_audit["scope_ok"],
        "safety_ok": safety_audit["safety_ok"],
        "phase6_handoff_ready": readiness_status == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED,
        "recommended_next_action": (
            "Proceed to Phase6 planning with promotion disabled."
            if readiness_status == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED
            else "Fix Phase5 audit blockers before Phase6 handoff."
        ),
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


def sum_int(payloads: list[dict[str, Any]], key: str) -> int:
    total = 0
    for payload in payloads:
        try:
            total += int(payload.get(key, 0))
        except (TypeError, ValueError):
            total += 0
    return total


def any_bool(payloads: list[dict[str, Any]], key: str) -> bool:
    return any(bool(payload.get(key, False)) for payload in payloads)


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
