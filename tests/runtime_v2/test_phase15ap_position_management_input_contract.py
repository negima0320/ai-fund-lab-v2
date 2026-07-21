from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.artifact_lookup import RuntimeArtifactLookupHalt, RuntimeArtifactMember
from ai_fund_lab_v2.runtime_v2.position_management import producer as pm_producer
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions


BUSINESS_DATE = "2026-07-09"
PM_ADAPTER_RELATIVE_PATH = Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py")


class _Phase15APArtifactSet:
    artifact_instance_id = "phase15ap.fixture.pm.runtime_adapter@sha256-current"
    accepted_event_id = "phase15ap-fixture-accepted-current"

    def __init__(self, member: RuntimeArtifactMember) -> None:
        self.raw_resolver_result = {
            "schema_version": "artifact_registry_resolver_result.v1",
            "members": [
                {
                    "member_role": "RUNTIME_ADAPTER",
                    "physical_path": member.physical_path.as_posix(),
                    "content_hash": member.content_hash,
                    "authority_mode": "ACCEPTED_CURRENT_PATH",
                    "accepted_current_path": True,
                }
            ],
        }
        self._member = member

    def require_member(self, role: str) -> RuntimeArtifactMember:
        if role != "RUNTIME_ADAPTER":
            raise RuntimeArtifactLookupHalt(f"required artifact member missing: POSITION_MANAGEMENT_POLICY_SET:{role}")
        return self._member


@pytest.fixture(autouse=True)
def _phase15ap_current_pm_adapter_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha(source)
    artifact_set = _Phase15APArtifactSet(
        RuntimeArtifactMember(
            member_role="RUNTIME_ADAPTER",
            physical_path=PM_ADAPTER_RELATIVE_PATH,
            content_hash=digest,
            schema_hash=None,
            artifact_type="RUNTIME_ADAPTER",
            artifact_set_id="control.position_management.accepted_set",
            logical_artifact_id="control.position_management.accepted_set.runtime_adapter",
        )
    )
    monkeypatch.setattr(pm_producer, "resolve_position_management_policy_artifacts", lambda: artifact_set)


def test_phase15ap_valid_pm_input_contract_allows_pm_and_sell_planning(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "PASS"
    assert result.to_manifest_fields()["pm_input_schema_status"] == "READY"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["defaulted_fields"] == []
    assert artifact["decision_count"] == 1


def test_phase15ap_stale_current_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")], current_as_of="2026-07-08")
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_input_stale_artifacts"
    assert artifact["stale_artifacts"] == ["current"]
    assert artifact["review_required"] is True


def test_phase15ap_current_positions_with_zero_pm_feature_rows_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), feature_symbols=())

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_feature_rows_missing_for_current_positions"
    assert artifact["missing_symbols"] == ["6522"]


def test_phase15ap_partial_held_symbol_feature_coverage_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522"), _position("7203")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522", "7203"), feature_symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "7203" in artifact["missing_symbols"]


def test_phase15ap_current_empty_with_no_position_reason_is_no_position_ready(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=(), include_no_position_reason=True)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "NO_POSITION"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["decision_count"] == 0


def test_phase15ap_current_empty_without_no_position_reason_is_no_position_ready(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=(), include_no_position_reason=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "NO_POSITION"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["missing_fields"] == []


def test_phase15ap_opportunity_missing_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    _, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=tmp_path / "missing_opportunity.json",
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_opportunity_artifact_missing"
    assert "pm_opportunity_source" in artifact["missing_fields"]


def test_phase15ap_opportunity_review_required_blocks_pm(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), opportunity_status="REVIEW_REQUIRED")

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert artifact["input_contract"]["pm_opportunity_status"] == "REVIEW_REQUIRED"


def test_phase15ap_hidden_default_fields_are_not_used(tmp_path):
    position = _position("6522")
    position.pop("holding_days")
    position.pop("peak_return")
    position.pop("current_price")
    position.pop("market_value")
    runtime_root = _runtime_root(tmp_path, positions=[position])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "current.positions[6522].holding_days" in artifact["missing_fields"]
    assert "current.positions[6522].peak_return" in artifact["missing_fields"]
    assert "current.positions[6522].current_price" in artifact["missing_fields"]
    assert artifact["defaulted_fields"] == []


