from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.models import BrokerBalanceSnapshot, utc_now_iso
from ai_fund_lab_v2.broker.normalizer import normalize_balance_summary, normalize_buying_power
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text
from ai_fund_lab_v2.broker.secrets import DEFAULT_PRIVATE_KEY_PEM_FILENAME, TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.transport import HttpPostBrokerTransport


WEB_DISPLAY_REFERENCE_AMOUNTS = {
    "web_cash_buying_power": Decimal("20000000"),
    "web_withdrawable_cash": Decimal("17989000"),
    "web_ipo_buying_power": Decimal("17989000"),
    "web_margin_buying_power": Decimal("54512121"),
}


@dataclass(frozen=True)
class TachibanaAccountSmokeResult:
    status: str
    executed: bool
    report_path: Path
    message: str = ""


def run_tachibana_account_balance_smoke(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10e_tachibana_account_balance_smoke_result.json",
    source: str = "phase10e_account_balance_readonly_smoke",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
) -> TachibanaAccountSmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _skipped_payload(resolved_settings, source, "Explicit run flag was not provided; no Tachibana account/balance smoke was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = _skipped_payload(resolved_settings, source, "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana account/balance smoke was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])

    diagnosis: dict[str, Any] = {}
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
        account_response = request_client.get_account_summary()
        buying_power_response = request_client.get_buying_power()
        account_summary = normalize_balance_summary(account_response)
        buying_power = normalize_buying_power(buying_power_response)
        account_error = classify_protocol_error(account_response.raw)
        buying_power_error = classify_protocol_error(buying_power_response.raw)
        readonly_status = (
            "PASS"
            if account_response.is_success()
            and buying_power_response.is_success()
            and not account_error["protocol_error_present"]
            and not buying_power_error["protocol_error_present"]
            else "FAILED_READONLY"
        )
        logout_payload = _logout(client, session, auth_settings=auth_settings, codec=codec)
        payload = {
            "status": readonly_status if logout_payload["status"] == "PASS" else "PASS_WITH_LOGOUT_WARNING",
            "executed": True,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": auth_settings.environment,
            "login": {"status": "PASS"},
            "account_summary": _snapshot_dict(account_summary),
            "buying_power": _snapshot_dict(buying_power),
            "response_summary": {
                "account_summary": _response_summary(account_response.raw),
                "buying_power": _response_summary(buying_power_response.raw),
            },
            "protocol_error_diagnosis": {
                "account_summary": account_error,
                "buying_power": buying_power_error,
            },
            "request_shape_diagnosis": {
                "account_summary": diagnose_account_request_shape(
                    request_client.request_builder.balance_summary(),
                    endpoint_type="request_url",
                    codec=codec,
                ),
                "buying_power": diagnose_account_request_shape(
                    request_client.request_builder.buying_power(),
                    endpoint_type="request_url",
                    codec=codec,
                ),
            },
            "field_mapping_diagnosis": {
                "account_summary": diagnose_account_balance_keys(account_response.raw),
                "buying_power": diagnose_account_balance_keys(buying_power_response.raw),
            },
            "cause_classification": classify_account_balance_issue(
                account_error=account_error,
                buying_power_error=buying_power_error,
                account_shape=diagnose_account_request_shape(
                    request_client.request_builder.balance_summary(),
                    endpoint_type="request_url",
                    codec=codec,
                ),
                buying_power_shape=diagnose_account_request_shape(
                    request_client.request_builder.buying_power(),
                    endpoint_type="request_url",
                    codec=codec,
                ),
                account_field_diagnosis=diagnose_account_balance_keys(account_response.raw),
                buying_power_field_diagnosis=diagnose_account_balance_keys(buying_power_response.raw),
            ),
            "logout": logout_payload,
            "account_api_called": True,
            "balance_api_called": True,
            "positions_api_called": False,
            "orders_api_called": False,
            "executions_api_called": False,
            "quotes_api_called": False,
            "paper_ledger_updated": False,
            "broker_snapshot_updated": False,
            "secret_saved": False,
            "virtual_url_saved": False,
            "raw_response_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path)
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_CONFIGURATION", str(exc), source=source, diagnosis=diagnosis, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual smoke CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_READONLY", str(exc), source=source, diagnosis=diagnosis, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path, message=str(payload["message"]))


