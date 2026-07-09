import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)


def test_phase14e25_projects_only_runtime_owned_fills_to_current(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-initial",
            "environment": "demo",
            "source": "phase14e8_demo_operation_initial_state",
            "as_of": "2026-07-07",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": [],
            "created_at": "2026-07-07",
        },
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            _accepted_order("65220", "6522"),
            _accepted_order("78780", "7878"),
            _rejected_order("45910", "4591"),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            _position("6522", quantity=100, average_price=102, market_value=235000),
            _position("7878", quantity=100, average_price=102, market_value=155400),
            _position("6501", quantity=200, average_price=4942, market_value=959000),
        ],
    )

    result = project_runtime_owned_fills_to_current(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
    )

    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert result.runtime_owned_symbols == ("6522", "7878")
    assert result.excluded_broker_position_symbols == ("6501",)
    assert state["cash"] == 1_000_000 - (100 * 102 * 2)
    assert state["buying_power"] == state["cash"]
    assert state["market_value"] == 235000 + 155400
    assert state["total_equity"] == state["cash"] + state["market_value"]
    assert [position["symbol"] for position in state["positions"]] == ["6522", "7878"]
    assert all(position["symbol"] != "6501" for position in state["positions"])
    assert state["runtime_owned_projection"]["broker_cash_copied"] is False
    assert state["runtime_owned_projection"]["unrelated_demo_positions_copied"] is False
    assert state["source"] == "runtime_v2_runtime_owned_fill_projection"


def _accepted_order(symbol: str, broker_symbol: str) -> dict:
    return {
        "record_type": "order",
        "source": "runtime_v2_submit_pipeline",
        "status": "ACCEPTED",
        "symbol": symbol,
        "issue_code_normalization": {"broker_issue_code": broker_symbol},
        "record_id": f"ledger-order-submit-{symbol}",
    }


def _rejected_order(symbol: str, broker_symbol: str) -> dict:
    payload = _accepted_order(symbol, broker_symbol)
    payload["status"] = "REJECTED_OR_UNKNOWN"
    return payload


def _position(symbol: str, *, quantity: float, average_price: float, market_value: float) -> dict:
    return {
        "record_type": "position",
        "source": "runtime_v2_execution_readonly",
        "symbol": symbol,
        "position_key": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "market_value": market_value,
        "as_of": "2026-07-08T06:24:02+00:00",
        "recorded_at": "2026-07-08T06:24:02+00:00",
        "record_id": f"ledger-position-{symbol}",
    }


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
