from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.operations.io import stable_hash, utc_now_iso, write_json


PERSISTENT_LEDGER_DIR = "persistent_ledger"
JSONL_FILES = (
    "orders.jsonl",
    "executions.jsonl",
    "positions.jsonl",
    "cash_history.jsonl",
    "events.jsonl",
    "migrations.jsonl",
)

_PROHIBITED_KEYS = {
    "raw_request",
    "raw_response",
    "raw_request_payload",
    "raw_response_payload",
    "request_payload",
    "response_payload",
    "secret",
    "token",
    "session",
    "url",
    "auth_id",
    "account_id",
    "customer_id",
    "broker_order_id",
    "order_id",
    "execution_id",
}


def append_order(*, root: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    payload = _safe_record("persistent_order", record)
    payload["dedup_key"] = _dedup_key(payload, preferred=("item_id", "order_hash", "broker_order_id_hash"))
    appended = _append_jsonl_dedup(ledger_root / "orders.jsonl", payload, dedup_key=payload["dedup_key"])
    return _write_state_and_result(root=Path(root), record=payload, appended=appended, file_name="orders.jsonl")


def append_execution(*, root: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    payload = _safe_record("persistent_execution", record)
    payload["dedup_key"] = _dedup_key(payload, preferred=("execution_key", "execution_hash", "execution_id_hash"))
    appended = _append_jsonl_dedup(ledger_root / "executions.jsonl", payload, dedup_key=payload["dedup_key"])
    return _write_state_and_result(root=Path(root), record=payload, appended=appended, file_name="executions.jsonl")


def append_position_state(*, root: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    payload = _safe_record("persistent_position_state", record)
    payload["position_key"] = str(payload.get("position_key") or _position_key(payload))
    payload["dedup_key"] = _dedup_key(payload, preferred=("item_id", "position_hash", "position_key"))
    appended = _append_jsonl_dedup(ledger_root / "positions.jsonl", payload, dedup_key=payload["dedup_key"])
    return _write_state_and_result(root=Path(root), record=payload, appended=appended, file_name="positions.jsonl")


def append_cash_state(*, root: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    payload = _safe_record("persistent_cash_state", record)
    payload["dedup_key"] = _dedup_key(payload, preferred=("cash_state_key", "item_id", "cash_hash"))
    appended = _append_jsonl_dedup(ledger_root / "cash_history.jsonl", payload, dedup_key=payload["dedup_key"])
    return _write_state_and_result(root=Path(root), record=payload, appended=appended, file_name="cash_history.jsonl")


def append_event(*, root: Path, record: dict[str, Any]) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    payload = _safe_record("persistent_lifecycle_event", record)
    payload["dedup_key"] = _dedup_key(payload, preferred=("event_id", "event_hash", "item_id"))
    appended = _append_jsonl_dedup(ledger_root / "events.jsonl", payload, dedup_key=payload["dedup_key"])
    return _write_state_and_result(root=Path(root), record=payload, appended=appended, file_name="events.jsonl")


def summarize_persistent_ledger(*, root: Path) -> dict[str, Any]:
    ledger_root = _ensure_ledger_root(root)
    orders = _read_jsonl(ledger_root / "orders.jsonl")
    executions = _read_jsonl(ledger_root / "executions.jsonl")
    positions = _read_jsonl(ledger_root / "positions.jsonl")
    cash_history = _read_jsonl(ledger_root / "cash_history.jsonl")
    events = _read_jsonl(ledger_root / "events.jsonl")
    migrations = _read_jsonl(ledger_root / "migrations.jsonl")
    current_positions = _current_positions(positions)
    latest_cash = cash_history[-1] if cash_history else {}
    state = {
        "artifact_type": "persistent_ledger_state",
        "schema_version": "persistent_ledger_state_v1",
        "generated_at": utc_now_iso(),
        "ledger_root": str(ledger_root),
        "orders_count": len(orders),
        "executions_count": len(executions),
        "position_history_count": len(positions),
        "cash_history_count": len(cash_history),
        "event_count": len(events),
        "migration_count": len(migrations),
        "current_positions": current_positions,
        "current_position_count": len(current_positions),
        "current_market_value": str(sum(_decimal(row.get("market_value")) for row in current_positions)),
        "current_cash": {
            "cash_available": str(latest_cash.get("cash_available") or ""),
            "buying_power": str(latest_cash.get("buying_power") or ""),
            "currency": str(latest_cash.get("currency") or "JPY"),
            "source": str(latest_cash.get("source") or ""),
            "environment": str(latest_cash.get("environment") or ""),
        },
        "environments": sorted({str(row.get("environment")) for row in orders + executions + positions + cash_history + events if row.get("environment")}),
        "sources": sorted({str(row.get("source")) for row in orders + executions + positions + cash_history + events if row.get("source")}),
        "demo_production_common_storage": True,
        "runtime_reference_switched": False,
        "demo_ledger_legacy_deleted": False,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }
    return sanitize_mapping(state)


def read_persistent_ledger_state(root: Path) -> dict[str, Any]:
    state_path = _ledger_root(Path(root)) / "state.json"
    if not state_path.exists():
        return _empty_reader_state(root=Path(root), state_missing=True)
    return _reader_safe(json.loads(state_path.read_text(encoding="utf-8")) | {"state_missing": False})


def get_current_positions(root: Path) -> dict[str, Any]:
    state = read_persistent_ledger_state(root)
    positions = [_position_reader_view(row) for row in state.get("current_positions") or []]
    review_positions = [row for row in positions if row.get("review_required") is True or row.get("source") == "broker_orders_fallback"]
    source_summary = get_positions_source_summary(root)
    return _reader_safe(
        {
            "state_missing": state.get("state_missing") is True,
            "current_positions": positions,
            "current_position_count": len(positions),
            "current_market_value": str(state.get("current_market_value") or "0"),
            "current_positions_source": source_summary,
            "current_positions_review_required": bool(review_positions) or state.get("state_missing") is True,
            "review_required_position_count": len(review_positions),
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
    )


def get_current_cash(root: Path) -> dict[str, Any]:
    state = read_persistent_ledger_state(root)
    cash = state.get("current_cash") or {}
    buying_power = str(cash.get("buying_power") or "")
    cash_available = str(cash.get("cash_available") or "")
    return _reader_safe(
        {
            "state_missing": state.get("state_missing") is True,
            "cash_available": cash_available,
            "buying_power": buying_power,
            "evaluation_equity_basis": buying_power or cash_available or "0",
            "currency": str(cash.get("currency") or "JPY"),
            "cash_source": str(cash.get("source") or ""),
            "cash_review_required": cash.get("review_required") is True or state.get("state_missing") is True,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
    )


def get_position_by_code(root: Path, code: str) -> Optional[dict[str, Any]]:
    normalized = _code_variants(code)
    for row in get_current_positions(root).get("current_positions") or []:
        row_codes = _code_variants(row.get("issue_code")) | _code_variants(row.get("broker_issue_code")) | _code_variants(row.get("internal_code"))
        if normalized & row_codes:
            return _reader_safe(row)
    return None


def get_execution_history(root: Path, code: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(_ledger_root(Path(root)) / "executions.jsonl")
    return [_reader_safe(row) for row in rows if _matches_filters(row, code=code, date_from=date_from, date_to=date_to)]


def get_order_history(root: Path, code: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(_ledger_root(Path(root)) / "orders.jsonl")
    return [_reader_safe(row) for row in rows if _matches_filters(row, code=code, date_from=date_from, date_to=date_to)]


def get_positions_source_summary(root: Path) -> dict[str, Any]:
    state = read_persistent_ledger_state(root)
    positions = state.get("current_positions") or []
    by_source: dict[str, int] = {}
    by_environment: dict[str, int] = {}
    for row in positions:
        source = str(row.get("source") or "unknown")
        environment = str(row.get("environment") or "unknown")
        by_source[source] = by_source.get(source, 0) + 1
        by_environment[environment] = by_environment.get(environment, 0) + 1
    return _reader_safe(
        {
            "state_missing": state.get("state_missing") is True,
            "position_count": len(positions),
            "by_source": dict(sorted(by_source.items())),
            "by_environment": dict(sorted(by_environment.items())),
            "sources": sorted(by_source),
            "environments": sorted(by_environment),
            "review_required_position_count": sum(1 for row in positions if row.get("review_required") is True or row.get("source") == "broker_orders_fallback"),
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
    )


def get_review_required_positions(root: Path) -> list[dict[str, Any]]:
    return [
        _reader_safe(row | {"review_required": True, "production_equivalent": row.get("production_equivalent", False) if row.get("source") == "broker_orders_fallback" else row.get("production_equivalent", True)})
        for row in get_current_positions(root).get("current_positions") or []
        if row.get("review_required") is True or row.get("source") == "broker_orders_fallback" or row.get("production_equivalent") is False
    ]


def _write_state_and_result(*, root: Path, record: dict[str, Any], appended: bool, file_name: str) -> dict[str, Any]:
    state = summarize_persistent_ledger(root=root)
    write_json(_ledger_root(root) / "state.json", state)
    return {
        "status": "APPENDED" if appended else "DEDUP_SKIPPED",
        "ledger_root": str(_ledger_root(root)),
        "file": file_name,
        "dedup_key": record.get("dedup_key", ""),
        "state_path": str(_ledger_root(root) / "state.json"),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }


def _empty_reader_state(*, root: Path, state_missing: bool) -> dict[str, Any]:
    return {
        "artifact_type": "persistent_ledger_state",
        "schema_version": "persistent_ledger_state_v1",
        "ledger_root": str(_ledger_root(root)),
        "state_missing": state_missing,
        "current_positions": [],
        "current_position_count": 0,
        "current_market_value": "0",
        "current_cash": {
            "cash_available": "",
            "buying_power": "",
            "currency": "JPY",
            "source": "",
            "environment": "",
        },
        "current_state_confirmed_empty": False,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }


def _position_reader_view(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source") or "")
    payload = {
        **row,
        "review_required": row.get("review_required") is True or source == "broker_orders_fallback",
        "production_equivalent": row.get("production_equivalent", source != "broker_orders_fallback"),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "plain_broker_ids_saved": False,
    }
    return _reader_safe(payload)


def _matches_filters(row: dict[str, Any], *, code: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> bool:
    if code:
        target = _code_variants(code)
        row_codes = _code_variants(row.get("issue_code")) | _code_variants(row.get("broker_issue_code")) | _code_variants(row.get("internal_code")) | _code_variants(row.get("code"))
        if not (target & row_codes):
            return False
    business_date = str(row.get("business_date") or row.get("trade_date") or row.get("date") or "")
    if date_from and business_date and business_date < date_from:
        return False
    if date_to and business_date and business_date > date_to:
        return False
    return True


def _code_variants(code: Any) -> set[str]:
    text = str(code or "").strip()
    if not text:
        return set()
    variants = {text}
    if text.isdigit() and len(text) == 5 and text.endswith("0"):
        variants.add(text[:4])
    if text.isdigit() and len(text) == 4:
        variants.add(f"{text}0")
    return variants


def _reader_safe(payload: Any) -> Any:
    return sanitize_mapping(_drop_prohibited(payload))


def _safe_record(record_type: str, record: dict[str, Any]) -> dict[str, Any]:
    payload = _drop_prohibited(record)
    payload.update(
        {
            "record_type": record_type,
            "recorded_at": str(payload.get("recorded_at") or utc_now_iso()),
            "environment": str(payload.get("environment") or "unknown"),
            "source": str(payload.get("source") or "unknown"),
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
    )
    if "production_equivalent" not in payload:
        payload["production_equivalent"] = payload.get("environment") != "demo" or payload.get("source") != "broker_orders_fallback"
    return sanitize_mapping(payload)


def _drop_prohibited(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            text_key = str(key)
            if text_key.lower() in _PROHIBITED_KEYS:
                continue
            cleaned[text_key] = _drop_prohibited(item)
        return cleaned
    if isinstance(value, list):
        return [_drop_prohibited(item) for item in value]
    if isinstance(value, tuple):
        return [_drop_prohibited(item) for item in value]
    return value


def _dedup_key(payload: dict[str, Any], *, preferred: tuple[str, ...]) -> str:
    for key in preferred:
        if payload.get(key):
            return f"{key}:{payload[key]}"
    return stable_hash({key: value for key, value in payload.items() if key not in {"recorded_at"}})


def _append_jsonl_dedup(path: Path, payload: dict[str, Any], *, dedup_key: str) -> bool:
    existing = _read_jsonl(path)
    if any(row.get("dedup_key") == dedup_key for row in existing):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitize_mapping(payload), ensure_ascii=True, sort_keys=True) + "\n")
    return True


def _current_positions(position_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in position_history:
        key = str(row.get("position_key") or _position_key(row))
        quantity = _decimal(row.get("quantity") or row.get("net_quantity"))
        if quantity <= 0:
            latest.pop(key, None)
            continue
        latest[key] = {
            "position_key": key,
            "business_date": str(row.get("business_date") or ""),
            "environment": str(row.get("environment") or ""),
            "source": str(row.get("source") or ""),
            "issue_code": str(row.get("issue_code") or row.get("broker_issue_code") or row.get("code") or ""),
            "side": str(row.get("side") or "LONG"),
            "account_type": str(row.get("account_type") or "cash"),
            "quantity": str(quantity),
            "average_price": str(row.get("average_price") or row.get("price") or ""),
            "market_value": str(row.get("market_value") or ""),
            "review_required": row.get("review_required") is True,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "plain_broker_ids_saved": False,
        }
    return [latest[key] for key in sorted(latest)]


def _position_key(row: dict[str, Any]) -> str:
    issue_code = str(row.get("issue_code") or row.get("broker_issue_code") or row.get("code") or "")
    account_type = str(row.get("account_type") or "cash")
    side = str(row.get("side") or "LONG")
    environment = str(row.get("environment") or "unknown")
    return stable_hash({"environment": environment, "issue_code": issue_code, "account_type": account_type, "side": side})


def _ensure_ledger_root(root: Path) -> Path:
    ledger_root = _ledger_root(root)
    ledger_root.mkdir(parents=True, exist_ok=True)
    for file_name in JSONL_FILES:
        path = ledger_root / file_name
        if not path.exists():
            path.write_text("", encoding="utf-8")
    state_path = ledger_root / "state.json"
    if not state_path.exists():
        write_json(state_path, {"artifact_type": "persistent_ledger_state", "schema_version": "persistent_ledger_state_v1", "current_positions": [], "raw_request_saved": False, "raw_response_saved": False, "secret_saved": False, "plain_broker_ids_saved": False})
    return ledger_root


def _ledger_root(root: Path) -> Path:
    return Path(root) / PERSISTENT_LEDGER_DIR


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")
