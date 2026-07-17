from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import _feature_date_contract_payload
from ai_fund_lab_v2.runtime_v2.position_management.producer import validate_position_management_input_contract


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_bl", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_feature_date_contract(
    operations_root: Path,
    *,
    business_date: str,
    selected_feature_date: str,
) -> Path:
    path = operations_root / "feature_date_contract" / f"{business_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "PASS",
        "reason": "carryover_feature_artifacts_available" if selected_feature_date != business_date else "requested_feature_artifacts_available",
        "requested_feature_date": business_date,
        "selected_feature_date": selected_feature_date,
        "latest_available_market_date": selected_feature_date,
        "carryover_used": selected_feature_date != business_date,
        "carryover_reason": "requested_feature_date_missing_latest_available_within_freshness_limit" if selected_feature_date != business_date else "",
        "freshness_lag_business_days": 1 if selected_feature_date != business_date else 0,
        "freshness_limit_business_days": 1,
        "feature_artifact_dir": str(operations_root / "feature_artifacts" / selected_feature_date),
        "generated_feature_artifacts": {
            "position_feature_input.parquet": str(operations_root / "feature_artifacts" / selected_feature_date / "position_feature_input.parquet"),
            "opportunity_feature_input.parquet": str(operations_root / "feature_artifacts" / selected_feature_date / "opportunity_feature_input.parquet"),
        },
        "missing_feature_artifacts": [],
        "requested_feature_artifact_dir": str(operations_root / "feature_artifacts" / business_date),
        "requested_missing_feature_artifacts": [],
        "price_source_alignment": "selected_feature_date",
        "consumer_ready": True,
        "schema_version": "runtime_v2_feature_consumer_readiness_v1",
        "candidate_schema_status": "READY",
        "candidate_missing_columns": [],
        "opportunity_schema_status": "READY",
        "pm_schema_status": "READY",
        "consumer_readiness_artifact_path": str(operations_root / "feature_consumer_readiness" / f"{selected_feature_date}.json"),
        "contract_artifact_path": str(path),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_runtime_contract_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    operations_root = root / "operations"
    for business_date, selected in {
        "2026-07-06": "2026-07-06",
        "2026-07-07": "2026-07-07",
        "2026-07-08": "2026-07-08",
        "2026-07-09": "2026-07-08",
    }.items():
        _write_feature_date_contract(operations_root, business_date=business_date, selected_feature_date=selected)
    return root


def _pm_current() -> dict:
    return {
        "schema_version": "runtime_v2_current_temporal_v1",
        "temporal_schema_version": "runtime_v2_current_temporal_v1",
        "business_date": "2026-07-09",
        "as_of": "2026-07-09",
        "position_state_as_of": "2026-07-09",
        "valuation_as_of": "2026-07-09",
        "current_position_status": "READY",
        "current_valuation_status": "READY",
        "positions": [
            {
                "symbol": "7203",
                "quantity": 100,
                "as_of": "2026-07-09",
                "source": "runtime_test",
                "average_price": 1000.0,
                "current_price": 1010.0,
                "holding_days": 3,
                "peak_return": 0.03,
            }
        ],
    }


def _write_pm_files(tmp_path: Path, *, opportunity_target_date: str) -> tuple[Path, Path]:
    feature_path = tmp_path / "position_feature_input.csv"
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-08",
                "code": "7203",
                "holding_days": 3,
                "peak_return": 0.03,
            }
        ]
    ).to_csv(feature_path, index=False)
    opportunity_path = tmp_path / "opportunity_rankings.json"
    opportunity_path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_opportunity_ranking_v1",
                "schema_name": "runtime_v2_buy_opportunity_ranking",
                "artifact_role": "BUY_OPPORTUNITY_RANKING",
                "producer": "Runtime v2 BUY AI Producer",
                "status": "PASS",
                "business_date": "2026-07-09",
                "feature_date": opportunity_target_date,
                "model_version": "opportunity-model-v1",
                "generated_at": "2026-07-09T08:10:00+09:00",
                "rankings": [
                    {
                        "target_date": opportunity_target_date,
                        "code": "7203",
                        "expected_edge_score": 0.2,
                        "buy_rank": 1,
                        "downside_risk_score": 0.1,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return feature_path, opportunity_path


def test_phase17_bl_runner_uses_normal_contract_not_profile_as_authority(tmp_path: Path) -> None:
    runner = _load_runner()
    root = _write_runtime_contract_root(tmp_path)
    profile = {
        "accepted_feature_dates": {
            "2026-07-09": "2026-07-08",
        }
    }

    evidence = runner.resolve_feature_date(runtime_root=root, business_date="2026-07-09", profile=profile)

    assert evidence["source"] == "normal_feature_date_contract"
    assert evidence["feature_date_authority_source"] == "normal_feature_date_contract"
    assert evidence["selected_feature_date"] == "2026-07-08"
    assert evidence["profile_value_used_as_authority"] is False
    assert evidence["contract_materialized"] is True
    assert evidence["authority_status"] == "PASS"


def test_phase17_bl_data_readiness_blocks_cli_feature_date_contract_mismatch(tmp_path: Path) -> None:
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_date_contract(operations_root, business_date="2026-07-09", selected_feature_date="2026-07-08")

    payload = _feature_date_contract_payload(
        operations_root=operations_root,
        business_date="2026-07-09",
        explicit_feature_date="2026-07-09",
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["reason"] == "feature_date_authority_mismatch"
    assert payload["selected_feature_date"] == "2026-07-08"
    assert payload["cli_feature_date"] == "2026-07-09"
    assert payload["cli_feature_date_authority_status"] == "MISMATCH"


def test_phase17_bl_pm_accepts_business_date_artifact_with_previous_feature_date(tmp_path: Path) -> None:
    feature_path, opportunity_path = _write_pm_files(tmp_path, opportunity_target_date="2026-07-08")

    contract = validate_position_management_input_contract(
        current=_pm_current(),
        current_path=tmp_path / "current_state.json",
        runtime_state={"business_date": "2026-07-09"},
        runtime_state_path=tmp_path / "runtime_state.json",
        business_date="2026-07-09",
        feature_date="2026-07-08",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )

    assert contract["pm_input_schema_status"] == "READY"
    assert contract["pm_opportunity_status"] == "READY"
    assert contract["pm_feature_date"] == "2026-07-08"
    assert contract["pm_review_required"] is False


def test_phase17_bl_pm_fails_closed_when_opportunity_feature_date_differs(tmp_path: Path) -> None:
    feature_path, opportunity_path = _write_pm_files(tmp_path, opportunity_target_date="2026-07-09")

    contract = validate_position_management_input_contract(
        current=_pm_current(),
        current_path=tmp_path / "current_state.json",
        runtime_state={"business_date": "2026-07-09"},
        runtime_state_path=tmp_path / "runtime_state.json",
        business_date="2026-07-09",
        feature_date="2026-07-08",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )

    assert contract["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert contract["pm_opportunity_status"] == "HALT"
    assert "opportunity.contract:target date mismatch" in contract["pm_missing_fields"]
