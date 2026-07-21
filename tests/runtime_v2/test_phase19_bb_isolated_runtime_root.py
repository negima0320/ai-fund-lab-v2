from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.system_status import _temporal_authority_audit


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"
RUN_ID = "phase19_bb_pytest_isolated_root"


def _run_runtime_test(*args: str, evidence_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    command = [sys.executable, str(RUNTIME_TEST), *args]
    if evidence_root is not None:
        command.extend(["--evidence-root", str(evidence_root)])
    return subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def test_prepare_isolated_materializes_clean_day1_authority(tmp_path: Path) -> None:
    result = _run_runtime_test(
        "prepare-isolated",
        "--run-id",
        RUN_ID,
        "--target-business-date",
        "2026-07-06",
        "--json",
        "--write-evidence",
        evidence_root=tmp_path,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["shared_runtime_non_mutation"] is True
    assert payload["temporal_preflight"]["future_state_reference_count"] == 0
    assert payload["temporal_preflight"]["temporal_isolation_status"] == "PASS"
    assert payload["accepted_generation_resolution"]["resolution_status"] == "RESOLVED_COMMITTED"
    assert payload["day1_pre_run_artifact_inventory"]["status"] == "PASS"
    assert payload["historical_initial_state"]["cash"] == 1_000_000.0
    assert payload["historical_initial_state"]["positions"] == []


def test_system_status_runtime_root_points_at_isolated_root(tmp_path: Path) -> None:
    isolated = REPO_ROOT / ".runtime/runtime_tests" / RUN_ID / ".runtime"
    if not isolated.exists():
        test_prepare_isolated_materializes_clean_day1_authority(tmp_path)

    result = _run_runtime_test("system-status", "--runtime-root", str(isolated), "--json")
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]

    assert report["temporal_authority_audit"]["target_business_date"] == "2026-07-06"
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0
    assert report["temporal_authority_audit"]["temporal_isolation_status"] == "PASS"
    assert report["runtime_state_status"]["safety"]["safety_artifact_status"] == "NOT_YET_APPLICABLE"


def test_plan_can_bind_to_prepared_isolated_runtime_root(tmp_path: Path) -> None:
    isolated = REPO_ROOT / ".runtime/runtime_tests" / RUN_ID / ".runtime"
    if not isolated.exists():
        test_prepare_isolated_materializes_clean_day1_authority(tmp_path)

    result = _run_runtime_test(
        "plan",
        "--runtime-root",
        str(isolated),
        "--run-id",
        RUN_ID,
        "--business-days",
        "5",
        "--start-date",
        "2026-07-06",
        "--json",
        evidence_root=tmp_path,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["run_id"] == RUN_ID
    assert Path(payload["runtime_root"]) == isolated


def test_future_artifact_injection_blocks_temporal_preflight(tmp_path: Path) -> None:
    root = tmp_path / "runtime_tests" / "future-run" / ".runtime"
    state = root / "persistent_ledger" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"business_date": "2026-07-07", "positions": []}), encoding="utf-8")

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
    assert audit["future_state_reference_count"] == 1
