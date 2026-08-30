from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy import shadow_runtime


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


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


def test_phase32_h_prior_exit_context_uses_strict_prior_pm_exit_detail(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    run_dir = tmp_path / "run"
    campaign_id = "pc-phase32h-83060-0001"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "business_date": "2022-10-03",
                "side": "BUY",
                "symbol": "83060",
                "quantity": 100,
                "price": 641.5,
                "position_campaign_id": campaign_id,
                "campaign_id": campaign_id,
            },
            {
                "business_date": "2022-10-04",
                "side": "SELL",
                "symbol": "83060",
                "quantity": 100,
                "price": 648,
                "source_decision_type": "SELL_EXIT",
                "source_pm_decision_id": "pm-2022-10-04-83060-exit",
                "source_decision_id": "rp-2022-10-04-83060-sell-exit",
            },
        ],
    )
    _write_json(
        run_dir / "daily" / "2022-10-04" / "position_management" / "pm_decisions.json",
        {
            "decisions": [
                {
                    "business_date": "2022-10-04",
                    "symbol": "83060",
                    "pm_decision_id": "pm-2022-10-04-83060-exit",
                    "decision_type": "EXIT",
                    "decision_status": "SELL_FULL_POSITION",
                    "decision_reason": "trend_and_opportunity_broken",
                    "reason_codes": ["trend_and_opportunity_broken"],
                    "position_campaign_id": campaign_id,
                }
            ]
        },
    )

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=root,
        business_date="2022-10-05",
        candidate=_summary({"code": "83060"}),
        opportunity=_summary(
            {
                "code": "83060",
                "runtime_opportunity_score": 0.2,
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
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-10-05", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(
        row=row,
        semantic=semantic,
        capacity_ratio=0.01,
        liquidity_status="WATCH",
    )
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date="2022-10-05",
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="WATCH",
        target_membership=True,
        normal_target_weight=0.05,
        target_weight_reason="selected",
        zero_weight_reason="",
        review_reason="",
    )

    assert row["prior_exit_business_date"] == "2022-10-04"
    assert row["prior_campaign_id"] == campaign_id
    assert row["prior_exit_campaign_id"] == campaign_id
    assert row["prior_exit_decision_type"] == "EXIT"
    assert row["prior_exit_reason"] == "trend_and_opportunity_broken"
    assert row["prior_exit_reason_codes"] == ["trend_and_opportunity_broken"]
    assert row["source_pm_decision_id"] == "pm-2022-10-04-83060-exit"
    assert row["source_decision_id"] == "rp-2022-10-04-83060-sell-exit"
    assert row["prior_exit_provenance_status"] == "PASS"
    assert semantic["prior_exit_reason"] == "trend_and_opportunity_broken"
    assert semantic["prior_exit_context"]["prior_campaign_id"] == campaign_id
    assert semantic["prior_exit_context"]["source_decision_id"] == "rp-2022-10-04-83060-sell-exit"
    assert recovery["previous_exit_reason"] == "trend_and_opportunity_broken"
    assert recovery["previous_exit_reason_class"] == "TREND_MOMENTUM"
    assert recovery["reentry_recovery_reason"] != "insufficient_prior_exit_context"
    assert eligibility["prior_exit_context_status"] == "PASS"
    assert eligibility["prior_exit_reason_class"] == "TREND_MOMENTUM"
    assert eligibility["prior_exit_context"]["source_pm_decision_id"] == "pm-2022-10-04-83060-exit"
    assert eligibility["prior_exit_context"]["source_decision_id"] == "rp-2022-10-04-83060-sell-exit"


