from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping

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
from ai_fund_lab_v2.broker.retry_policy import BrokerRetryPolicy, run_retryable_call
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


class BrokerSnapshotLoginSessionError(RuntimeError):
    def __init__(self, message: str, *, diagnosis: dict[str, Any]) -> None:
        super().__init__(message)
        self.diagnosis = diagnosis


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
    max_login_session_attempts: int = 3,
    login_retry_backoff_seconds: float = 2.0,
    sleep_func: Callable[[float], None] = time.sleep,
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
        session, latency, login_diagnosis = _login_with_retry(
            auth_client,
            decryptor=decryptor,
            max_attempts=max_login_session_attempts,
            backoff_seconds=login_retry_backoff_seconds,
            sleep_func=sleep_func,
        )
        health["login"] = _health_item("PASS", latency_ms=latency)
        health["login"]["retry_attempts"] = login_diagnosis["retry_attempts"]

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

        origin_metadata = {
            "provider": "tachibana",
            "adapter": "tachibana_broker_snapshot",
            "transport": "HTTP_POST",
            "data_origin": "BROKER_API",
            "fixture_used": False,
            "mock_used": False,
            "read_only": True,
        }

        account_fetch = _readonly_fetch_with_retry(request_client.get_account_summary, sleep_func=sleep_func)
        buying_power_fetch = _readonly_fetch_with_retry(request_client.get_buying_power, sleep_func=sleep_func)
        account_response = account_fetch.value
        buying_power_response = buying_power_fetch.value
        account_summary = _normalize_with_origin(normalize_balance_summary, account_response, origin_metadata=origin_metadata)
        buying_power = _normalize_with_origin(normalize_buying_power, buying_power_response, origin_metadata=origin_metadata)
        health["account"] = _response_health(account_response.is_success() and buying_power_response.is_success(), account_fetch.elapsed_ms + buying_power_fetch.elapsed_ms)
        health["account"]["retry_attempts"] = max(account_fetch.retry_attempts, buying_power_fetch.retry_attempts)
        health["account"]["attempts"] = account_fetch.attempts_dicts() + buying_power_fetch.attempts_dicts()

        cash_fetch = _readonly_fetch_with_retry(request_client.get_cash_positions, sleep_func=sleep_func)
        margin_fetch = _readonly_fetch_with_retry(request_client.get_margin_positions, sleep_func=sleep_func)
        cash_response = cash_fetch.value
        margin_response = margin_fetch.value
        positions_safe_diagnosis = build_positions_api_safe_diagnosis(cash_response.raw, margin_response.raw)
        positions_safe_diagnosis_path = report_path.parent / "positions_safe_diagnosis.json"
        _write_json(positions_safe_diagnosis_path, positions_safe_diagnosis)
        positions = _normalize_with_origin(normalize_cash_positions, cash_response, origin_metadata=origin_metadata) + _normalize_with_origin(
            normalize_margin_positions,
            margin_response,
            origin_metadata=origin_metadata,
        )
        health["positions"] = _response_health(cash_response.is_success() and margin_response.is_success(), cash_fetch.elapsed_ms + margin_fetch.elapsed_ms, count=len(positions))
        health["positions"]["retry_attempts"] = max(cash_fetch.retry_attempts, margin_fetch.retry_attempts)
        health["positions"]["attempts"] = cash_fetch.attempts_dicts() + margin_fetch.attempts_dicts()
        health["positions"]["safe_diagnosis_path"] = str(positions_safe_diagnosis_path)
        health["positions"]["candidate_key_match_rate"] = positions_safe_diagnosis["combined"]["candidate_key_match_rate"]

        order_fetch = _readonly_fetch_with_retry(request_client.get_orders, sleep_func=sleep_func)
        order_response = order_fetch.value
        orders = _normalize_with_origin(normalize_order_list, order_response, origin_metadata=origin_metadata)
        health["orders"] = _response_health(order_response.is_success(), order_fetch.elapsed_ms, count=len(orders))
        health["orders"]["retry_attempts"] = order_fetch.retry_attempts
        health["orders"]["attempts"] = order_fetch.attempts_dicts()

        executions = []
        execution_latency = 0
        if orders:
            detail_attempts: list[dict[str, Any]] = []
            detail_failures: list[dict[str, Any]] = []
            detail_success_count = 0
            for order in orders:
                order_id = str(order.order_id or "")
                order_id_hash = _hash_value("order", order_id) if order_id else ""
                if not order_id:
                    detail_failures.append(
                        {
                            "order_id_hash": "",
                            "failure_stage": "order_detail_request",
                            "safe_error_class": "MissingOrderId",
                            "classification": "FAILED_BROKER_READONLY_FETCH",
                        }
                    )
                    continue
                try:
                    detail_fetch = _readonly_fetch_with_retry(lambda order_id=order_id: request_client.get_executions_history(order_id), sleep_func=sleep_func)
                except Exception as exc:  # noqa: BLE001 - continue other order details.
                    detail_failures.append(
                        {
                            "order_id_hash": order_id_hash,
                            "failure_stage": "order_detail_fetch",
                            "safe_error_class": exc.__class__.__name__,
                            "classification": "FAILED_BROKER_READONLY_FETCH",
                            "attempts": [record.to_dict() for record in getattr(exc, "attempts", [])],
                        }
                    )
                    continue
                execution_latency += detail_fetch.elapsed_ms
                detail_attempts.extend({"order_id_hash": order_id_hash, **attempt} for attempt in detail_fetch.attempts_dicts())
                detail_response = detail_fetch.value
                if detail_response.is_success():
                    detail_success_count += 1
                else:
                    detail_failures.append(
                        {
                            "order_id_hash": order_id_hash,
                            "failure_stage": "order_detail_response",
                            "safe_error_class": "BrokerResponseEnvelope",
                            "classification": "FAILED_BROKER_READONLY_FETCH",
                            "result_code_present": bool(detail_response.result_code),
                            "result_code_zero": detail_response.result_code == "0",
                        }
                    )
                executions.extend(_normalize_execution_with_origin(detail_response, order_id=order_id, origin_metadata=origin_metadata))
            execution_status = "PASS" if executions and not detail_failures else "PASS_WITH_EMPTY_RESULT" if not detail_failures else "FAIL"
            health["executions"] = _health_item(execution_status, latency_ms=execution_latency, count=len(executions))
            health["executions"]["detail_attempted_count"] = len(orders)
            health["executions"]["detail_success_count"] = detail_success_count
            health["executions"]["detail_failure_count"] = len(detail_failures)
            health["executions"]["attempts"] = detail_attempts
            health["executions"]["failures"] = detail_failures
        else:
            health["executions"] = _health_item("SKIPPED_NO_ORDERS", latency_ms=0, count=0)

        quotes = []
        if include_quotes and price_client is not None:
            quote_fetch = _readonly_fetch_with_retry(lambda: price_client.get_quotes(list(symbols), columns=auth_settings.quote_columns), sleep_func=sleep_func)
            quote_response = quote_fetch.value
            quote_latency = quote_fetch.elapsed_ms
            quotes = normalize_market_quotes(quote_response)
            quote_status = "PASS" if quotes else "PASS_WITH_EMPTY_RESULT"
            if not quote_response.is_success():
                quote_status = "FAIL"
            health["quotes"] = _health_item(quote_status, latency_ms=quote_latency, count=len(quotes))
            health["quotes"]["retry_attempts"] = quote_fetch.retry_attempts
            health["quotes"]["attempts"] = quote_fetch.attempts_dicts()
        else:
            health["quotes"] = _health_item("SKIPPED_NOT_REQUESTED", latency_ms=0, count=0)
        logout_payload = _logout(auth_client, session, auth_settings=auth_settings, codec=codec, sleep_func=sleep_func)
        health["logout"] = _health_item("PASS" if logout_payload["status"] == "PASS" else "FAIL")

        snapshot = {
            "schema_version": "tachibana_broker_snapshot_v1",
            "broker": "tachibana",
            "environment": auth_settings.environment,
            "generated_at": utc_now_iso(),
            "api_version": "e_api_v4r9",
            "session_status": "PASS",
            "provider": "tachibana",
            "adapter": "tachibana_broker_snapshot",
            "transport": "HTTP_POST",
            "raw_response_origin": "TACHIBANA_API_RESPONSE",
            "data_origin": "BROKER_API",
            "fixture_used": False,
            "mock_used": False,
            "read_only": True,
            "account_identity_hash": _settings_account_identity_hash(auth_settings),
            "account_identity_status": "REFERENCE_HASHED",
            "account_type": "demo" if auth_settings.environment == "demo" else auth_settings.environment,
            "session_environment": auth_settings.environment,
            "credential_reference_id": _credential_reference_id(auth_settings),
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
            "positions_api_safe_diagnosis_path": str(positions_safe_diagnosis_path),
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
            positions_safe_diagnosis_path=positions_safe_diagnosis_path,
        )
        _write_json(report_path, report)
        return TachibanaBrokerSnapshotResult(status, True, report_path, snapshot_path)
    except BrokerSnapshotLoginSessionError as exc:
        payload = _failure_payload(
            auth_settings,
            "FAILED_LOGIN_SESSION",
            str(exc),
            source=source,
            snapshot_path=snapshot_path,
            logout=logout_payload,
            safe_diagnosis=exc.diagnosis,
        )
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, _failure_status(str(exc), configuration_error=True), str(exc), source=source, snapshot_path=snapshot_path, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual snapshot CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, _failure_status(str(exc), configuration_error=False), str(exc), source=source, snapshot_path=snapshot_path, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaBrokerSnapshotResult(str(payload["status"]), True, report_path, snapshot_path, str(payload["message"]))


