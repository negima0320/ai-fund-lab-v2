import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


def test_phase14e50_sell_planning_cli_writes_sell_pending_from_current_only(tmp_path):
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[
            _position("3926", quantity=1000, price=351),
            _position("6897", quantity=500, price=676),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            {
                "record_type": "position",
                "symbol": "9001",
                "quantity": 100,
                "source": "broker_readonly_evidence_only",
            }
        ],
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
        ]
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json"))
    manifest = _load_json(manifests[-1])
    stage_names = {stage["name"] for stage in manifest["stages"]}
    symbols = {item["symbol"] for item in pending["items"]}

    assert exit_code == 0
    assert manifest["job"] == "sell_planning"
    assert "sell_planning_pending_pipeline" in stage_names
    assert manifest["submit_enabled"] is False
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False
    assert pending["state"] == "APPROVED"
    assert {item["side"] for item in pending["items"]} == {"SELL"}
    assert symbols == {"3926", "6897"}
    assert "9001" not in symbols
    assert pending["approval"]["approval_status"] == "APPROVED"
    assert (tmp_path / "reports" / "public" / "runtime_v2" / "latest.md").exists()


def test_phase14e50_sell_planning_cli_blocks_submit_enabled_true(tmp_path):
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[_position("3926", quantity=1000, price=351)],
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
        ]
    )

    assert exit_code == 40


def _write_runtime_state(root: Path, *, positions: list[dict]) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e50",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "updated_at": "2026-07-09T00:00:00Z",
            "positions": positions,
            "cash": 140500.0,
            "buying_power": 140500.0,
            "market_value": sum(float(item["market_value"]) for item in positions),
            "total_equity": 140500.0 + sum(float(item["market_value"]) for item in positions),
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e50-before",
            "state": "CONSUMED",
            "environment": "demo",
            "items": [],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e50-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-09T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [])
    return root


def _position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": "2026-07-09",
    }


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
