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


def test_phase32_l_buy_new_fill_campaign_is_row_authority_when_current_lacks_campaign(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    campaign_id = "pc-actual-fill-83060-0001"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution(
                "exec-83060-buy-new",
                "2022-10-26",
                "83060",
                "BUY",
                100,
                711.5,
                position_campaign_id=campaign_id,
                campaign_id=campaign_id,
                source_decision_type="BUY_NEW",
            )
        ],
    )

    result = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-10-27",
        current=_current("2022-10-27", "83060", quantity=100, average_price=711.5, market_value=69_110),
        as_of="2022-10-27T00:00:00+00:00",
    )
    campaign = _campaign(result, "83060")

    assert campaign["position_campaign_id"] == campaign_id
    assert campaign["events"][0]["position_campaign_id"] == campaign_id
    assert campaign["observed_state_authority"] == "PRE_ACTION_CURRENT_PLUS_PRIOR_CANONICAL_CAMPAIGN"


def test_phase32_l_reentry_new_campaign_keeps_fill_campaign_then_add_inherits_it(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    runtime_root = tmp_path / ".runtime"
    prior_campaign = "pc-prior-76470-0001"
    reentry_campaign = "pc-reentry-fill-76470-0002"
    _write_jsonl(
        runtime_root / "persistent_ledger" / "executions.jsonl",
        [
            _execution("exec-76470-buy-old", "2022-10-12", "76470", "BUY", 800, 25.0, position_campaign_id=prior_campaign),
            _execution("exec-76470-exit", "2022-10-14", "76470", "SELL", 800, 25.5, position_campaign_id=prior_campaign),
            _execution(
                "exec-76470-reentry",
                "2022-11-11",
                "76470",
                "BUY",
                300,
                26.0,
                position_campaign_id=reentry_campaign,
                source_decision_type="BUY_NEW",
            ),
            _execution(
                "exec-76470-add",
                "2022-11-25",
                "76470",
                "BUY",
                100,
                26.5,
                position_campaign_id=reentry_campaign,
                source_decision_type="BUY_ADD",
            ),
        ],
    )

    pre_add = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-11-24",
        current=_current("2022-11-24", "76470", quantity=300, average_price=26.0, market_value=8_100),
        as_of="2022-11-24T00:00:00+00:00",
    )
    open_before_add = _campaign(pre_add, "76470")
    assert open_before_add["position_campaign_id"] == reentry_campaign
    assert open_before_add["position_campaign_id"] != prior_campaign

    post_add = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2022-11-28",
        current=_current("2022-11-28", "76470", quantity=400, average_price=26.125, market_value=10_450),
        as_of="2022-11-28T00:00:00+00:00",
    )
    open_after_add = _campaign(post_add, "76470")
    assert open_after_add["position_campaign_id"] == reentry_campaign
    assert _buy_event_count(open_after_add) == 2
    assert open_after_add["add_history_summary"]["count"] == 1
    assert {event["position_campaign_id"] for event in open_after_add["events"] if event["side"] == "BUY"} == {
        reentry_campaign
    }


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
    return {
        "status": "PASS",
        "business_date": business_date,
        "source_ref": "state.json",
        "source_hash": "current-hash",
        "rows": (
            {
                "security_code": symbol,
                "quantity": quantity,
                "average_price": average_price,
                "market_value": market_value,
                "quantity_basis": "ADJUSTED",
                "valuation_price_basis": "ADJUSTED",
            },
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
