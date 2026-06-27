from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.models import BrokerExecutionSnapshot, utc_now_iso
from ai_fund_lab_v2.broker.normalizer import normalize_order_detail_executions, normalize_order_list
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text
from ai_fund_lab_v2.broker.secrets import DEFAULT_PRIVATE_KEY_PEM_FILENAME, TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.transport import HttpPostBrokerTransport


@dataclass(frozen=True)
class TachibanaExecutionsHistorySmokeResult:
    status: str
    executed: bool
    report_path: Path
    message: str = ""


def run_tachibana_executions_history_smoke(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10h_tachibana_executions_history_smoke_result.json",
    source: str = "phase10h_executions_history_readonly_smoke",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
) -> TachibanaExecutionsHistorySmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _skipped_payload(resolved_settings, source, "Explicit run flag was not provided; no Tachibana executions/history smoke was executed.")
        _write_json(report_path, payload)
        return TachibanaExecutionsHistorySmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = _skipped_payload(resolved_settings, source, "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana executions/history smoke was executed.")
        _write_json(report_path, payload)
        return TachibanaExecutionsHistorySmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])

    session = None
    auth_settings = resolved_settings
    codec = TachibanaV4R9Codec()
    logout_payload: dict[str, Any] = {"attempted": False, "status": "NOT_EXECUTED"}
    try:
        resolved_settings.require_demo_environment()
        secrets = TachibanaSecretLoader(resolved_settings).load()
        auth_settings = replace(
            resolved_settings,
            auth_id=secrets.auth_id,
            auth_id_file=secrets.auth_id_file,
            private_key_file=secrets.private_key_file,
            private_key_format=secrets.private_key_format,
        )
        fallback_key_file = _resolve_fallback_key_file(auth_settings)
        auth_transport = HttpPostBrokerTransport(
            endpoint_url=auth_settings.auth_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        client = TachibanaReadOnlyClient(auth_settings, auth_transport)
        decryptor = OpenSslRsaOaepDecryptor(
            auth_settings.require_private_key_file(),
            key_format=auth_settings.private_key_format,
            fallback_private_key_file=fallback_key_file,
        )
        session = client.login(decrypt_url=decryptor)
        request_transport = HttpPostBrokerTransport(
            endpoint_url=session.request_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        request_client = TachibanaReadOnlyClient(auth_settings, request_transport, builder=client.request_builder)
        order_list_response = request_client.get_orders()
        orders = normalize_order_list(order_list_response)
        detail_response = None
        executions: list[BrokerExecutionSnapshot] = []
        detail_status = "SKIPPED_NO_ORDERS"
        if orders:
            detail_response = request_client.get_executions_history(orders[0].order_id)
            executions = normalize_order_detail_executions(detail_response, order_id=orders[0].order_id)
            detail_status = "PASS_WITH_EMPTY_RESULT" if detail_response.is_success() and not executions else "PASS"
            if not detail_response.is_success():
                detail_status = "FAILED_READONLY"
        readonly_status = _readonly_status(order_list_response.is_success(), detail_status)
        logout_payload = _logout(client, session, auth_settings=auth_settings, codec=codec)
        payload = {
            "status": readonly_status if logout_payload["status"] == "PASS" else "PASS_WITH_LOGOUT_WARNING",
            "executed": True,
            "run_count": 1,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": auth_settings.environment,
            "official_clmid_conclusion": {
                "execution_history_clmid": "CLMOrderListDetail",
                "prerequisite_clmid": "CLMOrderList",
                "standalone_trade_history_clmid_confirmed": False,
                "market_price_history_excluded": "CLMMfdsGetMarketPriceHistory is price history, not broker order/execution history.",
            },
            "login": {"status": "PASS"},
            "login_success": True,
            "session_established": True,
            "executions": [_execution_dict(item) for item in executions],
            "execution_counts": {"orders": len(orders), "executions": len(executions)},
            "response_summary": {
                "order_list": _response_summary(order_list_response.raw),
                "order_detail": _response_summary(detail_response.raw) if detail_response is not None else {"status": "SKIPPED_NO_ORDERS"},
            },
            "logout": logout_payload,
            "logout_attempted": bool(logout_payload.get("attempted")),
            "logout_success": logout_payload.get("status") == "PASS",
            "executions_success": readonly_status in {"PASS", "PASS_WITH_EMPTY_RESULT"},
            "orders_api_called": True,
            "order_list_api_called": True,
            "order_detail_api_called": detail_response is not None,
            "executions_api_called": detail_response is not None,
            "executions_detail_status": detail_status,
            "positions_api_called": False,
            "quotes_api_called": False,
            "paper_ledger_updated": False,
            "broker_snapshot_updated": False,
            "secret_saved": False,
            "virtual_url_saved": False,
            "raw_response_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaExecutionsHistorySmokeResult(status=str(payload["status"]), executed=True, report_path=report_path)
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_CONFIGURATION", str(exc), source=source, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual smoke CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_READONLY", str(exc), source=source, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaExecutionsHistorySmokeResult(status=str(payload["status"]), executed=True, report_path=report_path, message=str(payload["message"]))


def _readonly_status(order_list_success: bool, detail_status: str) -> str:
    if not order_list_success or detail_status == "FAILED_READONLY":
        return "FAILED_READONLY"
    if detail_status in {"SKIPPED_NO_ORDERS", "PASS_WITH_EMPTY_RESULT"}:
        return "PASS_WITH_EMPTY_RESULT"
    return "PASS"


def _skipped_payload(settings: BrokerSettings, source: str, message: str) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "executed": False,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": message,
        "secret_saved": False,
        "virtual_url_saved": False,
        "raw_response_saved": False,
    }


def _failure_payload(settings: BrokerSettings, status: str, message: str, *, source: str, logout: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "executed": True,
        "run_count": 1,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": "Tachibana executions/history read-only smoke failed closed.",
        "failure_classification": _classify_failure(message),
        "login": {"status": "UNKNOWN_OR_FAILED"},
        "logout": logout or {"attempted": False, "status": "NOT_EXECUTED"},
        "logout_attempted": bool((logout or {}).get("attempted")),
        "logout_success": (logout or {}).get("status") == "PASS",
        "executions_success": False,
        "orders_api_called": False,
        "order_list_api_called": False,
        "order_detail_api_called": False,
        "executions_api_called": False,
        "positions_api_called": False,
        "quotes_api_called": False,
        "paper_ledger_updated": False,
        "broker_snapshot_updated": False,
        "secret_saved": False,
        "virtual_url_saved": False,
        "raw_response_saved": False,
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


def _execution_dict(execution: BrokerExecutionSnapshot) -> dict[str, Any]:
    data = asdict(execution)
    raw_execution_id = str(data.pop("execution_id", "") or "")
    raw_order_id = str(data.pop("order_id", "") or "")
    data["execution_id_hash"] = _hash_value("execution", raw_execution_id) if raw_execution_id else ""
    data["order_id_hash"] = _hash_value("order", raw_order_id) if raw_order_id else ""
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, tuple):
            data[key] = list(value)
    data.pop("snapshot_id", None)
    return sanitize_mapping(data)


def _hash_value(prefix: str, value: str) -> str:
    return f"{prefix}_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _response_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "sCLMID": str(raw.get("sCLMID") or ""),
        "sResultCode": str(raw.get("sResultCode") or ""),
        "sResultText_classification": "empty" if not str(raw.get("sResultText") or "").strip() else "present",
        "api_error_number_present": "p_errno" in raw,
        "api_error_text_present": "p_err" in raw,
        "sanitized_key_names": sorted(str(key) for key in raw.keys()),
    }


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
    return "executions_history_readonly_error"


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
            raise BrokerConfigurationError("No executions/history smoke transport is available.")

    return DummyTransport()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_mapping(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
