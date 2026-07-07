"""Current Asset State writer skeleton for Runtime v2."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetState


def asset_state_to_payload(state: CurrentAssetState) -> dict[str, Any]:
    """Convert CurrentAssetState to persistent_ledger/state.json payload."""

    payload = asdict(state)
    payload["positions"] = (
        None
        if state.positions is None
        else [asdict(position) for position in state.positions]
    )
    payload["cash_confirmed"] = state.cash is not None
    payload["buying_power_confirmed"] = state.buying_power is not None
    payload["updated_at"] = state.created_at
    return payload


def write_current_asset_state(path: Path, state: CurrentAssetState) -> Path:
    """Write current asset state to an explicit path."""

    if path is None:
        raise ValueError("path is required")
    if _is_production_runtime_path(path):
        raise ValueError("Phase13-O writer does not write production runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asset_state_to_payload(state), sort_keys=True),
        encoding="utf-8",
    )
    return path


def _is_production_runtime_path(path: Path) -> bool:
    parts = path.parts
    return ".runtime" in parts and "production" in parts