def test_phase32_j_prior_exit_context_can_join_by_pm_decision_id_when_sell_campaign_missing(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    run_dir = tmp_path / "run"
    campaign_id = "pc-phase32j-83060-0001"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "business_date": "2022-10-03",
                "side": "BUY",
                "symbol": "83060",
                "quantity": 100,
                "price": 641.5,
                "position_campaign_id": campaign_id,
                "campaign_id": campaign_id,
            },
            {
                "business_date": "2022-10-04",
                "side": "SELL",
                "symbol": "83060",
                "quantity": 100,
                "price": 661.2,
                "position_campaign_id": "",
                "campaign_id": "",
                "source_pm_decision_id": "pm-2022-10-04-83060-exit",
                "source_decision_id": "rp-2022-10-04-83060-sell_exit-a53ae6445098bc4c",
                "source_decision_type": "SELL_EXIT",
            },
        ],
    )
    _write_json(
        run_dir / "daily" / "2022-10-04" / "position_management" / "pm_decisions.json",
        {
            "decisions": [
                {
                    "business_date": "2022-10-04",
                    "symbol": "83060",
                    "pm_decision_id": "pm-2022-10-04-83060-exit",
                    "decision_type": "EXIT",
                    "decision_status": "SELL_FULL_POSITION",
                    "decision_reason": "trend_and_opportunity_broken",
                    "reason_codes": ["trend_and_opportunity_broken"],
                    "position_campaign_id": campaign_id,
                }
            ]
        },
    )

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=root,
        business_date="2022-10-05",
        candidate=_summary({"code": "83060"}),
        opportunity=_summary({"code": "83060"}),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    assert row["prior_campaign_id"] == campaign_id
    assert row["prior_exit_campaign_id"] == campaign_id
    assert row["source_pm_decision_id"] == "pm-2022-10-04-83060-exit"
    assert row["source_decision_id"] == "rp-2022-10-04-83060-sell_exit-a53ae6445098bc4c"
    assert row["prior_exit_provenance_status"] == "PASS"
    assert row["prior_exit_context"]["authority"] == "STRICT_PRIOR_PM_EXIT_DECISION_CONTEXT"
    assert row["prior_exit_context"]["source_decision_id"] == "rp-2022-10-04-83060-sell_exit-a53ae6445098bc4c"


def test_phase32_p_date_only_reentry_rows_are_enriched_with_canonical_prior_context(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    run_dir = tmp_path / "run"
    campaign_33700 = "pc-878ea6968d1e7574-33700-0001"
    campaign_76470 = "pc-ec3672c4e51adeca-76470-0001"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "business_date": "2022-10-03",
                "side": "BUY",
                "symbol": "33700",
                "quantity": 100,
                "price": 1798.0,
                "position_campaign_id": campaign_33700,
                "campaign_id": campaign_33700,
            },
            {
                "business_date": "2022-10-05",
                "side": "SELL",
                "symbol": "33700",
                "quantity": 100,
                "price": 1767.0,
                "position_campaign_id": campaign_33700,
                "campaign_id": campaign_33700,
                "source_pm_decision_id": "pm-2022-10-05-33700-reduce",
                "source_decision_id": "rp-2022-10-05-33700-sell_exit-95bbd0210e1cda41",
                "source_decision_type": "SELL_EXIT",
            },
            {
                "business_date": "2022-10-11",
                "side": "BUY",
                "symbol": "76470",
                "quantity": 100,
                "price": 2112.0,
                "position_campaign_id": campaign_76470,
                "campaign_id": campaign_76470,
            },
            {
                "business_date": "2022-10-14",
                "side": "SELL",
                "symbol": "76470",
                "quantity": 100,
                "price": 2054.0,
                "position_campaign_id": campaign_76470,
                "campaign_id": campaign_76470,
                "source_pm_decision_id": "pm-2022-10-14-76470-exit",
                "source_decision_id": "rp-2022-10-14-76470-sell_exit-084afc15fda747d9",
                "source_decision_type": "SELL_EXIT",
            },
        ],
    )
    _write_json(
        run_dir / "daily" / "2022-10-05" / "position_management" / "pm_decisions.json",
        {
            "decisions": [
                {
                    "business_date": "2022-10-05",
                    "symbol": "33700",
                    "pm_decision_id": "pm-2022-10-05-33700-reduce",
                    "decision_type": "REDUCE",
                    "decision_status": "SELL_FULL_POSITION",
                    "decision_reason": "risk_increased_but_trend_not_broken",
                    "reason_codes": ["risk_increased_but_trend_not_broken"],
                    "position_campaign_id": campaign_33700,
                }
            ]
        },
    )
    _write_json(
        run_dir / "daily" / "2022-10-14" / "position_management" / "pm_decisions.json",
        {
            "decisions": [
                {
                    "business_date": "2022-10-14",
                    "symbol": "76470",
                    "pm_decision_id": "pm-2022-10-14-76470-exit",
                    "decision_type": "EXIT",
                    "decision_status": "SELL_FULL_POSITION",
                    "decision_reason": "weak_hold_score",
                    "reason_codes": ["weak_hold_score"],
                    "position_campaign_id": campaign_76470,
                }
            ]
        },
    )

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=root,
        business_date="2022-10-17",
        candidate=_summary({"code": "33700"}, {"code": "76470"}),
        opportunity=_summary(
            {
                "code": "33700",
                "prior_exit_business_date": "2022-10-05",
                "prior_exit_reason": "EXIT",
                "prior_exit_reason_codes": ["risk_increased_but_trend_not_broken"],
            },
            {
                "code": "76470",
                "prior_exit_business_date": "2022-10-14",
                "prior_exit_reason": "EXIT",
                "prior_exit_reason_codes": ["weak_hold_score"],
            },
        ),
        current=_current(),
    )

    rows = {row["code"]: row for row in result["opportunity"]["rows"]}
    assert rows["33700"]["prior_campaign_id"] == campaign_33700
    assert rows["33700"]["source_pm_decision_id"] == "pm-2022-10-05-33700-reduce"
    assert rows["33700"]["source_decision_id"] == "rp-2022-10-05-33700-sell_exit-95bbd0210e1cda41"
    assert rows["33700"]["prior_exit_provenance_status"] == "PASS"
    assert rows["33700"]["prior_exit_context"]["authority"] == "STRICT_PRIOR_PM_EXIT_DECISION_CONTEXT"
    assert rows["76470"]["prior_campaign_id"] == campaign_76470
    assert rows["76470"]["source_pm_decision_id"] == "pm-2022-10-14-76470-exit"
    assert rows["76470"]["source_decision_id"] == "rp-2022-10-14-76470-sell_exit-084afc15fda747d9"
    assert rows["76470"]["prior_exit_provenance_status"] == "PASS"
    assert result["evidence"]["opportunity_supplied_count"] == 2


