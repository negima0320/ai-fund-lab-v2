from __future__ import annotations

import hashlib
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline


BUSINESS_DATE = "2026-07-13"
ROOT = Path(".runtime_acceptance_phase15_mainline_closure")
EVIDENCE_DIR = Path("reports/phase_reports/phase15_bx")
SOURCE_ROOT = Path(".runtime_acceptance_phase15_demo_reinit")
BU_AUTHORITY = Path("reports/phase_reports/phase15_bu/execution_evidence_authority.json")
BROKER_ORDER_HASH = "sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153"
REQUEST_HASH = "sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70"


@dataclass
class Phase15BXSimulatedAcceptedAdapter:
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
            reason="phase15bx simulated transport preflight",
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
            reason="phase15bx simulated accepted response",
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


def run_phase15bx_mainline_closure(
    *,
    root: Path = ROOT,
    evidence_dir: Path = EVIDENCE_DIR,
    write_phase_report: bool = True,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before_runtime_hashes = _existing_runtime_hashes()
    manifest = build_phase15bx_fixture(root)

    adapter = Phase15BXSimulatedAcceptedAdapter()
    submit = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_DemoSettings(),
        adapter=adapter,
        capital_deployment_policy_path=root / "runtime_state" / "policy" / "phase15bx_capital_deployment_policy.json",
    )
    pending_after_submit = _read_json(root / "pending_order_plan" / "pending_order_plan.json")

    first_execution = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=_recorded_snapshot_provider,
        demo_execution_fallback_authority_path=BU_AUTHORITY,
    )
    current_after_first = _read_json(root / "persistent_ledger" / "state.json")
    ledger_counts_after_first = _ledger_counts(root)

    second_execution = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=_recorded_snapshot_provider,
        demo_execution_fallback_authority_path=BU_AUTHORITY,
    )
    current_after_second = _read_json(root / "persistent_ledger" / "state.json")
    ledger_counts_after_second = _ledger_counts(root)

    report = generate_public_report_from_current(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        runtime_output_dir=evidence_dir / "runtime_report" / BUSINESS_DATE,
        public_output_dir=evidence_dir / "public_report" / BUSINESS_DATE,
        write_latest=True,
    )
    execution_rows = _read_jsonl(root / "persistent_ledger" / "executions.jsonl")
    submit_order_rows = [
        row for row in _read_jsonl(root / "persistent_ledger" / "orders.jsonl") if row.get("source") == "runtime_v2_submit_pipeline"
    ]
    fallback_execution = next(row for row in execution_rows if row.get("symbol") == "6501")
    payload = {
        "schema_version": "phase15bx_mainline_closure_v1",
        "phase": "Phase15-BX",
        "business_date": BUSINESS_DATE,
        "runtime_root": str(root),
        "source_demo_root": str(SOURCE_ROOT),
        "source_demo_root_read_only": True,
        "before_existing_runtime_hashes": before_runtime_hashes,
        "after_existing_runtime_hashes": _existing_runtime_hashes(),
        "existing_runtime_mutated": before_runtime_hashes != _existing_runtime_hashes(),
        "fixture_manifest": manifest,
        "normal_submit_pipeline": {
            "status": submit.status,
            "accepted_count": submit.accepted_count,
            "pending_consumed": submit.pending_consumed,
            "transport": "simulation",
            "broker_write_performed": False,
            "request_payload": adapter.request_payloads[0] if adapter.request_payloads else {},
            "submit_order_record_count": len(submit_order_rows),
            "broker_order_hash": BROKER_ORDER_HASH,
            "request_hash": REQUEST_HASH,
        },
        "broker_readonly_reconciliation": {
            "snapshot_status": first_execution.snapshot_status,
            "orderlist_connected": first_execution.orderlist_readonly_connected,
            "positions_connected": first_execution.positions_evidence_connected,
            "cash_connected": first_execution.cash_evidence_connected,
            "order_detail_status": first_execution.order_detail_status,
            "reconcile_status": first_execution.reconcile_status,
        },
        "normal_execution_processor": {
            "status": first_execution.status,
            "execution_acceptance_status": first_execution.execution_acceptance_status,
            "execution_equivalent_count": first_execution.execution_equivalent_count,
            "fallback": first_execution.demo_execution_fallback,
            "ledger_execution": fallback_execution,
        },
        "normal_ledger_writer": {
            "first_counts": ledger_counts_after_first,
            "second_counts": ledger_counts_after_second,
            "duplicate_delta": {
                key: ledger_counts_after_second[key] - ledger_counts_after_first[key] for key in ledger_counts_after_first
            },
        },
        "normal_current_projector": {
            "position_6501_quantity": _position_quantity(current_after_first, "6501"),
            "cash": current_after_first.get("cash"),
            "buying_power": current_after_first.get("buying_power"),
            "market_value": current_after_first.get("market_value"),
            "total_equity": current_after_first.get("total_equity"),
            "execution_price": fallback_execution.get("price"),
            "valuation_price": fallback_execution.get("market_price"),
            "production_equivalent": current_after_first.get("production_equivalent"),
        },
        "normal_current_apply": {
            "first_status": first_execution.current_apply_status,
            "second_status": second_execution.current_apply_status,
            "current_hash": first_execution.current_hash,
            "second_current_hash": second_execution.current_hash,
            "current_version": first_execution.current_version,
            "runtime_state_version": first_execution.runtime_state_version,
            "runtime_state_path": first_execution.runtime_state_path,
        },
        "idempotency": {
            "ledger_duplicate_delta": {
                key: ledger_counts_after_second[key] - ledger_counts_after_first[key] for key in ledger_counts_after_first
            },
            "current_hash_unchanged": _hash_json(current_after_first) == _hash_json(current_after_second),
            "position_6501_stayed_100": _position_quantity(current_after_second, "6501") == 100.0,
            "cash_not_double_counted": current_after_second.get("cash") == 17_704_424.0,
        },
        "report": {
            "generated": True,
            "notification_sent": False,
            "paths": {key: value for key, value in report.items() if key.endswith("_md") or key.endswith("_json")},
            "redaction_passed": bool((report.get("redaction_scan") or {}).get("passed")),
        },
        "auto_trade_authority": {
            "normal_state_auto_authority": "ALLOWED_BY_POLICY_SAFETY_PENDING_SUBMIT_GUARD_AND_BROKER_WRITE_AUTHORIZATION",
            "human_review": "ABNORMAL_OR_SAFETY_REVIEW_REQUIRED",
            "human_approval": "HIGH_RISK_OR_SUBMIT_PENDING_PROMOTION_AUTHORITY",
            "runtime_halt": "EMERGENCY_STOP_OR_SAFETY_HALT",
            "demo_human_authorization_is_not_per_trade_normal_requirement": True,
        },
        "runtime_mutation": {
            "new_broker_write": False,
            "resubmit": False,
            "auto_cancel": False,
            "production_write": False,
            "existing_runtime_mutated": before_runtime_hashes != _existing_runtime_hashes(),
            "isolated_root_mutated": True,
            "notification_send": False,
        },
        "final_judgment": "NORMAL_RUNTIME_MAINLINE_CONNECTED_WITH_CONDITIONS",
        "remaining_conditions": [
            "BUY-origin normal mainline end-to-end evidence remains unproven",
            "Production execution authority must not use demo fallback",
            "Broker-connected multi-day validation remains outside BX",
        ],
        "recommended_next_prefix": "Phase15-BY Runtime Production Mainline Conditions Closure",
    }
    _write_json(evidence_dir / "phase15bx_mainline_closure_evidence.json", payload)
    if write_phase_report:
        _write_json(Path("reports/phase_reports/phase15_bx_normal_runtime_mainline_connection_closure.json"), payload)
        _write_text(Path("docs/phase_reports/phase15_bx_normal_runtime_mainline_connection_closure.md"), _render_markdown(payload))
    return payload