def test_phase19_bu_pm_required_technical_feature_missing_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))
    feature = pd.read_csv(feature_path).drop(columns=["price_momentum_return_5d"])
    feature.to_csv(feature_path, index=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_feature_required_columns_missing"
    assert "pm_feature.price_momentum_return_5d" in artifact["missing_fields"]
    assert artifact["required_feature_validation"]["status"] == "FAIL"


def test_phase19_bu_pm_future_feature_data_rejected(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))
    feature = pd.read_csv(feature_path)
    feature["feature_as_of_date"] = "2026-07-10"
    feature.to_csv(feature_path, index=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert artifact["temporal_validation_status"] == "FAIL"
    assert "temporal_validation_failed" in artifact["required_feature_validation"]["reasons"]


def test_phase19_bu_pm_technical_features_affect_score_path(tmp_path):
    positive_runtime_root = _runtime_root(tmp_path / "positive_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    negative_runtime_root = _runtime_root(tmp_path / "negative_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    high_vol_runtime_root = _runtime_root(tmp_path / "high_vol_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    positive_opportunity, positive_feature = _pm_inputs(tmp_path / "positive", symbols=("6522",), expected_edge=0.08, downside=0.2)
    negative_opportunity, negative_feature = _pm_inputs(
        tmp_path / "negative",
        symbols=("6522",),
        expected_edge=0.08,
        downside=0.2,
        technicals={
            "price_momentum_return_5d": -0.08,
            "price_momentum_return_20d": -0.12,
            "trend_close_over_ma_20d": 0.94,
            "trend_ma_5_20_ratio": 0.94,
            "volume_momentum_ratio_5d": 1.0,
            "volatility_return_std_20d": 0.02,
        },
    )
    high_vol_opportunity, high_vol_feature = _pm_inputs(
        tmp_path / "high_vol",
        symbols=("6522",),
        expected_edge=0.08,
        downside=0.2,
        technicals={"volatility_return_std_20d": 0.16},
    )

    positive = produce_position_management_decisions(
        runtime_root=positive_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=positive_opportunity,
        feature_path=positive_feature,
    )
    negative = produce_position_management_decisions(
        runtime_root=negative_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=negative_opportunity,
        feature_path=negative_feature,
    )
    high_vol = produce_position_management_decisions(
        runtime_root=high_vol_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=high_vol_opportunity,
        feature_path=high_vol_feature,
    )
    positive_action = pd.read_csv(Path(positive.action_csv_path)).iloc[0]
    negative_action = pd.read_csv(Path(negative.action_csv_path)).iloc[0]
    high_vol_action = pd.read_csv(Path(high_vol.action_csv_path)).iloc[0]

    assert positive.status == "PASS"
    assert negative.status == "PASS"
    assert high_vol.status == "PASS"
    assert float(positive_action["hold_score"]) > float(negative_action["hold_score"])
    assert float(negative_action["exit_score"]) > float(positive_action["exit_score"])
    assert float(high_vol_action["reduce_score"]) > float(positive_action["reduce_score"])


def test_phase19_bu_pm_feature_contract_mode_parity(tmp_path):
    for mode in ("historical", "demo", "production"):
        runtime_root = _runtime_root(tmp_path / f"rt_{mode}", positions=[_position("6522")])
        opportunity_path, feature_path = _pm_inputs(tmp_path / f"inputs_{mode}", symbols=("6522",))
        result = produce_position_management_decisions(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode=mode,
            opportunity_path=opportunity_path,
            feature_path=feature_path,
        )
        artifact = _read_json(result.artifact_path)
        assert result.status == "PASS"
        assert artifact["feature_contract_version"] == "runtime_v2_pm_feature_input_contract_v2"
        assert artifact["input_contract"]["pm_required_feature_validation"]["status"] == "PASS"


def test_phase15ap_cli_does_not_enter_sell_planning_on_pm_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), feature_symbols=())
    policy_path = _write_policy(tmp_path / "capital_deployment.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--pm-opportunity-path",
            str(opportunity_path),
            "--pm-feature-path",
            str(feature_path),
        ]
    )
    manifest = _latest_manifest(runtime_root)
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["pm_status"] == "REVIEW_REQUIRED"
    assert manifest["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert "runtime_data_readiness_gate" in stage_names
    assert "position_management_ai_runtime_producer" not in stage_names
    assert "sell_planning_pending_pipeline" not in stage_names


def _runtime_root(tmp_path: Path, *, positions: list[dict[str, Any]], current_as_of: str = BUSINESS_DATE) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ap",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": current_as_of,
            "updated_at": current_as_of + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item.get("market_value") or 0) for item in positions),
            "total_equity": 500000 + sum(float(item.get("market_value") or 0) for item in positions),
            "review_required": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    _write_safety_decision(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _position(symbol: str, *, quantity: float = 100, average_price: float = 1000, current_price: float = 850) -> dict[str, Any]:
    current_return = (current_price / average_price) - 1.0
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "unrealized_pnl": (current_price - average_price) * quantity,
        "holding_days": 12,
        "peak_return": max(current_return, 0.0),
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
    }


