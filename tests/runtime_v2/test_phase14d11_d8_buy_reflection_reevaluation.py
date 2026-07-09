import json

from ai_fund_lab_v2.broker.phase14d11_buy_reflection_reevaluation import (
    run_phase14d11_d8_buy_reflection_reevaluation,
)
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, BrokerSettings


def test_phase14d11_d8_buy_reflection_passes_with_order_position_cash_evidence(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    _write_snapshot(snapshot_path, include_target_position=True)
    result = run_phase14d11_d8_buy_reflection_reevaluation(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "phase14_d11.md",
        json_report_path=tmp_path / "reports" / "phase14_d11.json",
        settings=_demo_settings(),
        run_readonly=False,
        snapshot_path=snapshot_path,
    )

    assert result.final_decision == "PHASE14D11_D8_BUY_REFLECTION_PASS"
    assert result.fill_classification == "ORDER_LIST_DERIVED_FULL_FILL"
    assert result.execution_equivalent is True
    assert result.ledger_event_count == 1
    assert result.asset_contains_target_position is True
    assert result.reconcile_pass is True
    assert result.report_detail_optional_missing_noted is True
    assert result.audit_pass is True
    assert result.additional_demo_submit_executed is False
    assert result.sell_submit_executed is False
    assert result.cancel_api_called is False


def test_phase14d11_blocks_reflection_when_position_evidence_is_missing(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    _write_snapshot(snapshot_path, include_target_position=False)
    result = run_phase14d11_d8_buy_reflection_reevaluation(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "phase14_d11.md",
        json_report_path=tmp_path / "reports" / "phase14_d11.json",
        settings=_demo_settings(),
        run_readonly=False,
        snapshot_path=snapshot_path,
    )

    assert result.final_decision == "PHASE14D11_REVIEW_REQUIRED"
    assert result.execution_equivalent is False
    assert result.ledger_event_count == 1
    assert result.report_detail_optional_missing_noted is True
    assert result.asset_contains_target_position is False


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url=DEMO_BASE_URL,
        readonly_smoke_enabled=True,
    )


def _write_snapshot(path, *, include_target_position: bool) -> None:
    positions = []
    if include_target_position:
        positions.append(
            {
                "account_type": "cash",
                "as_of": "2026-07-07T00:00:00+00:00",
                "average_price": "3000",
                "issue_code": "7203",
                "market_value": "300000",
                "quantity": "100",
                "raw_clmid": "CLMGenbutuKabuList",
            }
        )
    payload = {
        "generated_at": "2026-07-07T00:00:00+00:00",
        "health": {
            "account": {"status": "PASS"},
            "executions": {"status": "FAIL"},
            "orders": {"status": "PASS"},
            "positions": {"status": "PASS"},
        },
        "buying_power": {
            "buying_power": "19700000",
            "cash": "19700000",
            "raw_clmid": "CLMZanKaiKanougaku",
        },
        "orders": [
            {
                "as_of": "2026-07-07T00:00:00+00:00",
                "executed_quantity": "100",
                "issue_code": "7203",
                "order_id_hash": "order_7203",
                "quantity": "100",
                "remaining_quantity": "0",
                "side": "buy",
                "status": "全部約定",
            }
        ],
        "positions": positions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
