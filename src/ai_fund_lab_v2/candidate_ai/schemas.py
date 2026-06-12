from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REQUIRED_FEATURE_COLUMNS = frozenset(
    {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "universe_eligible",
        "excluded_reason",
    }
)

OPTIONAL_FEATURE_METADATA_COLUMNS = frozenset(
    {
        "feature_set_name",
        "created_at",
        "data_start_date",
        "data_end_date",
    }
)

ALLOWED_FEATURE_PREFIXES = (
    "price_momentum_",
    "volume_momentum_",
    "volatility_",
    "trend_",
    "relative_strength_",
    "market_regime_",
    "sector_relative_",
    "fundamental_",
    "liquidity_",
    "missing_flags_",
)

FORBIDDEN_FEATURE_TERMS = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "top_decile_",
    "downside_bad_",
    "momentum_candidate_label",
    "backtest",
    "trade",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "paper_trade",
    "position",
    "allocation",
    "order",
    "execution",
    "profit",
    "loss",
    "pnl",
)

MANIFEST_FIELDS = frozenset(
    {
        "feature_version",
        "created_at",
        "as_of_date",
        "target_date",
        "row_count",
        "eligible_count",
        "excluded_count",
        "source_snapshot_id",
        "input_sources",
        "output_path",
        "audit_path",
        "schema_version",
        "code_hash_optional",
    }
)

AUDIT_FIELDS = frozenset(
    {
        "status",
        "feature_version",
        "as_of_date",
        "target_date",
        "row_count",
        "forbidden_feature_detected",
        "forbidden_columns",
        "future_column_detected",
        "label_column_detected",
        "post_as_of_data_detected",
        "fins_publication_violation_detected",
        "target_date_leakage_detected",
        "missing_required_columns",
        "invalid_prefix_columns",
        "eligible_count",
        "excluded_count",
        "excluded_reason_counts",
    }
)


@dataclass(frozen=True)
class CandidateFeatureSchemaContract:
    required_columns: frozenset[str] = REQUIRED_FEATURE_COLUMNS
    optional_metadata_columns: frozenset[str] = OPTIONAL_FEATURE_METADATA_COLUMNS
    allowed_feature_prefixes: tuple[str, ...] = ALLOWED_FEATURE_PREFIXES
    forbidden_feature_terms: tuple[str, ...] = FORBIDDEN_FEATURE_TERMS


@dataclass(frozen=True)
class CandidateFeatureManifest:
    feature_version: str
    created_at: str
    as_of_date: str
    target_date: str
    row_count: int
    eligible_count: int
    excluded_count: int
    source_snapshot_id: str
    input_sources: tuple[str, ...]
    output_path: str
    audit_path: str
    schema_version: str
    code_hash_optional: str | None = None


@dataclass(frozen=True)
class CandidateFeatureAudit:
    status: str
    feature_version: str | None
    as_of_date: str | None
    target_date: str | None
    row_count: int
    forbidden_feature_detected: bool
    forbidden_columns: tuple[str, ...] = ()
    future_column_detected: bool = False
    label_column_detected: bool = False
    post_as_of_data_detected: bool = False
    fins_publication_violation_detected: bool = False
    target_date_leakage_detected: bool = False
    missing_required_columns: tuple[str, ...] = ()
    invalid_prefix_columns: tuple[str, ...] = ()
    eligible_count: int = 0
    excluded_count: int = 0
    excluded_reason_counts: dict[str, int] = field(default_factory=dict)
    messages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "feature_version": self.feature_version,
            "as_of_date": self.as_of_date,
            "target_date": self.target_date,
            "row_count": self.row_count,
            "forbidden_feature_detected": self.forbidden_feature_detected,
            "forbidden_columns": list(self.forbidden_columns),
            "future_column_detected": self.future_column_detected,
            "label_column_detected": self.label_column_detected,
            "post_as_of_data_detected": self.post_as_of_data_detected,
            "fins_publication_violation_detected": self.fins_publication_violation_detected,
            "target_date_leakage_detected": self.target_date_leakage_detected,
            "missing_required_columns": list(self.missing_required_columns),
            "invalid_prefix_columns": list(self.invalid_prefix_columns),
            "eligible_count": self.eligible_count,
            "excluded_count": self.excluded_count,
            "excluded_reason_counts": dict(self.excluded_reason_counts),
            "messages": list(self.messages),
        }
