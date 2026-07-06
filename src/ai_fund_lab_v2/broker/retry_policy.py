from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class BrokerAttemptRecord:
    attempt: int
    failure_stage: str
    safe_error_class: str
    retryable: bool
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrokerRetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 2.0
    retryable_classifications: tuple[str, ...] = (
        "FAILED_LOGIN_SESSION",
        "FAILED_BROKER_READONLY_FETCH",
        "FAILED_LOGOUT",
    )


@dataclass(frozen=True)
class BrokerRetryResult(Generic[T]):
    value: T
    attempts: list[BrokerAttemptRecord]
    retry_attempts: int
    elapsed_ms: int

    def attempts_dicts(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.attempts]


def run_retryable_call(
    func: Callable[[], T],
    *,
    policy: BrokerRetryPolicy,
    failure_stage: str,
    classification: str,
    sleep_func: Callable[[float], None] = time.sleep,
) -> BrokerRetryResult[T]:
    attempts_limit = max(1, int(policy.max_attempts))
    attempts: list[BrokerAttemptRecord] = []
    started = time.perf_counter()
    for attempt in range(1, attempts_limit + 1):
        try:
            value = func()
            return BrokerRetryResult(
                value=value,
                attempts=attempts,
                retry_attempts=attempt,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            retryable = classification in policy.retryable_classifications and attempt < attempts_limit
            attempts.append(
                BrokerAttemptRecord(
                    attempt=attempt,
                    failure_stage=failure_stage,
                    safe_error_class=exc.__class__.__name__,
                    retryable=retryable,
                    classification=classification,
                )
            )
            if not retryable:
                try:
                    setattr(exc, "attempts", attempts)
                except Exception:
                    pass
                raise
            sleep_func(max(0.0, float(policy.backoff_seconds)))
    raise RuntimeError("retry loop exhausted unexpectedly")


def classify_failure_stage(message: str, *, default_stage: str = "broker_api") -> str:
    normalized = message.lower()
    if "decrypt" in normalized or "session" in normalized or "login" in normalized:
        return "login_session"
    if "timeout" in normalized or "timed out" in normalized or "socket" in normalized or "urlopen" in normalized or "http" in normalized:
        return "readonly_fetch"
    if "parse" in normalized or "decode" in normalized or "normalize" in normalized:
        return "readonly_parse"
    return default_stage


def safe_attempts(attempts: list[BrokerAttemptRecord]) -> list[dict[str, Any]]:
    return [attempt.to_dict() for attempt in attempts]
