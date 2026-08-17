from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.shadow_runtime import (
    ARTIFACT_FILENAMES,
    _ai_output_summary,
    _existing_pm_decisions,
    _materialize_pre_action_position_campaigns,
    _optional_opportunity_artifact_path,
    _supply_add_expected_edge_baseline,
    _resolve_strategy_source_authority,
    _runtime_current_position_rows,
    generate_strategy_shadow_for_day,
    strategy_shadow_job_descriptor,
    validate_run_strategy_shadow,
)


def test_phase22_p_strategy_shadow_descriptor_is_shadow_only(tmp_path: Path) -> None:
    descriptor = strategy_shadow_job_descriptor(run_dir=tmp_path / "run", business_date="2026-07-06")

    assert descriptor["job"] == "strategy_shadow_generation"
    assert descriptor["execution_order"] == "after_daily_runtime_jobs"
    assert descriptor["active_runtime_consumer_eligibility"] == "NO"
    assert descriptor["runtime_switch_performed"] is False
    assert "read_only" in descriptor["mutation_policy"]


def test_phase22_p_strategy_shadow_generation_preserves_runtime_authority(tmp_path: Path) -> None:
    runtime_root = Path(".runtime")
    run_dir = tmp_path / "runs" / "phase22p-unit"
    run_dir.mkdir(parents=True)
    (run_dir / "plan.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_test_plan_v1",
                "run_id": "phase22p-unit",
                "profile_id": "historical-smoke",
                "runtime_root": str(runtime_root),
                "business_dates": [{"business_date": "2022-09-15", "feature_date": "2022-09-15", "jobs": []}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = generate_strategy_shadow_for_day(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id="phase22p-unit",
        profile_id="historical-smoke",
        business_date="2022-09-15",
        feature_date="2022-09-15",
        decision_timing="MORNING_FORMAL_PLANNING_AUTHORITY",
        authority_role="FORMAL_PLANNING_AUTHORITY_INPUT",
        materialization_role="IMMUTABLE_MORNING_PLANNING_SNAPSHOT",
    )

    assert summary["artifact_count"] == 12
    assert summary["runtime_mutation_performed"] is False
    assert summary["broker_connection_performed"] is False
    assert summary["broker_write_performed"] is False
    assert summary["active_runtime_consumer_eligibility"] == "YES"
    assert summary["strategy_intelligence_production_consumer_connected"] is True
    assert summary["legacy_authority_active"] is False
    assert summary["authority_role"] == "FORMAL_PLANNING_AUTHORITY_INPUT"
    assert summary["materialization_role"] == "IMMUTABLE_MORNING_PLANNING_SNAPSHOT"
    assert summary["decision_timing"] == "MORNING_FORMAL_PLANNING_AUTHORITY"
    assert summary["formal_planning_snapshot"] is True
    assert summary["post_runtime_shadow"] is False
    strategy_dir = run_dir / "daily" / "2022-09-15" / "strategy"
    assert (strategy_dir / "input_manifest.json").is_file()
    assert (strategy_dir / "strategy_decision_trace.json").is_file()
    assert (strategy_dir / "portfolio_policy.json").is_file()
    assert (strategy_dir / "portfolio_construction_draft.json").is_file()
    assert (strategy_dir / "position_sizing_preflight.json").is_file()
    assert (strategy_dir / "portfolio_construction.json").is_file()
    assert (strategy_dir / "position_sizing.json").is_file()
    assert (strategy_dir / "strategy_intelligence.json").is_file()
    assert (strategy_dir / "add_baseline_supply_evidence.json").is_file()
    assert not (strategy_dir / "dynamic_position_count.json").exists()
    assert not (strategy_dir / "dynamic_cash_exposure.json").exists()
    assert not (strategy_dir / "capital_deployment.json").exists()

    validation = validate_run_strategy_shadow(run_dir=run_dir, business_date="2022-09-15")
    assert validation["structural_validity"] == "PASS"
    assert validation["policy_acceptance"] == "NOT_REQUESTED"


def test_phase28_d55_c_strategy_artifact_sequence_materializes_draft_preflight_and_final() -> None:
    assert ARTIFACT_FILENAMES["portfolio_construction_draft"] == "portfolio_construction_draft.json"
    assert ARTIFACT_FILENAMES["position_sizing_preflight"] == "position_sizing_preflight.json"
    assert ARTIFACT_FILENAMES["portfolio_construction"] == "portfolio_construction.json"
    assert ARTIFACT_FILENAMES["position_sizing"] == "position_sizing.json"
    assert ARTIFACT_FILENAMES["strategy_intelligence"] == "strategy_intelligence.json"


def test_phase30_ac_pre_action_campaign_materialization_uses_prior_canonical_snapshot(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_position_campaigns(run_dir, "2026-07-14", "11110", "campaign-11110")
    _write_json(
        run_dir / "daily" / "2026-07-16" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": "2026-07-16",
            "position_campaigns": [
                {
                    "position_campaign_id": "future-campaign",
                    "symbol": "11110",
                    "campaign_status": "OPEN",
                    "current_quantity": 999,
                }
            ],
        },
    )
    current = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "source_ref": "state.json",
        "source_hash": "current-hash",
        "rows": (
            {
                "security_code": "11110",
                "quantity": 100,
                "average_price": 1000,
                "market_value": 112000,
                "quantity_basis": "ADJUSTED",
                "valuation_price_basis": "ADJUSTED",
            },
        ),
    }

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        business_date="2026-07-15",
        current=current,
        as_of="2026-07-15T00:00:00+00:00",
    )

    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    campaign = payload["position_campaigns"][0]
    assert campaign["position_campaign_id"] == "campaign-11110"
    assert campaign["current_quantity"] == 100
    assert round(campaign["current_campaign_relative_return"], 6) == 0.12
    assert payload["temporal_safety"]["same_day_eod_campaign_reconstruction_used"] is False
    assert payload["temporal_safety"]["future_information_used"] is False
    assert result["evidence"]["duplicate_campaign_authority_created"] is False


