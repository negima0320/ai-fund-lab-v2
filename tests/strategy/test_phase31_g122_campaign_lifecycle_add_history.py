from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.shadow_runtime import _materialize_pre_action_position_campaigns


def test_phase31_g122_open_campaign_add_buy_merges_ledger_event_history(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-94340-buy", "2022-10-03", "94340", "BUY", 200, 144.6),
            _execution("exec-94340-add-1", "2022-10-12", "94340", "BUY", 100, 146.4),
            _execution("exec-94340-add-2", "2022-10-13", "94340", "BUY", 100, 145.7),
        ],
    )
    first = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-12",
        current=_current("2022-10-12", "94340", quantity=200, average_price=144.6, market_value=29_280),
        as_of="2022-10-12T00:00:00+00:00",
    )
    first_campaign = _campaign(first, "94340")
    assert _buy_event_count(first_campaign) == 1
    assert first_campaign["buy_history_summary"]["count"] == 1

    second = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "94340", quantity=300, average_price=145.2, market_value=43_710),
        as_of="2022-10-13T00:00:00+00:00",
    )
    second_campaign = _campaign(second, "94340")
    assert second_campaign["position_campaign_id"] == first_campaign["position_campaign_id"]
    assert second_campaign["current_quantity"] == 300
    assert _buy_event_count(second_campaign) == 2
    assert second_campaign["buy_history_summary"]["count"] == 2
    assert second_campaign["buy_history_summary"]["latest_business_date"] == "2022-10-12"
    assert second_campaign["add_history_summary"]["count"] == 1
    assert second_campaign["add_history_summary"]["latest_business_date"] == "2022-10-12"

    third = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-14",
        current=_current("2022-10-14", "94340", quantity=400, average_price=145.325, market_value=58_120),
        as_of="2022-10-14T00:00:00+00:00",
    )
    third_campaign = _campaign(third, "94340")
    assert third_campaign["position_campaign_id"] == first_campaign["position_campaign_id"]
    assert third_campaign["current_quantity"] == 400
    assert _buy_event_count(third_campaign) == 3
    assert third_campaign["buy_history_summary"]["count"] == 3
    assert third_campaign["buy_history_summary"]["latest_business_date"] == "2022-10-13"
    assert third_campaign["add_history_summary"]["count"] == 2
    assert third_campaign["add_history_summary"]["latest_business_date"] == "2022-10-13"
    assert [event["business_date"] for event in third_campaign["events"] if event["side"] == "BUY"] == [
        "2022-10-03",
        "2022-10-12",
        "2022-10-13",
    ]


def test_phase31_g122_materialization_is_idempotent_for_add_events(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-94320-buy", "2022-10-05", "94320", "BUY", 200, 159.0),
            _execution("exec-94320-add", "2022-10-12", "94320", "BUY", 100, 159.2),
        ],
    )
    _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-12",
        current=_current("2022-10-12", "94320", quantity=200, average_price=159.0, market_value=31_840),
        as_of="2022-10-12T00:00:00+00:00",
    )
    first = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "94320", quantity=300, average_price=159.0667, market_value=47_760),
        as_of="2022-10-13T00:00:00+00:00",
    )
    second = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "94320", quantity=300, average_price=159.0667, market_value=47_760),
        as_of="2022-10-13T00:00:00+00:00",
    )
    first_campaign = _campaign(first, "94320")
    second_campaign = _campaign(second, "94320")

    assert _buy_event_count(first_campaign) == 2
    assert _buy_event_count(second_campaign) == 2
    assert first_campaign["buy_history_summary"] == second_campaign["buy_history_summary"]
    assert first_campaign["add_history_summary"] == second_campaign["add_history_summary"]


