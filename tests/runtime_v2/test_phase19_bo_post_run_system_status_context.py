from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2 import system_status


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_DATE = "2026-07-06"
FINAL_DATE = "2026-07-10"


def test_clean_historical_pre_run_context_remains_day1(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path = _runtime_root(tmp_path, state_date=TARGET_DATE, artifact_dates=[])
    monkeypatch.setattr(system_status, "build_ai_status_report", lambda **_: _ai_report(manifest_path, TARGET_DATE))

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    assert report["inspection_context"]["inspection_mode"] == "HISTORICAL_PRE_RUN"
    assert report["runtime_stage_contract"]["runtime_stage"] == "PRE_RUN"
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0


def test_completed_single_day_historical_post_run_context_is_coherent(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path = _runtime_root(tmp_path, state_date=TARGET_DATE, artifact_dates=[TARGET_DATE])
    monkeypatch.setattr(system_status, "build_ai_status_report", lambda **_: _ai_report(manifest_path, TARGET_DATE))

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
        post_run_context=_post_run_context(runtime_root, [TARGET_DATE]),
    )

    assert report["inspection_context"]["inspection_mode"] == "HISTORICAL_POST_RUN"
    assert report["inspection_context"]["target_business_date"] == TARGET_DATE
    assert report["runtime_stage_contract"]["runtime_stage"] == "EXECUTION_DONE"
    assert report["runtime_state_status"]["safety"]["safety_artifact_status"] == "READY"
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0


def test_completed_five_day_historical_post_run_uses_final_day_authority(tmp_path: Path, monkeypatch) -> None:
    days = ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", FINAL_DATE]
    runtime_root, manifest_path = _runtime_root(tmp_path, state_date=FINAL_DATE, artifact_dates=days)
    monkeypatch.setattr(system_status, "build_ai_status_report", lambda **_: _ai_report(manifest_path, FINAL_DATE))

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=days,
        post_run_context=_post_run_context(runtime_root, days),
    )

    assert report["inspection_context"]["target_business_date"] == FINAL_DATE
    assert report["runtime_input_lineage_contract"]["target_business_date"] == FINAL_DATE
    assert report["runtime_input_lineage_contract"]["actual_feature_business_date"] == FINAL_DATE
    assert report["runtime_input_lineage_contract"]["inference_business_date"] == FINAL_DATE
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0
    assert report["runtime_state_status"]["status"] == "PASS"


def test_genuine_future_state_contamination_still_blocks(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path = _runtime_root(tmp_path, state_date=FINAL_DATE, artifact_dates=[TARGET_DATE])
    monkeypatch.setattr(system_status, "build_ai_status_report", lambda **_: _ai_report(manifest_path, TARGET_DATE))

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    assert report["status"] == "BLOCK"
    assert report["temporal_authority_audit"]["temporal_isolation_status"] == "BLOCK"
    assert report["temporal_authority_audit"]["future_state_reference_count"] > 0


def test_missing_historical_post_run_safety_authority_still_blocks(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path = _runtime_root(tmp_path, state_date=TARGET_DATE, artifact_dates=[TARGET_DATE])
    _write_json(
        runtime_root / "runtime_state" / "run_manifest" / TARGET_DATE / "runtime-v2-morning-2026-07-06.json",
        {"business_date": TARGET_DATE, "job": "morning", "status": "PASS"},
    )
    monkeypatch.setattr(system_status, "build_ai_status_report", lambda **_: _ai_report(manifest_path, TARGET_DATE))
    context = _post_run_context(runtime_root, [TARGET_DATE])
    context["safety_status"] = "MISSING"
    context["safety_authority_source"] = ""

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
        post_run_context=context,
    )

    assert report["status"] == "BLOCK"
    assert report["runtime_state_status"]["safety"]["missing_state_classification"] == "POST_RUN_MATERIALIZATION_MISSING"


def test_cli_closed_run_context_resolver_selects_latest_final_business_date(tmp_path: Path) -> None:
    runtime_root, _ = _runtime_root(tmp_path, state_date=FINAL_DATE, artifact_dates=[FINAL_DATE])
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-historical-smoke-20260721T000000000000Z"
    run_root = evidence_root / "runs" / run_id
    _write_json(
        run_root / "fresh_run_summary.json",
        {
            "status": "PASS",
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "runtime_root": str(runtime_root),
            "completed_days": [TARGET_DATE, FINAL_DATE],
            "close_result": "PASS",
        },
    )
    _write_json(run_root / "final_summary.json", {"status": "PASS", "closed_at": "2026-07-21T00:00:00Z"})

    module = _runtime_test_module()
    context = module.latest_closed_runtime_test_system_status_context(
        evidence_root=evidence_root,
        profile={"profile_id": "historical-smoke", "mode": "historical"},
        runtime_root=runtime_root,
    )

    assert context["context_type"] == "HISTORICAL_POST_RUN"
    assert context["final_business_date"] == FINAL_DATE
    assert context["safety_status"] in {"READY", "PASS"}


def _runtime_root(tmp_path: Path, *, state_date: str, artifact_dates: list[str]) -> tuple[Path, Path]:
    runtime_root = tmp_path / ".runtime"
    manifest_path = tmp_path / "accepted_generation_manifest.json"
    _write_json(
        manifest_path,
        {
            "accepted_generation_id": "accepted-generation-fixture",
            "candidate_member": {
                "feature_order": ["f1"],
                "feature_schema_hash": "candidate-schema",
                "model_artifact_path": str(tmp_path / "candidate-model.pkl"),
                "scaler_artifact_path": str(tmp_path / "candidate-scaler.pkl"),
                "calibration_artifact_path": str(tmp_path / "candidate-calibration.json"),
            },
            "opportunity_member": {
                "feature_order": ["candidate_score", "f1"],
                "feature_schema_hash": "opportunity-schema",
                "model_artifact_path": str(tmp_path / "opportunity-model.pkl"),
                "scaler_artifact_path": str(tmp_path / "opportunity-scaler.pkl"),
                "calibration_artifact_path": str(tmp_path / "opportunity-calibration.json"),
            },
        },
    )
    for name in (
        "candidate-model.pkl",
        "candidate-scaler.pkl",
        "candidate-calibration.json",
        "opportunity-model.pkl",
        "opportunity-scaler.pkl",
        "opportunity-calibration.json",
    ):
        (tmp_path / name).write_text("fixture", encoding="utf-8")
    _write_state(runtime_root, state_date)
    for day in artifact_dates:
        _write_day(runtime_root, day)
    return runtime_root, manifest_path


def _write_state(runtime_root: Path, business_date: str) -> None:
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {"business_date": business_date, "as_of": business_date, "cash": 1_000_000, "positions": []},
    )
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        path = runtime_root / "persistent_ledger" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    _write_json(
        runtime_root / "runtime_state" / "current_state.json",
        {"business_date": business_date, "as_of": business_date, "state": "CURRENT_STATE_LOADED"},
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {"state": "EMPTY", "active": False, "created_at": business_date, "orders": []},
    )


