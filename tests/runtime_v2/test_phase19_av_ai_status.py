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


def _run_ai_status(*args: str, evidence_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    command = [sys.executable, str(RUNTIME_TEST), "ai-status", *args]
    if evidence_root is not None:
        command.extend(["--evidence-root", str(evidence_root)])
    return subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_ai_status_help() -> None:
    result = _run_ai_status("--help")
    assert result.returncode == 0
    assert "--detailed" in result.stdout
    assert "--write-evidence" in result.stdout
    assert "--check-runtime-readiness" in result.stdout


def test_ai_status_json_review_required_for_statistical_drift() -> None:
    result = _run_ai_status("--json", "--check-runtime-readiness")
    assert result.returncode == 10
    payload = json.loads(result.stdout)
    report = payload["ai_status_report"]
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["runtime_readiness"]["lifecycle_classification"] in {
        "STATISTICAL_DRIFT_REVIEW_REQUIRED",
        "MODEL_HEALTH_REVIEW_REQUIRED",
    }
    assert report["runtime_readiness"]["block_buy_planning"] is False
    assert report["runtime_readiness"]["lifecycle_decision"] == "REVIEW_REQUIRED"
    assert report["runtime_readiness"]["review_findings"]
    assert report["legacy_fallback_audit"]["legacy_fallback_used"] is False
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"


def test_ai_status_human_summary() -> None:
    result = _run_ai_status("--detailed", "--check-runtime-readiness")
    assert result.returncode == 10
    assert "AI Authority Status: RESOLVED_COMMITTED" in result.stdout
    assert "Broker Access: NOT_PERFORMED" in result.stdout
    assert "Exit Code: 10" in result.stdout


def test_ai_status_write_evidence(tmp_path: Path) -> None:
    result = _run_ai_status("--json", "--write-evidence", "--check-runtime-readiness", evidence_root=tmp_path)
    assert result.returncode == 10
    payload = json.loads(result.stdout)
    evidence_path = Path(payload["evidence_path"])
    assert evidence_path.is_dir()
    expected_files = {
        "ai_status_summary.json",
        "dataset_lineage.json",
        "split_audit.json",
        "candidate_ai_status.json",
        "opportunity_ai_status.json",
        "accepted_generation_status.json",
        "runtime_authority_status.json",
        "jquants_and_feature_freshness.json",
        "freshness_taxonomy.json",
        "runtime_readiness.json",
        "legacy_fallback_audit.json",
        "non_mutation.json",
        "final_judgment.json",
        "ai_status_report.md",
    }
    assert expected_files.issubset({path.name for path in evidence_path.iterdir()})
    summary = json.loads((evidence_path / "ai_status_summary.json").read_text(encoding="utf-8"))
    assert summary["overall_status"] == "REVIEW_REQUIRED"


def test_ai_status_does_not_mutate_runtime_pointer(tmp_path: Path) -> None:
    before = _sha256(POINTER)
    result = _run_ai_status("--json", "--write-evidence", evidence_root=tmp_path)
    after = _sha256(POINTER)
    assert result.returncode == 10
    assert before == after