def test_phase32_p_actual_strategy_entrypoint_materializes_rejected_reentry_prior_context(tmp_path: Path) -> None:
    source_run = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T032332732107Z")
    runtime_root = Path(".runtime")
    if not source_run.is_dir() or not runtime_root.is_dir():
        pytest.skip("Phase32-O target run evidence or runtime root is not available")
    if not (runtime_root / "runtime_state" / "buy_ai" / "2022-10-06" / "opportunity_rankings.json").is_file():
        pytest.skip("Phase32-O 2022-10-06 buy_ai opportunity evidence is not available")
    if not (runtime_root / "persistent_ledger" / "executions.jsonl").is_file():
        pytest.skip("Phase32-O persistent ledger execution evidence is not available")

    run_dir = tmp_path / source_run.name
    shutil.copytree(source_run, run_dir, ignore=shutil.ignore_patterns("*.parquet"))
    summary = shadow_runtime.generate_strategy_shadow_for_day(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id=source_run.name,
        profile_id="historical-extended-smoke",
        business_date="2022-10-06",
        feature_date="2022-10-06",
        historical_evaluation_authority_path=str(source_run / "historical_evaluation_authority.json"),
        artifact_subdir="strategy_phase32p_actual_path",
        decision_timing="MORNING_FORMAL_PLANNING_AUTHORITY",
        authority_role="FORMAL_PLANNING_AUTHORITY_INPUT",
        materialization_role="PHASE32P_ACTUAL_PATH_TEST",
    )
    assert summary["runtime_mutation_performed"] is False

    pc_path = run_dir / "daily" / "2022-10-06" / "strategy_phase32p_actual_path" / "portfolio_construction.json"
    payload = json.loads(pc_path.read_text(encoding="utf-8"))
    row = next(member for member in payload["portfolio_members"] if member.get("security_code") == "33700")

    assert row["membership_intent"] == "EXCLUDE"
    assert row["prior_exit_business_date"] == "2022-10-05"
    assert row["prior_campaign_id"] == "pc-878ea6968d1e7574-33700-0001"
    assert row["prior_exit_campaign_id"] == "pc-878ea6968d1e7574-33700-0001"
    assert row["source_pm_decision_id"] == "pm-2022-10-05-33700-reduce"
    assert row["source_decision_id"] == "rp-2022-10-05-33700-sell_exit-95bbd0210e1cda41"
    assert row["prior_exit_provenance_status"] == "PASS"
    assert row["prior_exit_context"]["provenance_status"] == "PASS"
    assert row["reentry_semantic_status"] == "FAIL_CLOSED"