def _write_day(runtime_root: Path, business_date: str) -> None:
    artifact_dir = runtime_root / "operations" / "feature_artifacts" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "candidate_features.parquet",
        "opportunity_feature_input.parquet",
        "position_feature_input.parquet",
        "capital_policy_input.parquet",
    ):
        (artifact_dir / filename).write_text(f"{business_date}\n", encoding="utf-8")
    buy_ai = runtime_root / "runtime_state" / "buy_ai" / business_date
    _write_json(buy_ai / "candidate_decisions.json", {"business_date": business_date, "feature_date": business_date, "candidate_count": 2, "rows": []})
    _write_json(buy_ai / "opportunity_rankings.json", {"business_date": business_date, "feature_date": business_date, "rows": []})
    _write_json(buy_ai / "opportunity_inference_summary.json", {"business_date": business_date, "feature_path": str(artifact_dir / "opportunity_feature_input.parquet")})
    _write_json(buy_ai / "ai_lifecycle_gate_decision.json", {"business_date": business_date, "decision": "ALLOW"})
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / business_date
    for job in ("sell_planning", "morning", "submit", "execution"):
        payload = {"business_date": business_date, "job": job, "exit_code": 0, "status": "PASS"}
        if job == "submit":
            payload.update(
                {
                    "data_readiness_safety_status": "READY",
                    "data_readiness_safety_authority_business_date": business_date,
                    "data_readiness_safety_authority_source": "data_readiness_historical_temporal_authority",
                    "data_readiness_safety_authority_policy_version": "historical_replay_neutral_safety_v1",
                    "safety_decision": "ALLOW",
                }
            )
        _write_json(manifest_dir / f"runtime-v2-{job}-{business_date}.json", payload)


def _post_run_context(runtime_root: Path, days: list[str]) -> dict[str, Any]:
    final_day = days[-1]
    safety_path = runtime_root / "runtime_state" / "run_manifest" / final_day / f"runtime-v2-submit-{final_day}.json"
    return {
        "context_type": "HISTORICAL_POST_RUN",
        "status": "PASS",
        "run_id": "runtime-test-historical-smoke-fixture",
        "run_evidence_root": "reports/runtime_tests/runs/runtime-test-historical-smoke-fixture",
        "completed_business_days": days,
        "final_business_date": final_day,
        "runtime_stage": "EXECUTION_DONE",
        "completed_runtime_components": ["approval", "execution", "notification", "reporting", "sell_planning", "submit"],
        "safety_status": "READY",
        "safety_business_date": final_day,
        "safety_authority_source": "data_readiness_historical_temporal_authority",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_decision": "ALLOW",
        "safety_authority_path": str(safety_path),
    }


def _ai_report(manifest_path: Path, business_date: str) -> dict[str, Any]:
    return {
        "accepted_generation_status": {"status": "PASS", "accepted_generation_id": "accepted-generation-fixture", "manifest_path": str(manifest_path)},
        "runtime_authority_status": {"status": "PASS", "runtime_business_date": business_date, "runtime_loaded_generation": "accepted-generation-fixture"},
        "jquants_and_feature_freshness": {
            "status": "PASS",
            "latest_jquants": {"latest_successful_daily_quotes_date": business_date, "latest_normalized_daily_quotes_date": business_date},
            "latest_buy_feature": {"feature_date": business_date, "manifest_path": ""},
            "generation_bound": {"raw_data_max_date_at_generation": business_date, "normalized_data_max_date_at_generation": business_date},
        },
        "dataset_lineage": {"status": "PASS"},
        "split_audit": {"status": "PASS"},
        "freshness_taxonomy": {"status": "PASS"},
        "candidate_ai_status": {"status": "PASS", "runtime_top50_count": 2},
        "opportunity_ai_status": {"status": "PASS", "runtime_top20_count": 2, "dual_gate_status": "DUAL_GATE_PASS"},
        "runtime_readiness": {"status": "PASS", "lifecycle_classification": {"status": "PASS"}},
    }


def _runtime_test_module():
    spec = importlib.util.spec_from_file_location("runtime_test_script", REPO_ROOT / "scripts" / "runtime_test.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["runtime_test_script"] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
