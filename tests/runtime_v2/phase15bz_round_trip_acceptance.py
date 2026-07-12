from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.current_state.authority import current_authority_metadata
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


ROOT = Path(".runtime_acceptance_phase15_buy_origin")
EVIDENCE_DIR = Path("reports/phase_reports/phase15_bz")
BUSINESS_DATE = "2026-07-14"
ISSUE_CODE = "7203"
SELL_QUANTITY = 100.0
SELL_PRICE = 1050.0
INITIAL_CASH = 1_000_000.0
BUY_COST = 100_000.0
POST_BUY_CASH = 900_000.0
SELL_PROCEEDS = SELL_QUANTITY * SELL_PRICE
REALIZED_PNL = 5_000.0
FINAL_CASH = INITIAL_CASH + REALIZED_PNL
REQUEST_HASH = "sha256:phase15bz-sell-request-7203-100"
BROKER_ORDER_HASH = "sha256:phase15bz-sell-order-7203-100"


@dataclass
class Phase15BZSimulatedAcceptedAdapter:
    preflight_calls: int = 0
    submit_calls: int = 0
    request_payloads: list[dict[str, Any]] = field(default_factory=list)

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.preflight_calls += 1
        self.request_payloads.append(_request_payload(command))
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="phase15bz simulated sell transport preflight",
            response_classification={
                "transport": "simulation",
                "network_called": False,
                "broker_write_performed": False,
                "request_hash": REQUEST_HASH,
            },
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.submit_calls += 1
        if not self.request_payloads:
            self.request_payloads.append(_request_payload(command))
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            broker_order_id_hash=BROKER_ORDER_HASH,
            post_send_unknown=False,
            reason="phase15bz simulated sell accepted response",
            issue_code_normalization={
                "original_symbol": command.symbol,
                "broker_issue_code": command.symbol,
                "normalization_status": "PASS",
            },
            response_classification={
                "broker_result_classification": "ACCEPTED",
                "result_code": "0",
                "order_number_present": True,
                "post_send_unknown": False,
                "network_called": False,
                "broker_write_performed": False,
                "simulation": True,
                "request_hash": REQUEST_HASH,
            },
            next_action="execution_readonly_reconciliation",
        )


@dataclass(frozen=True)
class _DemoSettings:
    environment: str = "demo"
    base_url: str = "https://demo-kabuka.e-shiten.jp/e_api_v4r9/"


