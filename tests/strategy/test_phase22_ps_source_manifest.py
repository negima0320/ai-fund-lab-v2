from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.strategy.source_manifest import build_strategy_source_manifest, classify_component_blockers, manifest_hash


BUSINESS_DATE = "2026-07-10"


def test_phase22_ps_manifest_resolves_pit_sources_and_is_deterministic(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime")
    strategy_dir = tmp_path / "run" / "daily" / BUSINESS_DATE / "strategy"
    _write_json(strategy_dir / "input_manifest.json", {"latest_fallback_used": False})
    _write_json(strategy_dir / "market_context.json", {"producer_result_status": "PASS", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "metrics": {"feature_date": BUSINESS_DATE}, "reason_codes": []})
    _write_json(strategy_dir / "corporate_event.json", {"producer_result_status": "REVIEW_REQUIRED", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "coverage_status": "PARTIAL", "event_count": 0, "reason_codes": ["corporate_event_source_coverage_incomplete"]})
    _write_json(strategy_dir / "position_sizing.json", {"producer_result_status": "BLOCK", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "reason_codes": ["configured_max_position_weight_above_safety_cap"]})

    first = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        run_id="run-1",
        profile_id="historical-smoke",
        business_date=BUSINESS_DATE,
        strategy_dir=strategy_dir,
        input_manifest={"latest_fallback_used": False},
    )
    second = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        run_id="run-1",
        profile_id="historical-smoke",
        business_date=BUSINESS_DATE,
        strategy_dir=strategy_dir,
        input_manifest={"latest_fallback_used": False},
    )

    assert manifest_hash(first) == manifest_hash(second)
    assert first["market_quotes"]["selected_as_of"] == BUSINESS_DATE
    assert first["market_quotes"]["future_row_rejection_count"] > 0
    assert first["market_quotes"]["status"] == "PASS"
    assert first["sector"]["pit_status"] == "PASS"
    assert first["sector"]["sector_pit_available"] is True
    assert first["sector"]["sector_fallback_used"] is False
    assert first["corporate_event"]["event_semantics"] == "SOURCE_PARTIAL"
    assert first["pit_validation"]["latest_fallback_used"] is False
    assert first["pit_validation"]["current_state_leakage_detected"] is False
    assert first["pit_validation"]["status"] == "PASS"
    assert first["direct_blockers"]["position_sizing"]["primary_blocker_class"] == "CONFIG_SAFETY_CONTRACT_VIOLATION"
    assert "DIRECT_SOURCE_PIT_VIOLATION" not in first["direct_blockers"]["position_sizing"]["blocker_classes"]


def test_phase22_ps_missing_same_day_candidate_does_not_use_latest_fallback(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime")
    missing_day = "2026-07-11"
    _write_json(runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "candidate_decisions.json", {"business_date": BUSINESS_DATE, "decisions": []})
    manifest = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        run_id="run-1",
        profile_id="historical-smoke",
        business_date=missing_day,
        strategy_dir=tmp_path / "run" / "daily" / missing_day / "strategy",
        input_manifest={},
    )

    assert manifest["candidate"]["status"] == "SOURCE_UNAVAILABLE"
    assert manifest["candidate"]["latest_fallback_used"] is False
    assert manifest["pit_validation"]["latest_fallback_used"] is False
    assert manifest["pit_validation"]["source_unavailable"] is True


