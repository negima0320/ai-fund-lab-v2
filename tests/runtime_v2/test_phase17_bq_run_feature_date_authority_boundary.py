from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.data_readiness import _feature_date_contract_payload


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def test_phase17_bq_run_re_resolves_feature_date_from_materialized_contract(tmp_path: Path, monkeypatch) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-historical-smoke-bq"
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        business_days=4,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id=run_id,
    )
    day4 = plan["business_dates"][3]
    day4["jobs"] = [job for job in day4["jobs"] if job["job"] in {"market_refresh", "data_readiness"}]
    plan["business_dates"] = [day4]
    _write_json(evidence_root / "runs" / run_id / "plan.json", plan)
    _write_backup_manifest(runner, evidence_root)
    executed: list[list[str]] = []

    def fake_run_runtime_cli(command: list[str], *, cwd: Path):
        executed.append(command)
        job = command[command.index("--job") + 1]
        if job == "market_refresh":
            _write_feature_date_contract(
                runtime_root,
                business_date="2026-07-09",
                selected_feature_date="2026-07-09",
            )
        return subprocess.CompletedProcess(command, 0, stdout='{"exit_code": 0}\n', stderr="")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run_runtime_cli)

    result = runner.run_command(
        argparse.Namespace(
            run_id=run_id,
            dry_run=False,
            confirm=True,
            explicit_mutation_confirm=True,
            business_days=None,
            start_date=None,
            date_from=None,
            date_to=None,
        ),
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
    )

    assert result.status == "PASS"
    data_readiness_command = executed[1]
    assert data_readiness_command[data_readiness_command.index("--feature-date") + 1] == "2026-07-09"
    run_state = json.loads((evidence_root / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    data_readiness_record = run_state["completed_jobs"][1]
    resolution = data_readiness_record["feature_date_command_resolution"]
    assert data_readiness_record["planned_command"][data_readiness_record["planned_command"].index("--feature-date") + 1] == "2026-07-08"
    assert resolution["feature_date_argument_action"] == "set_from_materialized_contract"
    assert resolution["feature_date_authority_source"] == "normal_feature_date_contract"
    assert resolution["planned_matches_materialized"] is False
    assert resolution["selected_feature_date"] == "2026-07-09"


def test_phase17_bq_cli_mismatch_still_fails_closed(tmp_path: Path) -> None:
    runtime_root = _make_clean_runtime_root(tmp_path)
    _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-09",
        selected_feature_date="2026-07-09",
    )

    payload = _feature_date_contract_payload(
        operations_root=runtime_root / "operations",
        business_date="2026-07-09",
        explicit_feature_date="2026-07-08",
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["reason"] == "feature_date_authority_mismatch"
    assert payload["cli_feature_date_authority_status"] == "MISMATCH"


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_bq", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _historical_profile() -> dict:
    return json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))


def _make_clean_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(root / "persistent_ledger" / "state.json", {"business_date": "", "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "active_pending": False})
    _write_json(root / "runtime_state" / "current_state.json", {"business_date": "", "state": "READY"})
    return root


def _write_backup_manifest(runner, evidence_root: Path) -> None:
    _write_json(
        evidence_root / "backups" / "backup-clean" / "backup_manifest.json",
        {
            "schema_version": runner.BACKUP_MANIFEST_SCHEMA_VERSION,
            "backup_id": "backup-clean",
            "backup_path": str(evidence_root / "backups" / "backup-clean"),
            "profile_id": "historical-smoke",
            "created_at": "2026-07-15T00:00:00Z",
        },
    )


def _write_feature_date_contract(
    runtime_root: Path,
    *,
    business_date: str,
    selected_feature_date: str,
) -> None:
    path = runtime_root / "operations" / "feature_date_contract" / f"{business_date}.json"
    _write_json(
        path,
        {
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": business_date,
            "selected_feature_date": selected_feature_date,
            "latest_available_market_date": selected_feature_date,
            "carryover_used": selected_feature_date != business_date,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(runtime_root / "operations" / "feature_artifacts" / selected_feature_date),
            "generated_feature_artifacts": {},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(runtime_root / "operations" / "feature_artifacts" / business_date),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "schema_version": "runtime_v2_feature_contract_v2",
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(runtime_root / "operations" / "feature_consumer_readiness" / f"{selected_feature_date}.json"),
            "contract_artifact_path": str(path),
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