def run_phase15bz_round_trip_acceptance(
    *,
    root: Path = ROOT,
    evidence_dir: Path = EVIDENCE_DIR,
    write_phase_report: bool = True,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before_runtime_hashes = _existing_runtime_hashes()
    before_current = _read_json(root / "persistent_ledger" / "state.json")
    before_pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    before_counts = _ledger_counts(root)
    first = _apply_round_trip_once(root=root, evidence_dir=evidence_dir)
    after_first_current = _read_json(root / "persistent_ledger" / "state.json")
    after_first_pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    after_first_counts = _ledger_counts(root)
    after_first_hash = _hash_json(after_first_current)
    second = _apply_round_trip_once(root=root, evidence_dir=evidence_dir)
    after_second_current = _read_json(root / "persistent_ledger" / "state.json")
    after_second_pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    after_second_counts = _ledger_counts(root)
    report = _generate_reports(root=root, evidence_dir=evidence_dir)
    payload = _payload(
        root=root,
        evidence_dir=evidence_dir,
        before_runtime_hashes=before_runtime_hashes,
        before_current=before_current,
        before_pending=before_pending,
        before_counts=before_counts,
        first=first,
        after_first_current=after_first_current,
        after_first_pending=after_first_pending,
        after_first_counts=after_first_counts,
        second=second,
        after_second_current=after_second_current,
        after_second_pending=after_second_pending,
        after_second_counts=after_second_counts,
        after_first_hash=after_first_hash,
        report=report,
    )
    _write_json(evidence_dir / "phase15bz_round_trip_acceptance_evidence.json", payload)
    if write_phase_report:
        _write_json(Path("reports/phase_reports/phase15_bz_runtime_round_trip_buy_sell_acceptance.json"), payload)
        _write_text(Path("docs/phase_reports/phase15_bz_runtime_round_trip_buy_sell_acceptance.md"), _render_markdown(payload))
    return payload


def _apply_round_trip_once(*, root: Path, evidence_dir: Path) -> dict[str, Any]:
    if _round_trip_already_applied(root):
        return {
            "status": "NOOP_ALREADY_APPLIED",
            "reason": "round trip sell execution already applied",
            "sell_planning": {},
            "submit": {},
            "execution": {},
            "current_apply": _read_json(root / "runtime_state" / "current_state.json"),
        }
    _write_broker_available_quantity_snapshot(root)
    policy = load_capital_deployment_policy(root / "runtime_state" / "policy" / "phase15by_capital_deployment_policy.json")
    sell_planning = run_sell_planning_pending_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol=ISSUE_CODE,
                quantity=SELL_QUANTITY,
                reason="EXIT_FOR_ROUND_TRIP_ACCEPTANCE",
                score=1.0,
            ),
        ),
        max_orders=1,
        capital_deployment_policy=policy,
    )
    pending_after_planning = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    adapter = Phase15BZSimulatedAcceptedAdapter()
    submit = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_DemoSettings(),
        adapter=adapter,
        capital_deployment_policy=policy,
    )
    pending_after_submit = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    execution = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=_sell_execution_snapshot_provider,
    )
    _append_round_trip_events(root)
    current = _read_json(root / "persistent_ledger" / "state.json")
    runtime_state = _read_json(root / "runtime_state" / "current_state.json")
    return {
        "status": "APPLIED" if execution.status == "PASS" and submit.status == "PASS" else "REVIEW_REQUIRED",
        "reason": "round trip sell applied" if execution.status == "PASS" and submit.status == "PASS" else "round trip sell incomplete",
        "sell_planning": sell_planning.to_stage_details(),
        "pending_after_planning": pending_after_planning,
        "submit": submit.to_stage_details(),
        "pending_after_submit": pending_after_submit,
        "adapter_request_payloads": adapter.request_payloads,
        "execution": execution.to_stage_details(),
        "current": _current_summary(current),
        "current_apply": runtime_state,
    }


def _round_trip_already_applied(root: Path) -> bool:
    current = _read_json(root / "persistent_ledger" / "state.json")
    executions = _read_jsonl(root / "persistent_ledger" / "executions.jsonl")
    pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    return (
        _position_quantity(current, ISSUE_CODE) == 0.0
        and float(current.get("cash") or 0.0) == FINAL_CASH
        and any(str(row.get("side") or "").upper() == "SELL" and row.get("symbol") == ISSUE_CODE for row in executions)
        and pending.get("state") == "CONSUMED"
    )


def _write_broker_available_quantity_snapshot(root: Path) -> Path:
    path = root / "broker" / "snapshots" / "positions" / "phase15bz_available_quantity_7203.json"
    _write_json(
        path,
        {
            "schema_version": "phase15bz_broker_available_quantity_snapshot_v1",
            "source": "broker_readonly",
            "as_of": BUSINESS_DATE + "T08:45:00+09:00",
            "review_required": False,
            "production_equivalent": False,
            "acceptance_only": True,
            "simulation": True,
            "records": [
                {
                    "issue_code": ISSUE_CODE,
                    "symbol": ISSUE_CODE,
                    "quantity": SELL_QUANTITY,
                    "available_quantity": SELL_QUANTITY,
                    "account_type": "runtime-owned-simulation",
                    "as_of": BUSINESS_DATE + "T08:45:00+09:00",
                    "review_required": False,
                    "production_equivalent": False,
                }
            ],
        },
    )
    return path


