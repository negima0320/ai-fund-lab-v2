from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from tests.runtime_v2.test_phase14e36_feature_date_contract_carryover_policy import (
    ARTIFACTS,
    _write_candidate_model,
    _write_feature_inputs,
    _write_fixed_current,
    _write_json,
    _write_opportunity_metrics,
    _write_opportunity_model,
    _write_policy as _write_morning_policy,
)
from tests.runtime_v2.test_phase15h_capital_deployment_policy import (
    _latest_manifest,
    _position,
    _write_pm_inputs,
    _write_policy as _write_sell_policy,
    _write_runtime_state,
)


def test_phase22_gr_morning_pm_schema_review_does_not_block_buy_planning_stage(tmp_path: Path) -> None:
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        feature_date="2026-07-08",
    )
    policy_path = _write_morning_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    _write_json(
        tmp_path / ".runtime" / "operations" / "feature_date_contract" / "2026-07-09.json",
        {
            "status": "PASS",
            "reason": "carryover_feature_artifacts_available",
            "requested_feature_date": "2026-07-09",
            "selected_feature_date": "2026-07-08",
            "latest_available_market_date": "2026-07-08",
            "carryover_used": True,
            "carryover_reason": "requested_feature_date_missing_latest_available_within_freshness_limit",
            "freshness_lag_business_days": 1,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_root / "2026-07-08"),
            "generated_feature_artifacts": {name: str(feature_root / "2026-07-08" / name) for name in ARTIFACTS},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_root / "2026-07-09"),
            "requested_missing_feature_artifacts": list(ARTIFACTS),
            "price_source_alignment": "selected_feature_date",
            "contract_artifact_path": str(
                tmp_path / ".runtime" / "operations" / "feature_date_contract" / "2026-07-09.json"
            ),
        },
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-09",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
            "--opportunity-model-path",
            str(opportunity_model_path),
            "--opportunity-training-metrics-path",
            str(_write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)),
        ]
    )

    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    stage_names = [stage["name"] for stage in manifest["stages"]]
    readiness_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_data_readiness_gate")
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")

    assert exit_code == 0
    assert stage_names.index("runtime_data_readiness_gate") < stage_names.index("morning_ai_planning_pending_pipeline")
    assert readiness_stage["status"] == "READY"
    assert readiness_stage["details"]["components"]["feature"]["pm_schema_status"] == "REVIEW_REQUIRED"
    assert morning_stage["status"] == "PASS"
    assert morning_stage["details"]["feature_date"] == "2026-07-08"


def test_phase22_gr_sell_planning_explicit_pm_inputs_own_feature_date_authority(tmp_path: Path) -> None:
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[_position("3926", quantity=1000, price=351)],
    )
    policy_path = _write_sell_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_path, feature_path = _write_pm_inputs(tmp_path, symbols=("3926",))

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--pm-opportunity-path",
            str(opportunity_path),
            "--pm-feature-path",
            str(feature_path),
        ]
    )

    manifest = _latest_manifest(runtime_root, "2026-07-09")
    readiness_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_data_readiness_gate")
    sell_stage = next(stage for stage in manifest["stages"] if stage["name"] == "sell_planning_pending_pipeline")

    assert exit_code == 0
    assert readiness_stage["status"] == "READY"
    assert readiness_stage["details"]["components"]["pm"]["contract"]["pm_feature_date"] == "2026-07-09"
    assert sell_stage["status"] in {"PASS", "NO_SIGNAL"}
