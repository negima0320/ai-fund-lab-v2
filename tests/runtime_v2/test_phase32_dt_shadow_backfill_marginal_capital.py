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
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/pycache-phase32-dt-tests"
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "shadow-backfill-marginal-capital", *args, "--json"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _minimal_pc(date: str, *, mismatch_date: str | None = None, omit_cash: bool = False) -> dict:
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
        "risk_pacing_intent": "NORMAL_DEPLOYMENT",
    }
    capital_competition = {
        "schema_version": "portfolio_construction.capital_competition.v1",
        "competitors": [
            {
                "accepted_weight": 0.05,
                "competitor_type": "ADD",
                "reason_codes": ["ADD_SELECTED", "COMPETITOR_SELECTED"],
                "status": "COMPETITOR_SELECTED",
                "symbol": "94320",
            },
            {
                "accepted_weight": 0.1,
                "competitor_type": "NEW_BUY",
                "reason_codes": ["COMPETITOR_SELECTED"],
                "status": "COMPETITOR_SELECTED",
                "symbol": "38520",
            },
        ],
        "canonical_cash_competitor_evidence": {} if omit_cash else cash,
        "market_candidate_cash_interaction": {
            "capital_competition_winner_symbol": "38520",
            "capital_competition_winner_type": "NEW_BUY",
        },
        "risk_pacing_evidence": {
            "risk_pacing_as_of": date,
            "risk_pacing_intent": "NORMAL_DEPLOYMENT",
            "schema_version": "risk_pacing_evidence.v1",
        },
    }
    return {
        "schema_version": "portfolio_construction.v1",
        "artifact_hash": f"pc-artifact-{date}",
        "business_date": mismatch_date or date,
        "feature_date": date,
        "producer_version": "test_pc_producer.v1",
        "incremental_budget_reconciliation": {"available_incremental_budget": 0.15},
        "portfolio_members": [
            {
                "business_date": date,
                "current_position": True,
                "current_quantity": 300,
                "current_weight": 0.04,
                "entry_admission_action": "ADD_REDUCED_ONLY",
                "entry_admission_state": "CONTINUATION_WITH_CAUTION",
                "membership_intent": "RETAIN",
                "phase29_l19_lot_resolution": {
                    "final_allocated_quantity": 100,
                    "one_lot_notional": 15000,
                    "one_lot_quantity": 100,
                    "pc_positive_executable_quantity_authority": {"status": "PASS"},
                },
                "pm_action": "ADD",
                "position_campaign_id": "pc-test-94320-0001",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "reentry_semantic_state": "REENTRY_NOT_APPLICABLE",
                "semantic_buy_type": "BUY_ADD",
                "source_candidate_id": "candidate-94320",
                "source_opportunity_id": "opportunity-94320",
                "source_pm_decision_ref": "pm-94320-add",
                "symbol": "94320",
                "target_weight": 0.05,
            },
            {
                "business_date": date,
                "current_position": False,
                "entry_admission_action": "BUY_NEW_ALLOWED",
                "membership_intent": "ADD_CANDIDATE",
                "phase29_l19_lot_resolution": {
                    "final_allocated_quantity": 100,
                    "one_lot_notional": 12000,
                    "one_lot_quantity": 100,
                },
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "reentry_semantic_state": "REENTRY_NOT_APPLICABLE",
                "semantic_buy_type": "BUY_NEW",
                "source_candidate_id": "candidate-38520",
                "source_opportunity_id": "opportunity-38520",
                "symbol": "38520",
            },
        ],
        "capital_competition": capital_competition,
        "source_hashes": {"test": "hash"},
        "upstream_artifacts": {"buy_quality": {"status": "PASS", "business_date_aligned": True}},
    }


def _write_run(evidence_root: Path, run_id: str, date: str, pc: dict) -> Path:
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
    _write_json(
        run_root / "daily" / date / "strategy" / "source_manifest.json",
        {
            "reason_codes": [
                "internal_dynamic_position_count:trend_regime:BULL",
                "internal_dynamic_cash_exposure:BULL",
                "internal_dynamic_position_count:market_breadth:STRONG",
                "internal_dynamic_position_count:volatility_regime:NORMAL",
            ]
        },
    )
    return run_root


def test_shadow_backfill_dry_run_does_not_write_output(tmp_path: Path) -> None:
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
    assert payload["summary"]["competitor_counts"]["BUY_ADD_NEXT_LOT"] == 1
    assert not output_root.exists()