def run_tachibana_account_transport_diagnosis(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10l3_tachibana_account_transport_diagnosis_result.json",
    source: str = "phase10l3_account_post_transport_compatibility_diagnosis",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
) -> TachibanaAccountSmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _skipped_payload(resolved_settings, source, "Explicit run flag was not provided; no Tachibana account transport diagnosis was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = _skipped_payload(resolved_settings, source, "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana account transport diagnosis was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])

    session = None
    auth_settings = resolved_settings
    codec = TachibanaV4R9Codec()
    logout_payload: dict[str, Any] = {"attempted": False, "status": "NOT_EXECUTED"}
    modes = ("json_body", "form_urlencoded_json_string")
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
        auth_client = TachibanaReadOnlyClient(auth_settings, auth_transport)
        decryptor = OpenSslRsaOaepDecryptor(
            auth_settings.require_private_key_file(),
            key_format=auth_settings.private_key_format,
            fallback_private_key_file=fallback_key_file,
        )
        session = auth_client.login(decrypt_url=decryptor)
        mode_results = [
            _diagnose_account_transport_mode(
                auth_settings=auth_settings,
                session_request_url=session.request_url,
                codec=codec,
                body_mode=mode,
                builder=auth_client.request_builder,
            )
            for mode in modes
        ]
        logout_payload = _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
        classification = classify_transport_compatibility(mode_results)
        payload = {
            "status": _transport_diagnosis_status(classification, logout_payload),
            "executed": True,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": auth_settings.environment,
            "login": {"status": "PASS"},
            "logout": logout_payload,
            "run_count": len(mode_results),
            "mode_results": mode_results,
            "cause_classification": classification,
            "account_api_called": True,
            "balance_api_called": True,
            "positions_api_called": False,
            "orders_api_called": False,
            "executions_api_called": False,
            "quotes_api_called": False,
            "paper_ledger_updated": False,
            "broker_snapshot_updated": False,
            "secret_saved": False,
            "virtual_url_saved": False,
            "request_body_values_saved": False,
            "raw_response_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path)
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_CONFIGURATION", str(exc), source=source, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual diagnosis CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_READONLY", str(exc), source=source, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path, message=str(payload["message"]))


def run_tachibana_account_error_reveal(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10l4_tachibana_account_error_reveal_result.json",
    source: str = "phase10l4_account_protocol_error_reveal",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
) -> TachibanaAccountSmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _skipped_payload(resolved_settings, source, "Explicit run flag was not provided; no Tachibana account error reveal was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = _skipped_payload(resolved_settings, source, "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana account error reveal was executed.")
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])

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
        auth_client = TachibanaReadOnlyClient(auth_settings, auth_transport)
        decryptor = OpenSslRsaOaepDecryptor(
            auth_settings.require_private_key_file(),
            key_format=auth_settings.private_key_format,
            fallback_private_key_file=fallback_key_file,
        )
        session = auth_client.login(decrypt_url=decryptor)
        request_transport = HttpPostBrokerTransport(
            endpoint_url=session.request_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        request_client = TachibanaReadOnlyClient(auth_settings, request_transport, builder=auth_client.request_builder)
        account_payload = request_client.request_builder.balance_summary()
        buying_payload = request_client.request_builder.buying_power()
        account_response = request_client.get_account_summary()
        buying_power_response = request_client.get_buying_power()
        account_reveal = reveal_protocol_error(account_response.raw, request_payload=account_payload, endpoint_type="request_url", body_mode="json_body", codec=codec)
        buying_power_reveal = reveal_protocol_error(buying_power_response.raw, request_payload=buying_payload, endpoint_type="request_url", body_mode="json_body", codec=codec)
        logout_payload = _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
        classification = classify_revealed_account_error([account_reveal, buying_power_reveal])
        payload = {
            "status": "FAILED_READONLY" if classification["primary"] != "NONE_DETECTED" else "PASS",
            "executed": True,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": auth_settings.environment,
            "login": {"status": "PASS"},
            "logout": logout_payload,
            "revealed_errors": {
                "account_summary": account_reveal,
                "buying_power": buying_power_reveal,
            },
            "cause_classification": classification,
            "account_api_called": True,
            "balance_api_called": True,
            "positions_api_called": False,
            "orders_api_called": False,
            "executions_api_called": False,
            "quotes_api_called": False,
            "paper_ledger_updated": False,
            "broker_snapshot_updated": False,
            "secret_saved": False,
            "virtual_url_saved": False,
            "request_body_values_saved": False,
            "raw_response_saved": False,
            "p_errno_saved": True,
            "p_err_saved": True,
        }
        _write_json(report_path, payload)
        return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path)
    except BrokerConfigurationError as exc:
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_CONFIGURATION", str(exc), source=source, logout=logout_payload)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual reveal CLI.
        if session is not None:
            logout_payload = _logout(TachibanaReadOnlyClient(auth_settings, _dummy_transport()), session, auth_settings=auth_settings, codec=codec)
        payload = _failure_payload(auth_settings, "FAILED_READONLY", str(exc), source=source, logout=logout_payload)
    _write_json(report_path, payload)
    return TachibanaAccountSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path, message=str(payload["message"]))


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