def test_phase30_ad1_first_buy_multi_symbol_bootstrap_uses_strict_prior_ledger(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_json(
        run_dir / "daily" / "2026-07-10" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "contract_version": "phase30_ac_pre_action_campaign_lifecycle.v1",
            "business_date": "2026-07-10",
            "authority": "CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE",
            "position_campaigns": [],
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-11110-buy", "2026-07-10", "11110", "BUY", 100, 1000),
            _execution("exec-22220-buy", "2026-07-10", "22220", "BUY", 200, 500),
            _execution("exec-33330-same-day-future", "2026-07-11", "33330", "BUY", 300, 100),
        ],
    )
    current = {
        "status": "PASS",
        "business_date": "2026-07-11",
        "source_ref": str(runtime_root / "persistent_ledger" / "state.json"),
        "source_hash": "current-hash",
        "rows": (
            {"security_code": "11110", "quantity": 100, "average_price": 1000, "market_value": 110000},
            {"security_code": "22220", "quantity": 200, "average_price": 500, "market_value": 100000},
            {"security_code": "33330", "quantity": 300, "average_price": 100, "market_value": 30000},
        ),
    }

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2026-07-11",
        current=current,
        as_of="2026-07-11T08:45:00+09:00",
    )

    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    by_symbol = {row["symbol"]: row for row in payload["position_campaigns"]}
    assert sorted(by_symbol) == ["11110", "22220"]
    assert by_symbol["11110"]["campaign_status"] == "OPEN"
    assert by_symbol["11110"]["current_quantity"] == 100
    assert by_symbol["11110"]["source_execution_id"] == "exec-11110-buy"
    assert round(by_symbol["11110"]["current_campaign_relative_return"], 6) == 0.1
    assert payload["pre_action_connection"]["bootstrap_open_campaign_symbols"] == ["11110", "22220"]
    assert payload["pre_action_connection"]["missing_current_campaign_symbols"] == ["33330"]
    assert payload["temporal_safety"]["same_day_future_execution_used"] is False
    assert payload["temporal_safety"]["future_information_used"] is False

    second = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2026-07-11",
        current=current,
        as_of="2026-07-11T08:45:00+09:00",
    )
    second_payload = json.loads(Path(second["artifact_path"]).read_text(encoding="utf-8"))
    assert [row["position_campaign_id"] for row in second_payload["position_campaigns"]] == [
        row["position_campaign_id"] for row in payload["position_campaigns"]
    ]


