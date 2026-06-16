from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


CANONICAL_KEYS = (
    "raw_daily_quotes",
    "normalized_daily_quotes",
    "listed_info",
    "trading_calendar",
    "candidate_features",
    "opportunity_features",
    "position_features",
    "capital_policy_inputs",
    "model_manifests",
)

DEFAULT_CONFIG_PATH = Path("config/phase9_data_sources.yaml")

FALLBACK_CANDIDATES = {
    "raw_daily_quotes": (
        Path(".runtime/data/raw/jquants/equities_bars_daily/responses"),
        Path(".runtime/data/raw/jquants/equities_bars_daily/data.parquet"),
    ),
    "normalized_daily_quotes": (
        Path(".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"),
        Path(".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet"),
    ),
    "listed_info": (Path(".runtime/data/raw/jquants/listed_issues/data.parquet"),),
    "trading_calendar": (Path(".runtime/data/raw/jquants/trading_calendar/data.parquet"),),
    "candidate_features": (Path(".runtime/phase9/features/2026-06-15/candidate_features.parquet"),),
    "opportunity_features": (Path(".runtime/phase9/features/2026-06-15/opportunity_feature_input.parquet"),),
    "position_features": (Path(".runtime/phase9/features/2026-06-15/position_feature_input.parquet"),),
    "capital_policy_inputs": (Path(".runtime/phase9/features/2026-06-15/capital_policy_input.parquet"),),
    "model_manifests": (),
}

PROHIBITED_PATH_TERMS = (
    "paper_ledger",
    "broker",
    "order_plan",
    "human_review",
    "blog",
    "public",
    "backtest",
    "trade_ledger",
    "daily_portfolio_ledger",
    "equity_curve",
    "performance",
)


@dataclass(frozen=True)
class CanonicalDataSourceRef:
    key: str
    path: str = ""
    source: str = "missing"
    exists: bool = False
    likely_jquants_derived: bool = False
    usable_for_phase9: bool = False
    fallback_used: bool = False
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def resolve_data_source(
    key: str,
    *,
    override_path: Path | str | None = None,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    allow_fallback: bool = False,
) -> CanonicalDataSourceRef:
    if key not in CANONICAL_KEYS:
        raise ValueError(f"unknown canonical data source key: {key}")
    if override_path:
        return _build_ref(key, Path(override_path), source="cli_override", fallback_used=False)
    config = load_phase9_data_source_config(config_path)
    configured = config.get(key)
    if configured:
        return _build_ref(key, Path(str(configured)), source="config", fallback_used=False)
    if allow_fallback:
        for candidate in FALLBACK_CANDIDATES.get(key, ()):
            if candidate.exists():
                return _build_ref(key, candidate, source="fallback", fallback_used=True)
    return CanonicalDataSourceRef(
        key=key,
        source="missing",
        blocked_reasons=(f"{key}_canonical_path_missing",),
    )


def resolve_phase9_data_sources(
    *,
    overrides: Mapping[str, Path | str | None] | None = None,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    allow_fallback: bool = False,
) -> dict[str, CanonicalDataSourceRef]:
    overrides = overrides or {}
    return {
        key: resolve_data_source(
            key,
            override_path=overrides.get(key),
            config_path=config_path,
            allow_fallback=allow_fallback,
        )
        for key in CANONICAL_KEYS
    }


def load_phase9_data_source_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, str | None]:
    path = Path(config_path)
    if not path.exists():
        return {}
    values: dict[str, str | None] = {}
    in_section = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            in_section = stripped[:-1] == "phase9_data_sources"
            continue
        if not in_section or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key not in CANONICAL_KEYS:
            continue
        text = value.strip().strip('"').strip("'")
        values[key] = None if text.lower() in {"", "null", "none", "~"} else text
    return values


def _build_ref(key: str, path: Path, *, source: str, fallback_used: bool) -> CanonicalDataSourceRef:
    warnings: list[str] = []
    blocked: list[str] = []
    exists = path.exists()
    if not exists:
        blocked.append(f"{key}_path_not_found")
    if _has_prohibited_terms(path):
        blocked.append(f"{key}_prohibited_source_path")
    likely = _likely_jquants(key, path)
    if key in {"raw_daily_quotes", "normalized_daily_quotes", "listed_info", "trading_calendar"} and not likely:
        blocked.append(f"{key}_not_jquants_derived")
    if fallback_used:
        warnings.append(f"{key}_fallback_used")
    usable = exists and not blocked
    return CanonicalDataSourceRef(
        key=key,
        path=str(path),
        source=source,
        exists=exists,
        likely_jquants_derived=likely,
        usable_for_phase9=usable,
        fallback_used=fallback_used,
        warnings=tuple(warnings),
        blocked_reasons=tuple(blocked),
    )


def _likely_jquants(key: str, path: Path) -> bool:
    path_text = str(path).lower()
    if "jquants" in path_text:
        return True
    if key == "normalized_daily_quotes" and "phase9/canonical_data/normalized_daily_quotes" in path_text:
        return True
    if key.endswith("features") or key == "capital_policy_inputs":
        return "phase9/features" in path_text
    if key == "model_manifests":
        return True
    return False


def _has_prohibited_terms(path: Path) -> bool:
    text = str(path).lower()
    return any(term in text for term in PROHIBITED_PATH_TERMS)