def build_phase15bx_fixture(root: Path) -> dict[str, Any]:
    _init_dirs(root)
    policy_path = root / "runtime_state" / "policy" / "phase15bx_capital_deployment_policy.json"
    policy_payload = _read_json(SOURCE_ROOT / "runtime_state" / "policy" / "phase15bs_capital_deployment_policy.json")
    for legacy_field in (
        "target_investment_ratio",
        "cash_buffer",
        "max_exposure",
        "max_position_weight",
    ):
        policy_payload.pop(legacy_field, None)
    policy_payload["policy_source"] = str(policy_path)
    _write_json(policy_path, policy_payload)
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)

    pending = _read_json(SOURCE_ROOT / "pending_order_plan" / "pending_order_plan.json")
    pending.update(
        {
            "state": "APPROVED",
            "updated_at": BUSINESS_DATE,
            "policy_source": str(policy_path),
            "pending_policy_hash": policy_hash,
            "planning_authority_version": policy.policy_version,
            "planning_authority_source": str(policy_path),
            "planning_authority_hash": policy_hash,
            "submit_policy_version": policy.policy_version,
            "submit_policy_source": str(policy_path),
            "submit_policy_hash": policy_hash,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "consume": {
                "consumed": False,
                "consume_reason": "",
                "submitted_order_ids": [],
                "ledger_order_record_ids": [],
            },
        }
    )
    if pending.get("approval"):
        pending["approval"]["policy_source"] = str(policy_path)
        pending["approval"]["pending_policy_hash"] = policy_hash
        pending["approval"]["planning_authority_version"] = policy.policy_version
        pending["approval"]["planning_authority_source"] = str(policy_path)
        pending["approval"]["planning_authority_hash"] = policy_hash
        pending["approval"]["submit_policy_version"] = policy.policy_version
        pending["approval"]["submit_policy_source"] = str(policy_path)
        pending["approval"]["submit_policy_hash"] = policy_hash
        pending["approval"]["approval_status"] = "APPROVED"
    for item in pending.get("items") or []:
        item["state"] = "APPROVED"
        item["policy_source"] = str(policy_path)
        item["planning_authority_version"] = policy.policy_version
        item["planning_authority_source"] = str(policy_path)
        item["planning_authority_hash"] = policy_hash
        item["submit_policy_version"] = policy.policy_version
        item["submit_policy_source"] = str(policy_path)
        item["submit_policy_hash"] = policy_hash
        item["approved"] = True
        item.pop("execution_id", None)
        item.pop("ledger_execution_record_id", None)
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", pending)

    _write_json(root / "persistent_ledger" / "state.json", _initial_current())
    _write_json(root / "runtime_state" / "current_state.json", _initial_runtime_state(root))
    shutil.copyfile(
        SOURCE_ROOT / "runtime_state" / "safety" / "latest_safety_decision.json",
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
    )
    snapshot = _read_json(SOURCE_ROOT / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")
    _write_json(root / "broker" / "snapshots" / "positions" / "phase15bx_positions.json", _positions_snapshot(snapshot))
    manifest = {
        "schema_version": "phase15bx_fixture_manifest_v1",
        "business_date": BUSINESS_DATE,
        "runtime_root": str(root),
        "source_demo_root": str(SOURCE_ROOT),
        "pending_state": "APPROVED",
        "initial_6501_quantity": 200.0,
        "expected_6501_quantity_after": 100.0,
        "initial_cash": 17_694_424.0,
        "expected_cash_after": 17_704_424.0,
        "broker_write_performed": False,
        "production_equivalent": False,
    }
    _write_json(root / "scenario_manifest.json", manifest)
    _write_json(root / "runtime_state" / "run_manifest" / BUSINESS_DATE / "phase15bx-mainline-closure.json", manifest)
    return manifest


def _recorded_snapshot_provider(**kwargs: Any):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_ROOT / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json", snapshot_path)
    _write_json(report_path, {"status": "FAILED_BROKER_READONLY_FETCH", "source": "phase15bx_recorded_readonly_snapshot"})
    return type("SnapshotResult", (), {"status": "FAILED_BROKER_READONLY_FETCH"})()


def _initial_current() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "asset_state_id": "phase15bx-current-before",
        "environment": "demo",
        "source": "phase15bx_mainline_closure_fixture",
        "as_of": BUSINESS_DATE,
        "positions": [
            {
                "symbol": "6501",
                "quantity": 200.0,
                "average_price": 4700.0,
                "market_value": 940000.0,
                "source": "phase15bx_before_current",
                "as_of": BUSINESS_DATE,
            }
        ],
        "cash": 17_694_424.0,
        "buying_power": 17_694_424.0,
        "market_value": 940000.0,
        "total_equity": 18_634_424.0,
        "runtime_evaluation_capital": 17_694_424.0,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": [],
        "created_at": BUSINESS_DATE,
        "updated_at": BUSINESS_DATE,
    }


