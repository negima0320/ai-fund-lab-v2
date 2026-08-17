from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy import shadow_runtime


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _summary(*rows: dict) -> dict:
    return {
        "status": "PASS",
        "business_date": "2022-09-01",
        "feature_date": "2022-09-01",
        "source_ref": "fixture",
        "source_hash": "fixture-hash",
        "payload": {"rankings": list(rows)},
        "rows": tuple(rows),
    }


def _current(*rows: dict) -> dict:
    return {
        "status": "PASS",
        "business_date": "2022-09-01",
        "feature_date": "2022-09-01",
        "source_ref": "fixture-current",
        "source_hash": "fixture-current-hash",
        "summary": {"positions": list(rows)},
        "rows": tuple(rows),
    }


def test_phase29_l21k_normal_buy_new_without_prior_exit_is_unchanged(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [])

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary({"code": "11110", "runtime_opportunity_score": 0.2}),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)

    assert "prior_exit_business_date" not in row
    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert semantic["reentry_cooldown_status"] == "NOT_APPLICABLE"


def test_phase29_l21k_prior_same_symbol_exit_materializes_reentry_input(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-29", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-30", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 95, "source_decision_type": "EXIT"},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary({"code": "11110", "runtime_opportunity_score": 0.2, "opportunity_buy_rank": 2, "quality_action": "FULL_ALLOCATION_ELIGIBLE"}),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)

    assert row["prior_exit_business_date"] == "2022-08-30"
    assert row["prior_exit_reason"] == "EXIT"
    assert semantic["semantic_buy_type"] == "REENTRY"
    assert semantic["business_days_since_exit"] == 1
    assert semantic["reentry_cooldown_status"] == "FAIL_CLOSED"


def test_phase29_l21k_current_position_buy_add_is_not_marked_reentry(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-29", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-30", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 95},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary({"code": "11110", "runtime_opportunity_score": 0.2}),
        current=_current({"symbol": "11110", "quantity": 10, "market_value": 1000}),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row={**row, "current_position": True, "pm_action": "ADD"}, business_date="2022-09-01", is_buy_new=False)

    assert "prior_exit_business_date" not in row
    assert semantic["semantic_buy_type"] == "BUY_ADD"
    assert semantic["reentry_cooldown_status"] == "NOT_APPLICABLE"


def test_phase29_l21k_multiple_campaigns_resolve_latest_pit_prior_exit(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-10", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-12", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 90},
            {"business_date": "2022-08-22", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-30", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 95},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary({"code": "11110"}),
        current=_current(),
    )

    assert result["opportunity"]["rows"][0]["prior_exit_business_date"] == "2022-08-30"
    assert result["opportunity"]["rows"][0]["prior_exit_campaign_id"].endswith("0002")


def test_phase29_l21k_future_and_same_day_exits_are_not_consumed(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-09-01", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-09-01", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 95},
            {"business_date": "2022-09-02", "side": "BUY", "symbol": "22220", "quantity": 100, "price": 100},
            {"business_date": "2022-09-05", "side": "SELL", "symbol": "22220", "quantity": 100, "price": 95},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}, {"code": "22220"}),
        opportunity=_summary({"code": "11110"}, {"code": "22220"}),
        current=_current(),
    )

    assert all("prior_exit_business_date" not in row for row in result["opportunity"]["rows"])
    assert result["evidence"]["future_or_same_day_exit_used"] is False


def test_phase29_l21k_23880_reproduction_reaches_existing_l16_reentry_contract(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "23880", "quantity": 1200, "price": 148},
            {"business_date": "2022-08-29", "side": "SELL", "symbol": "23880", "quantity": 300, "price": 133},
            {"business_date": "2022-08-30", "side": "SELL", "symbol": "23880", "quantity": 900, "price": 132},
            {"business_date": "2022-09-01", "side": "BUY", "symbol": "23880", "quantity": 1300, "price": 136},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "23880"}),
        opportunity=_summary(
            {
                "code": "23880",
                "runtime_opportunity_score": 0.00797852,
                "opportunity_buy_rank": 5,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 0.9709452004,
                "price_momentum_return_20d": 0.2222222222,
                "corporate_action_status": "UNKNOWN",
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=None, liquidity_status="UNKNOWN")

    assert row["prior_exit_business_date"] == "2022-08-30"
    assert semantic["semantic_buy_type"] == "REENTRY"
    assert semantic["business_days_since_exit"] == 1
    assert recovery["reentry_score_gate_status"] == "DIAGNOSTIC_ONLY"
    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "insufficient_prior_exit_context"


def test_phase29_l21r3_23880_prior_exit_persists_through_temporary_exclude_then_reentry(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "23880", "quantity": 1200, "price": 148},
            {"business_date": "2022-08-30", "side": "SELL", "symbol": "23880", "quantity": 1200, "price": 132},
        ],
    )

    for business_date, is_buy_new, expected_cooldown in (
        ("2022-09-01", True, "FAIL_CLOSED"),
        ("2022-09-02", True, "FAIL_CLOSED"),
        ("2022-09-05", True, "PASS"),
        ("2022-09-06", False, "PASS"),
        ("2022-09-07", True, "PASS"),
    ):
        result = shadow_runtime._supply_prior_exit_state(
            runtime_root=root,
            business_date=business_date,
            candidate=_summary({"code": "23880", "universe_eligible": is_buy_new}),
            opportunity=_summary({"code": "23880", "runtime_opportunity_score": 0.2, "opportunity_buy_rank": 2}),
            current=_current(),
        )

        row = result["opportunity"]["rows"][0]
        semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date=business_date, is_buy_new=is_buy_new)

        assert row["prior_exit_business_date"] == "2022-08-30"
        assert semantic["prior_exit_business_date"] == "2022-08-30"
        assert semantic["semantic_buy_type"] == "REENTRY"
        assert semantic["reentry_cooldown_status"] == expected_cooldown