def _failure_payload(
    settings: BrokerSettings,
    status: str,
    message: str,
    *,
    source: str,
    diagnosis: dict[str, Any] | None = None,
    logout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "executed": True,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": "Tachibana account/balance read-only smoke failed closed.",
        "failure_classification": _classify_failure(message),
        "diagnosis": diagnosis or {},
        "login": {"status": "UNKNOWN_OR_FAILED"},
        "logout": logout or {"attempted": False, "status": "NOT_EXECUTED"},
        "account_api_called": False,
        "balance_api_called": False,
        "positions_api_called": False,
        "orders_api_called": False,
        "executions_api_called": False,
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


def _snapshot_dict(snapshot: BrokerBalanceSnapshot) -> dict[str, Any]:
    data = asdict(snapshot)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, tuple):
            data[key] = list(value)
    data.pop("snapshot_id", None)
    return sanitize_mapping(data)


def _response_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "sCLMID": str(raw.get("sCLMID") or ""),
        "sResultCode": str(raw.get("sResultCode") or ""),
        "sResultText_classification": "empty" if not str(raw.get("sResultText") or "").strip() else "present",
        "api_error_number_present": "p_errno" in raw,
        "api_error_text_present": "p_err" in raw,
        "sanitized_key_names": sorted(_sanitize_field_name(str(key)) for key in raw.keys()),
    }


def classify_protocol_error(raw: dict[str, Any]) -> dict[str, Any]:
    errno = raw.get("p_errno")
    errno_text = "" if errno is None else str(errno).strip()
    errno_numeric = _decimal_or_none(errno) is not None
    errno_zero = errno_numeric and _decimal_or_none(errno) == 0
    p_err = raw.get("p_err")
    p_err_text = "" if p_err is None else str(p_err)
    return sanitize_mapping(
        {
            "p_errno_present": "p_errno" in raw,
            "p_errno_numeric": errno_numeric,
            "p_errno_zero": errno_zero,
            "p_errno_digit_length": _digit_length(errno_text) if errno_numeric else 0,
            "p_err_present": "p_err" in raw,
            "p_err_empty": not p_err_text.strip(),
            "p_err_length_bucket": _length_bucket(len(p_err_text)),
            "p_err_classification": _classify_error_text(p_err_text),
            "protocol_error_present": ("p_errno" in raw and not errno_zero) or ("p_err" in raw and bool(p_err_text.strip())),
        }
    )


def diagnose_account_request_shape(payload: dict[str, Any], *, endpoint_type: str, codec: TachibanaV4R9Codec | None = None) -> dict[str, Any]:
    encoded = codec.encode_request(payload) if codec is not None else payload
    clmid = str(payload.get("sCLMID") or "")
    return sanitize_mapping(
        {
            "sclmid": clmid,
            "sclmid_supported": clmid in {"CLMZanKaiSummary", "CLMZanKaiKanougaku"},
            "endpoint_type": endpoint_type,
            "http_method": "POST",
            "content_type": "application/json; charset=utf-8",
            "official_sample_post_content_type": "not_explicit_in_mfds_json_api_request_post_js",
            "payload_compressed": codec is not None,
            "p_no_present": "p_no" in payload,
            "p_sd_date_present": "p_sd_date" in payload,
            "sIssueCode_present": "sIssueCode" in payload,
            "sSizyouC_present": "sSizyouC" in payload,
            "encoded_key_names": sorted(str(key) for key in encoded.keys()),
            "encoded_sclmid_key": _encoded_key_for("sCLMID", codec=codec),
            "encoded_p_no_key": _encoded_key_for("p_no", codec=codec),
            "encoded_p_sd_date_key": _encoded_key_for("p_sd_date", codec=codec),
            "values_saved": False,
        }
    )


