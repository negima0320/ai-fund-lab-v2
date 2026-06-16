from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


def approval_id() -> str:
    return f"approval_{uuid4().hex}"


@dataclass(frozen=True)
class HumanReviewApprovalRecord:
    plan_id: str
    reviewer: str
    decision: str
    comment: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    approval_id: str = field(default_factory=approval_id)
    approval_does_not_allow_live_order: bool = True

    def __post_init__(self) -> None:
        if self.decision not in {"approved", "rejected", "needs_change"}:
            raise ValueError("Unsupported review decision.")
        if not self.approval_does_not_allow_live_order:
            raise ValueError("Phase8 approval must not allow live orders.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_approval_record(record: HumanReviewApprovalRecord, runtime_dir: Path | str = ".runtime") -> Path:
    path = Path(runtime_dir) / "order_manager" / "review" / f"{record.approval_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_mapping(record.to_dict()), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

