from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.completion_audit import (
    PHASE5_COMPLETE_WITH_PROMOTION_DISABLED,
    PHASE5_NEEDS_REWORK,
    REQUIRED_ARTIFACTS,
    REQUIRED_DESIGN_DOCS,
    REQUIRED_DOCS,
    REQUIRED_REQUIREMENT_DOCS,
    audit_phase5_completion,
)
from ai_fund_lab_v2.opportunity_ai.policy_finalization import FINAL_OUTPUT_COLUMNS


def test_phase5l_completion_audit_passes_when_artifacts_complete(tmp_path: Path) -> None:
    dirs = _write_complete_fixture(tmp_path)

    result = audit_phase5_completion(
        phase_reports_dir=dirs["phase_reports"],
        ai_design_dir=dirs["ai_design"],
        requirements_dir=dirs["requirements"],
        opportunity_reports_dir=dirs["reports"],
        output_dir=tmp_path / "phase5l",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == PHASE5_COMPLETE_WITH_PROMOTION_DISABLED
    assert result.summary["promotion_ready"] is False
    assert result.summary["phase5_complete"] is True
    assert result.audit["final_schema_consistency"]["risk_guard_status_present"] is True
    assert result.audit["final_schema_consistency"]["calibration_policy_name_present"] is True
    assert result.audit["scope_boundary_audit"]["does_not_decide_purchase_count"] is True
    assert result.audit["safety_boundary_audit"]["safety_ok"] is True
    assert (tmp_path / "phase5l" / "completion_audit.json").is_file()
    assert (tmp_path / "phase5l" / "completion_summary.json").is_file()


def test_phase5l_completion_audit_reworks_on_schema_missing_column(tmp_path: Path) -> None:
    dirs = _write_complete_fixture(tmp_path)
    schema_path = dirs["reports"] / "phase5k" / "final_opportunity_output_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["output_columns"] = [column for column in schema["output_columns"] if column != "risk_guard_status"]
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    result = audit_phase5_completion(
        phase_reports_dir=dirs["phase_reports"],
        ai_design_dir=dirs["ai_design"],
        requirements_dir=dirs["requirements"],
        opportunity_reports_dir=dirs["reports"],
        output_dir=tmp_path / "phase5l",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == PHASE5_NEEDS_REWORK
    assert result.audit["final_schema_consistency"]["risk_guard_status_present"] is False


def _write_complete_fixture(tmp_path: Path) -> dict[str, Path]:
    phase_reports = tmp_path / "docs" / "phase_reports"
    ai_design = tmp_path / "docs" / "03_ai_design"
    requirements = tmp_path / "docs" / "01_requirements"
    reports = tmp_path / "reports" / "opportunity_ai"
    for directory in (phase_reports, ai_design, requirements, reports):
        directory.mkdir(parents=True, exist_ok=True)
    for doc in REQUIRED_DOCS:
        (phase_reports / doc).write_text(f"# {doc}\n", encoding="utf-8")
    for doc in REQUIRED_DESIGN_DOCS:
        (ai_design / doc).write_text(f"# {doc}\n", encoding="utf-8")
    for doc in REQUIRED_REQUIREMENT_DOCS:
        (requirements / doc).write_text(f"# {doc}\n", encoding="utf-8")
    for relative in REQUIRED_ARTIFACTS:
        path = reports / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(json.dumps(_json_payload_for(relative)), encoding="utf-8")
        elif path.suffix == ".csv":
            pd.DataFrame([{"policy_name": "simple_rule_top5"}]).to_csv(path, index=False)
        else:
            path.write_text("fixture", encoding="utf-8")
    return {
        "phase_reports": phase_reports,
        "ai_design": ai_design,
        "requirements": requirements,
        "reports": reports,
    }


def _json_payload_for(relative: str) -> dict[str, object]:
    base = {
        "readiness_status": "OK",
        "promotion_ready": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "leakage_status": "OK",
        "leakage_audit_status": "OK",
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "backtest_feature_column_count": 0,
        "ai_output_feature_column_count": 0,
    }
    if relative == "phase5i/full_history_audit.json":
        return {
            **base,
            "readiness_status": "READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION",
            "candidate_rows": 57150,
            "dataset_rows": 56995,
            "train_rows": 40559,
            "validation_rows": 12106,
            "test_rows": 4330,
            "model_unique_score_count": 15540,
            "all_same_score": False,
        }
    if relative == "phase5i/full_history_combined_validation_metrics.json":
        return {
            **base,
            "quality_metrics": {
                "validation": {"candidate_top50_average": {}},
                "test": {"candidate_top50_average": {}},
            },
        }
    if relative == "phase5j/recommended_policy.json":
        return {"policy_name": "simple_rule_top5", "promotion_ready": False}
    if relative == "phase5k/policy_finalization_audit.json":
        return {
            **base,
            "readiness_status": "READY_FOR_PHASE5L_COMPLETION_AUDIT",
            "policy_candidate_count": 7,
            "recommended_policy_name": "simple_rule_top5",
            "simple_rule_top5_requires_risk_guard": True,
            "fixed_top10_finalized_as_buy_count": False,
            "phase5_decides_purchase_count": False,
            "top6_10_tail_dilution_status": "TAIL_DILUTION_CONFIRMED",
            "final_output_schema_fixed": True,
        }
    if relative == "phase5k/policy_finalization_summary.json":
        return {
            **base,
            "readiness_status": "READY_FOR_PHASE5L_COMPLETION_AUDIT",
            "scope_boundary": {
                "does_rank_candidate_top50": True,
                "does_manage_positions": False,
                "does_allocate_capital": False,
                "does_place_orders": False,
                "does_decide_purchase_count": False,
                "does_promote_model": False,
                "does_switch_readers": False,
            },
            "final_recommendation": {"primary_phase5_policy_candidate": "simple_rule_top5"},
        }
    if relative == "phase5k/final_opportunity_output_schema.json":
        return {
            "schema_version": "fixture",
            "output_columns": FINAL_OUTPUT_COLUMNS,
        }
    return base
