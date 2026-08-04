from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.system_status import build_system_status_report, inspect_safety_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_system_status_preserves_post_run_missing_safety_block() -> None:
    report = build_system_status_report(
        runtime_root=REPO_ROOT / ".runtime",
        expected_business_date="2026-07-06",
        created_at="2026-07-20T00:00:00Z",
    )

    safety = report["runtime_state_status"]["safety"]

    assert safety["safety_artifact_status"] == "NOT_YET_APPLICABLE"
    assert safety["missing_state_classification"] == "PRE_RUN_NOT_MATERIALIZED"
    assert safety["materialization_stage"] == "PRE_RUN"
    assert report["runtime_state_status"]["status"] == "PASS"
    assert report["runtime_state_status"]["temporal_isolation"]["block_reason"] == "NOT_RECORDED"


def test_missing_safety_after_target_morning_manifest_blocks(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / "2026-07-06"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "runtime-v2-morning-2026-07-06.json").write_text(
        json.dumps(
            {
                "business_date": "2026-07-06",
                "job": "morning",
                "stages": [{"name": "morning_ai_planning_pending_pipeline", "status": "PASS"}],
            }
        ),
        encoding="utf-8",
    )

    safety = inspect_safety_artifact(runtime_root, expected_business_date="2026-07-06")

    assert safety["status"] == "BLOCK"
    assert safety["safety_artifact_status"] == "BLOCK"
    assert safety["missing_state_classification"] == "POST_RUN_MATERIALIZATION_MISSING"


def test_formal_safety_route_materializes_latest_decision(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    _write_minimal_runtime_inputs(runtime_root, business_date="2026-07-06")
    now = datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc)

    evaluation = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date="2026-07-06",
        mode="historical",
        now=now,
    )
    producer = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date="2026-07-06",
        mode="historical",
        source_artifact_path=evaluation.safety_report_path,
        now=datetime(2026, 7, 6, 0, 1, tzinfo=timezone.utc),
    )
    safety = inspect_safety_artifact(runtime_root, expected_business_date="2026-07-06")

    assert evaluation.status == "REVIEW_REQUIRED"
    assert producer.status == "REVIEW_REQUIRED"
    assert Path(producer.runtime_safety_decision_path).is_file()
    assert safety["safety_artifact_status"] == "READY"
    assert safety["missing_state_classification"] == "MATERIALIZED"
    assert safety["artifact_business_date"] == "2026-07-06"


def _write_minimal_runtime_inputs(runtime_root: Path, *, business_date: str) -> None:
    ledger = runtime_root / "persistent_ledger"
    state = runtime_root / "runtime_state"
    ledger.mkdir(parents=True)
    state.mkdir(parents=True)
    (ledger / "state.json").write_text(
        json.dumps(
            {
                "schema_version": "phase19_ay_isolated_current_v1",
                "business_date": business_date,
                "generated_at": f"{business_date}T00:00:00+09:00",
                "cash": 1_000_000,
                "positions": [],
            }
        ),
        encoding="utf-8",
    )
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (ledger / name).write_text("", encoding="utf-8")
    (state / "current_state.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_operation_state_v1",
                "business_date": business_date,
                "mode": "historical",
                "state": "CURRENT_STATE_LOADED",
                "safety_state": "NORMAL",
                "generated_at": f"{business_date}T00:00:00+09:00",
            }
        ),
        encoding="utf-8",
    )