def _measure(func: Callable[[], Any]) -> tuple[Any, int]:
    start = time.perf_counter()
    result = func()
    return result, int((time.perf_counter() - start) * 1000)


def _normalize_with_origin(func: Callable[..., Any], response: Any, *, origin_metadata: Mapping[str, Any]) -> Any:
    try:
        return func(response, origin_metadata=origin_metadata)
    except TypeError as exc:
        if "origin_metadata" not in str(exc):
            raise
        return func(response)


def _normalize_execution_with_origin(response: Any, *, order_id: str, origin_metadata: Mapping[str, Any]) -> Any:
    try:
        return normalize_order_detail_executions(response, order_id=order_id, origin_metadata=origin_metadata)
    except TypeError as exc:
        if "origin_metadata" not in str(exc):
            raise
        return normalize_order_detail_executions(response, order_id=order_id)


def _login_with_retry(
    client: TachibanaReadOnlyClient,
    *,
    decryptor: OpenSslRsaOaepDecryptor,
    max_attempts: int,
    backoff_seconds: float,
    sleep_func: Callable[[float], None],
) -> tuple[Any, int, dict[str, Any]]:
    policy = BrokerRetryPolicy(max_attempts=max_attempts, backoff_seconds=backoff_seconds)
    try:
        result = run_retryable_call(
            lambda: client.login(decrypt_url=decryptor),
            policy=policy,
            failure_stage="login_session",
            classification="FAILED_LOGIN_SESSION",
            sleep_func=sleep_func,
        )
    except BrokerConfigurationError as exc:
        attempts = [
            {
                **record.to_dict(),
                "decrypt_attempted": bool(_safe_decryptor_diagnosis(decryptor).get("attempts")),
                "decrypt_success": _decrypt_success(_safe_decryptor_diagnosis(decryptor)),
            }
            for record in getattr(exc, "attempts", [])
        ]
        raise BrokerSnapshotLoginSessionError(
            "Tachibana broker snapshot login/session acquisition failed after retry.",
            diagnosis=_login_failure_diagnosis(str(exc), attempts, decryptor=decryptor),
        ) from exc
    except Exception as exc:  # noqa: BLE001 - sanitized retry boundary.
        attempts = [
            {
                **record.to_dict(),
                "decrypt_attempted": bool(_safe_decryptor_diagnosis(decryptor).get("attempts")),
                "decrypt_success": _decrypt_success(_safe_decryptor_diagnosis(decryptor)),
            }
            for record in getattr(exc, "attempts", [])
        ]
        raise BrokerSnapshotLoginSessionError(
            "Tachibana broker snapshot login/session acquisition failed after retry.",
            diagnosis=_login_failure_diagnosis(str(exc), attempts, decryptor=decryptor),
        ) from exc
    return result.value, result.elapsed_ms, {
        "retry_attempts": result.retry_attempts,
        "attempts": result.attempts_dicts(),
        "final_failure_classification": "",
    }


