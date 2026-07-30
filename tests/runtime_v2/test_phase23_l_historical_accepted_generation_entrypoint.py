from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from tests.strategy.test_phase22_g_runtime_planning import _produce as produce_runtime_planning_fixture


BUSINESS_DATE = "2026-07-15"


def test_phase23_l_daily_entrypoint_resolves_historical_generation_and_reaches_pending(tmp_path: Path, monkeypatch) -> None:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir(parents=True)
    old_manifest = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="old-generation",
        accepted_at="2026-06-15T00:00:00+00:00",
        effective_from="2026-06-15",
    )
    future_manifest = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="future-generation",
        accepted_at="2026-07-20T00:00:00+00:00",
        effective_from="2026-07-20",
    )
    _install_generation(runtime_root, old_manifest)
    _install_generation(runtime_root, future_manifest)
    _append_history(runtime_root, old_manifest)
    _append_history(runtime_root, future_manifest)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {
            "transaction_state": "COMMITTED",
            "bundle_manifest_path": str(future_manifest),
            "aggregate_hash": _read_json(future_manifest)["aggregate_hash"],
        },
    )
    _write_price(runtime_root, symbol="6098", close=1000.0)

    calls: dict[str, object] = {}

    class FakeBuyAIResult:
        status = "PASS"
        reason = ""
        lifecycle_gate_evidence = {}

        def to_manifest_fields(self) -> dict:
            return {"buy_ai_status": "PASS", "accepted_generation_id": "old-generation"}

    def fake_buy_ai(**kwargs):
        return FakeBuyAIResult()

    class FakeDataReadinessResult:
        status = "PASS"
        reason = ""
        payload = {"status": "PASS", "review_reasons": [], "halt_reasons": []}
        artifact_path = ""

        def to_manifest_fields(self) -> dict:
            return {"data_readiness_status": "PASS"}

    def fake_data_readiness(**kwargs):
        return FakeDataReadinessResult()

    def fake_generate_strategy_shadow_for_day(**kwargs):
        resolution = resolve_accepted_generation(kwargs["runtime_root"], business_date=kwargs["business_date"])
        calls["resolver_generation_id"] = resolution.generation_id
        calls["resolver_status"] = resolution.resolution_status
        strategy_dir = Path(kwargs["run_dir"]) / "daily" / kwargs["business_date"] / "strategy"
        strategy_dir.mkdir(parents=True, exist_ok=True)
        runtime_plan = produce_runtime_planning_fixture(
            tmp_path / "rp",
            pm_actions={"7203": "HOLD"},
            pc_members={"6098": ("ADD_CANDIDATE", False)},
            current_codes=(),
        )
        Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
        _write_position_sizing(strategy_dir / "position_sizing.json", symbol="6098", target_notional=120_000.0)
        return {
            "schema_version": "strategy_shadow_summary.v1",
            "strategy_shadow_judgment": "PASS",
            "accepted_generation_resolution_status": resolution.resolution_status,
            "accepted_generation_id": resolution.generation_id,
        }

    monkeypatch.setattr(run_daily_operation, "produce_buy_ai_decisions", fake_buy_ai)
    monkeypatch.setattr(run_daily_operation, "evaluate_runtime_data_readiness", fake_data_readiness)
    monkeypatch.setattr(run_daily_operation, "generate_strategy_shadow_for_day", fake_generate_strategy_shadow_for_day)

    exit_code = run_daily_operation.main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            BUSINESS_DATE,
            "--evaluation-time",
            f"{BUSINESS_DATE}T08:30:00+09:00",
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
        ]
    )

    assert exit_code == 0
    assert calls["resolver_status"] == "RESOLVED_COMMITTED"
    assert calls["resolver_generation_id"] == "old-generation"
    pending = read_pending_order_plan_path(path=runtime_root / "pending_order_plan" / "pending_order_plan.json", environment="demo")
    assert pending.exists and pending.valid
    assert pending.plan is not None
    assert pending.plan.items
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    stage = next(item for item in manifest["stages"] if item["name"] == "phase23_i_strategy_planning_authority_pipeline")
    assert stage["status"] == "PASS"


def _accepted_manifest_with_scalers(tmp_path: Path, *, generation_id: str, accepted_at: str, effective_from: str) -> Path:
    generation_dir = tmp_path / "accepted_generation_sources" / generation_id
    candidate = generation_dir / "candidate_model.pkl"
    opportunity = generation_dir / "opportunity_model.pkl"
    candidate_scaler = generation_dir / "candidate_scaler.pkl"
    opportunity_scaler = generation_dir / "opportunity_scaler.pkl"
    generation_dir.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(f"{generation_id}-candidate-model".encode("ascii"))
    opportunity.write_bytes(f"{generation_id}-opportunity-model".encode("ascii"))
    candidate_scaler.write_bytes(f"{generation_id}-candidate-scaler".encode("ascii"))
    opportunity_scaler.write_bytes(f"{generation_id}-opportunity-scaler".encode("ascii"))
    payload = {
        "schema_version": "accepted_buy_ai_bundle.v1",
        "generation_id": generation_id,
        "accepted_at": accepted_at,
        "effective_from": effective_from,
        "runtime_eligibility_status": "RUNTIME_ELIGIBLE_ACCEPTED_ONLY",
        "candidate_member": {
            "model_file": str(candidate),
            "model_hash": _sha(candidate),
            "scaler_file": str(candidate_scaler),
            "scaler_hash": _sha(candidate_scaler),
            "feature_schema_hash": _stable_hash({"feature_order": ["candidate_score"]}),
        },
        "opportunity_member": {
            "model_file": str(opportunity),
            "model_hash": _sha(opportunity),
            "scaler_file": str(opportunity_scaler),
            "scaler_hash": _sha(opportunity_scaler),
            "feature_schema_hash": _stable_hash({"feature_order": ["candidate_score", "opportunity_score"]}),
        },
        "runtime_baseline": {},
        "freshness_metadata": {},
    }
    payload["aggregate_hash"] = _stable_hash(payload)
    manifest = generation_dir / "accepted_generation_manifest.json"
    _write_json(manifest, payload)
    return manifest


def _install_generation(runtime_root: Path, manifest: Path) -> None:
    payload = _read_json(manifest)
    _write_json(runtime_root / "ai_lifecycle" / "generations" / payload["generation_id"] / "accepted_generation_manifest.json", payload)


def _append_history(runtime_root: Path, manifest: Path) -> None:
    payload = _read_json(manifest)
    path = runtime_root / "ai_lifecycle" / "authority_history" / "accepted_generation_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_type": "ACCEPTED_GENERATION_CREATED",
        "generation_id": payload["generation_id"],
        "accepted_at": payload["accepted_at"],
        "effective_from": payload["effective_from"],
        "aggregate_hash": payload["aggregate_hash"],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _write_price(runtime_root: Path, *, symbol: str, close: float) -> None:
    path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": symbol, "Date": BUSINESS_DATE, "Close": close}]).to_parquet(path)


def _write_position_sizing(path: Path, *, symbol: str, target_notional: float) -> None:
    _write_json(
        path,
        {
            "schema_version": "position_sizing.v1",
            "business_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "positions": [
                {
                    "security_code": symbol,
                    "position_reference": f"pc-{symbol}",
                    "target_notional": target_notional,
                    "current_notional": 0.0,
                    "incremental_target_notional": target_notional,
                    "incremental_buy_notional": target_notional,
                    "sizing_status": "SIZED",
                }
            ],
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
