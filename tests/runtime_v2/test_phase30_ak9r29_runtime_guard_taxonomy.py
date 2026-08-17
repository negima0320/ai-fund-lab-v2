from __future__ import annotations

import json
import pickle
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.guard_taxonomy import (
    BATCH_LEVEL_FAILURE,
    DATA_INTEGRITY_SAFETY,
    EXECUTION_SAFETY,
    INTERNAL_SYSTEM_CONSISTENCY,
    ITEM_SCOPED_REVIEW,
    MARKET_PORTFOLIO_SAFETY,
    normalize_review_result,
)


BUSINESS_DATE = "2026-07-08"


@pytest.mark.parametrize(
    ("case_name", "producer", "reason", "payload", "expected_class", "expected_code", "batch_blocking", "system_defect"),
    [
        ("cash", "planning_submit_feasibility", "insufficient_cash", {}, EXECUTION_SAFETY, "INSUFFICIENT_CASH", True, False),
        ("hard_cap", "submit_guard", "safety_hard_cap_exceeded", {}, MARKET_PORTFOLIO_SAFETY, "SAFETY_HARD_CAP", True, False),
        (
            "item_scoped",
            "pending",
            "pending_review_required",
            {"review_scope": "BUY_ITEM_SCOPED_REVIEW", "review_required_buy_item_ids": ["buy-review"]},
            ITEM_SCOPED_REVIEW,
            "PENDING_ITEM_SCOPED_REVIEW",
            False,
            False,
        ),
        (
            "reviewed_sell",
            "pending",
            "pending_review_required",
            {"review_scope": "BUY_ITEM_SCOPED_REVIEW", "review_required_sell_item_ids": ["sell-review"]},
            BATCH_LEVEL_FAILURE,
            "REVIEWED_SELL_BATCH_BLOCK",
            True,
            False,
        ),
        ("temporal", "data_readiness", "historical_safety_temporal_authority_missing", {}, DATA_INTEGRITY_SAFETY, "TEMPORAL_MISMATCH", True, False),
        ("corporate_action", "corporate_action", "corporate_action_event_type_or_adjustment_application_unresolved", {}, DATA_INTEGRITY_SAFETY, "CORPORATE_ACTION_UNRESOLVED", True, False),
        ("malformed", "data_readiness", "malformed_authority", {}, DATA_INTEGRITY_SAFETY, "MALFORMED_AUTHORITY", True, False),
        ("quantity", "submit_guard", "quantity mismatch", {}, EXECUTION_SAFETY, "QUANTITY_MISMATCH", True, False),
        ("system", "submit_guard", "canonical authority missing unexpectedly", {}, INTERNAL_SYSTEM_CONSISTENCY, "CANONICAL_AUTHORITY_MISSING", True, True),
        ("pass_diag", "data_readiness", "normal_pass", {}, DATA_INTEGRITY_SAFETY, "NORMAL_PASS", True, False),
    ],
)
def test_phase30_ak9r29_taxonomy_shadow_cases(
    case_name: str,
    producer: str,
    reason: str,
    payload: dict,
    expected_class: str,
    expected_code: str,
    batch_blocking: bool,
    system_defect: bool,
) -> None:
    typed = normalize_review_result(producer=producer, reason=reason, source_payload=payload)

    assert typed["guard_class"] == expected_class, case_name
    assert typed["guard_code"] == expected_code, case_name
    assert typed["batch_blocking"] is batch_blocking, case_name
    assert typed["system_defect"] is system_defect, case_name
    assert typed["diagnostic_reason"] == reason
    assert typed["scope"] in {"ITEM", "SIDE", "BATCH", "PORTFOLIO", "DATA", "SYSTEM"}
    assert typed["affected_side"] in {"BUY", "SELL", "BOTH", "NONE"}
    assert typed["recoverability"]


def test_phase30_ak9r29_data_readiness_materializes_typed_guard_metadata(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="morning",
        feature_root=root / "operations" / "feature_artifacts",
        feature_date=BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        broker_environment="historical_simulated",
        runtime_test_evidence_root=tmp_path / "evidence",
        runtime_test_run_id="runtime-test-ak9r29",
        runtime_test_profile_id="historical-smoke",
    )

    manifest_fields = result.to_manifest_fields()
    assert result.status in {"REVIEW_REQUIRED", "HALT"}
    assert result.payload["review_reasons"]
    assert result.payload["review_guard_results"]
    assert "DATA_INTEGRITY_SAFETY" in result.payload["review_guard_classes"]
    assert manifest_fields["review_guard_summary"]["business_semantic_reason_string_dependency"] is False
    assert manifest_fields["system_defect_guard_count"] >= 0


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "environment": "historical",
            "business_date": BUSINESS_DATE,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "source_market_date": BUSINESS_DATE,
            "positions": [],
            "cash": 1000000,
            "buying_power": 1000000,
            "total_equity": 1000000,
            "review_required": False
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {"business_date": BUSINESS_DATE, "status": "READY"},
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "pending_plan_id": "future-empty",
            "state": "EMPTY",
            "environment": "historical",
            "active_pending": False,
            "target_session_date": "2026-07-09",
            "items": []
        },
    )
    _write_feature_readiness(root / "operations" / "feature_artifacts")
    return root


def _write_feature_readiness(root: Path) -> None:
    _write_json(
        root / "feature_consumer_readiness" / f"{BUSINESS_DATE}.json",
        {
            "status": "READY",
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "schemas": {"pm": {"missing_columns": []}},
        },
    )


def _write_model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(object(), fh)
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
