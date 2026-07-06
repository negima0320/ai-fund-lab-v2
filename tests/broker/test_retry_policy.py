from __future__ import annotations

from ai_fund_lab_v2.broker.retry_policy import BrokerRetryPolicy, run_retryable_call


def test_run_retryable_call_records_safe_attempts_and_succeeds() -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("timed out")
        return "ok"

    result = run_retryable_call(
        flaky,
        policy=BrokerRetryPolicy(max_attempts=3, backoff_seconds=0),
        failure_stage="readonly_fetch",
        classification="FAILED_BROKER_READONLY_FETCH",
        sleep_func=lambda seconds: sleeps.append(seconds),
    )

    assert result.value == "ok"
    assert result.retry_attempts == 2
    assert result.attempts_dicts() == [
        {
            "attempt": 1,
            "failure_stage": "readonly_fetch",
            "safe_error_class": "TimeoutError",
            "retryable": True,
            "classification": "FAILED_BROKER_READONLY_FETCH",
        }
    ]
    assert sleeps == [0]
