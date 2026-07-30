"""Runtime v2 BUY-side AI package boundary.

The package initializer intentionally avoids importing ``producer`` eagerly.
Some consumers import small utility submodules under ``PYTHONPATH=src`` where
repository-level scripts are not importable, so public producer symbols are
resolved lazily for compatibility.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BuyAIRuntimeResult",
    "load_ai_planning_signals_from_opportunity_artifact",
    "produce_buy_ai_decisions",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        producer = import_module("ai_fund_lab_v2.runtime_v2.buy_ai.producer")
        return getattr(producer, name)
    raise AttributeError(name)
