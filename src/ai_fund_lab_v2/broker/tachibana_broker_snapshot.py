from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.normalizer import (
    normalize_balance_summary,
    normalize_buying_power,
    normalize_cash_positions,
    normalize_margin_positions,
    normalize_market_quotes,
    normalize_order_detail_executions,
    normalize_order_list,
)
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text
from ai_fund_lab_v2.broker.secrets import DEFAULT_PRIVATE_KEY_PEM_FILENAME, TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_quote_smoke import DEFAULT_QUOTE_SYMBOLS
from ai_fund_lab_v2.broker.transport import HttpPostBrokerTransport


DEFAULT_SNAPSHOT_PATH = Path(".runtime/broker/tachibana/demo/latest_broker_snapshot.json")


@dataclass(frozen=True)
class TachibanaBrokerSnapshotResult:
    status: str
    executed: bool
    report_path: Path
    snapshot_path: Path
    message: str = ""


def run_tachibana_broker_snapshot(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10j_tachibana_broker_snapshot_integration.json",
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    source: str = "phase10j_broker_snapshot_integration",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
    symbols: tuple[str, ...] = DEFAULT_QUOTE_SYMBOLS,
    include_quotes: bool = True,
) -> TachibanaBrokerSnapshotResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _skipped_payload(resolved_settings, source, snapshot_path, "Explicit run flag was not provided; no Tachibana broker snapshot was executed.")
        _write_json(report_path, payload)
        return TachibanaBrokerSnapshotResult("SKIPPED", False, report_path, snapshot_path, payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = _skipped_payload(resolved_settings, source, snapshot_path, "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana broker snapshot was executed.")
        _write_json(report_path, payload)
        return TachibanaBrokerSnapshotResult("SKIPPED", False, report_path, snapshot_path, payload["message"])

    started_at = utc_now_iso()
    session = None
    auth_settings = resolved_settings
    codec = TachibanaV4R9Codec()
    health = _initial_health()
    logout_payload: dict[str, Any] = {"attempted": False, "status": "NOT_EXECUTED"}
    try:
        resolved_settings.require_demo_environment()
        if include_quotes:
            _validate_symbols(symbols, resolved_settings)
        secrets = TachibanaSecretLoader(resolved_settings).load()
        auth_settings = replace(
            resolved_settings,
            auth_id=secrets.auth_id,
            auth_id_file=secrets.auth_id_file,
            private_key_file=secrets.private_key_file,
            private_key_format=secrets.private_key_format,
            rate_limit_per_second=min(resolved_settings.rate_limit_per_second, 5.0),
        )
        fallback_key_file = _resolve_fallback_key_file(auth_settings)
        auth_transport = HttpPostBrokerTransport(
            endpoint_url=auth_settings.auth_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        auth_client = TachibanaReadOnlyClient(auth_settings, auth_transport)
        decryptor = OpenSslRsaOaepDecryptor(
            auth_settings.require_private_key_file(),
            key_format=auth_settings.private_key_format,
            fallback_private_key_file=fallback_key_file,
        )
        session, latency = _measure(lambda: auth_client.login(decrypt_url=decryptor))
        health["login"] = _health_item("PASS", latency_ms=latency)

        request_client = TachibanaReadOnlyClient(
            auth_settings,
            HttpPostBrokerTransport(
                endpoint_url=session.request_url,
                timeout_seconds=auth_settings.timeout_seconds,
                rate_limit_per_second=auth_settings.rate_limit_per_second,
                codec=codec,
            ),
            builder=auth_client.request_builder,
        )
        price_client = None
        if include_quotes:
            price_client = TachibanaReadOnlyClient(
                auth_settings,
                HttpPostBrokerTransport(
                    endpoint_url=session.price_url,
                    timeout_seconds=auth_settings.timeout_seconds,
                    rate_limit_per_second=auth_settings.rate_limit_per_second,
                    codec=codec,
                ),
                builder=auth_client.request_builder,
            )

        account_response, account_latency = _measure(request_client.get_account_summary)
        buying_power_response, buying_power_latency = _measure(request_client.get_buying_power)
        account_summary = normalize_balance_summary(account_response)
        buying_power = normalize_buying_power(buying_power_response)
        health["account"] = _response_health(account_response.is_success() and buying_power_response.is_success(), account_latency + buying_power_latency)

        cash_response, cash_latency = _measure(request_client.get_cash_positions)
        margin_response, margin_latency = _measure(request_client.get_margin_positions)
        positions = normalize_cash_positions(cash_response) + normalize_margin_positions(margin_response)
        health["positions"] = _response_health(cash_response.is_success() and margin_response.is_success(), cash_latency + margin_latency, count=len(positions))

        order_response, order_latency = _measure(request_client.get_orders)
        orders = normalize_order_list(order_response)
        health["orders"] = _response_health(order_response.is_success(), order_latency, count=len(orders))

        detail_response = None
        executions = []
        execution_latency = 0
        if orders:
            detail_response, execution_latency = _measure(lambda: request_client.get_executions_history(orders[0].order_id))
            executions = normalize_order_detail_executions(detail_response, order_id=orders[0].order_id)
            execution_status = "PASS" if executions else "PASS_WITH_EMPTY_RESULT"
            if not detail_response.is_success():
                execution_status = "FAIL"
            health["executions"] = _health_item(execution_status, latency_ms=execution_latency, count=len(executions))
        else:
            health["executions"] = _health_item("SKIPPED_NO_ORDERS", latency_ms=0, count=0)

        quotes = []
        if include_quotes and price_client is not None:
            quote_response, quote_latency = _measure(lambda: price_client.get_quotes(list(symbols), columns=auth_settings.quote_columns))
            quotes = normalize_market_quotes(quote_response)
            quote_status = "PASS" if quotes else "PASS_WITH_EMPTY_RESULT"
            if not quote_response.is_success():
                quote_status = "FAIL"
            health["quotes"] = _health_item(quote_status, latency_ms=quote_latency, count=len(quotes))
        else:
            health["quotes"] = _health_item("SKIPPED_NOT_REQUESTED", latency_ms=0, count=0)
        logout_payload = _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
        health["logout"] = _health_item("PASS" if logout_payload["status"] == "PASS" else "FAIL")

        snapshot = {
            "schema_version": "tachibana_broker_snapshot_v1",
            "broker": "tachibana",
            "environment": auth_settings.environment,
            "generated_at": utc_now_iso(),
            "api_version": "e_api_v4r9",
            "session_status": "PASS",
            "account_summary": _snapshot_dict(account_summary),
            "buying_power": _snapshot_dict(buying_power),
            "positions": [_snapshot_dict(item) for item in positions],
            "orders": [_order_dict(item) for item in orders],
            "executions": [_execution_dict(item) for item in executions],
            "quotes": [_quote_dict(item) for item in quotes],
            "health": health,
            "warnings": _warnings(positions, orders, executions, quotes),
            "redaction_status": _redaction_status(),
            "source": source,
            "quotes_requested": include_quotes,
        }
        snapshot = sanitize_mapping(snapshot)
        _write_json_atomic(snapshot_path, snapshot)

        status = _snapshot_status(health, logout_payload)
        report = _report_payload(
            status=status,
            started_at=started_at,
            settings=auth_settings,
            source=source,
            snapshot_path=snapshot_path,
            health=health,
            logout=logout_payload,
            counts={
                "positions": len(positions),
                "orders": len(orders),
                "executions": len(executions),
                "quotes": len(quotes),
            },
            quotes_requested=include_quotes,
        )
        _write_json(report_path, report)
        return TachibanaBrokerSnapshotResult(status, True, report_path, snapshot_path)
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_CONFIGURATION", str(exc), source=source, snapshot_path=snapshot_path, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual snapshot CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_READONLY", str(exc), source=source, snapshot_path=snapshot_path, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaBrokerSnapshotResult(str(payload["status"]), True, report_path, snapshot_path, str(payload["message"]))


def _measure(func: Callable[[], Any]) -> tuple[Any, int]:
    start = time.perf_counter()
    result = func()
    return result, int((time.perf_counter() - start) * 1000)


def _initial_health() -> dict[str, Any]:
    return {
        "login": _health_item("NOT_EXECUTED"),
        "account": _health_item("NOT_EXECUTED"),
        "positions": _health_item("NOT_EXECUTED"),
        "orders": _health_item("NOT_EXECUTED"),
        "executions": _health_item("NOT_EXECUTED"),
        "quotes": _health_item("NOT_EXECUTED"),
        "logout": _health_item("NOT_EXECUTED"),
        "api_errors": [],
        "empty_result_classification": {},
    }


def _health_item(status: str, *, latency_ms: int = 0, count: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "latency_ms": latency_ms}
    if count is not None:
        payload["count"] = count
    return payload


def _response_health(success: bool, latency_ms: int, *, count: int | None = None) -> dict[str, Any]:
    return _health_item("PASS" if success else "FAIL", latency_ms=latency_ms, count=count)


def _snapshot_status(health: dict[str, Any], logout: dict[str, Any]) -> str:
    failed = [key for key in ("login", "account", "positions", "orders", "executions", "quotes") if health[key]["status"] == "FAIL"]
    if failed:
        return "FAILED_READONLY"
    if logout["status"] != "PASS" or any(health[key]["status"] in {"PASS_WITH_EMPTY_RESULT", "SKIPPED_NO_ORDERS"} for key in ("executions", "quotes")):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def _report_payload(
    *,
    status: str,
    started_at: str,
    settings: BrokerSettings,
    source: str,
    snapshot_path: Path,
    health: dict[str, Any],
    logout: dict[str, Any],
    counts: dict[str, int],
    quotes_requested: bool,
) -> dict[str, Any]:
    return sanitize_mapping(
        {
            "status": status,
            "executed": True,
            "run_count": 1,
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": settings.environment,
            "snapshot_path": str(snapshot_path),
            "snapshot_written": status in {"PASS", "PASS_WITH_WARNINGS"},
            "health": health,
            "counts": counts,
            "quotes_requested": quotes_requested,
            "logout": logout,
            "paper_ledger_updated": False,
            "broker_snapshot_updated": True,
            "ai_learning_updated": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "virtual_url_saved": False,
            "redaction_status": _redaction_status(),
        }
    )


def _skipped_payload(settings: BrokerSettings, source: str, snapshot_path: Path, message: str) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "executed": False,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": message,
        "snapshot_path": str(snapshot_path),
        "snapshot_written": False,
        "paper_ledger_updated": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "virtual_url_saved": False,
    }


def _failure_payload(settings: BrokerSettings, status: str, message: str, *, source: str, snapshot_path: Path, logout: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "executed": True,
        "run_count": 1,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": "Tachibana broker snapshot integration failed closed.",
        "failure_classification": _classify_failure(message),
        "snapshot_path": str(snapshot_path),
        "snapshot_written": False,
        "logout": logout or {"attempted": False, "status": "NOT_EXECUTED"},
        "paper_ledger_updated": False,
        "broker_snapshot_updated": False,
        "ai_learning_updated": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "virtual_url_saved": False,
    }


def _logout(client: TachibanaReadOnlyClient, session, *, auth_settings: BrokerSettings, codec: TachibanaV4R9Codec) -> dict[str, Any]:
    logout_transport = HttpPostBrokerTransport(
        endpoint_url=session.request_url,
        timeout_seconds=auth_settings.timeout_seconds,
        rate_limit_per_second=auth_settings.rate_limit_per_second,
        codec=codec,
    )
    try:
        response = client.logout(session, transport=logout_transport)
    except Exception as exc:  # noqa: BLE001 - best-effort cleanup.
        return {"attempted": True, "status": "BEST_EFFORT_FAILED", "failure_classification": _classify_failure(str(exc))}
    return {
        "attempted": True,
        "status": "PASS" if response.is_success() else "WARNING",
        "result_code": response.result_code,
        "result_text": sanitize_text(response.result_text),
    }


def _snapshot_dict(snapshot: Any) -> dict[str, Any]:
    data = asdict(snapshot)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, tuple):
            data[key] = list(value)
    data.pop("snapshot_id", None)
    return sanitize_mapping(data)