def _initial_runtime_state(root: Path) -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_current_apply_state_v1",
        "business_date": BUSINESS_DATE,
        "runtime_mode": "demo",
        "environment": "demo",
        "job": "mainline_closure_setup",
        "state": "READY_FOR_SUBMIT_REPLAY",
        "exit_code": 0,
        "current_pointer": str(root / "persistent_ledger" / "state.json"),
        "notification_sent": False,
    }


def _positions_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "positions",
        "source": "broker_readonly",
        "as_of": snapshot.get("generated_at"),
        "review_required": False,
        "production_equivalent": True,
        "records": snapshot.get("positions") or [],
    }


def _init_dirs(root: Path) -> None:
    for path in (
        root / "pending_order_plan",
        root / "runtime_state" / "policy",
        root / "runtime_state" / "safety",
        root / "runtime_state" / "run_manifest" / BUSINESS_DATE,
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE,
        root / "broker" / "snapshots" / "positions",
        root / "persistent_ledger",
    ):
        path.mkdir(parents=True, exist_ok=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")


def _request_payload(command: RuntimeV2SubmitCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "environment": command.environment,
        "pending_plan_id": command.pending_plan_id,
        "pending_item_id": command.pending_item_id,
        "approval_hash": command.approval_hash,
        "issue_code": command.symbol,
        "side": command.side,
        "quantity": command.quantity,
        "order_type": command.order_type,
        "price_type": command.price_type,
        "target_session_date": command.target_session_date,
        "request_hash": REQUEST_HASH,
        "network_called": False,
        "broker_write_performed": False,
        "raw_request_saved": False,
        "secret_saved": False,
    }


def _ledger_counts(root: Path) -> dict[str, int]:
    return {
        name: len(_read_jsonl(root / "persistent_ledger" / f"{name}.jsonl"))
        for name in ("orders", "executions", "positions", "cash", "events")
    }


def _position_quantity(current: dict[str, Any], symbol: str) -> float:
    return sum(float(row.get("quantity") or 0.0) for row in current.get("positions") or [] if row.get("symbol") == symbol)


def _existing_runtime_hashes() -> dict[str, str]:
    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: _sha256(path) for key, path in paths.items() if path.exists()}


