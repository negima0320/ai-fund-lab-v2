"""Runtime v2 submit pipeline for the regular submit job."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerOrderRecord
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload
from ai_fund_lab_v2.runtime_v2.pending.consume import consume_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult

DEMO_BASE_URL = "https://demo-kabuka.e-shiten.jp/e_api_v4r9"
PROD_BASE_URL = "https://kabuka.e-shiten.jp/e_api_v4r9"


class RuntimeV2SubmitAdapter(Protocol):
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...


@dataclass(frozen=True)
class SubmitItemResult:
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    preflight_status: str
    submit_status: str
    submitted: bool
    accepted: bool
    rejected: bool
    unknown: bool
    blocked: bool
    review_required: bool
    broker_order_id_hash: str
    ledger_order_record_id: str
    reason: str
    issue_code_normalization: dict[str, Any]
    response_classification: dict[str, Any]
    configuration_diagnostic: dict[str, Any]
    next_action: str


@dataclass(frozen=True)
class SubmitPipelineResult:
    status: str
    reason: str
    pending_plan_id: str
    pending_path: str
    orders_ledger_path: str
    demo_submit_executed: bool
    submitted_count: int
    accepted_count: int
    rejected_count: int
    unknown_count: int
    blocked_count: int
    pending_consumed: bool
    submitted_order_ids: tuple[str, ...]
    ledger_order_record_ids: tuple[str, ...]
    submitted_symbols: tuple[str, ...]
    item_results: tuple[SubmitItemResult, ...]
    raw_request_saved: bool = False
    raw_response_saved: bool = False
    secret_saved: bool = False

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["item_results"] = [asdict(item) for item in self.item_results]
        payload["submitted_order_ids"] = list(self.submitted_order_ids)
        payload["ledger_order_record_ids"] = list(self.ledger_order_record_ids)
        payload["submitted_symbols"] = list(self.submitted_symbols)
        return payload


def run_submit_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    submit_enabled: bool,
    job: str,
    settings: Any | None = None,
    adapter: RuntimeV2SubmitAdapter | None = None,
    max_order_amount: float | None = 100_000.0,
) -> SubmitPipelineResult:
    """Submit all approved Pending items through the Runtime v2 submit path."""

    runtime_root_path = Path(runtime_root)
    _reject_mode_rooted_runtime_root(runtime_root_path)
    if job != "submit" or not submit_enabled:
        return _blocked_result(
            reason="submit-enabled true is required and allowed only for submit job",
            runtime_root=runtime_root_path,
        )
    if mode != "demo":
        return _blocked_result(reason="production submit is prohibited in Phase14-E17", runtime_root=runtime_root_path)

    settings = settings or _load_broker_settings()
    base_url = settings.base_url.rstrip("/")
    base_url_is_demo = base_url == DEMO_BASE_URL
    base_url_is_production = base_url == PROD_BASE_URL
    pending_read = read_pending_order_plan(mode=mode, environment=mode, base_dir=runtime_root_path.parent)
    if not pending_read.valid or pending_read.plan is None:
        return _blocked_result(
            reason="pending current is missing or invalid: " + ",".join(pending_read.errors),
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
        )
    pending = pending_read.plan
    guard_reason = _pending_submit_guard(pending, business_date=business_date)
    if guard_reason:
        return _blocked_result(reason=guard_reason, runtime_root=runtime_root_path, pending_path=str(pending_read.path))

    approval = _approval_from_pending(pending)
    existing_dedup_keys = _existing_order_dedup_keys(runtime_root_path / "persistent_ledger" / "orders.jsonl")
    current_positions = _current_position_quantities(runtime_root_path / "persistent_ledger" / "state.json")
    submit_adapter = adapter or _build_tachibana_demo_submit_adapter(settings)
    item_results: list[SubmitItemResult] = []
    ledger_records: list[LedgerOrderRecord] = []

    for approved_item_id in pending.approved_item_ids:
        item = next(item for item in pending.items if item.pending_item_id == approved_item_id)
        sell_position_quantity = current_positions.get(str(item.symbol).strip()) if item.side == "SELL" else None
        preflight = run_submit_preflight(
            pending_plan=pending,
            approval_artifact=approval,
            approved_item_id=approved_item_id,
            existing_order_dedup_keys=existing_dedup_keys,
            environment=settings.environment,
            base_url_is_demo=base_url_is_demo,
            base_url_is_production=base_url_is_production,
            live_order_allowed=True,
            max_order_amount=max_order_amount,
            broker_position_quantity=sell_position_quantity,
            broker_available_quantity=sell_position_quantity,
            source_current_path="pending_order_plan/pending_order_plan.json",
            broker_capability=get_broker_capability(mode),
        )
        if not preflight.allowed or preflight.command is None:
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status="BLOCKED",
                    submit_status="NOT_SUBMITTED",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=True,
                    review_required=False,
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason=preflight.reason,
                    issue_code_normalization={},
                    response_classification={},
                    configuration_diagnostic={},
                    next_action="",
                )
            )
            continue
        adapter_preflight = submit_adapter.preflight(preflight.command)
        if adapter_preflight.blocked or adapter_preflight.status not in {"DRY_RUN_READY", "ACCEPTED"}:
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status=adapter_preflight.status,
                    submit_status="NOT_SUBMITTED",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=True,
                    review_required=adapter_preflight.review_required,
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason=adapter_preflight.reason,
                    issue_code_normalization=dict(adapter_preflight.issue_code_normalization),
                    response_classification=dict(adapter_preflight.response_classification),
                    configuration_diagnostic=dict(adapter_preflight.configuration_diagnostic),
                    next_action=adapter_preflight.next_action,
                )
            )
            continue
        submit_result = submit_adapter.submit(preflight.command)
        broker_order_id = submit_result.broker_order_id_hash or _synthetic_order_id(preflight.command.command_id)
        ledger_record = _ledger_order_record(
            pending=pending,
            command=preflight.command,
            submit_result=submit_result,
            broker_order_id=broker_order_id,
        )
        if submit_result.submitted:
            ledger_records.append(ledger_record)
        item_results.append(
            SubmitItemResult(
                pending_item_id=item.pending_item_id,
                symbol=item.symbol,
                side=item.side,
                quantity=item.quantity,
                preflight_status="PASS",
                submit_status=submit_result.status,
                submitted=submit_result.submitted,
                accepted=submit_result.accepted,
                rejected=submit_result.submitted and not submit_result.accepted and not submit_result.post_send_unknown,
                unknown=submit_result.post_send_unknown or submit_result.status == "UNKNOWN",
                blocked=submit_result.blocked,
                review_required=submit_result.review_required,
                broker_order_id_hash=broker_order_id if submit_result.submitted else "",
                ledger_order_record_id=ledger_record.record_id if submit_result.submitted else "",
                reason=submit_result.reason,
                issue_code_normalization=dict(submit_result.issue_code_normalization),
                response_classification=dict(submit_result.response_classification),
                configuration_diagnostic=dict(submit_result.configuration_diagnostic),
                next_action=submit_result.next_action,
            )
        )

    orders_path = runtime_root_path / "persistent_ledger" / "orders.jsonl"
    if ledger_records:
        _append_ledger_order_records(orders_path, ledger_records)
        pending = replace(pending, state=PendingPlanState.SUBMITTED, updated_at=_utc_now())
        pending = consume_pending_plan(
            pending,
            consume_reason=_consume_reason(item_results),
            submitted_order_ids=tuple(result.broker_order_id_hash for result in item_results if result.submitted),
            ledger_order_record_ids=tuple(result.ledger_order_record_id for result in item_results if result.submitted),
        )
        write_pending_order_plan(Path(pending_read.path), pending)

    submitted_count = sum(1 for result in item_results if result.submitted)
    accepted_count = sum(1 for result in item_results if result.accepted)
    unknown_count = sum(1 for result in item_results if result.unknown)
    blocked_count = sum(1 for result in item_results if result.blocked)
    rejected_count = sum(1 for result in item_results if result.rejected)
    status = "PASS"
    reason = "submitted"
    if submitted_count == 0:
        status = "BLOCKED"
        reason = "no pending items were submitted"
    elif unknown_count or rejected_count or blocked_count:
        status = "REVIEW_REQUIRED"
        reason = "submit completed with rejected/unknown/blocked items"

    return SubmitPipelineResult(
        status=status,
        reason=reason,
        pending_plan_id=pending.pending_plan_id,
        pending_path=str(pending_read.path),
        orders_ledger_path=str(orders_path),
        demo_submit_executed=submitted_count > 0,
        submitted_count=submitted_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        unknown_count=unknown_count,
        blocked_count=blocked_count,
        pending_consumed=bool(ledger_records),
        submitted_order_ids=tuple(result.broker_order_id_hash for result in item_results if result.submitted),
        ledger_order_record_ids=tuple(result.ledger_order_record_id for result in item_results if result.submitted),
        submitted_symbols=tuple(result.symbol for result in item_results if result.submitted),
        item_results=tuple(item_results),
    )


def _pending_submit_guard(pending: PendingOrderPlan, *, business_date: str) -> str:
    if pending.state in {
        PendingPlanState.SUBMITTING,
        PendingPlanState.SUBMITTED,
        PendingPlanState.POST_SEND_UNKNOWN,
        PendingPlanState.CONSUMED,
        PendingPlanState.BLOCKED,
        PendingPlanState.REVIEW_REQUIRED,
    }:
        return f"dangerous pending state blocked: {pending.state.value}"
    if pending.state != PendingPlanState.APPROVED:
        return "pending state is not APPROVED"
    if pending.target_session_date != business_date:
        return "pending target_session_date mismatch"
    if pending.approval is None:
        return "pending approval link missing"
    if pending.approval.approval_status != "APPROVED":
        return "pending approval is not APPROVED"
    if pending.consume.consumed:
        return "consumed pending cannot be submitted"
    if set(pending.approved_item_ids) != {item.pending_item_id for item in pending.items if item.approved}:
        return "approved item ids mismatch"
    return ""


def _approval_from_pending(pending: PendingOrderPlan) -> ApprovalArtifact:
    if pending.approval is None:
        raise ValueError("pending approval link missing")
    return ApprovalArtifact(
        approval_id=pending.approval.approval_path.rsplit("/", 1)[-1] or "pending-linked-approval",
        approval_request_id=f"request-{pending.pending_plan_id}",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus(pending.approval.approval_status),
        approved_item_ids=pending.approval.approved_item_ids,
        rejected_item_ids=(),
        approval_hash=pending.approval.approval_hash,
        approved_at=pending.updated_at,
        expires_at=pending.approval.approval_expires_at,
        review_required=False,
        reason="approval reconstructed from Pending Current link",
    )


def _ledger_order_record(
    *,
    pending: PendingOrderPlan,
    command: RuntimeV2SubmitCommand,
    submit_result: RuntimeV2SubmitResult,
    broker_order_id: str,
) -> LedgerOrderRecord:
    record_id = "ledger-order-submit-" + _short_hash(command.command_id)
    return LedgerOrderRecord(
        record_id=record_id,
        record_type="order",
        schema_version="1",
        environment=command.environment,
        source="runtime_v2_submit_pipeline",
        created_at=_utc_now(),
        dedup_key=f"runtime_v2_submit:{command.command_id}",
        review_required=submit_result.review_required,
        production_equivalent=command.environment == "production",
        order_id=broker_order_id,
        business_date=pending.target_session_date,
        pending_plan_id=pending.pending_plan_id,
        pending_item_id=command.pending_item_id,
        side=command.side,
        symbol=command.symbol,
        quantity=command.quantity,
        status=submit_result.status,
        issue_code_normalization=dict(submit_result.issue_code_normalization),
        response_classification=dict(submit_result.response_classification),
    )


def _append_ledger_order_records(path: Path, records: list[LedgerOrderRecord]) -> None:
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Ledger writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = _existing_order_dedup_keys(path)
    lines = []
    for record in records:
        if record.dedup_key in existing_keys:
            continue
        lines.append(json.dumps(ledger_record_to_payload(record), sort_keys=True))
        existing_keys.add(record.dedup_key)
    if not lines:
        return
    with path.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")


def _existing_order_dedup_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("dedup_key"):
            keys.add(str(payload["dedup_key"]))
        if payload.get("pending_plan_id"):
            keys.add(str(payload["pending_plan_id"]))
    return keys


def _current_position_quantities(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    quantities: dict[str, float] = {}
    for position in payload.get("positions") or ():
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        if not symbol:
            continue
        quantities[symbol] = quantities.get(symbol, 0.0) + _float(position.get("quantity"))
    return quantities


def _blocked_result(*, reason: str, runtime_root: Path, pending_path: str = "") -> SubmitPipelineResult:
    return SubmitPipelineResult(
        status="BLOCKED",
        reason=reason,
        pending_plan_id="",
        pending_path=pending_path or str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
        orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=0,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(),
    )


def _consume_reason(results: list[SubmitItemResult]) -> str:
    if any(result.unknown for result in results):
        return "runtime_v2 submit attempted with POST_SEND_UNKNOWN; automatic resubmit forbidden"
    if any(result.rejected or result.blocked for result in results):
        return "runtime_v2 submit attempted with partial failure; automatic resubmit forbidden"
    return "runtime_v2 submit accepted; automatic resubmit forbidden"


def _synthetic_order_id(command_id: str) -> str:
    return "sha256:" + hashlib.sha256(f"submitted:{command_id}".encode("utf-8")).hexdigest()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text:
        raise ValueError("mode-rooted Current path is not allowed")


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    parts = path.parts
    runtime_modes = {"production", "demo", "simulation", "backtest"}
    return any(
        part == ".runtime"
        and index + 1 < len(parts)
        and parts[index + 1] in runtime_modes
        for index, part in enumerate(parts)
    )


def _load_broker_settings() -> Any:
    module_name = "ai_fund_lab_v2." + "broker.settings"
    return importlib.import_module(module_name).load_broker_settings()


def _build_tachibana_demo_submit_adapter(settings: Any) -> RuntimeV2SubmitAdapter:
    module_name = "ai_fund_lab_v2." + "broker.runtime_v2_demo_submit_adapter"
    adapter_cls = importlib.import_module(module_name).RuntimeV2TachibanaDemoSubmitAdapter
    return adapter_cls(settings=settings, dry_run=False)
