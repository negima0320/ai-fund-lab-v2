import csv
import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.order_manager.phase7_artifact_loader import (
    Phase7ArtifactLoadError,
    load_phase7_artifact_connection,
)


def test_phase7_artifact_loader_connects_cap5_and_shadow_policies(tmp_path: Path) -> None:
    final_dir = tmp_path / "reports" / "capital_allocation_ai" / "phase7_final"
    decision_dir = tmp_path / "reports" / "capital_allocation_ai" / "phase7a"
    final_dir.mkdir(parents=True)
    decision_dir.mkdir(parents=True)
    (final_dir / "phase7_final_summary.json").write_text(
        json.dumps(
            {
                "phase7_completion_status": "PHASE7_COMPLETED_WITH_VALIDATED_CAPITAL_ALLOCATION_POLICY",
                "primary_policy": "CAP5",
                "conservative_policy": "CAP4",
                "weak_regime_comparison_policy": "POLICY_Y_CAP4_EDGE08_CONF5",
            }
        ),
        encoding="utf-8",
    )
    with (decision_dir / "capital_allocation_decisions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "target_date",
                "code",
                "action",
                "current_position_value",
                "target_position_value",
                "buy_amount",
                "sell_amount",
                "replacement_reason",
                "defensive_reason",
                "emergency_reason",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "target_date": "2026-06-15",
                "code": "7203",
                "action": "HOLD",
                "current_position_value": "100000",
                "target_position_value": "100000",
                "buy_amount": "0",
                "sell_amount": "0",
            }
        )

    connection = load_phase7_artifact_connection(tmp_path)

    assert connection.primary_policy == "CAP5"
    assert connection.shadow_policies == ("CAP4", "POLICY_Y_CAP4_EDGE08_CONF5")
    assert connection.allocation.policy_id == "CAP5"
    assert connection.allocation.decisions[0].quantity == 100


def test_phase7_artifact_loader_missing_artifact_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(Phase7ArtifactLoadError):
        load_phase7_artifact_connection(tmp_path)
