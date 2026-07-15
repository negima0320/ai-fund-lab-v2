from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"
CONFIRM_FLAG = "--yes-i-understand-this-mutates-trading-state"


def test_phase17_ae_reset_removes_stale_feature_contract_and_plan_ignores_preexisting_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    runtime_root = _make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"
    _write_stale_day2_artifacts(runtime_root)
    _write_retained_artifacts(runtime_root)

    backup = _call_main(
        runner,
        ["backup", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--confirm", CONFIRM_FLAG],
        capsys,
    )
    reset = _call_main(
        runner,
        [
            "reset",
            "--runtime-root",
            str(runtime_root),
            "--evidence-root",
            str(evidence_root),
            "--backup-id",
            backup["backup_id"],
            "--initial-cash",
            "1000000",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    plan = _call_main(
        runner,
        ["plan", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--business-days", "5", "--start-date", "2026-07-06"],
        capsys,
    )

    assert backup["status"] == "PASS"
    assert reset["status"] == "PASS"
    assert reset["clean_state_invariant"]["schema_version"] == "runtime_test_reset_clean_state_invariant_v1"
    assert reset["clean_state_invariant"]["passes"] is True
    assert reset["clean_state_invariant"]["stale_feature_date_contracts_remaining"] == []
    assert reset["clean_state_invariant"]["stale_feature_consumer_readiness_remaining"] == []
    assert reset["clean_state_invariant"]["stale_run_manifests_remaining"] == []
    assert not (runtime_root / "operations" / "feature_date_contract" / "2026-07-07.json").exists()
    assert not (runtime_root / "operations" / "feature_consumer_readiness" / "2026-07-07.json").exists()
    assert not (runtime_root / "operations" / "feature_artifacts" / "2026-07-07").exists()
    assert (runtime_root / "artifact_registry" / "index" / "registry_index.json").exists()
    assert (runtime_root / "candidate_ai" / "model.bin").exists()
    assert (runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet").exists()
    assert plan["status"] == "PASS"
    assert len(plan["business_dates"]) == 5
    assert plan["business_dates"][1]["feature_date_evidence"]["source"] == "runtime_test_plan_preflight"
    assert plan["business_dates"][1]["feature_date_evidence"]["contract_materialized"] is False

    rollback = _call_main(
        runner,
        ["rollback", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert rollback["status"] == "PASS"
    assert (runtime_root / "operations" / "feature_date_contract" / "2026-07-07.json").exists()


def test_phase17_ae_plan_does_not_accept_stale_contract_as_authority_without_reset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    runtime_root = _make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"
    _write_stale_day2_artifacts(runtime_root)

    plan = _call_main(
        runner,
        ["plan", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--business-days", "5", "--start-date", "2026-07-06"],
        capsys,
    )

    assert plan["status"] == "PASS"
    day2 = plan["business_dates"][1]["feature_date_evidence"]
    assert day2["stale_existing_contract_ignored"] is True
    assert day2["status"] == "PASS"
    assert day2["reason"] == "runtime_test_plan_preflight_uses_profile_window_not_stale_feature_contract"


def test_phase17_ae_reset_rejects_non_historical_profile_without_deleting_demo_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    runtime_root = _make_runtime_root(tmp_path)
    stale_path = runtime_root / "operations" / "feature_date_contract" / "2026-07-07.json"
    _write_stale_day2_artifacts(runtime_root)
    profile = json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))
    profile["profile_id"] = "demo-fixture"
    profile["mode"] = "demo"
    profile["runtime_root"] = str(runtime_root)
    profile_path = tmp_path / "demo_profile.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    result = _call_main(
        runner,
        ["reset", "--profile", str(profile_path), "--runtime-root", str(runtime_root), "--evidence-root", str(tmp_path / "reports"), "--dry-run"],
        capsys,
    )

    assert result["status"] == "PRECONDITION_FAILURE"
    assert stale_path.exists()


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_ae", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    exit_code = module.main(args + ["--json"])
    payload = json.loads(capsys.readouterr().out)
    payload["_exit_code"] = exit_code
    return payload


def _make_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    (root / "persistent_ledger" / "state.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_current_temporal_v1",
                "environment": "historical",
                "cash": 1000000,
                "buying_power": 1000000,
                "positions": [],
                "current_state_confirmed_empty": True,
            }
        ),
        encoding="utf-8",
    )
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    (root / "pending_order_plan" / "pending_order_plan.json").write_text(
        json.dumps({"schema_version": "runtime_v2_pending_slot_v1", "status": "EMPTY", "state": "EMPTY", "active_pending": False}),
        encoding="utf-8",
    )
    (root / "runtime_state" / "current_state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_operation_state_v1", "runtime_mode": "historical", "environment": "historical", "state": "READY"}),
        encoding="utf-8",
    )
    return root


def _write_stale_day2_artifacts(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "operations" / "feature_date_contract" / "2026-07-07.json",
        {
            "schema_version": "runtime_v2_feature_contract_v2",
            "status": "REVIEW_REQUIRED",
            "reason": "consumer_schema_review_required:pm",
            "requested_feature_date": "2026-07-07",
            "selected_feature_date": "2026-07-07",
            "latest_available_market_date": "2026-07-07",
            "consumer_ready": False,
            "pm_schema_status": "REVIEW_REQUIRED",
        },
    )
    _write_json(
        runtime_root / "operations" / "feature_consumer_readiness" / "2026-07-07.json",
        {
            "schema_version": "runtime_v2_feature_contract_v2",
            "status": "REVIEW_REQUIRED",
            "reason": "consumer_schema_review_required:pm",
            "consumer_ready": False,
            "pm_schema_status": "REVIEW_REQUIRED",
        },
    )
    feature_dir = runtime_root / "operations" / "feature_artifacts" / "2026-07-07"
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name in ("candidate_features.parquet", "opportunity_feature_input.parquet", "position_feature_input.parquet", "capital_policy_input.parquet"):
        (feature_dir / name).write_text("stale", encoding="utf-8")
    _write_json(runtime_root / "runtime_state" / "market" / "2026-07-07" / "latest.json", {"status": "STALE"})
    _write_json(runtime_root / "runtime_state" / "run_manifest" / "2026-07-07" / "old.json", {"status": "REVIEW_REQUIRED"})
    _write_json(runtime_root / "runtime_state" / "historical_broker" / "2026-07-07" / "state.json", {"status": "STALE"})


def _write_retained_artifacts(runtime_root: Path) -> None:
    _write_json(runtime_root / "artifact_registry" / "index" / "registry_index.json", {"registry": "keep"})
    _write_json(runtime_root / "artifact_registry" / "checkpoints" / "latest.json", {"checkpoint": "keep"})
    model = runtime_root / "candidate_ai" / "model.bin"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text("model", encoding="utf-8")
    canonical = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("canonical", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
