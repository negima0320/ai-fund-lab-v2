import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.report.markdown_writer import (
    load_runtime_v2_report_context,
    scan_public_report,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import (
    generate_public_report_from_current,
)


def test_generates_runtime_and_public_markdown_from_fixed_current(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / "2026-07-07",
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / "2026-07-07",
        business_date="2026-07-07",
    )

    runtime_report = Path(result["runtime_report_md"]).read_text(encoding="utf-8")
    public_report = Path(result["public_report_md"]).read_text(encoding="utf-8")

    assert "Runtime v2 Operation Report" in runtime_report
    assert "Runtime v2 Public Report" in public_report
    assert "Cash: JPY 19,999,648" in public_report
    assert "Buying power: JPY 19,999,648" in public_report
    assert "6501" in public_report
    assert "## Current Portfolio" in public_report
    assert "## Today's Operation Summary" in public_report
    assert "## Ledger History Summary" in public_report
    assert "Filled count: 1" in public_report
    assert "Execution-equivalent count: 1" in public_report
    assert "Cumulative orders: 2" in public_report
    assert "Execution-equivalent records: 1" in public_report
    assert "Cumulative rejected history: 1" in public_report
    assert "BUY orders: 1" not in public_report
    assert "SELL orders: 1" not in public_report
    assert "Reconcile: PASS" in public_report
    assert "Audit: PASS" in public_report
    assert "payload summary only" in public_report
    public_json = json.loads(Path(result["public_report_json"]).read_text(encoding="utf-8"))
    latest_json = json.loads(Path(result["latest_json"]).read_text(encoding="utf-8"))
    assert public_json["summary"]["current_portfolio"]["position_count"] == 1
    assert public_json["summary"]["today_operation"]["filled_count"] == 1
    assert public_json["summary"]["today_operation"]["execution_equivalent_count"] == 1
    assert public_json["summary"]["ledger_history"]["cumulative_orders"] == 2
    assert public_json["summary"]["ledger_history"]["execution_equivalent_count"] == 1
    assert public_json["summary"]["ledger_history"]["cumulative_rejected_history"] == 1
    assert latest_json["summary"]["today_operation"]["filled_count"] == 1
    assert result["redaction_scan"]["passed"] is True


def test_public_report_redacts_internal_ids_and_forbidden_sources(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / "2026-07-07",
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / "2026-07-07",
        business_date="2026-07-07",
    )

    public_report = Path(result["public_report_md"]).read_text(encoding="utf-8").lower()
    forbidden = (
        "raw_request",
        "raw_response",
        "sordernumber",
        "order_id",
        "pending_item_id",
        "ledger_record_id",
        "record_id",
        "sha256:",
        ".runtime/phase14d",
        ".runtime/demo",
        "phase9",
        "demo_ledger",
    )
    assert all(marker not in public_report for marker in forbidden)
    assert scan_public_report(public_report)["passed"] is True


def test_loader_uses_fixed_current_paths_only(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    context = load_runtime_v2_report_context(runtime_root, business_date="2026-07-07")

    assert context.source_current_paths == (
        "persistent_ledger/state.json",
        "persistent_ledger/orders.jsonl",
        "persistent_ledger/executions.jsonl",
        "persistent_ledger/positions.jsonl",
        "persistent_ledger/cash.jsonl",
        "persistent_ledger/events.jsonl",
        "pending_order_plan/pending_order_plan.json",
        "runtime_state/current_state.json",
    )


def test_loader_rejects_mode_rooted_current_source():
    with pytest.raises(ValueError):
        load_runtime_v2_report_context(Path(".runtime/demo"), business_date="2026-07-07")


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "as_of": "2026-07-07",
            "environment": "demo",
            "cash": 19999648.0,
            "buying_power": 19999648.0,
            "market_value": 3298000.0,
            "total_equity": 23297648.0,
            "cash_confirmed": True,
            "buying_power_confirmed": True,
            "review_required": False,
            "positions": [
                {
                    "symbol": "6501",
                    "quantity": 200,
                    "average_price": 4805,
                    "market_value": 986000,
                },
                {
                    "symbol": "7203",
                    "quantity": 0,
                    "average_price": 0,
                    "market_value": 0,
                },
            ],
        },
    )
    _write_jsonl(
        root / "persistent_ledger" / "orders.jsonl",
        [
            {
                "record_type": "order",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "status": "REJECTED_OR_UNKNOWN",
                "recorded_at": "2026-07-06T09:00:00+09:00",
                "order_id": "must-not-leak",
                "record_id": "must-not-leak",
            },
            {
                "record_type": "order",
                "symbol": "7203",
                "side": "SELL",
                "quantity": 100,
                "status": "filled",
                "recorded_at": "2026-07-07T09:00:00+09:00",
                "order_id": "must-not-leak",
                "ledger_record_id": "must-not-leak",
            },
        ],
    )
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {
                "record_type": "execution",
                "execution_evidence_type": "execution_equivalent",
                "business_date": "2026-07-07",
                "symbol": "7203",
                "side": "SELL",
                "quantity": 100,
                "filled_quantity": 100,
                "remaining_quantity": 0,
                "order_status": "filled",
                "execution_status": "filled",
                "recorded_at": "2026-07-07T09:00:00+09:00",
            }
        ],
    )
    _write_jsonl(
        root / "persistent_ledger" / "positions.jsonl",
        [{"record_type": "position", "symbol": "6501", "quantity": 200}],
    )
    _write_jsonl(
        root / "persistent_ledger" / "cash.jsonl",
        [{"record_type": "cash", "cash": 19999648.0, "buying_power": 19999648.0}],
    )
    _write_jsonl(
        root / "persistent_ledger" / "events.jsonl",
        [{"record_type": "event", "severity": "INFO", "message": "evidence accepted"}],
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "environment": "demo",
            "state": "CONSUMED",
            "items": [{"symbol": "7203", "side": "SELL", "quantity": 100}],
            "consume": {"consumed": True},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "environment": "demo",
            "runtime_mode": "demo",
            "state": "RECONCILED",
            "updated_at": "2026-07-07",
        },
    )
    return root


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