def _order_dict(order: Any) -> dict[str, Any]:
    data = _snapshot_dict(order)
    raw_order_id = str(data.pop("order_id", "") or "")
    data["order_id_hash"] = _hash_value("order", raw_order_id) if raw_order_id else ""
    return sanitize_mapping(data)


def _execution_dict(execution: Any) -> dict[str, Any]:
    data = _snapshot_dict(execution)
    raw_execution_id = str(data.pop("execution_id", "") or "")
    raw_order_id = str(data.pop("order_id", "") or "")
    data["execution_id_hash"] = _hash_value("execution", raw_execution_id) if raw_execution_id else ""
    data["order_id_hash"] = _hash_value("order", raw_order_id) if raw_order_id else ""
    return sanitize_mapping(data)


def _quote_dict(quote: dict[str, Any]) -> dict[str, Any]:
    data = dict(quote)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, tuple):
            data[key] = list(value)
    return sanitize_mapping(data)


def _redaction_status() -> dict[str, bool]:
    return {
        "raw_response_saved": False,
        "virtual_url_saved": False,
        "auth_identifier_saved": False,
        "private_secret_saved": False,
        "account_customer_id_saved": False,
        "order_number_plaintext_saved": False,
        "execution_id_plaintext_saved": False,
    }


def _warnings(*collections: Any) -> list[str]:
    warnings: list[str] = []
    for collection in collections:
        if isinstance(collection, list) and not collection:
            continue
    return warnings