def test_shadow_backfill_writes_isolated_dual_provenance_output(tmp_path: Path) -> None:
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
        (output_root / "daily" / "2023-02-13" / "unified_marginal_capital_shadow.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["competitor_counts"]["BUY_ADD_NEXT_LOT"] == 1
    assert summary["add_identity_missing_count"] == 0
    assert "ec_add_increment_evidence_tier_counts" in summary
    assert "ec_add_increment_demand_status_counts" in summary
    assert "ec_zero_desired_reclassification_counts" in summary
    assert "ec_stage_b_winner_counts" in summary
    assert "ee_unified_next_capital_unit_record_counts" in summary
    assert "ee_add_unknown_shadow_representation_counts" in summary
    assert "ee_new_buy_superior_reclassification_counts" in summary
    assert "ee_add_capitalization_impact" in summary
    assert daily["provenance"]["original_production"]["source_baseline"]["source_commit"] == "original-commit"
    assert daily["provenance"]["dq_evaluator"]["dq_schema_version"] == "unified_marginal_capital_shadow.v2"
    assert daily["live_runtime_state_used"] is False
    assert daily["upstream_historical_producers_recomputed"] is False
    assert daily["shadow"]["contract_flags"]["add_campaign_identity_preserved"] is True
    assert daily["shadow"]["contract_flags"]["executable_capital_ranking_present"] is True
    assert daily["shadow"]["contract_flags"]["add_strength_to_increment_target_authoritative_consumer_count"] == 0
    add_row = next(row for row in daily["shadow"]["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    assert "add_strength_to_increment_target_authority" in add_row
    assert "unified_next_capital_unit_record" in add_row
    assert daily["shadow"]["unified_next_capital_unit_evidence"]["authoritative_consumer_count"] == 0
    assert daily["shadow"]["unified_next_capital_unit_evidence"]["raw_evidence_and_normalized_value_separated"] is True
    assert "ec_strength_increment_executable_capital_ranking" in daily["shadow"]
    assert "stage_b_divergence_counts" in summary


def test_shadow_backfill_fails_closed_on_date_mismatch(tmp_path: Path) -> None:
    evidence_root = tmp_path / "runtime_tests"
    run_id = "runtime-test-source"
    _write_run(
        evidence_root,
        run_id,
        "2023-02-13",
        _minimal_pc("2023-02-13", mismatch_date="2023-02-14"),
    )

    result = _run_backfill(
        "--source-run-id",
        run_id,
        "--start-date",
        "2023-02-13",
        "--end-date",
        "2023-02-13",
        "--output-root",
        str(evidence_root / "analysis" / "mismatch"),
        "--evidence-root",
        str(evidence_root),
        "--dry-run",
    )

    assert result.returncode == 70
    assert "business_date mismatch" in result.stdout


def test_shadow_backfill_fails_closed_on_missing_input(tmp_path: Path) -> None:
    evidence_root = tmp_path / "runtime_tests"
    run_id = "runtime-test-source"
    _write_run(evidence_root, run_id, "2023-02-13", _minimal_pc("2023-02-13", omit_cash=True))

    result = _run_backfill(
        "--source-run-id",
        run_id,
        "--start-date",
        "2023-02-13",
        "--end-date",
        "2023-02-13",
        "--output-root",
        str(evidence_root / "analysis" / "missing"),
        "--evidence-root",
        str(evidence_root),
        "--dry-run",
    )

    assert result.returncode == 70
    assert "canonical cash evidence missing" in result.stdout


def test_shadow_backfill_deterministic_for_same_inputs(tmp_path: Path) -> None:
    evidence_root = tmp_path / "runtime_tests"
    run_id = "runtime-test-source"
    _write_run(evidence_root, run_id, "2023-02-13", _minimal_pc("2023-02-13"))

    args = (
        "--source-run-id",
        run_id,
        "--start-date",
        "2023-02-13",
        "--end-date",
        "2023-02-13",
        "--output-root",
        str(evidence_root / "analysis" / "deterministic"),
        "--evidence-root",
        str(evidence_root),
        "--dry-run",
    )
    first = json.loads(_run_backfill(*args).stdout)
    second = json.loads(_run_backfill(*args).stdout)

    assert first["summary"]["controls"] == second["summary"]["controls"]
    assert first["summary"]["competitor_counts"] == second["summary"]["competitor_counts"]
    assert first["summary"]["add_value_feasibility_counts"] == second["summary"]["add_value_feasibility_counts"]
