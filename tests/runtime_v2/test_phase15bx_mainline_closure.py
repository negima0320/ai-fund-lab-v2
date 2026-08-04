from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from tests.runtime_v2.phase15bx_mainline_closure import (
    BU_AUTHORITY,
    run_phase15bx_mainline_closure,
)
def test_phase15bx_demo_execution_fallback_is_rejected_in_production(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_mainline_closure"
    root.mkdir(parents=True)

    result = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date="2026-07-13",
        mode="production",
        snapshot_provider=lambda **_: None,
        demo_execution_fallback_authority_path=BU_AUTHORITY,
    )

    assert result.status == "BLOCKED"
    assert "prohibited in production" in result.reason