def test_phase32_cw_entry_premise_snapshot_persists_and_add_does_not_overwrite(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(
                "exec-37820-buy",
                "2022-10-03",
                "37820",
                "BUY",
                300,
                50.0,
                entry_admission_action="CONTINUATION_WITH_CAUTION",
                quality_action="REDUCED_ALLOCATION_ONLY",
                buy_quality_score=0.61,
                accepted_caution_reasons=["WEAK", "ELEVATED_RISK"],
                quality_authorized_target_weight=0.019,
            ),
            _execution(
                "exec-37820-add",
                "2022-10-04",
                "37820",
                "BUY",
                100,
                51.0,
                entry_admission_action="ADD_ALLOWED",
                accepted_caution_reasons=["ADD_FRESH_STRENGTH"],
            ),
        ],
    )
    first = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-04",
        current=_current("2022-10-04", "37820", quantity=300, average_price=50.0, market_value=15_300),
        as_of="2022-10-04T00:00:00+00:00",
    )
    first_campaign = _campaign(first, "37820")
    first_snapshot = first_campaign["entry_premise_snapshot"]

    assert first_campaign["entry_premise_snapshot_status"] == "AVAILABLE"
    assert first_snapshot["schema_version"] == "campaign_entry_premise_snapshot.v1"
    assert first_snapshot["entry_business_date"] == "2022-10-03"
    assert first_snapshot["entry_admission_action"] == "CONTINUATION_WITH_CAUTION"
    assert first_snapshot["future_information_used"] is False
    assert first_snapshot["historical_outcome_used"] is False

    second = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-05",
        current=_current("2022-10-05", "37820", quantity=400, average_price=50.25, market_value=20_400),
        as_of="2022-10-05T00:00:00+00:00",
    )
    second_campaign = _campaign(second, "37820")

    assert second_campaign["position_campaign_id"] == first_campaign["position_campaign_id"]
    assert second_campaign["entry_premise_snapshot"] == first_snapshot
    assert second_campaign["entry_premise_snapshot"]["entry_admission_action"] == "CONTINUATION_WITH_CAUTION"
    assert second_campaign["entry_premise_snapshot"]["entry_business_date"] == "2022-10-03"
    assert second_campaign["add_history_summary"]["count"] == 1


def test_phase32_cw_missing_entry_premise_materializes_review_required(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("exec-67860-buy", "2022-10-03", "67860", "BUY", 200, 75.0)],
    )

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-04",
        current=_current("2022-10-04", "67860", quantity=200, average_price=75.0, market_value=15_000),
        as_of="2022-10-04T00:00:00+00:00",
    )
    campaign = _campaign(result, "67860")
    snapshot = campaign["entry_premise_snapshot"]

    assert campaign["entry_premise_snapshot_status"] == "REVIEW_REQUIRED"
    assert snapshot["snapshot_status"] == "REVIEW_REQUIRED"
    assert snapshot["silent_reconstruction_used"] is False
    assert snapshot["reason_codes"] == ["entry_premise_source_evidence_missing"]


