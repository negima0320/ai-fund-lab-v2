"""Feature-date contract shared by market refresh and Morning planning."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any


REQUIRED_FEATURE_ARTIFACTS = (
    "candidate_features.parquet",
    "opportunity_feature_input.parquet",
    "position_feature_input.parquet",
    "capital_policy_input.parquet",
)


@dataclass(frozen=True)
class FeatureDateContract:
    status: str
    reason: str
    requested_feature_date: str
    selected_feature_date: str
    latest_available_market_date: str
    carryover_used: bool
    carryover_reason: str
    freshness_lag_business_days: int | None
    freshness_limit_business_days: int
    feature_artifact_dir: str
    generated_feature_artifacts: dict[str, str]
    missing_feature_artifacts: tuple[str, ...]
    requested_feature_artifact_dir: str
    requested_missing_feature_artifacts: tuple[str, ...]
    price_source_alignment: str
    contract_artifact_path: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_feature_artifacts"] = list(self.missing_feature_artifacts)
        payload["requested_missing_feature_artifacts"] = list(self.requested_missing_feature_artifacts)
        return payload


def resolve_feature_date_contract(
    *,
    operations_root: Path | str,
    requested_feature_date: str,
    latest_available_market_date: str = "",
    freshness_limit_business_days: int = 1,
) -> FeatureDateContract:
    root = Path(operations_root)
    requested_artifacts, requested_missing = _artifact_status(root, requested_feature_date)
    if not requested_missing:
        return FeatureDateContract(
            status="PASS",
            reason="requested_feature_artifacts_available",
            requested_feature_date=requested_feature_date,
            selected_feature_date=requested_feature_date,
            latest_available_market_date=latest_available_market_date or requested_feature_date,
            carryover_used=False,
            carryover_reason="",
            freshness_lag_business_days=0,
            freshness_limit_business_days=freshness_limit_business_days,
            feature_artifact_dir=str(root / "feature_artifacts" / requested_feature_date),
            generated_feature_artifacts=requested_artifacts,
            missing_feature_artifacts=(),
            requested_feature_artifact_dir=str(root / "feature_artifacts" / requested_feature_date),
            requested_missing_feature_artifacts=(),
            price_source_alignment="selected_feature_date",
        )

    latest = latest_available_market_date or _latest_available_from_markers(root, requested_feature_date)
    if not latest:
        return _missing_contract(
            root=root,
            requested_feature_date=requested_feature_date,
            selected_feature_date=requested_feature_date,
            latest_available_market_date="",
            requested_missing=requested_missing,
            freshness_limit_business_days=freshness_limit_business_days,
            reason="feature_artifacts_missing:no_latest_available_market_date",
        )

    selected_artifacts, selected_missing = _artifact_status(root, latest)
    lag = _business_day_lag(latest, requested_feature_date)
    if selected_missing:
        return _missing_contract(
            root=root,
            requested_feature_date=requested_feature_date,
            selected_feature_date=latest,
            latest_available_market_date=latest,
            requested_missing=requested_missing,
            selected_missing=selected_missing,
            freshness_lag_business_days=lag,
            freshness_limit_business_days=freshness_limit_business_days,
            reason="feature_artifacts_missing:selected_latest_artifacts_missing",
        )
    if lag is None or lag > freshness_limit_business_days:
        return FeatureDateContract(
            status="REVIEW_REQUIRED",
            reason="carryover_stale",
            requested_feature_date=requested_feature_date,
            selected_feature_date=latest,
            latest_available_market_date=latest,
            carryover_used=True,
            carryover_reason="requested_feature_date_missing_but_latest_available_is_stale",
            freshness_lag_business_days=lag,
            freshness_limit_business_days=freshness_limit_business_days,
            feature_artifact_dir=str(root / "feature_artifacts" / latest),
            generated_feature_artifacts=selected_artifacts,
            missing_feature_artifacts=(),
            requested_feature_artifact_dir=str(root / "feature_artifacts" / requested_feature_date),
            requested_missing_feature_artifacts=requested_missing,
            price_source_alignment="selected_feature_date",
        )

    return FeatureDateContract(
        status="PASS",
        reason="carryover_feature_artifacts_available",
        requested_feature_date=requested_feature_date,
        selected_feature_date=latest,
        latest_available_market_date=latest,
        carryover_used=True,
        carryover_reason="requested_feature_date_missing_latest_available_within_freshness_limit",
        freshness_lag_business_days=lag,
        freshness_limit_business_days=freshness_limit_business_days,
        feature_artifact_dir=str(root / "feature_artifacts" / latest),
        generated_feature_artifacts=selected_artifacts,
        missing_feature_artifacts=(),
        requested_feature_artifact_dir=str(root / "feature_artifacts" / requested_feature_date),
        requested_missing_feature_artifacts=requested_missing,
        price_source_alignment="selected_feature_date",
    )


def write_feature_date_contract(
    *,
    operations_root: Path | str,
    requested_feature_date: str,
    contract: FeatureDateContract,
) -> Path:
    path = Path(operations_root) / "feature_date_contract" / f"{requested_feature_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = contract.to_payload()
    payload["contract_artifact_path"] = str(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def load_feature_date_contract(
    *,
    operations_root: Path | str,
    requested_feature_date: str,
) -> FeatureDateContract | None:
    path = Path(operations_root) / "feature_date_contract" / f"{requested_feature_date}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FeatureDateContract(
        status=str(payload.get("status") or ""),
        reason=str(payload.get("reason") or ""),
        requested_feature_date=str(payload.get("requested_feature_date") or requested_feature_date),
        selected_feature_date=str(payload.get("selected_feature_date") or ""),
        latest_available_market_date=str(payload.get("latest_available_market_date") or ""),
        carryover_used=bool(payload.get("carryover_used")),
        carryover_reason=str(payload.get("carryover_reason") or ""),
        freshness_lag_business_days=payload.get("freshness_lag_business_days"),
        freshness_limit_business_days=int(payload.get("freshness_limit_business_days") or 1),
        feature_artifact_dir=str(payload.get("feature_artifact_dir") or ""),
        generated_feature_artifacts=dict(payload.get("generated_feature_artifacts") or {}),
        missing_feature_artifacts=tuple(payload.get("missing_feature_artifacts") or ()),
        requested_feature_artifact_dir=str(payload.get("requested_feature_artifact_dir") or ""),
        requested_missing_feature_artifacts=tuple(payload.get("requested_missing_feature_artifacts") or ()),
        price_source_alignment=str(payload.get("price_source_alignment") or "selected_feature_date"),
        contract_artifact_path=str(payload.get("contract_artifact_path") or path),
    )


def _artifact_status(root: Path, feature_date: str) -> tuple[dict[str, str], tuple[str, ...]]:
    feature_dir = root / "feature_artifacts" / feature_date
    generated = {
        name: str(feature_dir / name)
        for name in REQUIRED_FEATURE_ARTIFACTS
        if (feature_dir / name).is_file()
    }
    missing = tuple(name for name in REQUIRED_FEATURE_ARTIFACTS if name not in generated)
    return generated, missing


def _latest_available_from_markers(root: Path, requested_feature_date: str) -> str:
    marker = root / "feature_refresh" / requested_feature_date / "latest_features.json"
    if marker.exists():
        payload = json.loads(marker.read_text(encoding="utf-8"))
        latest = str(payload.get("latest_available_market_date") or payload.get("data_until") or "")
        if latest:
            return latest
    feature_root = root / "feature_artifacts"
    if not feature_root.exists():
        return ""
    candidates = sorted(path.name for path in feature_root.iterdir() if path.is_dir())
    return candidates[-1] if candidates else ""


def _missing_contract(
    *,
    root: Path,
    requested_feature_date: str,
    selected_feature_date: str,
    latest_available_market_date: str,
    requested_missing: tuple[str, ...],
    freshness_limit_business_days: int,
    reason: str,
    selected_missing: tuple[str, ...] | None = None,
    freshness_lag_business_days: int | None = None,
) -> FeatureDateContract:
    return FeatureDateContract(
        status="REVIEW_REQUIRED",
        reason=reason,
        requested_feature_date=requested_feature_date,
        selected_feature_date=selected_feature_date,
        latest_available_market_date=latest_available_market_date,
        carryover_used=selected_feature_date != requested_feature_date,
        carryover_reason="feature_input_missing_requires_review",
        freshness_lag_business_days=freshness_lag_business_days,
        freshness_limit_business_days=freshness_limit_business_days,
        feature_artifact_dir=str(root / "feature_artifacts" / selected_feature_date),
        generated_feature_artifacts={},
        missing_feature_artifacts=selected_missing or requested_missing,
        requested_feature_artifact_dir=str(root / "feature_artifacts" / requested_feature_date),
        requested_missing_feature_artifacts=requested_missing,
        price_source_alignment="selected_feature_date",
    )


def _business_day_lag(start: str, end: str) -> int | None:
    try:
        current = date.fromisoformat(start)
        target = date.fromisoformat(end)
    except ValueError:
        return None
    if current > target:
        return None
    lag = 0
    while current < target:
        current = current + timedelta(days=1)
        if current.weekday() < 5:
            lag += 1
    return lag

