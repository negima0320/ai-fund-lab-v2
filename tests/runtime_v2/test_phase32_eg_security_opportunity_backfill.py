from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts" / "runtime_test.py"


def _run_backfill(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/pycache-phase32-eg-tests"
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "shadow-backfill-security-opportunity", *args, "--json"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _minimal_pc(date: str) -> dict:
    return {
        "schema_version": "portfolio_construction.v1",
        "artifact_hash": f"pc-artifact-{date}",
        "business_date": date,
        "feature_date": date,
        "producer_version": "test_pc_producer.v1",
        "portfolio_members": [
            {
                "business_date": date,
                "current_position": True,
                "current_quantity": 300,
                "current_weight": 0.04,
                "target_weight": 0.05,
                "entry_admission_action": "ADD_ALLOWED",
                "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
                "entry_admission_evidence_sufficiency": "SUFFICIENT",
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "position_campaign_id": "pc-test-94320-0001",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "quality_status": "PASS",
                "source_candidate_id": "candidate-94320",
                "source_opportunity_id": "opportunity-94320",
                "input_opportunity_rank": 3,
                "runtime_opportunity_score": 0.44,
                "strategy_intelligence_continuation_quality_status": "PASS",
                "strategy_intelligence_downside_risk_status": "PASS",
                "strategy_intelligence_relative_strength_state": "STRONG",
                "tick_normalized_trend_state": "ROBUST",
                "momentum_confidence_state": "CONFIRMED",
                "liquidity_capacity_status": "PASS",
                "rolling_median_traded_value_20": 100000000,
                "add_investment_evidence": {
                    "incremental_value": {"state": "UNKNOWN"},
                    "expected_edge": {"state": "IMPROVING"},
                    "opportunity_cost": {"state": "NEW_BUY_SUPERIOR"},
                },
                "symbol": "94320",
            },
            {
                "business_date": date,
                "current_position": False,
                "entry_admission_action": "BUY_NEW_ALLOWED",
                "membership_intent": "ADD_CANDIDATE",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "source_candidate_id": "candidate-38520",
                "source_opportunity_id": "opportunity-38520",
                "input_opportunity_rank": 1,
                "runtime_opportunity_score": 0.77,
                "strategy_intelligence_continuation_quality_status": "PASS",
                "strategy_intelligence_downside_risk_status": "PASS",
                "tick_normalized_trend_state": "ROBUST",
                "liquidity_capacity_status": "PASS",
                "symbol": "38520",
            },
        ],
        "source_hashes": {"test": "hash"},
        "upstream_artifacts": {"buy_quality": {"status": "PASS", "business_date_aligned": True}},
    }


def _write_run(evidence_root: Path, run_id: str, date: str, pc: dict) -> None:
    run_root = evidence_root / "runs" / run_id
    _write_json(
        run_root / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "status": "COMPLETED",
            "source_baseline": {
                "source_commit": "original-commit",
                "source_dirty": True,
                "accepted_artifact_hash": "accepted-hash",
                "registry_hash": "registry-hash",
            },
        },
    )
    _write_json(run_root / "daily" / date / "strategy" / "portfolio_construction.json", pc)


def test_phase32_eg_security_opportunity_backfill_dry_run_is_non_mutating(tmp_path: Path) -> None:
    evidence_root = tmp_path / "runtime_tests"
    run_id = "runtime-test-source"
    _write_run(evidence_root, run_id, "2023-02-13", _minimal_pc("2023-02-13"))
    output_root = evidence_root / "analysis" / "dry-run"

    result = _run_backfill(
        "--source-run-id",
        run_id,
        "--start-date",
        "2023-02-13",
        "--end-date",
        "2023-02-13",
        "--output-root",
        str(output_root),
        "--evidence-root",
        str(evidence_root),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["summary"]["authoritative_consumer_count"] == 0
    assert payload["summary"]["record_count"] == 2
    assert not output_root.exists()


def test_phase32_eg_security_opportunity_backfill_writes_isolated_shadow_output(tmp_path: Path) -> None:
    evidence_root = tmp_path / "runtime_tests"
    run_id = "runtime-test-source"
    _write_run(evidence_root, run_id, "2023-02-13", _minimal_pc("2023-02-13"))
    output_root = evidence_root / "analysis" / "actual"

    result = _run_backfill(
        "--source-run-id",
        run_id,
        "--start-date",
        "2023-02-13",
        "--end-date",
        "2023-02-13",
        "--output-root",
        str(output_root),
        "--evidence-root",
        str(evidence_root),
        "--confirm",
    )

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    daily = json.loads(
        (output_root / "daily" / "2023-02-13" / "security_opportunity_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["authoritative_consumer_count"] == 0
    assert summary["ee_add_unknown_security_evidence_coverage"]["COMPLETE"] == 1
    evidence = daily["security_opportunity_evidence"]
    assert evidence["authoritative_consumer_count"] == 0
    assert evidence["action_authority"] is False
    held = next(record for record in evidence["records"] if record["symbol"] == "94320")
    assert held["position_relationship"]["relationship_state"] == "HELD"
    assert "current_weight" not in held["intrinsic_security_evidence"]
