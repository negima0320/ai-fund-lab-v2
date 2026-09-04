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
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/pycache-phase32-ej-tests"
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "shadow-backfill-position-size-adequacy", *args, "--json"],
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
    cash = {
        "business_date": date,
        "cash_competitor_evidence_hash": f"cash-{date}",
        "cash_preference_semantic": "RISK_OPTIONALITY_PREFERRED",
        "current_cash_weight": 0.2,
        "evidence_completeness": "COMPLETE",
        "future_information_used": False,
        "historical_outcome_used": False,
        "reason_codes": ["VALID_POLICY_RESERVE"],
        "remaining_cash_weight": 0.2,
    }
    return {
        "schema_version": "portfolio_construction.v1",
        "artifact_hash": f"pc-artifact-{date}",
        "business_date": date,
        "feature_date": date,
        "producer_version": "test_pc_producer.v1",
        "incremental_budget_reconciliation": {"available_incremental_budget": 0.15},
        "portfolio_members": [
            {
                "business_date": date,
                "current_position": True,
                "current_quantity": 300,
                "current_weight": 0.04,
                "target_weight": 0.06,
                "entry_admission_action": "ADD_ALLOWED",
                "entry_admission_state": "CONTINUATION_WITH_CAUTION",
                "entry_admission_evidence_sufficiency": "SUFFICIENT",
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "position_campaign_id": "pc-test-94320-0001",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "source_candidate_id": "candidate-94320",
                "source_opportunity_id": "opportunity-94320",
                "source_pm_decision_ref": "pm-94320-add",
                "input_opportunity_rank": 2,
                "runtime_opportunity_score": 0.66,
                "strategy_intelligence_continuation_quality_status": "PASS",
                "strategy_intelligence_downside_risk_status": "PASS",
                "strategy_intelligence_relative_strength_state": "STRONG",
                "tick_normalized_trend_state": "ROBUST",
                "liquidity_capacity_status": "PASS",
                "rolling_median_traded_value_20": 100000000,
                "add_investment_evidence": {
                    "incremental_value": {"state": "POSITIVE"},
                    "expected_edge": {"state": "IMPROVING"},
                    "opportunity_cost": {"state": "PASS"},
                },
                "phase29_l19_lot_resolution": {
                    "final_allocated_quantity": 100,
                    "one_lot_notional": 15000,
                    "one_lot_quantity": 100,
                },
                "symbol": "94320",
            }
        ],
        "capital_competition": {
            "competitors": [
                {"accepted_weight": 0.02, "competitor_type": "ADD", "status": "COMPETITOR_SELECTED", "symbol": "94320"},
            ],
            "canonical_cash_competitor_evidence": cash,
            "market_candidate_cash_interaction": {
                "capital_competition_winner_symbol": "94320",
                "capital_competition_winner_type": "ADD",
            },
            "risk_pacing_evidence": {"risk_pacing_as_of": date, "risk_pacing_intent": "NORMAL_DEPLOYMENT"},
        },
    }


def _write_run(evidence_root: Path, run_id: str, date: str, pc: dict) -> None:
    run_root = evidence_root / "runs" / run_id
    _write_json(
        run_root / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "status": "COMPLETED",
            "source_baseline": {"source_commit": "original-commit", "source_dirty": True},
        },
    )
    _write_json(run_root / "daily" / date / "strategy" / "portfolio_construction.json", pc)
    _write_json(run_root / "daily" / date / "strategy" / "source_manifest.json", {})


def test_phase32_ej_position_size_adequacy_backfill_dry_run_is_non_mutating(tmp_path: Path) -> None:
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
    assert payload["summary"]["winner_position_size_adequacy_shadow"] == "PASS"
    assert payload["summary"]["authoritative_consumer_count"] == 0
    assert payload["summary"]["current_target_used_as_control_not_label"] == "PASS"
    assert not output_root.exists()


def test_phase32_ej_position_size_adequacy_backfill_writes_analysis_only_artifact(tmp_path: Path) -> None:
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
        (output_root / "daily" / "2023-02-13" / "winner_position_size_adequacy_shadow.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["production_change_executed"] is False
    assert summary["runtime_state_mutated"] is False
    assert summary["potential_undercapitalized_count"] == 1
    shadow = daily["winner_position_size_adequacy_shadow"]
    assert shadow["authoritative_consumer_count"] == 0
    assert shadow["production_allocation_consumer"] is False
    assert shadow["diagnostic_rows"][0]["position_size_adequacy_class"] == "POTENTIAL_UNDERCAPITALIZED"