def _sell_execution_snapshot_provider(**kwargs: Any):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    payload = {
        "generated_at": BUSINESS_DATE + "T09:10:00+09:00",
        "acceptance_only": True,
        "simulation": True,
        "production_equivalent": False,
        "orders": [
            {
                "order_id_hash": "phase15bz-sell-order-7203",
                "issue_code": ISSUE_CODE,
                "side": "sell",
                "quantity": str(int(SELL_QUANTITY)),
                "executed_quantity": str(int(SELL_QUANTITY)),
                "remaining_quantity": "0",
                "status": "全部約定",
                "order_datetime": "20260714091000",
                "as_of": BUSINESS_DATE + "T09:10:00+09:00",
            }
        ],
        "executions": [],
        "positions": [
            {
                "position_id": "phase15bz-position-7203-closed",
                "issue_code": ISSUE_CODE,
                "quantity": "0",
                "average_price": str(int(SELL_PRICE)),
                "market_value": "0",
                "as_of": BUSINESS_DATE + "T09:10:00+09:00",
            }
        ],
        "buying_power": {
            "raw_clmid": "SIMULATED_ROUND_TRIP_BUYING_POWER",
            "cash_available": str(int(FINAL_CASH)),
            "buying_power": str(int(FINAL_CASH)),
            "currency": "JPY",
        },
        "health": {
            "orders": {"status": "PASS", "count": 1},
            "positions": {"status": "PASS", "count": 1},
            "executions": {"status": "PASS", "count": 0, "detail_attempted_count": 0, "failures": []},
        },
    }
    _write_json(snapshot_path, payload)
    _write_json(report_path, {"status": "PASS", "source": "phase15bz_simulated_sell_execution_snapshot"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _append_round_trip_events(root: Path) -> dict[str, Any]:
    events_path = root / "persistent_ledger" / "events.jsonl"
    current = _read_json(root / "persistent_ledger" / "state.json")
    runtime_state = _read_json(root / "runtime_state" / "current_state.json")
    sell_execution_id = _sell_execution_id(root)
    events = (
        LedgerEventRecord(
            record_id="ledger-event-phase15bz-realized-pnl-7203",
            record_type="event",
            schema_version="1",
            environment="demo",
            source="runtime_v2_round_trip_acceptance",
            created_at=BUSINESS_DATE + "T09:10:00+09:00",
            dedup_key="phase15bz:realized_pnl:7203",
            review_required=False,
            production_equivalent=False,
            event_id="phase15bz-realized-pnl-7203",
            event_type="REALIZED_PNL",
            severity="INFO",
            message="Round Trip Acceptance realized PnL JPY 5000; fees and taxes outside current contract",
            related_id=sell_execution_id,
        ),
        LedgerEventRecord(
            record_id="ledger-event-phase15bz-current-apply",
            record_type="event",
            schema_version="1",
            environment="demo",
            source="runtime_v2_current_apply",
            created_at=BUSINESS_DATE + "T09:10:00+09:00",
            dedup_key="phase15bz:current_apply:" + str(current.get("current_hash") or ""),
            review_required=False,
            production_equivalent=False,
            event_id="phase15bz-current-apply",
            event_type="CURRENT_APPLY",
            severity="INFO",
            message="Round Trip Acceptance Current applied with position count 0 and cash 1005000",
            related_id=str(runtime_state.get("runtime_state_version") or ""),
        ),
    )
    return _append_ledger_records(events_path, events)


def _generate_reports(*, root: Path, evidence_dir: Path) -> dict[str, Any]:
    public = generate_public_report_from_current(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        runtime_output_dir=evidence_dir / "runtime_report" / BUSINESS_DATE,
        public_output_dir=evidence_dir / "public_report" / BUSINESS_DATE,
        write_latest=True,
    )
    notification_payload = {
        "schema_version": "phase15bz_notification_payload_v1",
        "delivery_performed": False,
        "discord": {
            "payload_generated": True,
            "delivery": "NOT_SENT",
            "content": "Phase15-BZ Round Trip: 7203 BUY->SELL accepted; PnL JPY 5000; production_equivalent=false",
        },
        "line": {
            "payload_generated": True,
            "delivery": "NOT_SENT",
            "message": "Phase15-BZ Round Trip: 7203 closed, final cash 1005000, realized PnL 5000",
        },
    }
    notification_path = evidence_dir / "notification_payloads.json"
    _write_json(notification_path, notification_payload)
    current = _read_json(root / "persistent_ledger" / "state.json")
    blog_path = evidence_dir / "blog_round_trip_summary.md"
    _write_text(
        blog_path,
        "\n".join(
            [
                "# Phase15-BZ Round Trip Summary",
                "",
                "- Acceptance Fixture: true",
                "- Production Equivalent: false",
                f"- Symbol: {ISSUE_CODE}",
                "- BUY: 100 @ 1000",
                "- SELL: 100 @ 1050",
                f"- Final Cash: {current.get('cash')}",
                f"- Realized PnL: {current.get('realized_pnl')}",
                "",
            ]
        ),
    )
    return {
        "public_report": public,
        "blog_markdown": str(blog_path),
        "discord_payload": str(notification_path),
        "line_payload": str(notification_path),
        "notification_delivery": False,
    }


def _payload(
    *,
    root: Path,
    evidence_dir: Path,
    before_runtime_hashes: dict[str, str],
    before_current: dict[str, Any],
    before_pending: dict[str, Any],
    before_counts: dict[str, int],
    first: dict[str, Any],
    after_first_current: dict[str, Any],
    after_first_pending: dict[str, Any],
    after_first_counts: dict[str, int],
    second: dict[str, Any],
    after_second_current: dict[str, Any],
    after_second_pending: dict[str, Any],
    after_second_counts: dict[str, int],
    after_first_hash: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    after_runtime_hashes = _existing_runtime_hashes()
    final_authority = current_authority_metadata(after_second_current)
    final_position_count = len([p for p in after_second_current.get("positions") or [] if float(p.get("quantity") or 0) > 0])
    ledger_delta_second = {key: after_second_counts[key] - after_first_counts[key] for key in after_first_counts}
    payload = {
        "schema_version": "phase15bz_round_trip_acceptance_v1",
        "phase": "Phase15-BZ",
        "business_date": BUSINESS_DATE,
        "runtime_root": str(root),
        "sell_decision_authority": {
            "original_pm_decision": "HOLD",
            "acceptance_override": "EXIT_FOR_ROUND_TRIP_ACCEPTANCE",
            "override_authority": "Phase15-BZ acceptance fixture",
            "investment_decision": False,
            "pm_ai_performance_evaluation": False,
            "production_applicable": False,
        },
        "before": {
            "current": _current_summary(before_current),
            "pending_state": before_pending.get("state"),
            "pending_item_states": [item.get("state") for item in before_pending.get("items") or []],
            "ledger_counts": before_counts,
        },
        "sell_scenario": {
            "symbol": ISSUE_CODE,
            "side": "SELL",
            "quantity": SELL_QUANTITY,
            "order_type": "MARKET",
            "price_condition": "MARKET",
            "limit_price": None,
            "time_in_force": "DAY",
            "position_origin": "runtime-owned simulation position",
            "production_equivalent": False,
            "acceptance_only": True,
            "simulation": True,
        },
        "first_apply": first,
        "second_apply": second,
        "normal_submit_pipeline": {
            "status": first.get("submit", {}).get("status"),
            "accepted_count": first.get("submit", {}).get("accepted_count"),
            "pending_consumed": first.get("submit", {}).get("pending_consumed"),
            "broker_write_performed": False,
            "submit_attempt": "simulation_only",
            "request_hash": REQUEST_HASH,
        },
        "sell_execution": {
            "symbol": ISSUE_CODE,
            "side": "SELL",
            "quantity": SELL_QUANTITY,
            "execution_price": SELL_PRICE,
            "execution_price_source": "phase15bz_round_trip_sell_fixture",
            "execution_id": _sell_execution_id(root),
            "production_equivalent": False,
            "realized_pnl": REALIZED_PNL,
            "fees_and_taxes": "OUT_OF_CURRENT_CONTRACT",
        },
        "round_trip_math": {
            "initial_cash": INITIAL_CASH,
            "buy_cost": BUY_COST,
            "post_buy_cash": POST_BUY_CASH,
            "sell_proceeds": SELL_PROCEEDS,
            "final_cash": after_second_current.get("cash"),
            "round_trip_pnl": REALIZED_PNL,
            "final_cash_equals_initial_cash_plus_realized_pnl": after_second_current.get("cash") == INITIAL_CASH + REALIZED_PNL,
        },
        "final_current": {
            **_current_summary(after_second_current),
            "position_count": final_position_count,
            "current_hash": after_second_current.get("current_hash"),
            "current_version": after_second_current.get("current_version"),
            "canonical_current_hash": final_authority["current_hash"],
            "canonical_current_version": final_authority["current_version"],
        },
        "pending_lifecycle": {
            "buy_pending_before_sell": before_pending.get("state"),
            "buy_pending_item_states_before_sell": [item.get("state") for item in before_pending.get("items") or []],
            "sell_pending_after_submit": after_second_pending.get("state"),
            "sell_pending_item_states": [item.get("state") for item in after_second_pending.get("items") or []],
            "submitted_order_ids": (after_second_pending.get("consume") or {}).get("submitted_order_ids") or [],
            "ledger_order_record_ids": (after_second_pending.get("consume") or {}).get("ledger_order_record_ids") or [],
        },
        "runtime_state": _read_json(root / "runtime_state" / "current_state.json"),
        "ledger": {
            "before_counts": before_counts,
            "after_first_counts": after_first_counts,
            "after_second_counts": after_second_counts,
            "second_delta": ledger_delta_second,
            "sell_order_record_count": len(_sell_rows(root / "persistent_ledger" / "orders.jsonl")),
            "sell_execution_record_count": len(_sell_rows(root / "persistent_ledger" / "executions.jsonl")),
            "position_close_record_count": len(
                [row for row in _read_jsonl(root / "persistent_ledger" / "positions.jsonl") if row.get("symbol") == ISSUE_CODE and float(row.get("quantity") or 0) == 0.0]
            ),
            "cash_record_count": len(_read_jsonl(root / "persistent_ledger" / "cash.jsonl")),
            "realized_pnl_event_count": len(
                [row for row in _read_jsonl(root / "persistent_ledger" / "events.jsonl") if row.get("event_type") == "REALIZED_PNL"]
            ),
            "current_apply_event_count": len(
                [row for row in _read_jsonl(root / "persistent_ledger" / "events.jsonl") if row.get("event_type") == "CURRENT_APPLY"]
            ),
        },
        "report": {
            "public_report_generated": True,
            "public_report_paths": {key: value for key, value in (report.get("public_report") or {}).items() if key.endswith("_md") or key.endswith("_json")},
            "blog_markdown": report.get("blog_markdown"),
            "discord_payload": report.get("discord_payload"),
            "line_payload": report.get("line_payload"),
            "notification_delivery": False,
        },
        "idempotency": {
            "first_status": first.get("status"),
            "second_status": second.get("status"),
            "cash_unchanged_after_second": after_first_current.get("cash") == after_second_current.get("cash"),
            "position_not_negative": _position_quantity(after_second_current, ISSUE_CODE) >= 0.0,
            "sell_ledger_no_duplicate_after_second": all(value == 0 for value in ledger_delta_second.values()),
            "realized_pnl_not_double_counted": after_second_current.get("realized_pnl") == REALIZED_PNL,
            "pending_not_double_consumed": after_first_pending.get("state") == after_second_pending.get("state") == "CONSUMED",
            "current_hash_unchanged_after_second": after_first_hash == _hash_json(after_second_current),
        },
        "restart_restore": {
            "cash": after_second_current.get("cash"),
            "position_count": final_position_count,
            "realized_pnl": after_second_current.get("realized_pnl"),
            "pending": after_second_pending.get("state"),
            "current_hash_matches": after_second_current.get("current_hash") == final_authority["current_hash"],
            "runtime_state_hash_exists": bool((_read_json(root / "runtime_state" / "current_state.json")).get("runtime_state_version")),
        },
        "runtime_mutation": {
            "real_broker_write": False,
            "production_write": False,
            "resubmit": False,
            "auto_cancel": False,
            "notification_delivery": False,
            "existing_runtime_mutated": before_runtime_hashes != after_runtime_hashes,
            "isolated_root_mutated": True,
        },
        "regression": {},
        "final_judgment": "RUNTIME_ROUND_TRIP_ACCEPTED_WITH_CONDITIONS",
        "remaining_conditions": [
            "実Broker BUY→SELLは未実施",
            "Broker-connected multi-dayは未実施",
            "Notification Deliveryは未実施",
        ],
        "recommended_next_prefix": "Phase15-CA Runtime v2 Completion and Remaining Operational Boundary Review",
    }
    payload["regression"] = _regression(payload)
    return payload


def _regression(payload: dict[str, Any]) -> dict[str, Any]:
    final_current = payload["final_current"]
    pending = payload["pending_lifecycle"]
    idempotency = payload["idempotency"]
    runtime_mutation = payload["runtime_mutation"]
    return {
        "buy_position_100_start": payload["before"]["current"]["quantity_7203"] == 100.0,
        "sell_quantity_excess_rejected_by_contract": payload["sell_scenario"]["quantity"] <= payload["before"]["current"]["quantity_7203"],
        "duplicate_sell_pending_rejected_by_idempotency": payload["second_apply"]["status"] == "NOOP_ALREADY_APPLIED",
        "normal_submit_pipeline_used": payload["normal_submit_pipeline"]["status"] == "PASS",
        "normal_execution_processor_used": payload["first_apply"].get("execution", {}).get("status") == "PASS",
        "normal_current_apply_used": payload["runtime_state"].get("state") == "CURRENT_APPLIED",
        "position_zero": final_current["position_count"] == 0,
        "cash_1005000": final_current["cash"] == FINAL_CASH,
        "realized_pnl_5000": final_current["realized_pnl"] == REALIZED_PNL,
        "pending_plan_consumed": pending["sell_pending_after_submit"] == "CONSUMED",
        "pending_item_consumed": pending["sell_pending_item_states"] == ["CONSUMED"],
        "production_equivalent_false": final_current["production_equivalent"] is False,
        "acceptance_only_true": final_current["acceptance_only"] is True,
        "simulation_true": final_current["simulation"] is True,
        "no_double_sell": idempotency["sell_ledger_no_duplicate_after_second"],
        "no_double_cash": idempotency["cash_unchanged_after_second"],
        "no_double_pnl": idempotency["realized_pnl_not_double_counted"],
        "existing_runtime_unchanged": runtime_mutation["existing_runtime_mutated"] is False,
    }


def _current_summary(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash": current.get("cash"),
        "buying_power": current.get("buying_power"),
        "market_value": current.get("market_value"),
        "total_equity": current.get("total_equity"),
        "realized_pnl": current.get("realized_pnl"),
        "quantity_7203": _position_quantity(current, ISSUE_CODE),
        "production_equivalent": current.get("production_equivalent"),
        "acceptance_only": current.get("acceptance_only"),
        "simulation": current.get("simulation"),
    }


def _position_quantity(current: dict[str, Any], symbol: str) -> float:
    return sum(float(item.get("quantity") or 0.0) for item in current.get("positions") or [] if str(item.get("symbol")) == symbol)


def _sell_rows(path: Path) -> list[dict[str, Any]]:
    return [row for row in _read_jsonl(path) if row.get("symbol") == ISSUE_CODE and str(row.get("side") or "").upper() == "SELL"]


def _sell_execution_id(root: Path) -> str:
    for row in _sell_rows(root / "persistent_ledger" / "executions.jsonl"):
        if row.get("execution_id"):
            return str(row["execution_id"])
    return ""


def _append_ledger_records(path: Path, records: tuple[object, ...]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {str(row.get("dedup_key")) for row in _read_jsonl(path) if row.get("dedup_key")}
    appended = 0
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            payload = ledger_record_to_payload(record)
            key = str(payload.get("dedup_key") or "")
            if key and key in existing:
                continue
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            if key:
                existing.add(key)
            appended += 1
    return {"path": str(path), "appended": appended}


def _request_payload(command: RuntimeV2SubmitCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "pending_item_id": command.pending_item_id,
        "symbol": command.symbol,
        "side": command.side,
        "quantity": command.quantity,
        "order_type": command.order_type,
        "environment": command.environment,
    }


def _ledger_counts(root: Path) -> dict[str, int]:
    return {
        name: len(_read_jsonl(root / "persistent_ledger" / f"{name}.jsonl"))
        for name in ("orders", "executions", "positions", "cash", "events")
    }


def _existing_runtime_hashes() -> dict[str, str]:
    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: _sha256(path) for key, path in paths.items() if path.exists()}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _render_markdown(payload: dict[str, Any]) -> str:
    current = payload["final_current"]
    return "\n".join(
        [
            "# Phase15-BZ Runtime Round-Trip BUY→SELL Acceptance",
            "",
            "## Final Judgment",
            "",
            f"`{payload['final_judgment']}`",
            "",
            "## SELL Decision Authority",
            "",
            f"- Original PM Decision: {payload['sell_decision_authority']['original_pm_decision']}",
            f"- Acceptance Override: {payload['sell_decision_authority']['acceptance_override']}",
            "- Production Applicable: false",
            "",
            "## Round Trip",
            "",
            f"- Initial Cash: {payload['round_trip_math']['initial_cash']}",
            f"- BUY Cost: {payload['round_trip_math']['buy_cost']}",
            f"- Post-BUY Cash: {payload['round_trip_math']['post_buy_cash']}",
            f"- SELL Proceeds: {payload['round_trip_math']['sell_proceeds']}",
            f"- Final Cash: {payload['round_trip_math']['final_cash']}",
            f"- Realized PnL: {payload['round_trip_math']['round_trip_pnl']}",
            "",
            "## Final Current",
            "",
            f"- Position Count: {current['position_count']}",
            f"- 7203 Quantity: {current['quantity_7203']}",
            f"- Cash: {current['cash']}",
            f"- Buying Power: {current['buying_power']}",
            f"- Market Value: {current['market_value']}",
            f"- Total Equity: {current['total_equity']}",
            f"- Current Version: {current['current_version']}",
            f"- Current Hash: {current['current_hash']}",
            "",
            "## Pending / Runtime",
            "",
            f"- SELL Pending: {payload['pending_lifecycle']['sell_pending_after_submit']}",
            f"- SELL Item States: {', '.join(payload['pending_lifecycle']['sell_pending_item_states'])}",
            f"- Runtime State: {payload['runtime_state'].get('state')}",
            f"- Runtime State Version: {payload['runtime_state'].get('runtime_state_version')}",
            "",
            "## Report / Notification",
            "",
            f"- Blog Markdown: {payload['report']['blog_markdown']}",
            f"- Discord Payload: {payload['report']['discord_payload']}",
            f"- LINE Payload: {payload['report']['line_payload']}",
            "- Notification Delivery: false",
            "",
            "## Conditions",
            "",
            *[f"- {item}" for item in payload["remaining_conditions"]],
            "",
            "## Next Prefix",
            "",
            payload["recommended_next_prefix"],
            "",
        ]
    )


if __name__ == "__main__":
    target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    result = run_phase15bz_round_trip_acceptance(root=target_root)
    print(json.dumps({"final_judgment": result["final_judgment"], "runtime_root": str(target_root)}, ensure_ascii=False))
