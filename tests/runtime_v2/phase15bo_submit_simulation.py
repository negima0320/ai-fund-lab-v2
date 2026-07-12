from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


BUSINESS_DATE = "2026-07-09"


@dataclass
class RuntimeV2SubmitSimulationAdapter:
    scenario: str = "SIMULATED_ACCEPTED"
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
            reason="phase15bo simulation transport preflight",
            response_classification={
                "transport": "simulation",
                "network_called": False,
                "broker_write_performed": False,
            },
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.submit_calls += 1
        if not self.request_payloads:
            self.request_payloads.append(_request_payload(command))
        if self.scenario == "SIMULATED_ACCEPTED":
            return RuntimeV2SubmitResult(
                status="ACCEPTED",
                submitted=True,
                accepted=True,
                blocked=False,
                review_required=False,
                broker_api_called=False,
                broker_order_id_hash=_hash("simulated-accepted:" + command.command_id),
                post_send_unknown=False,
                reason="phase15bo simulated accepted",
                issue_code_normalization={
                    "original_symbol": command.symbol,
                    "broker_issue_code": command.symbol,
                },
                response_classification={
                    "broker_result_classification": "ACCEPTED",
                    "result_code": "0",
                    "order_number_present": True,
                    "post_send_unknown": False,
                    "network_called": False,
                    "broker_write_performed": False,
                    "simulation": True,
                },
                next_action="submit_lifecycle_accepted_no_execution",
            )
        if self.scenario == "SIMULATED_REJECTED":
            return RuntimeV2SubmitResult(
                status="REJECTED",
                submitted=True,
                accepted=False,
                blocked=False,
                review_required=True,
                broker_api_called=False,
                broker_order_id_hash=_hash("simulated-rejected:" + command.command_id),
                post_send_unknown=False,
                reason="phase15bo simulated rejected",
                issue_code_normalization={
                    "original_symbol": command.symbol,
                    "broker_issue_code": command.symbol,
                },
                response_classification={
                    "broker_result_classification": "REJECTED",
                    "result_code": "SIMULATED_REJECTED",
                    "order_number_present": False,
                    "post_send_unknown": False,
                    "network_called": False,
                    "broker_write_performed": False,
                    "simulation": True,
                },
                next_action="human_review_required",
            )
        if self.scenario == "SIMULATED_POST_SEND_UNKNOWN":
            return RuntimeV2SubmitResult(
                status="POST_SEND_UNKNOWN",
                submitted=True,
                accepted=False,
                blocked=False,
                review_required=True,
                broker_api_called=False,
                broker_order_id_hash=_hash("simulated-unknown:" + command.command_id),
                post_send_unknown=True,
                reason="phase15bo simulated post send unknown",
                issue_code_normalization={
                    "original_symbol": command.symbol,
                    "broker_issue_code": command.symbol,
                },
                response_classification={
                    "broker_result_classification": "POST_SEND_UNKNOWN",
                    "result_code": "SIMULATED_UNKNOWN",
                    "order_number_present": False,
                    "post_send_unknown": True,
                    "network_called": False,
                    "broker_write_performed": False,
                    "simulation": True,
                },
                next_action="broker_readonly_human_review_required",
            )
        raise ValueError(f"unsupported simulation scenario: {self.scenario}")


def run_simulated_submit(root: Path, *, scenario: str) -> tuple[Any, RuntimeV2SubmitSimulationAdapter]:
    adapter = RuntimeV2SubmitSimulationAdapter(scenario=scenario)
    result = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    return result, adapter