def test_phase30_ad1_add_reduce_exit_and_reentry_lifecycle_from_ledger(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-11110-buy-1", "2026-07-10", "11110", "BUY", 100, 1000),
            _execution("exec-11110-add", "2026-07-11", "11110", "BUY", 50, 1100),
            _execution("exec-11110-reduce", "2026-07-12", "11110", "SELL", 30, 1200),
            _execution("exec-22220-buy-1", "2026-07-10", "22220", "BUY", 100, 500),
            _execution("exec-22220-exit", "2026-07-11", "22220", "SELL", 100, 490),
            _execution("exec-22220-reentry", "2026-07-12", "22220", "BUY", 100, 510),
            _execution("exec-33330-buy-1", "2026-07-10", "33330", "BUY", 100, 800),
            _execution("exec-33330-exit", "2026-07-11", "33330", "SELL", 100, 790),
        ],
    )
    current = {
        "status": "PASS",
        "business_date": "2026-07-13",
        "source_ref": str(runtime_root / "persistent_ledger" / "state.json"),
        "source_hash": "current-hash",
        "rows": (
            {"security_code": "11110", "quantity": 120, "average_price": 1033.3333333333, "market_value": 132000},
            {"security_code": "22220", "quantity": 100, "average_price": 510, "market_value": 52000},
        ),
    }

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2026-07-13",
        current=current,
        as_of="2026-07-13T08:45:00+09:00",
    )

    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    by_symbol = {row["symbol"]: row for row in payload["position_campaigns"]}
    assert by_symbol["11110"]["campaign_status"] == "OPEN"
    assert by_symbol["11110"]["current_quantity"] == 120
    assert by_symbol["11110"]["add_history_summary"]["count"] == 1
    assert by_symbol["11110"]["reduce_history_summary"]["count"] == 1
    assert by_symbol["22220"]["campaign_status"] == "OPEN"
    assert by_symbol["22220"]["source_execution_id"] == "exec-22220-reentry"
    assert by_symbol["22220"]["position_campaign_id"] != by_symbol["11110"]["position_campaign_id"]
    assert "33330" not in by_symbol
    assert result["evidence"]["bootstrap_open_campaign_symbols"] == ["11110", "22220"]
    assert result["evidence"]["duplicate_campaign_authority_created"] is False


def test_phase30_ad1_prior_open_campaign_closes_when_strict_prior_ledger_exits(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_position_campaigns(run_dir, "2026-07-10", "11110", "campaign-11110")
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-11110-buy", "2026-07-10", "11110", "BUY", 100, 1000),
            _execution("exec-11110-exit", "2026-07-11", "11110", "SELL", 100, 900),
        ],
    )

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2026-07-12",
        current={"status": "PASS", "business_date": "2026-07-12", "rows": ()},
        as_of="2026-07-12T08:45:00+09:00",
    )

    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    assert payload["position_campaigns"][0]["position_campaign_id"] == "campaign-11110"
    assert payload["position_campaigns"][0]["campaign_status"] == "CLOSED"
    assert payload["position_campaigns"][0]["current_quantity"] == 0.0
    assert result["evidence"]["closed_campaign_symbols"] == ["11110"]


def test_phase28_d55_c_same_campaign_baseline_supply_uses_latest_prior_strategy_evidence(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    prior_pc = run_dir / "daily" / "2026-07-14" / "strategy" / "portfolio_construction.json"
    _write_json(
        prior_pc,
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": "2026-07-14",
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "current_position": True,
                    "position_campaign_id": "campaign-11110",
                    "runtime_opportunity_score": 0.70,
                }
            ],
        },
    )
    _write_json(
        run_dir / "daily" / "2026-07-15" / "strategy" / "portfolio_construction.json",
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": "2026-07-15",
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "current_position": True,
                    "position_campaign_id": "campaign-11110",
                    "runtime_opportunity_score": 0.99,
                }
            ],
        },
    )
    opportunity = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "expected_edge_score": 0.82},),
    }
    current = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "position_campaign_id": "campaign-11110"},),
    }
    _write_position_campaigns(run_dir, "2026-07-15", "11110", "campaign-11110")

    result = _supply_add_expected_edge_baseline(
        run_dir=run_dir,
        business_date="2026-07-15",
        opportunity=opportunity,
        current=current,
    )

    row = result["opportunity"]["rows"][0]
    evidence = result["evidence"]
    assert row["expected_edge_baseline_score"] == 0.70
    assert row["expected_edge_baseline_business_date"] == "2026-07-14"
    assert row["expected_edge_baseline_campaign_id"] == "campaign-11110"
    assert row["add_baseline_source_artifact_path"] == str(prior_pc)
    assert evidence["supplied_count"] == 1
    assert evidence["future_baseline_used"] is False
    assert evidence["symbol_only_baseline_used"] is False
    assert evidence["missing_baseline_behavior"] == "UNKNOWN_FAIL_CLOSED"


