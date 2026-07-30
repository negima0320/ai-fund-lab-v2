"""AI Lifecycle v2 package boundary.

Dataset rebuild helpers are exported lazily so runtime inference consumers can
import focused submodules such as ``training_pipeline`` without loading
repository-level script adapters through the package initializer.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["DatasetRebuildRequest", "rebuild_common_pit_dataset"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        dataset_rebuild = import_module("ai_fund_lab_v2.ai_lifecycle.dataset_rebuild")
        return getattr(dataset_rebuild, name)
    raise AttributeError(name)