def test_phase32_l_83060_actual_path_reentry_provenance_reaches_final_result(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    run_dir = tmp_path / "run"
    prior_campaign = "pc-2109759b35be4a73-83060-0001"
    reentry_campaign = "pc-1533c2a55c4c8bf5-83060-0001"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "business_date": "2022-10-03",
                "side": "BUY",
                "symbol": "83060",
                "quantity": 100,
                "price": 641.5,
                "position_campaign_id": prior_campaign,
                "campaign_id": prior_campaign,
                "source_decision_id": "rp-2022-10-03-83060-buy_new-a1e4c3343d5177dc",
                "source_decision_type": "BUY_NEW",
            },
            {
                "business_date": "2022-10-04",
                "side": "SELL",
                "symbol": "83060",
                "quantity": 100,
                "price": 661.2,
                "position_campaign_id": prior_campaign,
                "campaign_id": prior_campaign,
                "source_pm_decision_id": "pm-2022-10-04-83060-exit",
                "source_decision_id": "rp-2022-10-04-83060-sell_exit-2310c155634662da",
                "source_decision_type": "SELL_EXIT",
            },
            {
                "business_date": "2022-10-26",
                "side": "BUY",
                "symbol": "83060",
                "quantity": 100,
                "price": 711.5,
                "position_campaign_id": reentry_campaign,
                "campaign_id": reentry_campaign,
                "source_decision_id": "rp-2022-10-26-83060-buy_new-e7156d336f465694",
                "source_decision_type": "BUY_NEW",
            },
        ],
    )
    _write_json(
        run_dir / "daily" / "2022-10-04" / "position_management" / "pm_decisions.json",
        {
            "decisions": [
                {
                    "business_date": "2022-10-04",
                    "symbol": "83060",
                    "pm_decision_id": "pm-2022-10-04-83060-exit",
                    "decision_type": "EXIT",
                    "decision_status": "SELL_FULL_POSITION",
                    "decision_reason": "trend_and_opportunity_broken",
                    "reason_codes": ["trend_and_opportunity_broken"],
                    "position_campaign_id": prior_campaign,
                }
            ]
        },
    )

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=root,
        business_date="2022-10-26",
        candidate=_summary({"code": "83060"}),
        opportunity=_summary(
            {
                "code": "83060",
                "runtime_opportunity_score": 0.2,
                "opportunity_buy_rank": 9,
                "quality_action": "REDUCED_ALLOCATION_ONLY",
                "trend_close_over_ma_20d": 1.05,
                "price_momentum_return_20d": 0.02,
                "corporate_action_status": "NO_EVENT",
                "broker_eligibility_status": "PASS",
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-10-26", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="NORMAL")
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date="2022-10-26",
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="NORMAL",
        target_membership=True,
        normal_target_weight=0.04,
        target_weight_reason="selected",
        zero_weight_reason="",
        review_reason="",
    )

    assert semantic["semantic_buy_type"] == "REENTRY"
    assert eligibility["eligibility_status"] == "PASS"
    assert eligibility["prior_campaign_id"] == prior_campaign
    assert eligibility["source_pm_decision_id"] == "pm-2022-10-04-83060-exit"
    assert eligibility["source_decision_id"] == "rp-2022-10-04-83060-sell_exit-2310c155634662da"
    assert eligibility["prior_exit_provenance_status"] == "PASS"
    assert eligibility["prior_exit_context"]["prior_campaign_id"] == prior_campaign
    assert eligibility["safety_restriction_status"] == "PASS"
    assert reentry_campaign != prior_campaign


def test_phase32_h_missing_prior_exit_detail_stays_review_required(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-23", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100},
            {"business_date": "2022-08-26", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 104, "source_decision_type": "SELL_EXIT"},
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
                "price_momentum_return_20d": 0.02,
                "corporate_action_status": "NO_EVENT",
            }
        ),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")

    assert row["prior_exit_reason"] == "SELL_EXIT"
    assert row["prior_exit_provenance_status"] == "REVIEW_REQUIRED"
    assert semantic["prior_exit_context"]["provenance_status"] == "REVIEW_REQUIRED"
    assert recovery["previous_exit_reason_class"] == "GENERIC"
    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "insufficient_prior_exit_context"


