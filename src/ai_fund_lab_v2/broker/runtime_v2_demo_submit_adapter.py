"""Tachibana Demo Submit adapter for Runtime v2-native submit commands."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.config_diagnostics import build_broker_configuration_diagnostic
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.retry_policy import BrokerRetryPolicy, run_retryable_call
from ai_fund_lab_v2.broker.secrets import TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import (
    DEMO_BASE_URL,
    PROD_BASE_URL,
    BrokerConfigurationError,
    BrokerSettings,
    load_broker_settings,
)
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import _resolve_fallback_key_file
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
    TachibanaOrderRequestError,
    normalize_redacted_order_submit_result,
)
from ai_fund_lab_v2.broker.transport import DemoOrderBrokerTransport, HttpPostBrokerTransport
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


@dataclass(frozen=True)
class RuntimeV2TachibanaDemoSubmitAdapter:
    """Dry-run first adapter boundary for Runtime v2 Demo Submit.

    The adapter accepts RuntimeV2SubmitCommand directly. It does not require or
    construct legacy runtime OrderCommand/RuntimeMode as submit authority.
    """

    settings: BrokerSettings | None = None
    dry_run: bool = True

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        settings = self.settings or load_broker_settings()
        blocked_reason = _blocked_reason(command, settings)
        if blocked_reason:
            diagnostic = build_broker_configuration_diagnostic(settings)
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason=blocked_reason,
                configuration_diagnostic=diagnostic,
                next_action=diagnostic["next_action"],
            )
        try:
            request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
                command,
                second_password_present=bool(settings.second_password_file),
            )
        except TachibanaOrderRequestError as exc:
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason=str(exc),
            )
        summary = TachibanaCashStockOrderRequestBuilder().build_final_payload_summary(
            request,
            dry_run=True,
        )
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason=f"runtime_v2_tachibana_demo_submit_dry_run_ready:{summary['sCLMID']}",
            issue_code_normalization=dict(request.issue_code_normalization),
            response_classification={},
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if self.dry_run:
            return self.preflight(command)
        settings = self.settings or load_broker_settings()
        blocked_reason = _blocked_reason(command, settings)
        if blocked_reason:
            diagnostic = build_broker_configuration_diagnostic(settings)
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason=blocked_reason,
                configuration_diagnostic=diagnostic,
                next_action=diagnostic["next_action"],
            )
        try:
            request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
                command,
                second_password_present=True,
            )
        except TachibanaOrderRequestError as exc:
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason=str(exc),
            )
        session = None
        auth_client = None
        auth_settings = settings
        codec = TachibanaV4R9Codec()
        send_started = False
        try:
            settings.require_demo_environment()
            secrets = TachibanaSecretLoader(settings).load()
            auth_settings = replace(
                settings,
                auth_id=secrets.auth_id,
                auth_id_file=secrets.auth_id_file,
                private_key_file=secrets.private_key_file,
                private_key_format=secrets.private_key_format,
                rate_limit_per_second=min(settings.rate_limit_per_second, 5.0),
            )
            auth_client = TachibanaReadOnlyClient(
                auth_settings,
                HttpPostBrokerTransport(
                    endpoint_url=auth_settings.auth_url,
                    timeout_seconds=auth_settings.timeout_seconds,
                    rate_limit_per_second=auth_settings.rate_limit_per_second,
                    codec=codec,
                ),
            )
            decryptor = OpenSslRsaOaepDecryptor(
                auth_settings.require_private_key_file(),
                key_format=auth_settings.private_key_format,
                fallback_private_key_file=_resolve_fallback_key_file(auth_settings),
            )
            login = run_retryable_call(
                lambda: auth_client.login(decrypt_url=decryptor),
                policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=2.0),
                failure_stage="login_session",
                classification="FAILED_LOGIN_SESSION",
            )
            session = login.value
            builder = TachibanaCashStockOrderRequestBuilder(sequence_manager=auth_client.request_builder.sequence_manager)
            second_password_value = TachibanaSecretLoader(auth_settings).load_second_password_value_for_demo_order_only()
            try:
                payload = builder.build_final_payload_with_second_password(
                    request,
                    second_password_value=second_password_value,
                )
                object.__setattr__(auth_client.request_builder, "sequence_no", builder.sequence_no)
                order_transport = DemoOrderBrokerTransport(
                    endpoint_url=session.request_url,
                    settings=auth_settings,
                    demo_order_wire_execution=True,
                    production_order_allowed=False,
                    timeout_seconds=auth_settings.timeout_seconds,
                    rate_limit_per_second=auth_settings.rate_limit_per_second,
                    codec=codec,
                )
                send_started = True
                raw = order_transport.request(payload)
            finally:
                second_password_value = ""
            normalized = normalize_redacted_order_submit_result(raw)
            _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
            return RuntimeV2SubmitResult(
                status=normalized.status,
                submitted=True,
                accepted=normalized.accepted,
                blocked=False,
                review_required=not normalized.accepted,
                broker_api_called=True,
                broker_order_id_hash=normalized.broker_order_id_hash,
                post_send_unknown=False,
                reason=normalized.reason,
                raw_request_saved=False,
                raw_response_saved=False,
                secret_saved=False,
                issue_code_normalization=dict(request.issue_code_normalization),
                response_classification=_response_classification(normalized),
            )
        except Exception as exc:  # noqa: BLE001 - submit boundary must fail closed and sanitized.
            if session is not None and auth_client is not None:
                try:
                    _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
                except Exception:  # noqa: BLE001 - best effort only.
                    pass
            diagnostic = (
                build_broker_configuration_diagnostic(auth_settings, error=exc)
                if isinstance(exc, BrokerConfigurationError)
                else {}
            )
            return RuntimeV2SubmitResult(
                status="POST_SEND_UNKNOWN" if send_started else "PRE_SEND_FAILURE",
                submitted=send_started,
                accepted=False,
                blocked=not send_started,
                review_required=send_started,
                broker_api_called=send_started,
                post_send_unknown=send_started,
                reason=exc.__class__.__name__,
                issue_code_normalization={},
                response_classification={
                    "p_errno": None,
                    "sResultCode": "",
                    "p_err_classification": "EXCEPTION_AFTER_SEND" if send_started else "EXCEPTION_BEFORE_SEND",
                    "business_classification": "POST_SEND_UNKNOWN" if send_started else "PRE_SEND_FAILURE",
                    "order_number_present": False,
                    "result_code_present": False,
                },
                configuration_diagnostic=diagnostic,
                next_action=str(diagnostic.get("next_action", "")),
            )


def _logout(
    client: TachibanaReadOnlyClient,
    session: Any,
    *,
    auth_settings: BrokerSettings,
    codec: TachibanaV4R9Codec,
) -> str:
    transport = HttpPostBrokerTransport(
        endpoint_url=session.request_url,
        timeout_seconds=auth_settings.timeout_seconds,
        rate_limit_per_second=auth_settings.rate_limit_per_second,
        codec=codec,
    )
    try:
        response = run_retryable_call(
            lambda: client.logout(session, transport=transport),
            policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=1.0),
            failure_stage="logout",
            classification="FAILED_LOGOUT",
        ).value
    except Exception:  # noqa: BLE001 - logout must not change submit classification.
        return "BEST_EFFORT_FAILED"
    return "PASS" if response.is_success() else "LOGOUT_WARNING"


def _blocked_reason(command: RuntimeV2SubmitCommand, settings: BrokerSettings) -> str:
    if command.environment != "demo":
        return "environment guard failure"
    if settings.environment != "demo":
        return "settings environment is not demo"
    if settings.base_url.rstrip("/") == PROD_BASE_URL:
        return "production endpoint blocked"
    if settings.base_url.rstrip("/") != DEMO_BASE_URL:
        return "demo base url guard failure"
    if command.source_current_path != "pending_order_plan/pending_order_plan.json":
        return "submit source must be pending_order_plan current"
    if command.side not in {"BUY", "SELL"}:
        return "unsupported side"
    if command.symbol.startswith("9"):
        return "9000-series symbols excluded from demo fill test candidates"
    if not command.live_order_allowed:
        return "live order disabled"
    if command.quantity <= 0:
        return "quantity must be positive"
    return ""


def _response_classification(normalized: Any) -> dict[str, Any]:
    return {
        "p_errno": normalized.p_errno,
        "sResultCode": normalized.result_code_value,
        "p_err_classification": normalized.p_err_classification,
        "business_classification": normalized.business_classification,
        "order_number_present": normalized.order_number_present,
        "result_code_present": normalized.result_code_present,
        "result_code_zero": normalized.result_code_zero,
        "warning_code_present": normalized.warning_code_present,
        "warning_code_value": normalized.warning_code_value,
        "warning_code_zero": normalized.warning_code_zero,
    }