def test_phase32_cy_authoritative_entry_lineage_materializes_sparse_fill_snapshots(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    day0_buys = [
        ("33500", 400, 40.0, "bq-33500", "REDUCED_ALLOCATION_ONLY", 0.557743, "MEDIUM", 0.0250, 0.01652, 29),
        ("37820", 300, 68.0, "bq-37820", "REDUCED_ALLOCATION_ONLY", 0.716582, "MEDIUM", 0.0330, 0.02040, 6),
        ("67860", 200, 80.0, "bq-67860", "REDUCED_ALLOCATION_ONLY", 0.482751, "LOW", 0.0300, 0.01600, 37),
        ("76470", 700, 27.0, "bq-76470", "REDUCED_ALLOCATION_ONLY", 0.576307, "MEDIUM", 0.0400, 0.01890, 26),
        ("82540", 100, 302.0, "bq-82540", "REDUCED_ALLOCATION_ONLY", 0.513128, "LOW", 0.0400, 0.03020, 35),
        ("89180", 2100, 9.0, "bq-89180", "REDUCED_ALLOCATION_ONLY", 0.585257, "MEDIUM", 0.033636, 0.01890, 25),
        ("94340", 200, 144.6, "bq-94340", "FULL_ALLOCATION_ELIGIBLE", 0.76586, "HIGH", 0.02882, 0.02882, 3),
        ("96100", 100, 198.0, "bq-96100", "REDUCED_ALLOCATION_ONLY", 0.47122, "LOW", 0.0250, 0.01980, 41),
    ]
    _write_strategy_entry_artifacts(run_dir, "2022-10-03", day0_buys)
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(f"exec-{symbol}", "2022-10-03", symbol, "BUY", quantity, price)
            for symbol, quantity, price, *_ in day0_buys
        ],
    )

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-04",
        current=_current_many(
            "2022-10-04",
            [
                (symbol, quantity, price, quantity * price)
                for symbol, quantity, price, *_ in day0_buys
            ],
        ),
        as_of="2022-10-04T00:00:00+00:00",
    )

    campaigns = {
        row["symbol"]: row
        for row in json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))["position_campaigns"]
    }
    assert set(campaigns) == {symbol for symbol, *_ in day0_buys}
    for symbol, quantity, _price, quality_id, quality_action, quality_score, quality_band, base, quality_target, rank in day0_buys:
        snapshot = campaigns[symbol]["entry_premise_snapshot"]
        assert campaigns[symbol]["entry_premise_snapshot_status"] == "PASS"
        assert snapshot["snapshot_status"] == "PASS"
        assert snapshot["symbol"] == symbol
        assert snapshot["entry_business_date"] == "2022-10-03"
        assert snapshot["accepted_quantity"] == quantity
        assert snapshot["buy_quality_action"] == quality_action
        assert snapshot["buy_quality_score"] == quality_score
        assert snapshot["buy_quality_band"] == quality_band
        assert snapshot["pre_quality_base_target_weight"] == base
        assert snapshot["quality_authorized_target_weight"] == quality_target
        assert snapshot["opportunity_rank"] == rank
        assert snapshot["source_lineage"]["quality_decision_id"] == quality_id
        assert snapshot["source_lineage"]["source_decision_id"].startswith(f"plan-{symbol}")
        assert snapshot["symbol_only_reconstruction_used"] is False
        assert snapshot["future_information_used"] is False
        assert snapshot["historical_outcome_used"] is False


def test_phase31_g122_quantity_increase_without_buy_execution_does_not_synthesize_add(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [_execution("exec-54010-buy", "2023-01-20", "54010", "BUY", 100, 500.0)],
    )
    first = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2023-01-23",
        current=_current("2023-01-23", "54010", quantity=100, average_price=500.0, market_value=50_000),
        as_of="2023-01-23T00:00:00+00:00",
    )
    first_campaign = _campaign(first, "54010")
    assert _buy_event_count(first_campaign) == 1

    second = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2023-01-24",
        current=_current("2023-01-24", "54010", quantity=200, average_price=250.0, market_value=50_000),
        as_of="2023-01-24T00:00:00+00:00",
    )
    second_campaign = _campaign(second, "54010")

    assert second_campaign["current_quantity"] == 200
    assert _buy_event_count(second_campaign) == 1
    assert second_campaign["buy_history_summary"]["count"] == 1
    assert "add_history_summary" not in second_campaign or second_campaign["add_history_summary"]["count"] == 0