def _readonly_fetch_with_retry(func: Callable[[], Any], *, sleep_func: Callable[[float], None]):
    return run_retryable_call(
        func,
        policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=2.0),
        failure_stage="readonly_fetch",
        classification="FAILED_BROKER_READONLY_FETCH",
        sleep_func=sleep_func,
    )


POSITION_CANDIDATE_KEYS: dict[str, tuple[str, ...]] = {
    "issue_code": ("issue_code", "sIssueCode", "sOrderIssueCode", "sMeigaraCode", "sCode", "860"),
    "quantity": ("quantity", "sQuantity", "sZanKabuSuu", "sOrderOrderSuryou", "sOrderSuryou", "sSuryou", "sTategyokuSuryou", "864"),
    "market_value": ("market_value", "sMarketValue", "sHyokaGaku", "sHyoukaGaku", "858"),
    "price": ("price", "average_price", "market_price", "sPrice", "sAveragePrice", "sBokaTanka", "sHeikinTanka", "sMarketPrice", "sGenzaine", "sGenzaichi", "855", "859"),
}

CASH_POSITION_LIST_KEYS = ("positions", "aGenbutuKabuList", "aCLMGenbutuKabuList")
MARGIN_POSITION_LIST_KEYS = ("positions", "aShinyouTategyokuList", "aCLMShinyouTategyokuList")


