from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"
POINTER = REPO_ROOT / ".runtime/runtime_state/accepted_buy_ai_bundle.json"
CURRENT = REPO_ROOT / ".runtime/persistent_ledger/state.json"
PENDING = REPO_ROOT / ".runtime/pending_order_plan/pending_order_plan.json"


def _run_system_status(*args: str, evidence_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    command = [sys.executable, str(RUNTIME_TEST), "system-status", *args]
    if evidence_root is not None:
        command.extend(["--evidence-root", str(evidence_root)])
    return subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_system_status_help_has_minimal_options() -> None:
    result = _run_system_status("--help")
    assert result.returncode == 0
    assert "--json" in result.stdout
    assert "--write-evidence" in result.stdout
    assert "--scope" in result.stdout
    assert "--detailed" not in result.stdout


def test_system_status_json_reviews_whole_system() -> None:
    result = _run_system_status("--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    report = payload["system_status_report"]
    assert payload["scope"] == "overview"
    assert payload["status_summary"]["inspection_judgment"] == "PASS"
    assert payload["status_summary"]["model_health_judgment"] == "REVIEW_REQUIRED"
    assert report["status"] == "PASS"
    assert report["inspection_context"]["inspection_mode"] == "HISTORICAL_POST_RUN"
    assert report["inspection_context"]["target_business_date"] == "2026-07-14"
    assert report["data_status"]["status"] == "PASS"
    assert report["ai_status"]["status"] == "PASS"
    assert report["runtime_status"]["status"] == "PASS"
    assert report["runtime_status"]["model_health"]["status"] == "REVIEW_REQUIRED"
    assert report["runtime_state_status"]["status"] == "PASS"
    assert report["temporal_authority_audit"]["temporal_isolation_status"] == "PASS"
    assert report["broker_layer_status"]["broker_connection"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0


def test_system_status_human_summary() -> None:
    result = _run_system_status()
    assert result.returncode == 0
    assert "AI Fund Lab v2 System Status" in result.stdout
    assert "Data                : PASS" in result.stdout
    assert "Broker Connectivity : NOT_PERFORMED" in result.stdout
    assert "Inspection Mode     : HISTORICAL_POST_RUN" in result.stdout
    assert "Target Date         : 2026-07-14" in result.stdout
    assert "Exit Code: 0" in result.stdout


def test_system_status_write_evidence(tmp_path: Path) -> None:
    result = _run_system_status("--json", "--write-evidence", evidence_root=tmp_path)
    assert result.returncode == 20
    payload = json.loads(result.stdout)
    evidence_path = Path(payload["evidence_path"])
    expected = {
        "system_status_summary.json",
        "data_status.json",
        "ai_status.json",
        "runtime_status.json",
        "runtime_state_status.json",
        "broker_layer_status.json",
        "overall_status.json",
        "temporal_authority_audit.json",
        "target_period_data_sufficiency.json",
        "non_mutation.json",
        "final_judgment.json",
        "system_status_report.md",
    }
    assert expected.issubset({path.name for path in evidence_path.iterdir()})


def test_system_status_does_not_mutate_authority_or_trading_state(tmp_path: Path) -> None:
    before = {path: _sha256(path) for path in (POINTER, CURRENT, PENDING)}
    result = _run_system_status("--json", "--write-evidence", evidence_root=tmp_path)
    after = {path: _sha256(path) for path in (POINTER, CURRENT, PENDING)}
    assert result.returncode == 20
    assert before == after