def test_phase22_ps_candidate_and_opportunity_business_date_mismatch_blocks(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime")
    _write_json(runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "candidate_decisions.json", {"business_date": "2026-07-09", "decisions": []})
    _write_json(runtime_root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json", {"business_date": "2026-07-09", "rankings": []})
    manifest = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        run_id="run-1",
        profile_id="historical-smoke",
        business_date=BUSINESS_DATE,
        strategy_dir=tmp_path / "run" / "daily" / BUSINESS_DATE / "strategy",
        input_manifest={},
    )

    assert manifest["candidate"]["business_date_valid"] is False
    assert manifest["opportunity"]["business_date_valid"] is False
    assert manifest["pit_validation"]["status"] == "BLOCK"
    assert "candidate_business_date_mismatch" in manifest["pit_validation"]["reason_codes"]
    assert "opportunity_business_date_mismatch" in manifest["pit_validation"]["reason_codes"]


def test_phase22_ps_only_future_quotes_block_and_bootstrap_required(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", quotes_start="2026-07-13", quote_days=3)
    manifest = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=runtime_root,
        run_id="run-1",
        profile_id="historical-smoke",
        business_date=BUSINESS_DATE,
        strategy_dir=tmp_path / "run" / "daily" / BUSINESS_DATE / "strategy",
        input_manifest={},
    )

    assert manifest["market_quotes"]["status"] == "BLOCK"
    assert "market_quotes_no_pit_rows" in manifest["market_quotes"]["reason_codes"]
    assert manifest["bootstrap"]["status"] == "BOOTSTRAP_REQUIRED"
    assert manifest["pit_validation"]["status"] == "BLOCK"


def test_phase22_ps_classifies_direct_and_propagated_blockers() -> None:
    result = classify_component_blockers(
        artifacts={
            "market_context": {"producer_result_status": "BLOCK", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "reason_codes": ["future_source_row_rejected"]},
            "portfolio_policy": {"producer_result_status": "BLOCK", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "reason_codes": ["market_context_block:BLOCK"]},
            "runtime_planning": {"producer_result_status": "BLOCK", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "reason_codes": ["SOURCE_BLOCKED"]},
        },
        business_date=BUSINESS_DATE,
    )

    assert "market_context" in result["direct_blockers"]
    assert "portfolio_policy" in result["propagated_blockers"]
    assert "runtime_planning" in result["propagated_blockers"]
    assert result["root_blocker_components"] == ["market_context"]


def test_phase22_pw_blocker_classes_separate_review_config_coverage_and_temporal() -> None:
    result = classify_component_blockers(
        artifacts={
            "position_sizing": {
                "producer_result_status": "BLOCK",
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "reason_codes": [
                    "dynamic_cash_exposure_review_required:REVIEW_REQUIRED",
                    "configured_max_position_weight_above_safety_cap",
                ],
            },
            "corporate_event": {
                "producer_result_status": "BLOCK",
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "reason_codes": ["corporate_event_source_coverage_incomplete"],
            },
            "runtime_planning": {
                "producer_result_status": "BLOCK",
                "business_date": BUSINESS_DATE,
                "feature_date": "2026-07-11",
                "reason_codes": ["feature_date_authority_mismatch"],
            },
        },
        business_date=BUSINESS_DATE,
    )

    sizing = result["direct_blockers"]["position_sizing"]
    corporate = result["direct_blockers"]["corporate_event"]
    planning = result["direct_blockers"]["runtime_planning"]
    assert "DIRECT_SOURCE_PIT_VIOLATION" not in sizing["direct_blocker_classes"]
    assert sizing["primary_blocker_class"] == "CONFIG_SAFETY_CONTRACT_VIOLATION"
    assert sizing["primary_reason_code"] == "configured_max_position_weight_above_safety_cap"
    assert "DOWNSTREAM_COMPONENT_REVIEW_REQUIRED" in sizing["direct_blocker_classes"]
    assert corporate["primary_blocker_class"] == "SOURCE_COVERAGE_INCOMPLETE"
    assert planning["primary_blocker_class"] == "TEMPORAL_AUTHORITY_MISMATCH"
    assert "BUSINESS_DATE_MISMATCH" in planning["direct_blocker_classes"]


def _runtime_root(root: Path, *, quotes_start: str = "2026-06-10", quote_days: int = 40) -> Path:
    _write_quotes(root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet", start=quotes_start, days=quote_days)
    _write_listed(root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet")
    _write_json(root / "persistent_ledger" / "state.json", {"business_date": BUSINESS_DATE, "cash": 1000.0, "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"business_date": BUSINESS_DATE, "items": []})
    _write_json(root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "candidate_decisions.json", {"business_date": BUSINESS_DATE, "decisions": []})
    _write_json(root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json", {"business_date": BUSINESS_DATE, "rankings": []})
    return root


def _write_quotes(path: Path, *, start: str, days: int) -> None:
    dates = [(date.fromisoformat(start) + timedelta(days=offset)).isoformat() for offset in range(days)]
    dates = [day for day in dates if date.fromisoformat(day).weekday() < 5]
    if start < BUSINESS_DATE:
        dates.append("2026-07-13")
    rows = [{"target_date": day, "code": code, "Close": 100.0 + idx, "Volume": 1000} for idx, day in enumerate(sorted(set(dates))) for code in ("1001", "1002")]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"target_date": BUSINESS_DATE, "code": "1001", "S33Nm": "Tech"},
            {"target_date": "2026-07-13", "code": "1002", "S33Nm": "Retail"},
        ]
    ).to_parquet(path)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