def test_phase31_g122_flat_after_exit_buy_starts_new_campaign(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-76470-buy-1", "2022-10-12", "76470", "BUY", 800, 25.0),
            _execution("exec-76470-exit", "2022-10-14", "76470", "SELL", 800, 25.5),
            _execution("exec-76470-reentry", "2022-11-11", "76470", "BUY", 800, 26.0),
        ],
    )
    first = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "76470", quantity=800, average_price=25.0, market_value=20_000),
        as_of="2022-10-13T00:00:00+00:00",
    )
    first_id = _campaign(first, "76470")["position_campaign_id"]
    closed = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-17",
        current={"status": "PASS", "business_date": "2022-10-17", "rows": ()},
        as_of="2022-10-17T00:00:00+00:00",
    )
    closed_campaign = _campaign(closed, "76470")
    assert closed_campaign["position_campaign_id"] == first_id
    assert closed_campaign["campaign_status"] == "CLOSED"

    reentry = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-11-14",
        current=_current("2022-11-14", "76470", quantity=800, average_price=26.0, market_value=20_800),
        as_of="2022-11-14T00:00:00+00:00",
    )
    campaigns = _campaigns(reentry, "76470")
    open_campaigns = [row for row in campaigns if row["campaign_status"] == "OPEN"]

    assert len(open_campaigns) == 1
    assert open_campaigns[0]["position_campaign_id"] != first_id
    assert _buy_event_count(open_campaigns[0]) == 1
    assert open_campaigns[0]["buy_history_summary"]["count"] == 1


def test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    canonical_campaign_id = "pc-canonical-94320-0001"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(
                "exec-94320-buy",
                "2022-10-05",
                "94320",
                "BUY",
                200,
                159.0,
                position_campaign_id=canonical_campaign_id,
            ),
            _execution(
                "exec-94320-add",
                "2022-10-12",
                "94320",
                "BUY",
                100,
                159.2,
                position_campaign_id="pc-f9cfb6b5498e35e5-94320-0001",
                canonical_position_campaign_id=canonical_campaign_id,
                source_decision_type="BUY_ADD",
            ),
        ],
    )
    _write_prior_campaign(run_dir, "2022-10-12", "94320", canonical_campaign_id, quantity=200)

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "94320", quantity=300, average_price=159.0667, market_value=47_720),
        as_of="2022-10-13T00:00:00+00:00",
    )
    campaign = _campaign(result, "94320")

    assert campaign["position_campaign_id"] == canonical_campaign_id
    assert campaign["current_quantity"] == 300
    assert _buy_event_count(campaign) == 2
    assert campaign["buy_history_summary"]["count"] == 2
    assert campaign["add_history_summary"]["count"] == 1
    assert campaign["events"][1]["canonical_position_campaign_id"] == canonical_campaign_id


@pytest.mark.parametrize(
    (
        "business_date",
        "next_business_date",
        "symbol",
        "canonical_campaign_id",
        "runtime_campaign_id",
        "starting_quantity",
        "ending_quantity",
    ),
    [
        (
            "2022-10-12",
            "2022-10-13",
            "94320",
            "pc-e62b56d6967476ec-94320-0001",
            "pc-f9cfb6b5498e35e5-94320-0001",
            200,
            300,
        ),
        (
            "2022-10-12",
            "2022-10-13",
            "94340",
            "pc-1018b460441d595a-94340-0001",
            "pc-f9cfb6b5498e35e5-94340-0001",
            200,
            300,
        ),
        (
            "2022-10-13",
            "2022-10-14",
            "94340",
            "pc-1018b460441d595a-94340-0001",
            "pc-f9cfb6b5498e35e5-94340-0001",
            300,
            400,
        ),
        (
            "2023-02-15",
            "2023-02-16",
            "54010",
            "pc-ace730ca2278c71f-54010-0001",
            "pc-f9cfb6b5498e35e5-54010-0001",
            100,
            200,
        ),
        (
            "2023-05-31",
            "2023-06-01",
            "30410",
            "pc-9357311690cdfb6c-30410-0001",
            "pc-f9cfb6b5498e35e5-30410-0001",
            100,
            200,
        ),
    ],
)
def test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge(
    tmp_path: Path,
    business_date: str,
    next_business_date: str,
    symbol: str,
    canonical_campaign_id: str,
    runtime_campaign_id: str,
    starting_quantity: int,
    ending_quantity: int,
) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(
                f"exec-{symbol}-add",
                business_date,
                symbol,
                "BUY",
                ending_quantity - starting_quantity,
                159.2,
                position_campaign_id=runtime_campaign_id,
                canonical_position_campaign_id=canonical_campaign_id,
                source_decision_type="BUY_ADD",
            )
        ],
    )
    _write_prior_campaign(run_dir, business_date, symbol, canonical_campaign_id, quantity=starting_quantity)

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=next_business_date,
        current=_current(
            next_business_date,
            symbol,
            quantity=ending_quantity,
            average_price=159.0667,
            market_value=ending_quantity * 159.0667,
        ),
        as_of=f"{next_business_date}T00:00:00+00:00",
    )
    campaign = _campaign(result, symbol)

    assert campaign["position_campaign_id"] == canonical_campaign_id
    assert campaign["current_quantity"] == ending_quantity
    assert _buy_event_count(campaign) == 2
    assert campaign["buy_history_summary"]["count"] == 2
    assert campaign["add_history_summary"]["count"] == 1
    assert campaign["events"][1]["position_campaign_id"] == runtime_campaign_id
    assert campaign["events"][1]["canonical_position_campaign_id"] == canonical_campaign_id