def _hash_value(prefix: str, value: str) -> str:
    return f"{prefix}_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _validate_symbols(symbols: tuple[str, ...], settings: BrokerSettings) -> None:
    if not symbols:
        raise BrokerConfigurationError("At least one quote symbol is required.")
    if len(symbols) > min(settings.quote_symbol_limit, 50):
        raise BrokerConfigurationError("Quote symbols exceed Phase10-J limit.")


def _classify_failure(message: str) -> str:
    normalized = message.lower()
    if "demo-only" in normalized or "demo base url" in normalized:
        return "demo_guard_error"
    if "auth_id" in normalized or "private_key" in normalized:
        return "local_secret_configuration_error"
    if "login" in normalized or "session" in normalized:
        return "login_session_error"
    if "http post" in normalized or "urlopen" in normalized or "timed out" in normalized:
        return "network_or_http_error"
    return "broker_snapshot_integration_error"


def _resolve_fallback_key_file(settings: BrokerSettings) -> Path | None:
    if settings.private_key_format == "pem":
        return None
    if settings.local_config_path is None:
        return None
    candidate = settings.local_config_path / DEFAULT_PRIVATE_KEY_PEM_FILENAME
    return candidate if candidate.is_file() else None


def _dummy_transport():
    class DummyTransport:
        def request(self, payload: dict[str, Any]) -> dict[str, Any]:
            raise BrokerConfigurationError("No broker snapshot transport is available.")

    return DummyTransport()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    _write_json(tmp_path, payload)
    tmp_path.replace(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_mapping(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