def classify_account_balance_issue(
    *,
    account_error: dict[str, Any],
    buying_power_error: dict[str, Any],
    account_shape: dict[str, Any],
    buying_power_shape: dict[str, Any],
    account_field_diagnosis: dict[str, Any],
    buying_power_field_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    request_shape_missing = not (
        account_shape.get("sclmid_supported")
        and account_shape.get("p_no_present")
        and account_shape.get("p_sd_date_present")
        and buying_power_shape.get("sclmid_supported")
        and buying_power_shape.get("p_no_present")
        and buying_power_shape.get("p_sd_date_present")
        and buying_power_shape.get("sIssueCode_present")
        and buying_power_shape.get("sSizyouC_present")
    )
    protocol_error = bool(account_error.get("protocol_error_present")) or bool(buying_power_error.get("protocol_error_present"))
    business_fields_present = _business_fields_present(account_field_diagnosis) or _business_fields_present(buying_power_field_diagnosis)
    if request_shape_missing:
        primary = "REQUEST_SHAPE_MISSING_FIELD"
        candidates = ["REQUEST_SHAPE_MISSING_FIELD"]
    elif protocol_error and not business_fields_present:
        primary = "UNKNOWN_PROTOCOL_ERROR"
        candidates = ["UNKNOWN_PROTOCOL_ERROR", "DEMO_API_LIMITATION", "ACCOUNT_PERMISSION_OR_STATE"]
    elif not business_fields_present:
        primary = "NORMALIZER_FIELD_MAPPING"
        candidates = ["NORMALIZER_FIELD_MAPPING"]
    else:
        primary = "NONE_DETECTED"
        candidates = []
    return {
        "primary": primary,
        "candidates": candidates,
        "request_shape_missing": request_shape_missing,
        "protocol_error_present": protocol_error,
        "business_fields_present": business_fields_present,
    }


def classify_transport_compatibility(mode_results: list[dict[str, Any]]) -> dict[str, Any]:
    current = next((item for item in mode_results if item.get("body_mode") == "json_body"), {})
    alternate = next((item for item in mode_results if item.get("body_mode") == "form_urlencoded_json_string"), {})
    current_business = bool(current.get("business_fields_present"))
    alternate_business = bool(alternate.get("business_fields_present"))
    current_protocol_error = bool(current.get("protocol_error_present"))
    alternate_protocol_error = bool(alternate.get("protocol_error_present"))
    if alternate_business and not current_business:
        primary = "POST_BODY_MODE_MISMATCH"
        candidates = ["POST_BODY_MODE_MISMATCH", "CONTENT_TYPE_MISMATCH"]
    elif current_business:
        primary = "NONE_DETECTED"
        candidates = []
    elif current_protocol_error and alternate_protocol_error:
        primary = "UNKNOWN_PROTOCOL_ERROR"
        candidates = ["UNKNOWN_PROTOCOL_ERROR", "ACCOUNT_PERMISSION_OR_STATE", "DEMO_API_LIMITATION"]
    else:
        primary = "UNKNOWN_PROTOCOL_ERROR"
        candidates = ["UNKNOWN_PROTOCOL_ERROR"]
    return {
        "primary": primary,
        "candidates": candidates,
        "current_mode_business_fields_present": current_business,
        "alternate_mode_business_fields_present": alternate_business,
        "current_mode_protocol_error_present": current_protocol_error,
        "alternate_mode_protocol_error_present": alternate_protocol_error,
    }


def reveal_protocol_error(
    raw: dict[str, Any],
    *,
    request_payload: dict[str, Any],
    endpoint_type: str,
    body_mode: str,
    codec: TachibanaV4R9Codec | None = None,
) -> dict[str, Any]:
    fields = diagnose_account_balance_keys(raw)
    return sanitize_mapping(
        {
            "clmid": str(raw.get("sCLMID") or request_payload.get("sCLMID") or ""),
            "p_errno": "" if raw.get("p_errno") is None else str(raw.get("p_errno")),
            "p_err": "" if raw.get("p_err") is None else str(raw.get("p_err")),
            "p_errno_saved": True,
            "p_err_saved": True,
            "business_fields_present": _business_fields_present(fields),
            "request_shape_summary": diagnose_account_request_shape(request_payload, endpoint_type=endpoint_type, codec=codec),
            "endpoint_type": endpoint_type,
            "body_mode": body_mode,
            "environment": "demo",
            "raw_response_saved": False,
            "request_body_values_saved": False,
        }
    )


def classify_revealed_account_error(revealed_errors: list[dict[str, Any]]) -> dict[str, Any]:
    texts = " ".join(str(item.get("p_err") or "") for item in revealed_errors).lower()
    errno_values = sorted({str(item.get("p_errno") or "") for item in revealed_errors})
    business_present = any(bool(item.get("business_fields_present")) for item in revealed_errors)
    if business_present:
        primary = "NONE_DETECTED"
        candidates: list[str] = []
    elif "p_no" in texts or "前要求" in texts or "引数" in texts or "session" in texts or "セッション" in texts or "ログイン" in texts:
        primary = "REQUEST_PRECONDITION_MISSING"
        candidates = ["REQUEST_PRECONDITION_MISSING", "ACCOUNT_PERMISSION_OR_STATE"]
    elif "service" in texts or "利用" in texts or "demo" in texts or "デモ" in texts:
        primary = "DEMO_API_LIMITATION"
        candidates = ["DEMO_API_LIMITATION", "ACCOUNT_PERMISSION_OR_STATE"]
    elif "permission" in texts or "権限" in texts or "許可" in texts:
        primary = "ACCOUNT_PERMISSION_OR_STATE"
        candidates = ["ACCOUNT_PERMISSION_OR_STATE"]
    elif "clmid" in texts or "未定義" in texts:
        primary = "INVALID_CLMID_FOR_DEMO"
        candidates = ["INVALID_CLMID_FOR_DEMO", "API_SPEC_MISMATCH"]
    elif any(value and value != "0" for value in errno_values):
        primary = "UNKNOWN_PROTOCOL_ERROR"
        candidates = ["UNKNOWN_PROTOCOL_ERROR", "ACCOUNT_PERMISSION_OR_STATE", "DEMO_API_LIMITATION"]
    else:
        primary = "API_SPEC_MISMATCH"
        candidates = ["API_SPEC_MISMATCH", "UNKNOWN_PROTOCOL_ERROR"]
    return {
        "primary": primary,
        "candidates": candidates,
        "p_errno_values": errno_values,
        "business_fields_present": business_present,
    }


def diagnose_account_balance_keys(raw: dict[str, Any]) -> dict[str, Any]:
    fields = []
    nonzero_numeric = 0
    candidate_fields: dict[str, list[str]] = {key: [] for key in WEB_DISPLAY_REFERENCE_AMOUNTS}
    for key in sorted(str(item) for item in raw.keys()):
        value = raw.get(key)
        entry = _diagnose_field(key, value)
        fields.append(entry)
        numeric = _decimal_or_none(value)
        if numeric is not None and numeric != 0:
            nonzero_numeric += 1
            for label, amount in WEB_DISPLAY_REFERENCE_AMOUNTS.items():
                if numeric == amount:
                    candidate_fields[label].append(_sanitize_field_name(key))
    return sanitize_mapping(
        {
            "field_count": len(raw),
            "nonzero_numeric_field_count": nonzero_numeric,
            "fields": fields,
            "web_display_candidates": {
                label: {
                    "matches_web_display_candidate": bool(names),
                    "candidate_field_names": names,
                }
                for label, names in candidate_fields.items()
            },
        }
    )


def _diagnose_account_transport_mode(
    *,
    auth_settings: BrokerSettings,
    session_request_url: str,
    codec: TachibanaV4R9Codec,
    body_mode: str,
    builder,
) -> dict[str, Any]:
    transport = HttpPostBrokerTransport(
        endpoint_url=session_request_url,
        timeout_seconds=auth_settings.timeout_seconds,
        rate_limit_per_second=auth_settings.rate_limit_per_second,
        codec=codec,
        body_mode=body_mode,  # type: ignore[arg-type]
    )
    client = TachibanaReadOnlyClient(auth_settings, transport, builder=builder)
    account_payload = client.request_builder.balance_summary()
    buying_payload = client.request_builder.buying_power()
    account_response = client.get_account_summary()
    buying_power_response = client.get_buying_power()
    account_error = classify_protocol_error(account_response.raw)
    buying_power_error = classify_protocol_error(buying_power_response.raw)
    account_fields = diagnose_account_balance_keys(account_response.raw)
    buying_fields = diagnose_account_balance_keys(buying_power_response.raw)
    account_business = _business_fields_present(account_fields)
    buying_business = _business_fields_present(buying_fields)
    return sanitize_mapping(
        {
            "body_mode": body_mode,
            "account_summary": {
                "response_summary": _response_summary(account_response.raw),
                "protocol_error_diagnosis": account_error,
                "field_mapping_diagnosis": account_fields,
                "request_shape_diagnosis": diagnose_account_request_shape(account_payload, endpoint_type="request_url", codec=codec),
                "post_transport_diagnosis": transport.diagnose_post_shape(account_payload, endpoint_type="request_url"),
            },
            "buying_power": {
                "response_summary": _response_summary(buying_power_response.raw),
                "protocol_error_diagnosis": buying_power_error,
                "field_mapping_diagnosis": buying_fields,
                "request_shape_diagnosis": diagnose_account_request_shape(buying_payload, endpoint_type="request_url", codec=codec),
                "post_transport_diagnosis": transport.diagnose_post_shape(buying_payload, endpoint_type="request_url"),
            },
            "business_fields_present": account_business or buying_business,
            "protocol_error_present": bool(account_error.get("protocol_error_present")) or bool(buying_power_error.get("protocol_error_present")),
            "raw_response_saved": False,
            "request_body_values_saved": False,
        }
    )


def _transport_diagnosis_status(classification: dict[str, Any], logout_payload: dict[str, Any]) -> str:
    if classification.get("alternate_mode_business_fields_present") or classification.get("current_mode_business_fields_present"):
        return "PASS" if logout_payload.get("status") == "PASS" else "PASS_WITH_LOGOUT_WARNING"
    return "FAILED_READONLY"


def _business_fields_present(diagnosis: dict[str, Any]) -> bool:
    expected = {
        "sSummaryGenkabuKaituke",
        "sGenbutuKabuKaituke",
        "sSyukkin",
        "sSyukkinKanougaku",
        "sIPOKounyu",
        "sSinyouSinkidate",
        "sSummaryNseityouTousiKanougaku",
    }
    return any(item.get("key") in expected for item in diagnosis.get("fields", []) if isinstance(item, dict))


def _diagnose_field(key: str, value: Any) -> dict[str, Any]:
    numeric = _decimal_or_none(value)
    text = "" if value is None else str(value).replace(",", "").strip()
    return {
        "key": _sanitize_field_name(key),
        "value_type": type(value).__name__,
        "numeric_convertible": numeric is not None,
        "numeric_zero_classification": "nonzero" if numeric not in (None, Decimal("0")) else ("zero" if numeric == 0 else "not_numeric"),
        "digit_length": _digit_length(text) if numeric is not None else 0,
        "present": value is not None,
    }


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except Exception:  # noqa: BLE001 - diagnosis only, value is not persisted.
        return None


def _digit_length(text: str) -> int:
    stripped = text.lstrip("-")
    if "." in stripped:
        stripped = stripped.split(".", 1)[0]
    return len(stripped) if stripped.isdigit() else 0


def _length_bucket(length: int) -> str:
    if length == 0:
        return "empty"
    if length <= 20:
        return "short"
    if length <= 80:
        return "medium"
    return "long"


def _classify_error_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "empty"
    lowered = stripped.lower()
    if "session" in lowered or "セッション" in stripped:
        return "session_related"
    if "auth" in lowered or "認証" in stripped:
        return "auth_related"
    if "request" in lowered or "parameter" in lowered or "パラメ" in stripped:
        return "request_or_parameter_related"
    if "permission" in lowered or "権限" in stripped:
        return "permission_related"
    if "service" in lowered or "利用" in stripped:
        return "service_availability_related"
    if "internal" in lowered or "exception" in lowered:
        return "client_internal_error_related"
    return "present_nonempty"


def _encoded_key_for(key: str, *, codec: TachibanaV4R9Codec | None) -> str:
    if codec is None:
        return key
    encoded = codec.encode_request({key: ""})
    return next(iter(encoded.keys()))


def _sanitize_field_name(key: str) -> str:
    lowered = key.lower()
    sensitive_tokens = ("auth", "password", "passwd", "secret", "token", "customer", "account", "kouza", "koza")
    if any(token in lowered for token in sensitive_tokens):
        return "[REDACTED_FIELD_NAME]"
    return key


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
    return "account_balance_readonly_error"


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
            raise BrokerConfigurationError("No account smoke transport is available.")

    return DummyTransport()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_mapping(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
