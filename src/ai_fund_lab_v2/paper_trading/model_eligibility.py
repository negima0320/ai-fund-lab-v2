from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


ELIGIBLE = "ELIGIBLE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"

FORBIDDEN_TRAINING_TERMS = (
    "Paper Ledger",
    "Broker Snapshot",
    "realized PnL",
    "selected symbols",
    "bought symbols",
    "cash",
    "portfolio value",
    "backtest results",
    "PM multiplier imitation",
)


@dataclass(frozen=True)
class ModelEligibilityResult:
    status: str
    model_version: str
    blocked_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def eligible(self) -> bool:
        return self.status == ELIGIBLE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_model_eligibility(
    manifest: Mapping[str, Any],
    *,
    decision_for: str,
) -> ModelEligibilityResult:
    blocked: list[str] = []
    warnings: list[str] = []
    model_version = str(manifest.get("model_version") or "")
    if not model_version:
        blocked.append("missing_model_version")
    train_until = str(manifest.get("train_until") or "")
    data_until = str(manifest.get("data_until") or "")
    if not train_until:
        blocked.append("missing_train_until")
    elif train_until > decision_for:
        blocked.append("train_until_after_decision_for")
    if not data_until:
        blocked.append("missing_data_until")
    elif data_until > decision_for:
        blocked.append("data_until_after_decision_for")
    if not str(manifest.get("feature_schema_hash") or ""):
        blocked.append("missing_feature_schema_hash")
    if str(manifest.get("leakage_audit_status") or "").upper() != "OK":
        blocked.append("leakage_audit_not_ok")
    artifact_path = str(manifest.get("artifact_path") or manifest.get("model_artifact_path") or "")
    if artifact_path:
        path = Path(artifact_path)
        if not path.is_file():
            blocked.append("artifact_path_not_readable")
        else:
            try:
                path.open("rb").close()
            except OSError:
                blocked.append("artifact_path_not_readable")
    training_sources = " ".join(str(item) for item in manifest.get("training_sources", ()))
    for term in FORBIDDEN_TRAINING_TERMS:
        if term.lower() in training_sources.lower():
            blocked.append(f"forbidden_training_source_{term.lower().replace(' ', '_')}")
    status = ELIGIBLE if not blocked else NOT_ELIGIBLE
    if not artifact_path:
        warnings.append("artifact_path_not_provided")
    return ModelEligibilityResult(
        status=status,
        model_version=model_version,
        blocked_reasons=tuple(blocked),
        warnings=tuple(warnings),
    )