def test_phase28_d55_c_same_campaign_baseline_supply_fails_closed_without_valid_prior_campaign(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_json(
        run_dir / "daily" / "2026-07-14" / "strategy" / "portfolio_construction.json",
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": "2026-07-14",
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "current_position": True,
                    "position_campaign_id": "campaign-other",
                    "runtime_opportunity_score": 0.70,
                }
            ],
        },
    )
    _write_json(
        run_dir / "daily" / "2026-07-16" / "strategy" / "portfolio_construction.json",
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": "2026-07-16",
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "current_position": True,
                    "position_campaign_id": "campaign-11110",
                    "runtime_opportunity_score": 0.99,
                }
            ],
        },
    )
    opportunity = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "expected_edge_score": 0.82},),
    }
    current = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "position_campaign_id": "campaign-11110"},),
    }
    _write_position_campaigns(run_dir, "2026-07-15", "11110", "campaign-11110")

    result = _supply_add_expected_edge_baseline(
        run_dir=run_dir,
        business_date="2026-07-15",
        opportunity=opportunity,
        current=current,
    )

    row = result["opportunity"]["rows"][0]
    assert "expected_edge_baseline_score" not in row
    assert result["evidence"]["supplied_count"] == 0
    assert result["evidence"]["missing_count"] == 1
    assert result["evidence"]["future_baseline_used"] is False
    assert result["evidence"]["missing_baseline_behavior"] == "UNKNOWN_FAIL_CLOSED"


def test_phase30_ac_baseline_supply_uses_canonical_position_campaign_authority(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    prior_pc = run_dir / "daily" / "2026-07-14" / "strategy" / "portfolio_construction.json"
    _write_json(
        prior_pc,
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": "2026-07-14",
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "current_position": True,
                    "position_campaign_id": "campaign-11110",
                    "runtime_opportunity_score": 0.70,
                }
            ],
        },
    )
    opportunity = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "expected_edge_score": 0.82},),
    }
    current = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": ({"security_code": "11110", "position_campaign_id": "campaign-11110"},),
    }
    _write_position_campaigns(run_dir, "2026-07-15", "11110", "campaign-11110")
    position_management = {
        "status": "PASS",
        "business_date": "2026-07-15",
        "rows": (
            {
                "security_code": "11110",
                "action": "ADD",
                "position_id": "runtime-current-11110",
                "current_position_reference": "runtime-current-11110",
                "lifecycle_reference": "runtime-current-11110",
            },
        ),
    }

    result = _supply_add_expected_edge_baseline(
        run_dir=run_dir,
        business_date="2026-07-15",
        opportunity=opportunity,
        current=current,
        position_management=position_management,
    )

    row = result["opportunity"]["rows"][0]
    evidence = result["evidence"]
    assert row["position_campaign_id"] == "campaign-11110"
    assert row["expected_edge_baseline_score"] == 0.70
    assert row["expected_edge_baseline_business_date"] == "2026-07-14"
    assert row["expected_edge_baseline_campaign_id"] == "campaign-11110"
    assert row["add_baseline_source_artifact_path"] == str(prior_pc)
    assert evidence["campaign_identity_authority"] == "positions/position_campaigns.json"
    assert evidence["current_campaign_count"] == 1
    assert evidence["supplied_count"] == 1
    assert evidence["missing_count"] == 0
    assert evidence["future_baseline_used"] is False
    assert evidence["symbol_only_baseline_used"] is False


