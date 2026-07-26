from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_v2.test_phase17_k_runtime_test_runner import load_runner


RUN_ID = "runtime-test-phase20l-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_phase20_l_campaign_identity_cost_basis_rebuy_and_duplicate_execution_guard() -> None:
    runner = load_runner()
    executions = [
        {"record_type": "execution", "business_date": "2026-07-01", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 100, "execution_id": "buy-1"},
        {"record_type": "execution", "business_date": "2026-07-02", "side": "BUY", "symbol": "11110", "quantity": 100, "price": 120, "execution_id": "add-1"},
        {"record_type": "execution", "business_date": "2026-07-03", "side": "BUY", "symbol": "11110", "quantity": 50, "price": 110, "execution_id": "add-2"},
        {"record_type": "execution", "business_date": "2026-07-04", "side": "SELL", "symbol": "11110", "quantity": 50, "price": 90, "execution_id": "reduce-1"},
        {"record_type": "execution", "business_date": "2026-07-05", "side": "BUY", "symbol": "11110", "quantity": 50, "price": 100, "execution_id": "add-after-reduce"},
        {"record_type": "execution", "business_date": "2026-07-06", "side": "SELL", "symbol": "11110", "quantity": 100, "price": 130, "execution_id": "reduce-2"},
        {"record_type": "execution", "business_date": "2026-07-07", "side": "SELL", "symbol": "11110", "quantity": 150, "price": 80, "execution_id": "exit-1"},
        {"record_type": "execution", "business_date": "2026-07-07", "side": "SELL", "symbol": "11110", "quantity": 150, "price": 80, "execution_id": "exit-1"},
        {"record_type": "execution", "business_date": "2026-07-07", "side": "BUY", "symbol": "11110", "quantity": 10, "price": 95, "execution_id": "rebuy-same-day"},
    ]

    daily_slices = []
    for business_date in ("2026-07-04", "2026-07-06", "2026-07-07"):
        daily_state = runner._derive_position_campaign_state(
            run_id=RUN_ID,
            business_date=business_date,
            executions=runner._dedupe_execution_rows(executions),
            plans={"buy": [], "sell": []},
            current_state={"positions": []},
        )
        daily_slices.extend(daily_state["realized_slices"])
    state = runner._derive_position_campaign_state(
        run_id=RUN_ID,
        business_date="2026-07-07",
        executions=runner._dedupe_execution_rows(executions),
        plans={"buy": [], "sell": []},
        current_state={"positions": [{"symbol": "11110", "quantity": 10, "average_price": 95, "current_price": 95, "unrealized_pnl": 0}]},
    )

    campaigns = state["campaigns"]
    assert [row["campaign_status"] for row in campaigns] == ["CLOSED", "OPEN"]
    assert campaigns[0]["position_campaign_id"].endswith("-0001")
    assert campaigns[1]["position_campaign_id"].endswith("-0002")
    assert [event["stage"] for event in campaigns[0]["events"]] == ["BUY", "ADD", "ADD", "SELL", "ADD", "SELL", "SELL"]
    assert len(daily_slices) == 3
    assert [row["remaining_quantity"] for row in daily_slices] == [200.0, 150.0, 0.0]
    assert daily_slices[0]["gross_realized_pnl"] == -1000.0
    assert daily_slices[1]["gross_realized_pnl"] == 2200.0
    assert daily_slices[2]["gross_realized_pnl"] == -4200.0
    assert campaigns[0]["realized_pnl"] == -3000.0


def test_phase20_l_zero_quantity_boundary_closes_campaign() -> None:
    runner = load_runner()
    state = runner._derive_position_campaign_state(
        run_id=RUN_ID,
        business_date="2026-07-02",
        executions=[
            {"record_type": "execution", "business_date": "2026-07-01", "side": "BUY", "symbol": "22220", "quantity": 1.0000001, "price": 100, "execution_id": "buy"},
            {"record_type": "execution", "business_date": "2026-07-02", "side": "SELL", "symbol": "22220", "quantity": 1.0, "price": 100, "execution_id": "sell"},
        ],
        plans={"buy": [], "sell": []},
        current_state={"positions": []},
    )

    assert state["campaigns"][0]["campaign_status"] == "CLOSED"
    assert state["campaigns"][0]["current_quantity"] == 0.0


def test_phase20_l_observability_loader_rejects_corrupt_mismatch_and_stale_files(tmp_path: Path) -> None:
    runner = load_runner()
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID
    _write_json(
        run_dir / "daily" / "2026-07-01" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "run_id": RUN_ID,
            "business_date": "2026-07-01",
            "position_campaigns": [{"position_campaign_id": "pc-a", "symbol": "11110", "campaign_status": "OPEN", "events": []}],
        },
    )
    _write_json(
        run_dir / "daily" / "2026-07-02" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "run_id": "other-run",
            "business_date": "2026-07-02",
            "position_campaigns": [{"position_campaign_id": "pc-other", "symbol": "22220", "campaign_status": "OPEN", "events": []}],
        },
    )
    _write_json(
        run_dir / "daily" / "2026-07-03" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "run_id": RUN_ID,
            "business_date": "2026-07-99",
            "position_campaigns": [{"position_campaign_id": "pc-bad-date", "symbol": "33330", "campaign_status": "OPEN", "events": []}],
        },
    )
    corrupt = run_dir / "daily" / "2026-07-04" / "positions" / "position_campaigns.json"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_text("{broken", encoding="utf-8")
    _write_json(
        run_dir / "daily" / "2026-07-99" / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "run_id": RUN_ID,
            "business_date": "2026-07-99",
            "position_campaigns": [{"position_campaign_id": "pc-stale", "symbol": "99990", "campaign_status": "OPEN", "events": []}],
        },
    )

    payload = runner._load_performance_observability(
        run_dir=run_dir,
        run_id=RUN_ID,
        completed_business_days={"2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"},
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["position_campaign_count"] == 1
    assert payload["position_campaigns"][0]["position_campaign_id"] == "pc-a"
    assert {issue["reason"] for issue in payload["read_issues"]} == {
        "OBSERVABILITY_EVIDENCE_RUN_ID_MISMATCH",
        "OBSERVABILITY_EVIDENCE_BUSINESS_DATE_MISMATCH",
        "OBSERVABILITY_EVIDENCE_JSON_READ_FAILED",
    }
    assert runner._observability_completeness_judgment(payload)["judgment"] == "REVIEW_REQUIRED"
    readiness = runner._performance_analysis_readiness_judgment(payload)
    assert readiness["judgment"] == "REVIEW_REQUIRED"
    assert readiness["runtime_judgment_impact"] == "NONE"
