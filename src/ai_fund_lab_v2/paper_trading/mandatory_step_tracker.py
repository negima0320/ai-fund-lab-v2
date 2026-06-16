from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso


STEP_NAMES = ("data_update", "feature_generation", "inference", "report_generation", "human_review", "safety_check")
STEP_STATUSES = {"PENDING", "OK", "SKIPPED", "FAILED", "BLOCKED"}


@dataclass(frozen=True)
class MandatoryStep:
    name: str
    status: str = "PENDING"
    started_at: str = ""
    finished_at: str = ""
    reason: str = ""
    artifact_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.name not in STEP_NAMES:
            raise ValueError(f"Unsupported mandatory step: {self.name}")
        if self.status not in STEP_STATUSES:
            raise ValueError(f"Unsupported mandatory step status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MandatoryStepTracker:
    steps: tuple[MandatoryStep, ...] = field(default_factory=lambda: tuple(MandatoryStep(name=name) for name in STEP_NAMES))

    def update(
        self,
        name: str,
        *,
        status: str,
        reason: str = "",
        artifact_refs: tuple[str, ...] = (),
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> "MandatoryStepTracker":
        replacement = MandatoryStep(
            name=name,
            status=status,
            started_at=started_at if started_at is not None else utc_now_iso(),
            finished_at=finished_at if finished_at is not None else (utc_now_iso() if status in {"OK", "SKIPPED", "FAILED", "BLOCKED"} else ""),
            reason=reason,
            artifact_refs=artifact_refs,
        )
        return MandatoryStepTracker(steps=tuple(replacement if step.name == name else step for step in self.steps))

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [step.to_dict() for step in self.steps], "overall_status": self.overall_status}

    @property
    def overall_status(self) -> str:
        statuses = {step.status for step in self.steps}
        if "FAILED" in statuses:
            return "FAILED"
        if "BLOCKED" in statuses:
            return "BLOCKED"
        if all(status in {"OK", "SKIPPED"} for status in statuses):
            return "OK"
        return "PENDING"