def test_phase29_l21p_reentry_recovery_passes_when_corporate_action_evidence_is_available(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 104, "source_decision_type": "EXIT_BY_TREND_AND_EDGE_BREAK"},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary(
            {
                "code": "11110",
                "runtime_opportunity_score": 0.2,
                "opportunity_buy_rank": 2,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 1.01,
                "price_momentum_return_20d": 0.05,
                "corporate_action_status": "NO_EVENT",
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert row["prior_exit_business_date"] == "2022-08-26"
    assert semantic["semantic_buy_type"] == "REENTRY"
    assert semantic["business_days_since_exit"] == 3
    assert semantic["reentry_cooldown_status"] == "PASS"
    assert recovery["reentry_recovery_status"] == "PASS"
    assert recovery["reentry_recovery_reason"] == "reentry_recovery_qualified"
    assert recovery["reentry_corporate_action_status"] == "NO_EVENT"


def test_phase29_l21p_reentry_recovery_requires_corporate_action_evidence(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 104, "source_decision_type": "EXIT_BY_TREND_AND_EDGE_BREAK"},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary(
            {
                "code": "11110",
                "runtime_opportunity_score": 0.2,
                "opportunity_buy_rank": 2,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 1.01,
                "price_momentum_return_20d": 0.05,
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert semantic["semantic_buy_type"] == "REENTRY"
    assert semantic["reentry_cooldown_status"] == "PASS"
    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "reentry_corporate_action_source_missing"
    assert recovery["reentry_corporate_action_status"] == "UNKNOWN"


def test_phase29_l21p_runtime_opportunity_score_is_canonical_reentry_score(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 104, "source_decision_type": "EXIT_BY_TREND_AND_EDGE_BREAK"},
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "22220", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "22220", "quantity": 100, "price": 104, "source_decision_type": "EXIT_BY_TREND_AND_EDGE_BREAK"},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}, {"code": "22220"}),
        opportunity=_summary(
            {
                "code": "11110",
                "runtime_opportunity_score": 0.2,
                "expected_edge_score": -0.5,
                "opportunity_buy_rank": 2,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 1.01,
                "price_momentum_return_20d": 0.02,
                "corporate_action_status": "NO_EVENT",
            },
            {
                "code": "22220",
                "runtime_opportunity_score": 0.01,
                "expected_edge_score": 0.5,
                "opportunity_buy_rank": 2,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 1.01,
                "price_momentum_return_20d": 0.02,
                "corporate_action_status": "NO_EVENT",
            },
        ),
        current=_current(),
    )

    rows = {row["code"]: row for row in result["opportunity"]["rows"]}
    passing_semantic = portfolio_construction._semantic_reentry_evidence(row=rows["11110"], business_date="2022-09-01", is_buy_new=True)
    failing_semantic = portfolio_construction._semantic_reentry_evidence(row=rows["22220"], business_date="2022-09-01", is_buy_new=True)
    passing_recovery = portfolio_construction._reentry_recovery_evidence(
        row=rows["11110"],
        semantic=passing_semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )
    failing_recovery = portfolio_construction._reentry_recovery_evidence(
        row=rows["22220"],
        semantic=failing_semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )

    assert passing_recovery["reentry_expected_edge"] == 0.2
    assert passing_recovery["reentry_recovery_status"] == "PASS"
    assert failing_recovery["reentry_expected_edge"] == 0.01
    assert failing_recovery["reentry_score_gate_status"] == "DIAGNOSTIC_ONLY"
    assert failing_recovery["reentry_recovery_status"] == "PASS"
    assert failing_recovery["reentry_recovery_reason"] == "reentry_recovery_qualified"


