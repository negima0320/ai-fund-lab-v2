from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import CONFIRM_FLAG, call_main, load_runner, make_runtime_root


def _job_name(command: list[str]) -> str:
    return command[command.index("--job") + 1]


def _write_runtime_manifest(path: Path, *, classification: str = "INSUFFICIENT_EVIDENCE", include_continuity: bool = True) -> None:
    stages = [
        {
            "name": "candidate_opportunity_ai_runtime_producer",
            "status": "REVIEW_REQUIRED",
            "details": {
                "ai_lifecycle_gate": {
                    "decision": "REVIEW_REQUIRED",
                    "classification": classification,
                    "block_buy_planning": True,
                    "block_buy_submit": True,
                    "block_sell_planning": False,
                    "block_sell_submit": False,
                    "sell_planning_permission": "PASS",
                    "sell_submit_authorization_permission": "PASS",
                }
            },
        }
    ]
    if include_continuity:
        stages.extend(
            [
                {
                    "name": "buy_lifecycle_sell_continuity",
                    "status": "PASS",
                    "details": {
                        "status": "PASS",
                        "block_buy": True,
                        "block_sell": False,
                        "buy_planning_permission": "BLOCK",
                        "buy_submit_permission": "BLOCK",
                        "sell_planning_permission": "PASS",
                        "sell_submit_authorization_permission": "PASS",
                        "broker_write_performed": False,
                    },
                },
                {
                    "name": "buy_lifecycle_sell_authorization_continuity",
                    "status": "PASS",
                    "details": {
                        "call_graph_reached": True,
                        "sell_planning_stage_reached": True,
                        "sell_submit_authorization_stage_reached": True,
                        "buy_planning_permission": "BLOCK",
                        "buy_submit_permission": "BLOCK",
                        "sell_planning_permission": "PASS",
                        "sell_submit_authorization_permission": "PASS",
                        "broker_write_performed": False,
                    },
                },
            ]
        )
    path.write_text(
        json.dumps(
            {
                "business_date": "2026-07-06",
                "ai_lifecycle_gate_decision": "REVIEW_REQUIRED",
                "ai_lifecycle_gate_classification": classification,
                "ai_lifecycle_gate_block_buy_planning": True,
                "ai_lifecycle_gate_block_buy_submit": True,
                "ai_lifecycle_gate_block_sell_planning": False,
                "ai_lifecycle_gate_block_sell_submit": False,
                "sell_planning_permission": "PASS",
                "sell_submit_authorization_permission": "PASS",
                "stages": stages,
            }
        ),
        encoding="utf-8",
    )


def test_phase18w_runner_continues_after_buy_only_review_required_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    morning_manifest = manifest_dir / "morning.json"
    _write_runtime_manifest(morning_manifest)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        if _job_name(command) == "morning":
            return subprocess.CompletedProcess(command, 20, json.dumps({"manifest": str(morning_manifest)}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert backup["status"] == "PASS"
    assert payload["status"] == "PASS"
    assert [_job_name(command) for command in commands] == list(runner.JOB_SEQUENCE)
    run_dir = next((evidence / "runs").iterdir())
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    morning = next(record for record in run_state["completed_jobs"] if record["job"] == "morning")
    assert morning["exit_code"] == 20
    assert morning["runtime_test_job_status"] == "REVIEW_REQUIRED_BUY_ONLY"
    scoped = json.loads((run_dir / "daily" / "2026-07-06" / "morning" / "scoped_block_continuation.json").read_text(encoding="utf-8"))
    assert scoped["scope"] == "BUY_ONLY"
    assert scoped["checks"]["call_graph_reached"] is True


def test_phase18w_runner_halts_when_nonzero_scope_is_critical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    morning_manifest = manifest_dir / "morning-critical.json"
    _write_runtime_manifest(morning_manifest, classification="CRITICAL_AUTHORITY_VIOLATION")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        if _job_name(command) == "morning":
            return subprocess.CompletedProcess(command, 20, json.dumps({"manifest": str(morning_manifest)}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert backup["status"] == "PASS"
    assert payload["status"] == "HALT"
    assert [_job_name(command) for command in commands] == ["market_refresh", "data_readiness", "morning"]
    run_dir = next((evidence / "runs").iterdir())
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    morning = run_state["halted_at"]
    assert morning["job"] == "morning"
    assert "runtime_test_job_status" not in morning