def test_phase26_hr2_post_runtime_shadow_uses_non_authoritative_subdir(tmp_path: Path) -> None:
    runtime_root = Path(".runtime")
    run_dir = tmp_path / "runs" / "phase26hr2-unit"
    run_dir.mkdir(parents=True)

    summary = generate_strategy_shadow_for_day(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id="phase26hr2-unit",
        profile_id="historical-smoke",
        business_date="2022-09-15",
        feature_date="2022-09-15",
        artifact_subdir="strategy_eod_shadow",
        decision_timing="EOD_POST_RUNTIME_OBSERVABILITY_SHADOW",
        authority_role="POST_RUNTIME_OBSERVABILITY_SHADOW",
        materialization_role="LATEST_RUNTIME_STATE_MATERIALIZATION",
    )

    assert summary["authority_role"] == "POST_RUNTIME_OBSERVABILITY_SHADOW"
    assert summary["materialization_role"] == "LATEST_RUNTIME_STATE_MATERIALIZATION"
    assert summary["decision_timing"] == "EOD_POST_RUNTIME_OBSERVABILITY_SHADOW"
    assert summary["formal_planning_snapshot"] is False
    assert summary["post_runtime_shadow"] is True
    assert (run_dir / "daily" / "2022-09-15" / "strategy_eod_shadow" / "strategy_shadow_summary.json").is_file()
    assert not (run_dir / "daily" / "2022-09-15" / "strategy" / "strategy_shadow_summary.json").exists()


def test_phase23_e_strategy_shadow_adapts_runtime_current_rows_for_pm_input() -> None:
    current = {
        "business_date": "2026-07-15",
        "rows": [
            {
                "position_id": "runtime-pos-7203",
                "symbol": "7203",
                "quantity": 100,
                "average_price": 1000,
                "acquired_at": "2026-07-10T00:00:00+00:00",
                "position_state_as_of": "2026-07-15",
                "valuation_as_of": "2026-07-15",
                "position_lifecycle_id": "lifecycle-7203",
            }
        ],
    }

    rows = _runtime_current_position_rows(current)

    assert rows == [
        {
            "position_id": "runtime-pos-7203",
            "symbol": "7203",
            "quantity": 100.0,
            "average_price": 1000.0,
            "acquired_at": "2026-07-10T00:00:00+00:00",
            "as_of": "2026-07-15",
            "position_state_as_of": "2026-07-15",
            "valuation_as_of": "2026-07-15",
            "position_lifecycle_id": "lifecycle-7203",
            "technical_features_join_key": {"code": "7203", "target_date": "2026-07-15"},
            "source": "runtime_current_position_adapter_input",
        }
    ]


def test_phase28_d19_existing_pm_decisions_lookup_preserves_same_day_source_hash(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    pm_path = runtime_root / "runtime_state" / "position_management" / "2026-07-15" / "position_management_decisions.json"
    _write_json(
        pm_path,
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": "2026-07-15",
            "decisions": [
                {
                    "symbol": "94320",
                    "decision_type": "ADD",
                    "pm_decision_id": "pm-2026-07-15-94320-add",
                }
            ],
        },
    )

    rows = _existing_pm_decisions(runtime_root=runtime_root, business_date="2026-07-15")

    assert len(rows) == 1
    assert rows[0]["decision_type"] == "ADD"
    assert rows[0]["pm_decision_id"] == "pm-2026-07-15-94320-add"
    assert rows[0]["_source_artifact_path"] == str(pm_path)
    assert rows[0]["_source_artifact_hash"] == _sha256_file(pm_path)
    assert rows[0]["_source_business_date"] == "2026-07-15"