def test_phase29_l21r_low_score_reentry_can_pass_when_relative_and_recovery_evidence_pass(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 104, "source_decision_type": "EXIT_BY_TREND_AND_EDGE_BREAK"},
        ],
    )

    result = shadow_runtime._supply_prior_exit_state(
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary(
            {
                "code": "11110",
                "runtime_opportunity_score": 0.05,
                "opportunity_buy_rank": 2,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "trend_close_over_ma_20d": 1.01,
                "price_momentum_return_20d": 0.02,
                "corporate_action_status": "NO_EVENT",
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert semantic["reentry_cooldown_status"] == "PASS"
    assert recovery["reentry_expected_edge"] == 0.05
    assert recovery["reentry_score_gate_status"] == "DIAGNOSTIC_ONLY"
    assert recovery["reentry_recovery_status"] == "PASS"


def test_phase29_l21r_weak_relative_rank_blocks_reentry_even_with_high_score(tmp_path: Path) -> None:
    row = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "runtime_opportunity_score": 0.5,
        "opportunity_buy_rank": 11,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.01,
        "price_momentum_return_20d": 0.02,
        "corporate_action_status": "NO_EVENT",
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert recovery["reentry_recovery_reason"] == "reentry_opportunity_not_requalified"


def test_phase29_l21r_corporate_action_and_capacity_fail_closed_semantics() -> None:
    base = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "CORPORATE_ACTION_EXIT",
        "runtime_opportunity_score": 0.05,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.01,
        "price_momentum_return_20d": 0.02,
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=base, business_date="2022-09-01", is_buy_new=True)
    blocking = portfolio_construction._reentry_recovery_evidence(
        row={**base, "corporate_action_status": "EVENT_PRESENT"},
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )
    missing_source = portfolio_construction._reentry_recovery_evidence(
        row={**base, "corporate_action_source_status": "SOURCE_MISSING"},
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )
    missing_capacity = portfolio_construction._reentry_recovery_evidence(
        row={**base, "corporate_action_status": "NO_EVENT"},
        semantic=semantic,
        capacity_ratio=None,
        liquidity_status="UNKNOWN",
    )

    assert blocking["reentry_recovery_status"] == "FAIL_CLOSED"
    assert blocking["reentry_recovery_reason"] == "reentry_corporate_action_blocking"
    assert missing_source["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert missing_source["reentry_recovery_reason"] == "reentry_corporate_action_source_missing"
    assert missing_capacity["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert missing_capacity["reentry_recovery_reason"] == "reentry_capacity_unavailable"


def test_phase29_l21r_previous_exit_reason_controls_technical_recovery_requirement() -> None:
    trend_exit = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "runtime_opportunity_score": 0.05,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 0.95,
        "price_momentum_return_20d": -0.02,
        "corporate_action_status": "NO_EVENT",
    }
    portfolio_exit = {
        **trend_exit,
        "prior_exit_reason": "PORTFOLIO_COMPETITION_REALLOCATION",
        "trend_close_over_ma_20d": 0.95,
        "price_momentum_return_20d": -0.02,
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=trend_exit, business_date="2022-09-01", is_buy_new=True)
    trend_recovery = portfolio_construction._reentry_recovery_evidence(row=trend_exit, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")
    portfolio_recovery = portfolio_construction._reentry_recovery_evidence(row=portfolio_exit, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert trend_recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert trend_recovery["reentry_recovery_reason"] == "reentry_trend_recovery_not_satisfied"
    assert portfolio_recovery["previous_exit_reason_class"] == "PORTFOLIO_COMPETITION"
    assert portfolio_recovery["reentry_recovery_status"] == "PASS"


def test_phase29_l21r_source_wiring_supplies_corporate_no_event_and_technical_fields(tmp_path: Path) -> None:
    corporate_path = tmp_path / "corporate_event.json"
    corporate_payload = {
        "business_date": "2022-09-01",
        "known_no_event_symbols": ["11110"],
        "known_event_symbols": [],
    }
    corporate_path.write_text(json.dumps(corporate_payload), encoding="utf-8")
    opportunity = _summary({"code": "11110", "runtime_opportunity_score": 0.05})
    technical = {
        "status": "PASS",
        "business_date": "2022-09-01",
        "feature_date": "2022-09-01",
        "source_ref": "technical_features.json",
        "source_hash": "tech-hash",
        "rows": (
            {
                "code": "11110",
                "business_date": "2022-09-01",
                "trend_close_over_ma_20d": 1.02,
                "price_momentum_return_20d": 0.03,
                "rolling_median_traded_value_20": 1_000_000_000,
                "rolling_median_traded_value_20_authority": {"authority_type": "LIQUIDITY_CAPACITY_AUTHORITY"},
                "rolling_median_traded_value_20_resolution": {"status": "PASS"},
            },
        ),
    }

    result = shadow_runtime._supply_reentry_source_evidence(
        business_date="2022-09-01",
        opportunity=opportunity,
        technical_features=technical,
        corporate_event_path=corporate_path,
    )

    row = result["opportunity"]["rows"][0]
    assert row["corporate_action_status"] == "NO_EVENT"
    assert row["corporate_action_source"] == "corporate_event.known_no_event_symbols"
    assert row["trend_close_over_ma_20d"] == 1.02
    assert row["price_momentum_return_20d"] == 0.03
    assert row["rolling_median_traded_value_20"] == 1_000_000_000
    assert row["rolling_median_traded_value_20_authority"]["authority_type"] == "LIQUIDITY_CAPACITY_AUTHORITY"
    assert row["rolling_median_traded_value_20_resolution"]["status"] == "PASS"