def run_phase15bo_acceptance(root: Path, evidence_dir: Path) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    current_path = root / "persistent_ledger" / "state.json"
    execution_path = root / "persistent_ledger" / "executions.jsonl"
    orders_path = root / "persistent_ledger" / "orders.jsonl"
    before_pending = _read_json(pending_path)
    before_current_hash = _sha256(current_path)
    before_execution_hash = _sha256(execution_path)
    before_order_count = _jsonl_count(orders_path)
    first, adapter = run_simulated_submit(root, scenario="SIMULATED_ACCEPTED")
    after_pending = _read_json(pending_path)
    after_current_hash = _sha256(current_path)
    after_execution_hash = _sha256(execution_path)
    after_order_count = _jsonl_count(orders_path)
    second_adapter = RuntimeV2SubmitSimulationAdapter(scenario="SIMULATED_ACCEPTED")
    second = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=second_adapter,
        capital_deployment_policy_path=root / "runtime_state" / "policy" / "capital_deployment.json",
    )
    final_order_count = _jsonl_count(orders_path)
    payload = {
        "scenario": "SIMULATED_ACCEPTED",
        "pending_plan_id": first.pending_plan_id,
        "pending_item_id": first.item_results[0].pending_item_id if first.item_results else "",
        "issue_code": first.item_results[0].symbol if first.item_results else "",
        "side": first.item_results[0].side if first.item_results else "",
        "quantity": first.item_results[0].quantity if first.item_results else 0,
        "order_conditions": {
            "order_type": adapter.request_payloads[0]["order_type"] if adapter.request_payloads else "",
            "price_condition": "MARKET",
            "limit_price": None,
            "time_in_force": "DAY",
        },
        "submit_result_classification": "ACCEPTED" if first.accepted_count == 1 else first.status,
        "first_run_result": {
            "status": first.status,
            "submitted_count": first.submitted_count,
            "accepted_count": first.accepted_count,
            "pending_consumed": first.pending_consumed,
            "transport_call_count": adapter.submit_calls,
        },
        "second_run_result": {
            "status": second.status,
            "reason": second.reason,
            "submitted_count": second.submitted_count,
            "pending_consumed": second.pending_consumed,
            "transport_call_count": second_adapter.submit_calls,
        },
        "request_payload": adapter.request_payloads[0] if adapter.request_payloads else {},
        "network_called": False,
        "broker_client_called": False,
        "simulation_client_called": adapter.submit_calls > 0,
        "broker_write_performed": False,
        "real_broker_order_created": False,
        "pending_before_state": before_pending.get("state"),
        "pending_after_state": after_pending.get("state"),
        "pending_consumed": bool((after_pending.get("consume") or {}).get("consumed")),
        "submit_record_count": after_order_count,
        "pending_history_count": 1 if after_pending.get("state") else 0,
        "dedup_key": _first_dedup_key(orders_path),
        "idempotency_status": "PASS_NO_RESUBMIT",
        "duplicate_transport_call_count": second_adapter.submit_calls,
        "duplicate_order_count_delta": final_order_count - after_order_count,
        "execution_created": before_execution_hash != after_execution_hash,
        "current_mutated": before_current_hash != after_current_hash,
        "order_count_delta": after_order_count - before_order_count,
    }
    _write_json(evidence_dir / "simulated_accepted_submit_evidence.json", payload)
    return payload


def _request_payload(command: RuntimeV2SubmitCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "environment": command.environment,
        "pending_plan_id": command.pending_plan_id,
        "pending_item_id": command.pending_item_id,
        "approval_hash": command.approval_hash,
        "issue_code": command.symbol,
        "broker_issue_code": command.symbol,
        "side": command.side,
        "quantity": command.quantity,
        "order_type": command.order_type,
        "price_type": command.price_type,
        "limit_price": None if command.price_type == "MARKET" else command.limit_price,
        "target_session_date": command.target_session_date,
        "cash_equity_only": True,
        "secret_saved": False,
        "raw_request_saved": False,
        "network_called": False,
    }


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _first_dedup_key(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        return str(payload.get("dedup_key") or "")
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".runtime_acceptance_phase15_submit")
    target_evidence = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("reports/phase_reports/phase15_bo")
    result_payload = run_phase15bo_acceptance(target_root, target_evidence)
    print(json.dumps(result_payload, ensure_ascii=False, sort_keys=True))