def test_phase23_f_strategy_shadow_adapts_candidate_rows_for_downstream_membership(tmp_path: Path) -> None:
    path = tmp_path / "candidate_decisions.json"
    path.write_text(
        json.dumps(
            {
                "artifact_schema_version": "runtime_v2_candidate_feature_input_v1",
                "business_date": "2026-07-10",
                "feature_date": "2026-07-10",
                "generation_bound_inference": {
                    "accepted_generation_id": "gen-20260710",
                    "manifest_hash": "manifest-hash",
                    "feature_order_hash": "feature-hash",
                },
                "rows": [
                    {
                        "business_date": "2026-07-10",
                        "feature_date": "2026-07-10",
                        "target_date": "2026-07-10",
                        "code": "89180",
                        "symbol": "89180",
                        "candidate_rank": 1,
                        "candidate_score": 0.99,
                        "candidate_reason": "high_candidate_score|liquidity_available",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _ai_output_summary(path, business_date="2026-07-10")
    rows = summary["rows"]

    assert summary["summary"]["row_count"] == 1
    assert summary["summary"]["candidate_adapter_contract_version"] == "runtime_buy_ai_candidate_downstream_adapter.v1"
    assert rows[0]["security_code"] == "89180"
    assert rows[0]["candidate_membership_status"] == "ELIGIBLE"
    assert rows[0]["accepted_generation_id"] == "gen-20260710"
    assert rows[0]["technical_features_join_key"] == {"code": "89180", "target_date": "2026-07-10"}
    assert rows[0]["latest_fallback_used"] is False


def test_phase23_bf_opportunity_path_resolves_as_optional_input(tmp_path: Path) -> None:
    path = tmp_path / "runtime_state" / "buy_ai" / "2026-07-06" / "opportunity_rankings.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_opportunity_rankings_v1",
                "business_date": "2026-07-06",
                "feature_date": "2026-07-06",
                "rankings": [{"symbol": "7203", "opportunity_buy_rank": 1, "expected_edge_score": 0.7}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _ai_output_summary(path, business_date="2026-07-06")

    assert _optional_opportunity_artifact_path(summary, business_date="2026-07-06") == path
    assert summary["summary"]["opportunity_capacity_count"] == 1
    assert summary["summary"]["buy_eligible_opportunity_count"] == 1
    assert summary["summary"]["buy_eligibility_policy_version"] == "runtime_v2_opportunity_buy_eligibility_v1"


def test_phase24_d_opportunity_summary_counts_buy_eligible_only_from_canonical_resolver(tmp_path: Path) -> None:
    path = tmp_path / "runtime_state" / "buy_ai" / "2026-07-06" / "opportunity_rankings.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_opportunity_rankings_v1",
                "business_date": "2026-07-06",
                "feature_date": "2026-07-06",
                "rankings": [
                    {"symbol": "7203", "opportunity_buy_rank": 1, "expected_edge_score": 0.7, "no_buy_reason": ""},
                    {
                        "symbol": "6758",
                        "opportunity_buy_rank": 2,
                        "expected_edge_score": -0.1,
                        "no_buy_reason": "non_positive_expected_edge_score",
                    },
                    {
                        "symbol": "9432",
                        "opportunity_buy_rank": 3,
                        "expected_edge_score": 0.2,
                        "no_buy_reason": "high_downside_risk_score",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _ai_output_summary(path, business_date="2026-07-06")

    assert summary["summary"]["opportunity_capacity_count"] == 3
    assert summary["summary"]["buy_eligible_opportunity_count"] == 2


def test_phase23_bf_opportunity_path_absent_returns_none_without_keyerror(tmp_path: Path) -> None:
    path = tmp_path / "runtime_state" / "buy_ai" / "2026-07-06" / "opportunity_rankings.json"

    summary = _ai_output_summary(path, business_date="2026-07-06")

    assert _optional_opportunity_artifact_path(summary, business_date="2026-07-06") is None


def test_phase23_bf_opportunity_path_wrong_business_date_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "runtime_state" / "buy_ai" / "2026-07-06" / "opportunity_rankings.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_opportunity_rankings_v1",
                "business_date": "2026-07-05",
                "feature_date": "2026-07-05",
                "rankings": [{"symbol": "7203", "rank": 1, "expected_edge_score": 0.7}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _ai_output_summary(path, business_date="2026-07-06")

    assert _optional_opportunity_artifact_path(summary, business_date="2026-07-06") is None


def test_phase23_bm_strategy_sources_use_run_scoped_historical_asof_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    market_refresh_dir = run_dir / "daily" / "2022-07-01" / "market_refresh"
    (market_refresh_dir / "historical_asof_view.json").parent.mkdir(parents=True)
    _write_json(market_refresh_dir / "historical_asof_view.json", {"business_date": "2022-07-01", "status": "PASS"})
    source_root = market_refresh_dir / "inputs" / "historical_asof" / "2022-07-01"
    normalized = source_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw = source_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed = source_root / "raw" / "jquants" / "listed_issues" / "data.parquet"
    calendar = source_root / "raw" / "jquants" / "trading_calendar" / "data.parquet"
    for path in (normalized, raw, listed, calendar):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{path.name}:{path.parent.name}".encode("utf-8"))
    _write_json(
        source_root / "logical_input_manifest.json",
        {
            "schema_version": "historical_asof_logical_input_manifest.v1",
            "business_date": "2022-07-01",
            "status": "PASS",
            "logical_paths": {
                "normalized_ohlcv": str(normalized),
                "raw_ohlcv": str(raw),
                "listed_issues": str(listed),
                "trading_calendar": str(calendar),
            },
            "source_identities": {
                "normalized_ohlcv": {"physical_file_hash": _sha256_file(normalized)},
                "listed_issues": {"physical_file_hash": _sha256_file(listed)},
                "trading_calendar": {"physical_file_hash": _sha256_file(calendar)},
            },
        },
    )

    authority = _resolve_strategy_source_authority(
        run_dir=run_dir,
        runtime_root=tmp_path / ".runtime",
        business_date="2022-07-01",
        operations_root=tmp_path / ".runtime" / "operations",
    )

    assert authority["status"] == "PASS"
    assert authority["resolution_source"] == "run_scoped_historical_logical_input_manifest"
    assert authority["run_scoped_historical_authority_used"] is True
    assert authority["operations_latest_fallback_used"] is False
    assert authority["paths"]["normalized_ohlcv"] == str(normalized)
    assert authority["paths"]["listed_issues"] == str(listed)
    assert authority["paths"]["trading_calendar"] == str(calendar)
    assert authority["paths"]["financial_statements"] == "."
    assert authority["expected_hashes"]["jquants_daily_quotes"] == _sha256_file(normalized)
    assert authority["expected_hashes"]["jquants_listed_issues"] == _sha256_file(listed)
    assert authority["expected_hashes"]["jquants_trading_calendar"] == _sha256_file(calendar)


def test_phase23_bm_historical_missing_manifest_does_not_fallback_to_operations(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    market_refresh_dir = run_dir / "daily" / "2022-07-01" / "market_refresh"
    _write_json(market_refresh_dir / "historical_asof_view.json", {"business_date": "2022-07-01", "status": "PASS"})

    authority = _resolve_strategy_source_authority(
        run_dir=run_dir,
        runtime_root=tmp_path / ".runtime",
        business_date="2022-07-01",
        operations_root=tmp_path / ".runtime" / "operations",
    )

    assert authority["status"] == "BLOCK"
    assert authority["reason"] == "historical_logical_input_manifest_missing"
    assert authority["run_scoped_historical_authority_used"] is False
    assert authority["operations_latest_fallback_used"] is False
    assert "__missing_historical_strategy_source_authority__" in authority["paths"]["normalized_ohlcv"]
    assert ".runtime/operations" not in authority["paths"]["normalized_ohlcv"]


def test_phase23_bm_production_demo_without_asof_preserves_operations_sources(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"

    authority = _resolve_strategy_source_authority(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        business_date="2026-07-06",
        operations_root=operations_root,
    )

    assert authority["status"] == "PASS"
    assert authority["authority"] == "operations_canonical_source_authority"
    assert authority["resolution_source"] == "operations_default"
    assert authority["run_scoped_historical_authority_used"] is False
    assert authority["operations_latest_fallback_used"] is False
    assert authority["paths"]["normalized_ohlcv"] == str(
        operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _execution(execution_id: str, business_date: str, symbol: str, side: str, quantity: float, price: float) -> dict:
    return {
        "record_id": f"ledger-{execution_id}",
        "execution_id": execution_id,
        "execution_key": execution_id,
        "dedup_key": execution_id,
        "business_date": business_date,
        "executed_at": f"{business_date}T09:00:00+09:00",
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "filled_quantity": quantity,
        "price": price,
        "average_price": price,
        "market_value": quantity * price,
        "quantity_basis": "ADJUSTED",
        "valuation_price_basis": "ADJUSTED",
    }


def _write_position_campaigns(run_dir: Path, business_date: str, symbol: str, campaign_id: str) -> Path:
    path = run_dir / "daily" / business_date / "positions" / "position_campaigns.json"
    _write_json(
        path,
        {
            "schema_version": "position_campaign_observability.v1",
            "contract_version": "phase30_ac_pre_action_campaign_lifecycle.v1",
            "business_date": business_date,
            "authority": "CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE",
            "position_campaigns": [
                {
                    "position_campaign_id": campaign_id,
                    "symbol": symbol,
                    "campaign_status": "OPEN",
                    "opened_business_date": "2026-07-10",
                    "current_quantity": 100,
                    "events": [{"business_date": "2026-07-10", "side": "BUY", "stage": "BUY"}],
                }
            ],
            "temporal_safety": {
                "temporal_stage": "PRE_ACTION_DECISION_SNAPSHOT",
                "same_day_eod_campaign_reconstruction_used": False,
                "future_information_used": False,
            },
        },
    )
    return path


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