def _pm_inputs(
    tmp_path: Path,
    *,
    symbols: tuple[str, ...],
    feature_symbols: tuple[str, ...] | None = None,
    expected_edge: float = -0.05,
    downside: float = 0.8,
    include_no_position_reason: bool = True,
    opportunity_status: str = "CSV",
    technicals: dict[str, float] | None = None,
) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    if opportunity_status == "REVIEW_REQUIRED":
        opportunity_path = tmp_path / "pm_opportunity.json"
        _write_json(
            opportunity_path,
            {
                "status": "REVIEW_REQUIRED",
                "review_required": True,
                "feature_date": BUSINESS_DATE,
                "model_version": "opportunity_fixture",
                "generated_at": BUSINESS_DATE + "T00:00:00Z",
                "rankings": [],
            },
        )
    else:
        opportunity_path = tmp_path / "pm_opportunity.csv"
        pd.DataFrame(
            [
                {
                    "target_date": BUSINESS_DATE,
                    "code": symbol,
                    "expected_edge_score": expected_edge,
                    "buy_rank": 999,
                    "downside_risk_score": downside,
                    "risk_guard_status": "high_risk" if downside >= 0.7 else "ok",
                    "candidate_score": 0.5,
                    "candidate_rank": 999,
                    "buy_reason": "",
                    "no_buy_reason": "",
                    "calibration_policy_name": "fixture",
                }
                for symbol in symbols
            ]
        ).to_csv(opportunity_path, index=False)
    feature_path = tmp_path / "pm_feature.csv"
    selected_feature_symbols = symbols if feature_symbols is None else feature_symbols
    technical_values = {
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.12,
        "trend_close_over_ma_20d": 1.05,
        "trend_ma_5_20_ratio": 1.03,
        "volume_momentum_ratio_5d": 1.1,
        "volatility_return_std_20d": 0.02,
    }
    technical_values.update(technicals or {})
    feature_rows = [
        {
            "target_date": BUSINESS_DATE,
            "feature_as_of_date": BUSINESS_DATE,
            "as_of_date": BUSINESS_DATE,
            "code": symbol,
            **technical_values,
            "feature_source_artifact": "candidate_features.parquet",
            "feature_source_hash": "fixture-candidate-feature-hash",
            "required_features": json.dumps(sorted(technical_values)),
            "optional_features": json.dumps(["no_position_reason"]),
            "missing_features": "[]",
            "defaulted_features": "[]",
            "temporal_validation_status": "PASS",
            "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
            "data_until": BUSINESS_DATE,
            "created_at": BUSINESS_DATE + "T00:00:00Z",
        }
        for symbol in selected_feature_symbols
    ]
    frame = pd.DataFrame(feature_rows)
    if frame.empty:
        columns = [
            "target_date",
            "feature_as_of_date",
            "as_of_date",
            "code",
            *technical_values.keys(),
            "feature_source_artifact",
            "feature_source_hash",
            "required_features",
            "optional_features",
            "missing_features",
            "defaulted_features",
            "temporal_validation_status",
            "feature_version",
            "data_until",
            "created_at",
        ]
        if include_no_position_reason:
            columns.append("no_position_reason")
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _write_safety_decision(root: Path) -> None:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15ap-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15ap fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _read_json(manifests[-1])


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
