from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.shadow_runtime import (
    _ai_output_summary,
    _optional_opportunity_artifact_path,
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

    assert summary["artifact_count"] == 9
    assert summary["runtime_mutation_performed"] is False
    assert summary["broker_connection_performed"] is False
    assert summary["broker_write_performed"] is False
    assert summary["active_runtime_consumer_eligibility"] == "NO"
    assert summary["authority_role"] == "FORMAL_PLANNING_AUTHORITY_INPUT"
    assert summary["materialization_role"] == "IMMUTABLE_MORNING_PLANNING_SNAPSHOT"
    assert summary["decision_timing"] == "MORNING_FORMAL_PLANNING_AUTHORITY"
    assert summary["formal_planning_snapshot"] is True
    assert summary["post_runtime_shadow"] is False
    strategy_dir = run_dir / "daily" / "2022-09-15" / "strategy"
    assert (strategy_dir / "input_manifest.json").is_file()
    assert (strategy_dir / "strategy_decision_trace.json").is_file()
    assert (strategy_dir / "portfolio_policy.json").is_file()
    assert not (strategy_dir / "dynamic_position_count.json").exists()
    assert not (strategy_dir / "dynamic_cash_exposure.json").exists()
    assert not (strategy_dir / "capital_deployment.json").exists()

    validation = validate_run_strategy_shadow(run_dir=run_dir, business_date="2022-09-15")
    assert validation["structural_validity"] == "PASS"
    assert validation["policy_acceptance"] == "NOT_REQUESTED"


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
    assert summary["summary"]["buy_eligible_opportunity_count"] == 1


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


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