def test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    canonical_campaign_id = "pc-canonical-94320-0001"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(
                "exec-94320-buy",
                "2022-10-05",
                "94320",
                "BUY",
                200,
                159.0,
                position_campaign_id=canonical_campaign_id,
            ),
            _execution(
                "exec-94320-other",
                "2022-10-12",
                "94320",
                "BUY",
                100,
                159.2,
                position_campaign_id="pc-other-94320-0001",
                source_decision_type="BUY_ADD",
            ),
        ],
    )
    _write_prior_campaign(run_dir, "2022-10-12", "94320", canonical_campaign_id, quantity=200)

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-13",
        current=_current("2022-10-13", "94320", quantity=300, average_price=159.0667, market_value=47_720),
        as_of="2022-10-13T00:00:00+00:00",
    )
    campaign = _campaign(result, "94320")

    assert campaign["position_campaign_id"] == canonical_campaign_id
    assert campaign["current_quantity"] == 300
    assert _buy_event_count(campaign) == 1
    assert "add_history_summary" not in campaign or campaign["add_history_summary"]["count"] == 0


def _campaign(result: dict, symbol: str) -> dict:
    campaigns = _campaigns(result, symbol)
    open_campaigns = [row for row in campaigns if row.get("campaign_status") == "OPEN"]
    return open_campaigns[0] if open_campaigns else campaigns[-1]


def _campaigns(result: dict, symbol: str) -> list[dict]:
    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    return [row for row in payload["position_campaigns"] if row.get("symbol") == symbol]


def _buy_event_count(campaign: dict) -> int:
    return sum(1 for event in campaign.get("events", []) if event.get("side") == "BUY")


def _current(business_date: str, symbol: str, *, quantity: float, average_price: float, market_value: float) -> dict:
    return _current_many(business_date, [(symbol, quantity, average_price, market_value)])


def _current_many(business_date: str, rows: list[tuple[str, float, float, float]]) -> dict:
    return {
        "status": "PASS",
        "business_date": business_date,
        "source_ref": "state.json",
        "source_hash": "current-hash",
        "rows": tuple(
            {
                "security_code": symbol,
                "quantity": quantity,
                "average_price": average_price,
                "market_value": market_value,
                "quantity_basis": "ADJUSTED",
                "valuation_price_basis": "ADJUSTED",
            }
            for symbol, quantity, average_price, market_value in rows
        ),
    }


def _execution(
    execution_id: str,
    business_date: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    **extra,
) -> dict:
    return {
        "execution_id": execution_id,
        "record_id": f"ledger-{execution_id}",
        "dedup_key": f"dedup-{execution_id}",
        "business_date": business_date,
        "symbol": symbol,
        "side": side,
        "filled_quantity": quantity,
        "price": price,
        "average_price": price,
        "market_value": quantity * price,
        "execution_price_basis": "ADJUSTED",
        "quantity_basis": "ADJUSTED",
        **extra,
    }


