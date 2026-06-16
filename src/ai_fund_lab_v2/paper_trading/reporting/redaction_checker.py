from __future__ import annotations

from dataclasses import dataclass


PUBLIC_REPORT_READY = "PUBLIC_REPORT_READY"
PUBLIC_REPORT_NOT_READY = "PUBLIC_REPORT_NOT_READY"

FORBIDDEN_PUBLIC_TERMS: tuple[str, ...] = (
    "raw model score",
    "raw internal score",
    "feature value",
    "feature schema hash",
    "feature_schema_hash",
    "artifact path",
    "model artifact hash",
    "model_artifact_hash",
    "safety internals",
    "broker account data",
    "account id",
    "secret",
    "api key",
    "unlock_trade",
)


@dataclass(frozen=True)
class RedactionCheckResult:
    status: str
    violations: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.status == PUBLIC_REPORT_READY

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "violations": list(self.violations), "ready": self.ready}


class PublicReportNotReadyError(ValueError):
    pass


def check_public_report_redaction(text: str, *, forbidden_terms: tuple[str, ...] = FORBIDDEN_PUBLIC_TERMS) -> RedactionCheckResult:
    normalized = text.lower()
    violations = tuple(term for term in forbidden_terms if term.lower() in normalized)
    status = PUBLIC_REPORT_READY if not violations else PUBLIC_REPORT_NOT_READY
    return RedactionCheckResult(status=status, violations=violations)


def assert_public_report_ready(text: str) -> RedactionCheckResult:
    result = check_public_report_redaction(text)
    if not result.ready:
        raise PublicReportNotReadyError(f"PUBLIC_REPORT_NOT_READY: {', '.join(result.violations)}")
    return result
