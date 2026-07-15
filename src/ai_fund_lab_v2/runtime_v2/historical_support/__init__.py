"""Support utilities for historical Runtime v2 readiness evidence.

This package is intentionally outside Runtime v2 Core. It can inspect and
prepare evidence for historical tests, but it must not replace the normal
Runtime mainline or mutate trading state.
"""

from ai_fund_lab_v2.runtime_v2.historical_support.baseline import collect_regression_baseline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    EnvironmentCompositionError,
    HistoricalExecutionSnapshotProvider,
    HistoricalSubmitAdapter,
    RuntimeEnvironmentComposition,
    resolve_environment_composition,
)
from ai_fund_lab_v2.runtime_v2.historical_support.gates import evaluate_historical_runtime_entry_gates
from ai_fund_lab_v2.runtime_v2.historical_support.reset_plan import (
    HistoricalInitialStateConfig,
    build_reset_plan,
    validate_reset_plan,
)

__all__ = [
    "HistoricalInitialStateConfig",
    "EnvironmentCompositionError",
    "HistoricalExecutionSnapshotProvider",
    "HistoricalSubmitAdapter",
    "RuntimeEnvironmentComposition",
    "build_reset_plan",
    "collect_regression_baseline",
    "evaluate_historical_runtime_entry_gates",
    "resolve_environment_composition",
    "validate_reset_plan",
]
