"""Pending Order Plan writer skeleton."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan


def pending_order_plan_to_payload(plan: PendingOrderPlan) -> dict[str, Any]:
    payload = asdict(plan)
    payload["state"] = plan.state.value
    payload["raw_request_saved"] = False
    payload["raw_response_saved"] = False
    payload["secret_saved"] = False
    return payload


def write_pending_order_plan(path: Path, plan: PendingOrderPlan) -> Path:
    if path is None:
        raise ValueError("path is required")
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Current writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pending_order_plan_to_payload(plan), sort_keys=True),
        encoding="utf-8",
    )
    return path


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    parts = path.parts
    runtime_modes = {"production", "demo", "simulation", "backtest"}
    return any(
        part == ".runtime"
        and index + 1 < len(parts)
        and parts[index + 1] in runtime_modes
        for index, part in enumerate(parts)
    )
