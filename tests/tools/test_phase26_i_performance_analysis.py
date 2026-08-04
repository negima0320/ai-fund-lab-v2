from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "performance_analysis"))

from common import analyze_run, write_all  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _build_run(root: Path) -> Path:
    run = root / "runs" / "runtime-test-unit"
    for day in ("2022-07-01", "2022-07-04"):
        _write_json(
            run / "daily" / day / "current_valuation_refresh" / "current_valuation_manifest.json",
            {
                "artifact": {
                    "candidate_current": {
                        "business_date": day,
                        "cash": 900_000 if day == "2022-07-01" else 1_011_000,
                        "market_value": 110_000 if day == "2022-07-01" else 0,
                        "total_equity": 1_010_000 if day == "2022-07-01" else 1_011_000,
                        "positions": [{"symbol": "11110"}] if day == "2022-07-01" else [],
                        "realized_pnl": 0 if day == "2022-07-01" else 11_000,
                        "new_unrealized_pnl": 10_000 if day == "2022-07-01" else 0,
                    }
                }
            },
        )
    _write_json(
        run / "daily" / "2022-07-01" / "execution" / "fills.json",
        {
            "fills": [
                {
                    "business_date": "2022-07-01",
                    "side": "BUY",
                    "symbol": "11110",
                    "quantity": 100,
                    "execution_price": 1000,
                    "gross_notional": {"value": 100_000},
                    "cash_effect": {"value": -100_000},
                    "position_campaign_id": "pc-11110-1",
                    "execution_id": "buy-1",
                    "pending_item_id": "pending-buy-1",
                }
            ]
        },
    )
    _write_json(
        run / "daily" / "2022-07-01" / "submit" / "runtime_manifest.json",
        {
            "submit_guard_item_evidence": [
                {
                    "symbol": "11110",
                    "side": "BUY",
                    "pending_item_id": "pending-buy-1",
                    "opportunity_buy_rank": 1,
                    "opportunity_expected_edge_score": 0.12,
                    "quantity_contract": {
                        "quality_score": 0.8,
                        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                        "quality_allocation_adjustment": 1.0,
                        "quality_decision_id": "bq-1",
                        "selected_notional": 100_000,
                    },
                }
            ]
        },
    )
    _write_json(
        run / "daily" / "2022-07-04" / "execution" / "fills.json",
        {
            "fills": [
                {
                    "business_date": "2022-07-04",
                    "side": "SELL",
                    "symbol": "11110",
                    "quantity": 100,
                    "execution_price": 1110,
                    "gross_notional": {"value": 111_000},
                    "cash_effect": {"value": 111_000},
                    "position_campaign_id": "pc-11110-1",
                    "execution_id": "sell-1",
                    "pending_item_id": "pending-sell-1",
                }
            ]
        },
    )
    return run


def test_phase26_i_generates_run_scoped_performance_report(tmp_path: Path) -> None:
    run = _build_run(tmp_path)

    analysis = analyze_run(run.name, tmp_path / "runs")
    write_all(analysis)

    summary = json.loads((run / "performance_report" / "performance_summary.json").read_text())
    assert summary["run_id"] == "runtime-test-unit"
    assert summary["runtime_input_policy"]["run_scoped_only"] is True
    assert summary["runtime_input_policy"]["strategy_input_added"] is False
    assert summary["Initial Equity"] == 1_000_000
    assert summary["Final Equity"] == 1_011_000
    assert summary["BUY Count"] == 1
    assert summary["SELL Count"] == 1
    assert summary["Profit Factor"] is None

    with (run / "performance_report" / "trade_with_quality.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["Quality Action"] == "FULL_ALLOCATION_ELIGIBLE"
    assert rows[0]["Rank"] == "1"


def test_phase26_i_rejects_path_escape(tmp_path: Path) -> None:
    _build_run(tmp_path)

    try:
        analyze_run("../runtime-test-unit", tmp_path / "runs")
    except SystemExit as exc:
        assert "invalid --run-id" in str(exc)
    else:
        raise AssertionError("path escape was not rejected")