def _write_prior_campaign(
    run_dir: Path,
    business_date: str,
    symbol: str,
    campaign_id: str,
    *,
    quantity: float,
) -> None:
    path = run_dir / "daily" / business_date / "positions" / "position_campaigns.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "position_campaign_observability.v1",
                "run_id": "test",
                "business_date": business_date,
                "position_campaigns": [
                    {
                        "position_campaign_id": campaign_id,
                        "symbol": symbol,
                        "campaign_status": "OPEN",
                        "opened_business_date": "2022-10-05",
                        "current_quantity": quantity,
                        "buy_history_summary": {"count": 1, "latest_business_date": "2022-10-05"},
                        "events": [
                            {
                                "business_date": "2022-10-05",
                                "side": "BUY",
                                "stage": "BUY",
                                "quantity": float(quantity),
                                "price": 159.0,
                                "source_execution_id": "exec-94320-buy",
                                "source_execution_record_id": "ledger-exec-94320-buy",
                                "source_execution_dedup_key": "dedup-exec-94320-buy",
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_strategy_entry_artifacts(
    run_dir: Path,
    business_date: str,
    rows: list[tuple[str, float, float, str, str, float, str, float, float, int]],
) -> None:
    strategy_dir = run_dir / "daily" / business_date / "strategy"
    plans = []
    positions = []
    for symbol, quantity, price, quality_id, quality_action, quality_score, quality_band, base, quality_target, rank in rows:
        plans.append(
            {
                "security_code": symbol,
                "planning_id": f"plan-{symbol}-20221003",
                "portfolio_construction_reference": f"pc-member-{symbol}",
                "planning_intent": "BUY_NEW",
                "order_side_intent": "BUY",
                "planned_quantity": quantity,
                "reference_price": price,
                "quality_decision_id": quality_id,
                "quality_action": quality_action,
                "quality_score": quality_score,
                "quality_band": quality_band,
                "opportunity_buy_rank": rank,
                "runtime_opportunity_score": round(1.0 / rank, 6),
                "strategy_authority_lineage": {
                    "lineage_hash": f"lineage-{symbol}",
                    "item": {"pc_member_id": f"pc-member-{symbol}", "portfolio_input_opportunity_rank": rank},
                    "refined_capital_decision_lineage": {
                        "reentry_binding": {
                            "entry_admission": {
                                "admission_action": "BUY_NEW_ALLOWED",
                                "entry_state": "CONTINUATION_WITH_CAUTION",
                                "reason_codes": ["CONTINUATION_WITH_CAUTION", quality_action],
                                "consumed_evidence": {
                                    "trend_health": "WEAK_BUT_POSITIVE",
                                    "acceleration_state": "COMPARABLE_MARGINAL",
                                    "participation_quality": "MIXED",
                                    "participation_risk": "ELEVATED_RISK",
                                    "persistence": "MARGINAL",
                                    "downside_risk_status": "PASS",
                                    "regime_compatibility": "PASS",
                                },
                            }
                        }
                    },
                },
            }
        )
        positions.append(
            {
                "security_code": symbol,
                "position_reference": f"ps-{symbol}",
                "quantity_delta_candidate": quantity,
                "reference_price": price,
                "semantic_buy_type": "BUY_NEW",
                "quality_decision_id": quality_id,
                "quality_action": quality_action,
                "quality_score": quality_score,
                "quality_band": quality_band,
                "opportunity_buy_rank": rank,
                "target_weight": quality_target,
                "target_weight_resolution": {
                    "production_deployability_class": "PRODUCTION_DEPLOYABLE_NEW",
                    "pre_quality_base_target_weight": base,
                    "quality_authorized_target_weight": quality_target,
                    "final_deployable_target_weight": quality_target,
                },
            }
        )
    _write_json(strategy_dir / "runtime_planning.json", {"business_date": business_date, "plans": plans})
    _write_json(strategy_dir / "position_sizing.json", {"business_date": business_date, "positions": positions})