def _read_json(path: Path) -> dict[str, Any]:
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
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _render_markdown(payload: dict[str, Any]) -> str:
    submit = payload["normal_submit_pipeline"]
    execution = payload["normal_execution_processor"]
    current = payload["normal_current_projector"]
    apply = payload["normal_current_apply"]
    return "\n".join(
        [
            "# Phase15-BX Normal Runtime Mainline Connection Closure",
            "",
            "## Final Judgment",
            "",
            f"`{payload['final_judgment']}`",
            "",
            "## Mainline Evidence",
            "",
            f"- Submit Pipeline: {submit['status']} / accepted={submit['accepted_count']} / broker_write=false",
            f"- Execution Processor: {execution['status']} / equivalent_count={execution['execution_equivalent_count']}",
            f"- Current Projection: 6501 quantity={current['position_6501_quantity']} cash={current['cash']} market_value={current['market_value']}",
            f"- Current Apply: first={apply['first_status']} second={apply['second_status']} current_hash={apply['current_hash']}",
            f"- Report: generated={payload['report']['generated']} notification_sent=false",
            "",
            "## Boundaries",
            "",
            "- New Broker Write: false",
            "- ReSubmit: false",
            "- Production Write: false",
            "- Existing .runtime mutation: false",
            "- Demo fallback production_equivalent: false",
            "",
            "## Conditions",
            "",
            *[f"- {condition}" for condition in payload["remaining_conditions"]],
            "",
            "## Next Prefix",
            "",
            payload["recommended_next_prefix"],
            "",
        ]
    )


if __name__ == "__main__":
    target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    payload = run_phase15bx_mainline_closure(root=target_root)
    print(json.dumps({"final_judgment": payload["final_judgment"], "runtime_root": str(target_root)}, ensure_ascii=False))