def test_phase32_h_multiple_campaigns_use_latest_matching_prior_campaign_context(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    run_dir = tmp_path / "run"
    old_campaign = "pc-phase32h-11110-0001"
    latest_campaign = "pc-phase32h-11110-0002"
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"business_date": "2022-08-10", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100, "position_campaign_id": old_campaign},
            {
                "business_date": "2022-08-12",
                "side": "SELL",
                "symbol": "11110",
                "quantity": 100,
                "price": 90,
                "source_pm_decision_id": "pm-2022-08-12-11110-exit",
                "source_decision_id": "rp-2022-08-12-11110-sell-exit",
            },
            {"business_date": "2022-08-22", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100, "position_campaign_id": latest_campaign},
            {
                "business_date": "2022-08-30",
                "side": "SELL",
                "symbol": "11110",
                "quantity": 100,
                "price": 95,
                "source_pm_decision_id": "pm-2022-08-30-11110-exit",
                "source_decision_id": "rp-2022-08-30-11110-sell-exit",
            },
        ],
    )
    for day, campaign_id, reason in (
        ("2022-08-12", old_campaign, "hard_stop_current_return"),
        ("2022-08-30", latest_campaign, "trend_and_opportunity_broken"),
    ):
        _write_json(
            run_dir / "daily" / day / "position_management" / "pm_decisions.json",
            {
                "decisions": [
                    {
                        "business_date": day,
                        "symbol": "11110",
                        "pm_decision_id": f"pm-{day}-11110-exit",
                        "decision_type": "EXIT",
                        "decision_status": "SELL_FULL_POSITION",
                        "decision_reason": reason,
                        "reason_codes": [reason],
                        "position_campaign_id": campaign_id,
                    }
                ]
            },
        )

    result = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=root,
        business_date="2022-09-01",
        candidate=_summary({"code": "11110"}),
        opportunity=_summary({"code": "11110"}),
        current=_current(),
    )

    row = result["opportunity"]["rows"][0]
    assert row["prior_exit_business_date"] == "2022-08-30"
    assert row["prior_campaign_id"] == latest_campaign
    assert row["prior_exit_reason"] == "trend_and_opportunity_broken"
    assert row["prior_exit_reason_codes"] == ["trend_and_opportunity_broken"]
    assert row["source_pm_decision_id"] == "pm-2022-08-30-11110-exit"
    assert row["source_decision_id"] == "rp-2022-08-30-11110-sell-exit"
    assert row["prior_exit_provenance_status"] == "PASS"
    assert "hard_stop_current_return" not in row["prior_exit_reason_codes"]


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


def test_phase32_j_reentry_recovery_failure_does_not_become_safety_block() -> None:
    row = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "prior_exit_reason_codes": ["trend_and_opportunity_broken"],
        "runtime_opportunity_score": 0.2,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 0.95,
        "price_momentum_return_20d": 0.02,
        "corporate_action_status": "NO_EVENT",
        "broker_eligibility_status": "PASS",
        "reason_codes": ["BROKER_PRODUCT_CATEGORY_SUPPORTED", "candidate_eligible"],
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date="2022-09-01",
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="WATCH",
        target_membership=True,
        normal_target_weight=0.05,
        target_weight_reason="selected",
        zero_weight_reason="",
        review_reason="",
    )

    assert recovery["reentry_recovery_status"] == "FAIL_CLOSED"
    assert recovery["reentry_recovery_reason"] == "reentry_trend_recovery_not_satisfied"
    assert eligibility["eligibility_status"] == "FAIL_CLOSED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    assert eligibility["renewed_current_evidence_status"] == "FAIL_CLOSED"
    assert eligibility["broker_eligibility_status"] == "PASS"
    assert eligibility["corporate_action_status"] == "NO_EVENT"
    assert eligibility["safety_restriction_status"] == "PASS"
    assert "REENTRY_BLOCKED_SAFETY" not in eligibility["reason_codes"]


