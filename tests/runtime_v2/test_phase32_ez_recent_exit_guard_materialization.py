from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerExecutionRecord, LedgerOrderRecord
from ai_fund_lab_v2.runtime_v2.recent_exit_guard import materialize_recent_exit_guard_from_execution
from ai_fund_lab_v2.strategy import portfolio_construction, shadow_runtime


def test_phase32_ez_83060_sell_exit_materializes_next_day_bounded_guard(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    run_dir = tmp_path / "runtime-test-ez"
    result = materialize_recent_exit_guard_from_execution(
        runtime_root=runtime_root,
        business_date="2022-10-04",
        runtime_test_run_id=run_dir.name,
        ledger_orders=[
            _order(
                symbol="83060",
                side="SELL",
                source_decision_id="rp-2022-10-04-83060-sell_exit-9a2c234d52b1449f",
                source_pm_decision_id="pm-2022-10-04-83060-exit",
                source_decision_type="SELL_EXIT",
                campaign_id="pc-6c27812c4ff1c33a-83060-0001",
            )
        ],
        ledger_executions=[
            _execution(
                symbol="83060",
                side="SELL",
                source_decision_id="rp-2022-10-04-83060-sell_exit-9a2c234d52b1449f",
                source_pm_decision_id="pm-2022-10-04-83060-exit",
                source_decision_type="SELL_EXIT",
                campaign_id="pc-6c27812c4ff1c33a-83060-0001",
            )
        ],
    )

    assert result.status == "PASS"
    assert result.emitted_count == 1
    payload = _read_json(runtime_root / "runtime_state" / "recent_exit_guard.json")
    assert payload["rows"][0]["symbol"] == "83060"

    supplied = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-05",
        candidate={"rows": ({"code": "83060"},), "payload": {"decisions": [{"code": "83060"}]}},
        opportunity={"rows": (), "payload": {"rankings": []}},
        current={"rows": ()},
    )
    row = supplied["candidate"]["rows"][0]
    assert row["prior_exit_business_date"] == "2022-10-04"
    assert row["prior_campaign_id"] == "pc-6c27812c4ff1c33a-83060-0001"
    assert row["source_pm_decision_id"] == "pm-2022-10-04-83060-exit"

    semantic = portfolio_construction._semantic_reentry_evidence(row=row, business_date="2022-10-05", is_buy_new=True)
    assert semantic["semantic_buy_type"] == "BUY_NEW"
    assert semantic["recent_exit_guard_state"] == "ACTIVE_RECENT_EXIT_GUARD"
    assert semantic["recent_exit_guard_status"] == "FAIL_CLOSED"


def test_phase32_ez_recent_exit_guard_compacts_expired_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    guard_path = runtime_root / "runtime_state" / "recent_exit_guard.json"
    _write_json(
        guard_path,
        {
            "schema_version": "runtime_v2.recent_exit_guard_index.v1",
            "rows": [
                {
                    "symbol": "83060",
                    "most_recent_full_exit_business_date": "2022-10-04",
                    "prior_campaign_id": "pc-old",
                    "source_pm_decision_id": "pm-old",
                    "source_decision_id": "rp-old",
                    "runtime_test_run_id": "runtime-test-ez",
                }
            ],
        },
    )

    result = materialize_recent_exit_guard_from_execution(
        runtime_root=runtime_root,
        business_date="2022-10-11",
        runtime_test_run_id="runtime-test-ez",
        ledger_orders=[],
        ledger_executions=[],
    )

    assert result.expired_count == 1
    assert result.rows == ()
    assert _read_json(guard_path)["rows"] == []


def test_phase32_ez_cross_run_guard_row_is_not_attached(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    run_dir = tmp_path / "runtime-test-current"
    _write_json(
        runtime_root / "runtime_state" / "recent_exit_guard.json",
        {
            "schema_version": "runtime_v2.recent_exit_guard_index.v1",
            "rows": [
                {
                    "symbol": "83060",
                    "most_recent_full_exit_business_date": "2022-10-04",
                    "prior_campaign_id": "pc-stale",
                    "source_pm_decision_id": "pm-stale",
                    "source_decision_id": "rp-stale",
                    "runtime_test_run_id": "runtime-test-foreign",
                }
            ],
        },
    )

    supplied = shadow_runtime._supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-05",
        candidate={"rows": ({"code": "83060"},), "payload": {"decisions": [{"code": "83060"}]}},
        opportunity={"rows": (), "payload": {"rankings": []}},
        current={"rows": ()},
    )

    assert supplied["candidate"]["rows"][0].get("prior_exit_business_date") is None
    assert supplied["evidence"]["stale_or_cross_run_guard_rows_rejected"] == 1


def test_phase32_ez_full_exit_missing_minimal_provenance_reviews(tmp_path: Path) -> None:
    result = materialize_recent_exit_guard_from_execution(
        runtime_root=tmp_path / ".runtime",
        business_date="2022-10-04",
        runtime_test_run_id="runtime-test-ez",
        ledger_orders=[],
        ledger_executions=[
            _execution(
                symbol="83060",
                side="SELL",
                source_decision_id="rp-2022-10-04-83060-sell_exit",
                source_pm_decision_id="",
                source_decision_type="SELL_EXIT",
                campaign_id="",
            )
        ],
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "full_exit_execution_missing_recent_exit_guard_minimal_provenance"
    assert result.malformed_count == 1
    assert result.rows == ()


def _order(
    *,
    symbol: str,
    side: str,
    source_decision_id: str,
    source_pm_decision_id: str,
    source_decision_type: str,
    campaign_id: str,
) -> LedgerOrderRecord:
    return LedgerOrderRecord(
        record_id=f"ledger-order-{symbol}",
        record_type="order",
        schema_version="1",
        environment="historical",
        source="runtime_v2_execution_readonly",
        created_at="2022-10-04",
        dedup_key=f"order:{symbol}",
        order_id=f"order:{symbol}",
        business_date="2022-10-04",
        side=side,
        symbol=symbol,
        quantity=100.0,
        status="filled",
        source_decision_id=source_decision_id,
        source_decision_type=source_decision_type,
        source_pm_decision_id=source_pm_decision_id,
        position_campaign_id=campaign_id,
        campaign_id=campaign_id,
        strategy_authority_lineage={"reason_codes": ["trend_and_opportunity_broken"]},
    )


def _execution(
    *,
    symbol: str,
    side: str,
    source_decision_id: str,
    source_pm_decision_id: str,
    source_decision_type: str,
    campaign_id: str,
) -> LedgerExecutionRecord:
    return LedgerExecutionRecord(
        record_id=f"ledger-execution-{symbol}",
        record_type="execution",
        schema_version="1",
        environment="historical",
        source="runtime_v2_execution_readonly",
        created_at="2022-10-04",
        dedup_key=f"execution:{symbol}",
        execution_id=f"execution:{symbol}",
        order_id=f"order:{symbol}",
        business_date="2022-10-04",
        mode="historical",
        side=side,
        symbol=symbol,
        quantity=100.0,
        filled_quantity=100.0,
        remaining_quantity=0.0,
        order_status="filled",
        execution_status="filled",
        source_decision_id=source_decision_id,
        source_decision_type=source_decision_type,
        source_pm_decision_id=source_pm_decision_id,
        position_campaign_id=campaign_id,
        campaign_id=campaign_id,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
