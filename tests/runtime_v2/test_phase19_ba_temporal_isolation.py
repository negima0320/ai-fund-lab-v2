from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.system_status import (
    _freshness_matrix,
    _temporal_authority_audit,
)


def test_future_stateful_artifacts_block_historical_preflight(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_json(root / "persistent_ledger" / "state.json", {"as_of": "2026-07-17T09:00:00Z", "positions": []})
    _write_json(root / "runtime_state" / "current_state.json", {"business_date": "2026-07-08"})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"last_transition_at": "2026-07-09T00:00:00Z"})

    audit = _temporal_authority_audit(
        root=root,
        runtime_mode="historical",
        profile_id="historical-smoke",
        target_business_date="2026-07-06",
        target_business_dates=["2026-07-06"],
        data_inspection={"runtime_features": []},
        candidate_runtime={},
        candidate_runtime_path=Path(""),
        opportunity_runtime={},
        opportunity_runtime_path=Path(""),
        opportunity_summary={},
        lifecycle={},
        lifecycle_path=Path(""),
    )

    assert audit["temporal_isolation_status"] == "BLOCK"
    assert audit["future_state_reference_count"] == 3


def test_position_count_zero_does_not_allow_future_feature_reference(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    feature = tmp_path / "position_feature_input.parquet"
    audit = _temporal_authority_audit(
        root=root,
        runtime_mode="historical",
        profile_id="historical-smoke",
        target_business_date="2026-07-06",
        target_business_dates=["2026-07-06"],
        data_inspection={
            "runtime_features": [
                {
                    "component_id": "position_runtime_feature",
                    "artifact_path": str(feature),
                    "feature_date": "2026-07-14",
                    "input_source_date": "2026-07-14",
                    "runtime_consumer": "position",
                    "source_data_refs": {"current_position_count": "0", "current_position_state_as_of": "2026-07-17"},
                }
            ]
        },
        candidate_runtime={},
        candidate_runtime_path=Path(""),
        opportunity_runtime={},
        opportunity_runtime_path=Path(""),
        opportunity_summary={},
        lifecycle={},
        lifecycle_path=Path(""),
    )

    assert audit["temporal_isolation_status"] == "BLOCK"
    assert audit["future_state_references"][0]["component_id"] == "position_runtime_feature"


def test_isolated_empty_historical_root_passes_temporal_preflight(tmp_path: Path) -> None:
    root = tmp_path / "runtime_tests" / "run-1" / ".runtime"
    _write_json(root / "persistent_ledger" / "state.json", {"as_of": "2026-07-06T00:00:00Z", "positions": []})
    _write_json(root / "runtime_state" / "current_state.json", {"business_date": "2026-07-06"})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY"})

    audit = _temporal_authority_audit(
        root=root,
        runtime_mode="historical",
        profile_id="historical-smoke",
        target_business_date="2026-07-06",
        target_business_dates=["2026-07-06", "2026-07-07"],
        data_inspection={"runtime_features": []},
        candidate_runtime={},
        candidate_runtime_path=Path(""),
        opportunity_runtime={},
        opportunity_runtime_path=Path(""),
        opportunity_summary={},
        lifecycle={},
        lifecycle_path=Path(""),
    )

    assert audit["temporal_isolation_status"] == "PASS"
    assert audit["future_state_reference_count"] == 0


def test_historical_freshness_expected_date_is_target_not_actual() -> None:
    matrix = _freshness_matrix(
        runtime_mode="historical",
        expected_business_date="2026-07-06",
        data_inspection={
            "data_sources": [{"component_name": "Raw", "latest_business_date": "2026-07-14", "status": "PASS"}],
            "datasets": [],
            "runtime_features": [],
        },
        ai_inventory={"active_ai_models": []},
        authority_generation={"accepted_at": "", "runtime_loaded_generation": "", "committed_accepted_generation_id": "", "status": "PASS"},
        runtime_state_status={"safety": {}, "pm": {}},
    )

    raw = matrix["items"][0]
    assert raw["expected_latest_date"] == "2026-07-06"
    assert raw["expected_date_source"] == "historical_target_business_date"
    assert raw["lag_business_days"] == ""
    assert raw["required_through_date"] == "2026-07-06"
    assert raw["available_through_date"] == "2026-07-14"
    assert raw["missing_required_business_days"] == 0
    assert raw["coverage_ahead_business_days"] == 6
    assert raw["freshness_date_semantics"] == "historical_coverage_not_lag"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
