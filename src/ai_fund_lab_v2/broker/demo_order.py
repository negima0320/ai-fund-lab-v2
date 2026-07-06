from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.retry_policy import BrokerRetryPolicy, run_retryable_call
from ai_fund_lab_v2.broker.secrets import TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import _resolve_fallback_key_file
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
    normalize_redacted_order_submit_result,
)
from ai_fund_lab_v2.broker.transport import DemoOrderBrokerTransport, HttpPostBrokerTransport
from ai_fund_lab_v2.runtime.order_command import OrderCommand


@dataclass(frozen=True)
class DemoOrderWireResult:
    status: str
    clm_kabu_new_order_called: bool
    demo_order_executed: bool
    broker_order_api_called: bool
    response: dict[str, Any]
    logout_status: str = "NOT_EXECUTED"
    error_classification: str = ""
    submit_classification: str = "PRE_SEND_FAILURE"
    classification_source: str = "tachibana_demo_order_adapter"
    post_send_unknown: bool = False
    retry_attempts: int = 1
    attempts: list[dict[str, Any]] = field(default_factory=list)
    broker_readonly_confirmation_attempted: bool = False
    broker_readonly_confirmation_status: str = "NOT_REQUIRED"
    raw_broker_order_id_saved: bool = False
    raw_request_saved: bool = False
    raw_response_saved: bool = False
    secret_saved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TachibanaDemoOrderAdapter:
    settings: BrokerSettings | None = None

    def submit_cash_stock_order(self, command: OrderCommand) -> DemoOrderWireResult:
        resolved_settings = self.settings or load_broker_settings()
        session = None
        logout_status = "NOT_EXECUTED"
        send_started = False
        auth_client = None
        auth_settings = resolved_settings
        codec = TachibanaV4R9Codec()
        attempts: list[dict[str, Any]] = []
        try:
            resolved_settings.require_demo_environment()
            secrets = TachibanaSecretLoader(resolved_settings).load()
            auth_settings = replace(
                resolved_settings,
                auth_id=secrets.auth_id,
                auth_id_file=secrets.auth_id_file,
                private_key_file=secrets.private_key_file,
                private_key_format=secrets.private_key_format,
                rate_limit_per_second=min(resolved_settings.rate_limit_per_second, 5.0),
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
            login_result = run_retryable_call(
                lambda: auth_client.login(decrypt_url=decryptor),
                policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=2.0),
                failure_stage="login_session",
                classification="FAILED_LOGIN_SESSION",
            )
            session = login_result.value
            attempts.extend(login_result.attempts_dicts())
            request = TachibanaCashStockOrderRequest.from_order_command(command, second_password_present=True)
            builder = TachibanaCashStockOrderRequestBuilder(sequence_manager=auth_client.request_builder.sequence_manager)
            second_password_value = TachibanaSecretLoader(auth_settings).load_second_password_value_for_demo_order_only()
            try:
                payload = builder.build_final_payload_with_second_password(request, second_password_value=second_password_value)
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
            normalized = normalize_redacted_order_submit_result(raw).to_dict()
            logout_status = _logout(auth_client, session, auth_settings=auth_settings, codec=codec)
            accepted = bool(normalized.get("accepted"))
            return DemoOrderWireResult(
                status=str(normalized.get("status") or "UNKNOWN"),
                clm_kabu_new_order_called=True,
                demo_order_executed=accepted,
                broker_order_api_called=True,
                response=normalized,
                logout_status=logout_status,
                submit_classification="ACCEPTED" if accepted else "BROKER_REJECTED",
                classification_source="broker_order_api_response",
                attempts=attempts,
                raw_broker_order_id_saved=False,
            )
        except (BrokerConfigurationError, Exception) as exc:  # noqa: BLE001 - fail closed at adapter boundary.
            attempts.extend(record.to_dict() for record in getattr(exc, "attempts", []))
            if session is not None and auth_client is not None:
                try:
                    logout_status = _logout(auth_client, session, auth_settings=auth_settings, codec=codec)  # type: ignore[name-defined]
                except Exception:  # noqa: BLE001
                    logout_status = "LOGOUT_FAILED_REDACTED"
            classification = "POST_SEND_UNKNOWN" if send_started else "PRE_SEND_FAILURE"
            return DemoOrderWireResult(
                status=classification,
                clm_kabu_new_order_called=send_started,
                demo_order_executed=False,
                broker_order_api_called=send_started,
                response={
                    "status": classification,
                    "accepted": False,
                    "rejected": not send_started,
                    "reason": type(exc).__name__,
                    "submit_classification": classification,
                    "raw_order_id_saved": False,
                    "raw_response_saved": False,
                },
                logout_status=logout_status,
                error_classification=type(exc).__name__,
                submit_classification=classification,
                post_send_unknown=send_started,
                retry_attempts=len(attempts) or 1,
                attempts=attempts,
                broker_readonly_confirmation_status="PENDING" if send_started else "NOT_REQUIRED",
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
    except Exception:  # noqa: BLE001 - logout is best-effort and must not change submit classification.
        return "BEST_EFFORT_FAILED"
    return "PASS" if response.is_success() else "LOGOUT_WARNING"