def build_positions_api_safe_diagnosis(cash_raw: Mapping[str, Any], margin_raw: Mapping[str, Any]) -> dict[str, Any]:
    cash = _position_response_key_diagnosis(cash_raw, list_keys=CASH_POSITION_LIST_KEYS)
    margin = _position_response_key_diagnosis(margin_raw, list_keys=MARGIN_POSITION_LIST_KEYS)
    return sanitize_mapping(
        {
            "schema_version": "tachibana_positions_api_safe_diagnosis_v1",
            "created_at": utc_now_iso(),
            "cash": cash,
            "margin": margin,
            "combined": {
                "row_count": cash["row_count"] + margin["row_count"],
                "candidate_key_match_rate": _combined_candidate_match_rate(cash, margin),
            },
            "raw_response_saved": False,
            "raw_values_saved": False,
            "secret_saved": False,
            "order_number_saved": False,
            "account_identifier_saved": False,
            "url_saved": False,
            "token_saved": False,
            "session_saved": False,
            "issue_code_value_saved": False,
            "quantity_value_saved": False,
            "price_value_saved": False,
        }
    )


def _position_response_key_diagnosis(raw: Mapping[str, Any], *, list_keys: tuple[str, ...]) -> dict[str, Any]:
    rows = _position_rows_for_diagnosis(raw, list_keys)
    row_key_names = sorted({str(key) for row in rows for key in row.keys()})
    candidate_presence = {
        name: [key for key in keys if any(key in row for row in rows)]
        for name, keys in POSITION_CANDIDATE_KEYS.items()
    }
    candidate_hit_counts = {
        name: sum(1 for row in rows if any(key in row for key in keys))
        for name, keys in POSITION_CANDIDATE_KEYS.items()
    }
    row_count = len(rows)
    return {
        "top_level_keys": sorted(str(key) for key in raw.keys()),
        "list_key_hits": [
            {"key": key, "row_count": len(value)}
            for key in list_keys
            if isinstance((value := raw.get(key)), list)
        ],
        "row_count": row_count,
        "row_key_names": row_key_names,
        "candidate_key_presence": candidate_presence,
        "candidate_key_hit_counts": candidate_hit_counts,
        "candidate_key_match_rate": {name: f"{count}/{row_count}" for name, count in candidate_hit_counts.items()},
    }