def test_phase32_j_prior_context_insufficiency_does_not_become_safety_block() -> None:
    row = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "SELL_EXIT",
        "runtime_opportunity_score": 0.2,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.01,
        "price_momentum_return_20d": 0.02,
        "corporate_action_status": "NO_EVENT",
        "broker_eligibility_status": "PASS",
        "reason_codes": ["BROKER_PRODUCT_CATEGORY_SUPPORTED", "candidate_eligible"],
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date="2022-09-01",
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="WATCH",
        target_membership=True,
        normal_target_weight=0.05,
        target_weight_reason="selected",
        zero_weight_reason="",
        review_reason="",
    )

    assert recovery["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert recovery["reentry_recovery_reason"] == "insufficient_prior_exit_context"
    assert eligibility["eligibility_status"] == "REVIEW_REQUIRED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_INSUFFICIENT_EVIDENCE"
    assert eligibility["prior_exit_context_status"] == "REVIEW_REQUIRED"
    assert eligibility["broker_eligibility_status"] == "PASS"
    assert eligibility["corporate_action_status"] == "NO_EVENT"
    assert eligibility["safety_restriction_status"] == "PASS"
    assert "REENTRY_BLOCKED_SAFETY" not in eligibility["reason_codes"]


def test_phase32_j_genuine_safety_block_remains_fail_closed() -> None:
    row = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "runtime_opportunity_score": 0.2,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.01,
        "price_momentum_return_20d": 0.02,
        "corporate_action_status": "NO_EVENT",
        "broker_eligibility_status": "PASS",
        "genuine_safety_restriction_status": "FAIL_CLOSED",
    }
    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
    recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")
    eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
        row=row,
        business_date="2022-09-01",
        is_buy_new=True,
        semantic=semantic,
        recovery=recovery,
        liquidity_status="WATCH",
        target_membership=True,
        normal_target_weight=0.05,
        target_weight_reason="selected",
        zero_weight_reason="",
        review_reason="",
    )

    assert recovery["reentry_recovery_status"] == "PASS"
    assert eligibility["broker_eligibility_status"] == "PASS"
    assert eligibility["corporate_action_status"] == "NO_EVENT"
    assert eligibility["eligibility_status"] == "FAIL_CLOSED"
    assert eligibility["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_SAFETY"
    assert eligibility["safety_restriction_status"] == "FAIL_CLOSED"
    assert "REENTRY_BLOCKED_SAFETY" in eligibility["reason_codes"]


def test_phase32_j_broker_and_corporate_statuses_stay_separate_from_safety() -> None:
    broker_row = {
        "code": "11110",
        "prior_exit_business_date": "2022-08-26",
        "prior_exit_reason": "EXIT_BY_TREND_AND_EDGE_BREAK",
        "runtime_opportunity_score": 0.2,
        "opportunity_buy_rank": 2,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "trend_close_over_ma_20d": 1.01,
        "price_momentum_return_20d": 0.02,
        "corporate_action_status": "NO_EVENT",
        "broker_eligibility_status": "FAIL_CLOSED",
        "reason_codes": ["broker_eligibility_buy_new_excluded"],
    }
    corporate_row = {
        **broker_row,
        "broker_eligibility_status": "PASS",
        "corporate_action_status": "EVENT_PRESENT",
        "reason_codes": ["candidate_eligible"],
    }

    results = []
    for row in (broker_row, corporate_row):
        semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-09-01", is_buy_new=True)
        recovery = portfolio_construction._reentry_recovery_evidence(row=row, semantic=semantic, capacity_ratio=0.01, liquidity_status="WATCH")
        eligibility = portfolio_construction._canonical_reentry_semantic_eligibility(
            row=row,
            business_date="2022-09-01",
            is_buy_new=True,
            semantic=semantic,
            recovery=recovery,
            liquidity_status="WATCH",
            target_membership=True,
            normal_target_weight=0.05,
            target_weight_reason="selected",
            zero_weight_reason="",
            review_reason="",
        )
        results.append((recovery, eligibility))
        assert eligibility["safety_restriction_status"] == "PASS"

    broker_recovery, broker_eligibility = results[0]
    corporate_recovery, corporate_eligibility = results[1]
    assert broker_recovery["reentry_recovery_status"] == "PASS"
    assert broker_eligibility["broker_eligibility_status"] == "FAIL_CLOSED"
    assert broker_eligibility["corporate_action_status"] == "NO_EVENT"
    assert corporate_recovery["reentry_corporate_action_status"] == "EVENT_PRESENT"
    assert corporate_eligibility["broker_eligibility_status"] == "PASS"
    assert corporate_eligibility["corporate_action_status"] == "EVENT_PRESENT"


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