def _position_rows_for_diagnosis(raw: Mapping[str, Any], list_keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for key in list_keys:
        value = raw.get(key)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, Mapping))
    return rows


def _combined_candidate_match_rate(cash: Mapping[str, Any], margin: Mapping[str, Any]) -> dict[str, str]:
    cash_counts = cash.get("candidate_key_hit_counts") or {}
    margin_counts = margin.get("candidate_key_hit_counts") or {}
    total_rows = int(cash.get("row_count") or 0) + int(margin.get("row_count") or 0)
    return {
        name: f"{int(cash_counts.get(name) or 0) + int(margin_counts.get(name) or 0)}/{total_rows}"
        for name in POSITION_CANDIDATE_KEYS
    }


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
        return "FAILED_BROKER_READONLY_FETCH"
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
    positions_safe_diagnosis_path: Path,
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
            "positions_safe_diagnosis_path": str(positions_safe_diagnosis_path),
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


def _credential_reference_id(settings: BrokerSettings) -> str:
    references = {
        "environment": settings.environment,
        "base_url": settings.base_url,
        "auth_id_file": str(settings.auth_id_file or ""),
        "private_key_file": str(settings.private_key_file or ""),
        "local_config_path": str(settings.local_config_path or ""),
    }
    material = json.dumps(references, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _settings_account_identity_hash(settings: BrokerSettings) -> str:
    material = json.dumps(
        {
            "provider": "tachibana",
            "environment": settings.environment,
            "credential_reference_id": _credential_reference_id(settings),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


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


def _failure_payload(
    settings: BrokerSettings,
    status: str,
    message: str,
    *,
    source: str,
    snapshot_path: Path,
    logout: dict[str, Any] | None = None,
    safe_diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnosis = safe_diagnosis or _safe_failure_diagnosis(message, safe_error_class="", retry_attempts=1, final_status=status)
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
        "retry_attempts": diagnosis.get("retry_attempts", 1),
        "safe_diagnosis": diagnosis,
        "logout": logout or {"attempted": False, "status": "NOT_EXECUTED"},
        "paper_ledger_updated": False,
        "broker_snapshot_updated": False,
        "ai_learning_updated": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "virtual_url_saved": False,
    }


def _failure_status(message: str, *, configuration_error: bool) -> str:
    classification = _classify_failure(message)
    if classification == "login_session_error":
        return "FAILED_LOGIN_SESSION"
    if classification == "network_or_http_error":
        return "FAILED_BROKER_READONLY_FETCH"
    if "parse" in message.lower() or "normalize" in message.lower() or "decode" in message.lower():
        return "FAILED_BROKER_READONLY_PARSE"
    if configuration_error:
        return "FAILED_CONFIGURATION"
    return "FAILED_BROKER_READONLY_FETCH"


def _login_failure_attempt(index: int, exc: BaseException, *, retryable: bool, decryptor: OpenSslRsaOaepDecryptor) -> dict[str, Any]:
    message = str(exc)
    decryptor_diagnosis = _safe_decryptor_diagnosis(decryptor)
    return {
        "attempt": index,
        "safe_error_class": exc.__class__.__name__,
        "failure_stage": _failure_stage(message),
        "retryable": retryable,
        "decrypt_attempted": bool(decryptor_diagnosis.get("attempts")),
        "decrypt_success": _decrypt_success(decryptor_diagnosis),
    }


def _login_failure_diagnosis(message: str, attempts: list[dict[str, Any]], *, decryptor: OpenSslRsaOaepDecryptor) -> dict[str, Any]:
    last = attempts[-1] if attempts else {}
    decryptor_diagnosis = _safe_decryptor_diagnosis(decryptor)
    diagnosis = _safe_failure_diagnosis(
        message,
        safe_error_class=str(last.get("safe_error_class") or ""),
        retry_attempts=len(attempts) or 1,
        final_status="FAILED_LOGIN_SESSION",
        decryptor_diagnosis=decryptor_diagnosis,
    )
    diagnosis["attempts"] = attempts
    return diagnosis


def _safe_failure_diagnosis(
    message: str,
    *,
    safe_error_class: str,
    retry_attempts: int,
    final_status: str,
    decryptor_diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage = _failure_stage(message)
    if final_status == "FAILED_LOGIN_SESSION":
        stage = "login_session" if stage == "snapshot_fetch" else stage
    decryptor_diagnosis = decryptor_diagnosis or {}
    return {
        "failure_stage": stage,
        "safe_error_class": safe_error_class,
        "login_result_code_present": "login failed" in message.lower() or stage == "login_ack",
        "login_result_code_zero": False if "login failed" in message.lower() else None,
        "session_url_field_present": False if stage == "session_url_missing" else None,
        "decrypt_attempted": bool(decryptor_diagnosis.get("attempts")) or stage == "session_url_decrypt",
        "decrypt_success": _decrypt_success(decryptor_diagnosis),
        "retry_attempts": retry_attempts,
        "final_failure_classification": final_status,
    }


def _safe_decryptor_diagnosis(decryptor: OpenSslRsaOaepDecryptor) -> dict[str, Any]:
    try:
        return sanitize_mapping(decryptor.safe_diagnosis())
    except Exception:  # noqa: BLE001 - diagnosis must never mask the primary failure.
        return {}


def _decrypt_success(diagnosis: dict[str, Any]) -> bool:
    if not diagnosis:
        return False
    if diagnosis.get("selected_backend"):
        return str(diagnosis.get("url_validation_failure_reason") or "none") == "none"
    return False


def _failure_stage(message: str) -> str:
    normalized = message.lower()
    if "decrypt" in normalized or "invalid url" in normalized:
        return "session_url_decrypt"
    if "missing surl" in normalized or "surlrequest" in normalized or "surlmaster" in normalized or "surlprice" in normalized or "surlevent" in normalized:
        return "session_url_missing"
    if "login" in normalized:
        return "login_ack"
    if "http post" in normalized or "urlopen" in normalized or "timed out" in normalized:
        return "snapshot_fetch"
    if "parse" in normalized or "normalize" in normalized or "decode" in normalized:
        return "snapshot_parse"
    return "snapshot_fetch"


def _logout(
    client: TachibanaReadOnlyClient,
    session,
    *,
    auth_settings: BrokerSettings,
    codec: TachibanaV4R9Codec,
    sleep_func: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    logout_transport = HttpPostBrokerTransport(
        endpoint_url=session.request_url,
        timeout_seconds=auth_settings.timeout_seconds,
        rate_limit_per_second=auth_settings.rate_limit_per_second,
        codec=codec,
    )
    try:
        result = run_retryable_call(
            lambda: client.logout(session, transport=logout_transport),
            policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=1.0),
            failure_stage="logout",
            classification="FAILED_LOGOUT",
            sleep_func=sleep_func,
        )
    except Exception as exc:  # noqa: BLE001 - best-effort cleanup.
        attempts = [record.to_dict() for record in getattr(exc, "attempts", [])]
        return {
            "attempted": True,
            "status": "BEST_EFFORT_FAILED",
            "failure_classification": _classify_failure(str(exc)),
            "retry_attempts": len(attempts) or 1,
            "attempts": attempts,
        }
    response = result.value
    return {
        "attempted": True,
        "status": "PASS" if response.is_success() else "WARNING",
        "retry_attempts": result.retry_attempts,
        "attempts": result.attempts_dicts(),
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
