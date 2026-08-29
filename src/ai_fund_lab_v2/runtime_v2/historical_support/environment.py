"""Formal Runtime environment composition for Historical mode.

This module composes environment-specific broker boundaries without replacing
Runtime v2 Core, Submit Guard, Execution Processor, Ledger, Current, Pending,
Safety, or Registry authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.runtime_v2.corporate_action_adjustment import (
    evaluate_corporate_action_adjustment_authority,
)
from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    resolve_listed_issues_snapshot,
)
from ai_fund_lab_v2.runtime_v2.historical_support.source_identity import (
    build_identity_from_logical_manifest,
    logical_input_manifest_path_from_asof_view,
    validate_bound_source_identity,
)
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


class EnvironmentCompositionError(ValueError):
    """Raised when an unsafe environment composition is requested."""


@dataclass(frozen=True)
class HistoricalSubmitAdapter:
    """Historical broker submit boundary.

    The full fill model is intentionally not implemented in Phase17-B1I-A.
    The adapter proves isolation and fails closed until the broker contract
    covers fill prices, partial fills, fees, slippage, and corporate actions.
    """

    broker_environment: str = "historical_simulated"
    runtime_root: Path | str = ".runtime"
    business_date: str = ""
    evaluation_time: str = ""
    pit_manifest_path: Path | str = "reports/phase17_d_5bd_smoke_minimum_readiness/5bd_window_pit_manifest.json"
    historical_asof_view_path: Path | str = ""
    ohlcv_path: Path | str = ".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    listed_issues_path: Path | str = ".runtime/operations/jquants/raw/jquants/listed_issues/data.parquet"
    raw_ohlcv_path: Path | str = ".runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet"

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if command.environment != "historical":
            return _blocked("historical submit adapter cannot run outside historical environment")
        validation = self._validate_command(command)
        if validation["status"] != "PASS":
            return RuntimeV2SubmitResult(
                status=validation["status"],
                submitted=False,
                accepted=False,
                blocked=validation["status"] == "HALT",
                review_required=validation["status"] != "HALT",
                broker_api_called=False,
                reason=str(validation["reason"]),
                response_classification=validation,
                configuration_diagnostic=self.diagnostic(),
                next_action="fix_historical_submit_preflight_input",
            )
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="historical submit adapter isolated; no external broker access",
            response_classification=validation,
            configuration_diagnostic=self.diagnostic(),
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if command.environment != "historical":
            return _blocked("historical submit adapter cannot run outside historical environment")
        validation = self._validate_command(command)
        if validation["status"] != "PASS":
            return RuntimeV2SubmitResult(
                status=validation["status"],
                submitted=False,
                accepted=False,
                blocked=validation["status"] == "HALT",
                review_required=validation["status"] != "HALT",
                broker_api_called=False,
                reason=str(validation["reason"]),
                response_classification=validation,
                configuration_diagnostic=self.diagnostic(),
                next_action="fix_historical_submit_input",
            )
        order_identity = _hash_text("historical-order|" + command.command_id)
        execution_identity = _hash_text("historical-execution|" + command.command_id)
        evidence_path = self._submission_evidence_path(execution_identity)
        if evidence_path.exists():
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason="duplicate historical submission evidence",
                response_classification={
                    "business_classification": "DUPLICATE_SUBMIT_BLOCKED",
                    "order_identity": order_identity,
                    "execution_identity": execution_identity,
                    "broker_write": False,
                    "simulation": True,
                    "historical_replay": True,
                },
                configuration_diagnostic=self.diagnostic(),
            )
        fill_price = float(validation["fill_price"])
        quantity = float(command.quantity)
        side = command.side.upper()
        cash_effect = fill_price * quantity * (-1 if side == "BUY" else 1)
        evidence = {
            "schema_version": "runtime_historical_submission_evidence_v1",
            "status": "ACCEPTED",
            "order_identity": order_identity,
            "execution_identity": execution_identity,
            "command_id": command.command_id,
            "pending_plan_id": command.pending_plan_id,
            "pending_item_id": command.pending_item_id,
            "strategy_authority_lineage": dict(command.strategy_authority_lineage or {}),
            "strategy_authority_lineage_hash": command.strategy_authority_lineage_hash,
            "source_decision_type": command.source_decision_type,
            "source_pm_decision_id": command.source_pm_decision_id,
            "source_pm_business_date": command.source_pm_business_date,
            "source_position_symbol": command.source_position_symbol,
            "position_campaign_id": command.position_campaign_id,
            "symbol": command.symbol,
            "side": side,
            "quantity": quantity,
            "order_type": command.order_type,
            "target_session_date": command.target_session_date,
            "fill_date": command.target_session_date,
            "fill_datetime": f"{command.target_session_date}T09:00:00+09:00",
            "fill_price": fill_price,
            "cash_effect": cash_effect,
            "source_price_ref": validation["source_price_ref"],
            "source_hash": validation["source_hash"],
            "source_identity": validation.get("source_identity", {}),
            "source_identity_validation": validation.get("source_identity_validation", {}),
            "pit_manifest_path": str(self.pit_manifest_path),
            "pit_manifest_hash": _sha256_file(Path(self.pit_manifest_path)),
            "smoke_limited_execution_model": True,
            "official_long_term_performance_model": False,
            "fees": 0,
            "tax": 0,
            "slippage": 0,
            "partial_fill": False,
            "all_or_none": True,
            "simulation": True,
            "historical_replay": True,
            "broker_write": False,
            "external_delivery": False,
            "production_equivalent": False,
        }
        _write_json(evidence_path, evidence)
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            broker_order_id_hash=order_identity,
            raw_request_saved=False,
            raw_response_saved=False,
            secret_saved=False,
            reason="historical market fill evidence accepted",
            response_classification={
                "business_classification": "HISTORICAL_FILL_ACCEPTED",
                "simulation": True,
                "historical_replay": True,
                "broker_write": False,
                "production_equivalent": False,
                "acceptance_only": False,
                "order_identity": order_identity,
                "execution_identity": execution_identity,
                "evidence_path": str(evidence_path),
            },
            configuration_diagnostic=self.diagnostic(),
        )

    def diagnostic(self) -> dict[str, Any]:
        return {
            "adapter": "HistoricalSubmitAdapter",
            "broker_environment": self.broker_environment,
            "simulation": True,
            "historical_replay": True,
            "broker_write": False,
            "broker_api_called": False,
            "production_equivalent": False,
            "acceptance_only": False,
            "runtime_root": str(self.runtime_root),
            "business_date": self.business_date,
            "evaluation_time": self.evaluation_time,
            "historical_asof_view_path": str(self.historical_asof_view_path),
            "ohlcv_path": str(self.ohlcv_path),
            "listed_issues_path": str(self.listed_issues_path),
            "raw_ohlcv_path": str(self.raw_ohlcv_path),
        }

    def corporate_action_event_evidence(self, *, symbol: str, business_date: str) -> dict[str, Any]:
        """Return the PIT corporate action event evidence used by submit preflight."""

        return _corporate_action_evidence(Path(self.raw_ohlcv_path), business_date, symbol)

    def _validate_command(self, command: RuntimeV2SubmitCommand) -> dict[str, Any]:
        if not self.business_date:
            return _classification("HALT", "historical business_date missing")
        if not self.evaluation_time:
            return _classification("HALT", "historical evaluation_time missing")
        if command.target_session_date != self.business_date:
            return _classification("HALT", "target_session_date must equal business_date")
        if command.order_type != "MARKET" or command.price_type != "MARKET":
            return _classification("REVIEW_REQUIRED", "historical limit order rule is not accepted")
        if command.side.upper() not in {"BUY", "SELL"}:
            return _classification("HALT", "unsupported historical side")
        if float(command.quantity) <= 0:
            return _classification("HALT", "quantity must be positive")
        trading_unit = _trading_unit_from_listed_info(command.listed_info)
        if trading_unit is not None and float(command.quantity) % trading_unit != 0:
            return _classification("HALT", "quantity does not satisfy accepted trading unit")
        price = self._resolve_open_price(
            command.symbol,
            command.target_session_date,
            command.listed_info,
            side=command.side,
            quantity=float(command.quantity),
        )
        if price["status"] != "PASS":
            return price
        return {
            **price,
            "status": "PASS",
            "reason": "historical market fill preflight accepted",
            "lot_trading_unit_authority": (
                "PENDING_LISTED_INFO_TRADING_UNIT"
                if trading_unit is not None
                else "ACCEPTED_EXISTING_RUNTIME_QUANTITY_AUTHORITY"
            ),
        }

    def _resolve_open_price(
        self,
        symbol: str,
        target_session_date: str,
        listed_info: dict[str, Any] | None,
        *,
        side: str,
        quantity: float,
    ) -> dict[str, Any]:
        ohlcv_path = Path(self.ohlcv_path)
        source_validation = self._validate_normalized_ohlcv_source_identity(ohlcv_path, target_session_date)
        if source_validation["status"] != "PASS":
            source_extra = {key: value for key, value in source_validation.items() if key not in {"status", "reason"}}
            return _classification(
                "HALT",
                str(source_validation.get("reason") or "historical source identity mismatch"),
                **source_extra,
            )
        universe = _resolve_symbol_in_pit_universe(
            runtime_root=Path(self.runtime_root),
            historical_asof_view_path=Path(self.historical_asof_view_path),
            legacy_listed_path=Path(self.listed_issues_path),
            symbol=symbol,
            business_date=target_session_date,
            listed_info=listed_info,
            broker_environment=self.broker_environment,
        )
        if universe["status"] != "PASS":
            return {
                **universe,
                "status": "HALT",
                "submit_guard_reason": "symbol missing from PIT universe",
            }
        ca_evidence = _corporate_action_evidence(Path(self.raw_ohlcv_path), target_session_date, symbol)
        ca_status = str(ca_evidence.get("corporate_action_status") or "")
        if ca_status != "PASS":
            current_quantity = _runtime_current_quantity(Path(self.runtime_root), symbol)
            adjustment_authority = evaluate_corporate_action_adjustment_authority(
                runtime_root=Path(self.runtime_root),
                business_date=target_session_date,
                symbol=symbol,
                side=side,
                submit_quantity=quantity,
                pending_quantity=quantity,
                current_quantity=current_quantity,
                broker_available_quantity=current_quantity,
                event_evidence=ca_evidence,
            )
            if adjustment_authority.get("corporate_action_adjustment_authority_status") == "PASS":
                ca_evidence = {**ca_evidence, **adjustment_authority}
            else:
                blocked_evidence = {**ca_evidence, **adjustment_authority}
                return _classification(
                    "HALT",
                    "corporate action guard failed",
                    **blocked_evidence,
                    pit_universe_authority=universe,
                )
        else:
            adjustment_authority = evaluate_corporate_action_adjustment_authority(
                runtime_root=Path(self.runtime_root),
                business_date=target_session_date,
                symbol=symbol,
                side=side,
                submit_quantity=quantity,
                pending_quantity=quantity,
                current_quantity=_runtime_current_quantity(Path(self.runtime_root), symbol),
                broker_available_quantity=_runtime_current_quantity(Path(self.runtime_root), symbol),
                event_evidence=ca_evidence,
            )
            ca_evidence = {**ca_evidence, **adjustment_authority}
        if str(ca_evidence.get("corporate_action_adjustment_authority_status") or "PASS") != "PASS":
            return _classification(
                "HALT",
                "corporate action guard failed",
                **ca_evidence,
                pit_universe_authority=universe,
            )
        try:
            import pandas as pd

            frame = pd.read_parquet(ohlcv_path).copy()
        except Exception as exc:
            return _classification("HALT", f"ohlcv source unreadable: {exc}")
        frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        normalized_symbol = _normalize_listed_issue_code(symbol)
        code_column = "Code" if "Code" in frame.columns else "code" if "code" in frame.columns else ""
        if not code_column:
            return _classification("HALT", "target session OHLCV code column missing")
        rows = frame[
            (frame["Date_s"] == target_session_date)
            & (frame[code_column].map(_normalize_listed_issue_code) == normalized_symbol)
        ]
        if len(rows) != 1:
            return _classification("HALT", "missing or non-unique target session OHLCV row")
        value = rows.iloc[0].get("Open")
        if value is None or float(value) <= 0:
            return _classification("HALT", "target session Open is missing or invalid")
        return {
            "status": "PASS",
            "reason": "target session Open resolved",
            "fill_price": float(value),
            "source_price_ref": f"{ohlcv_path}:{target_session_date}:{symbol}:Open",
            "source_hash": str(source_validation.get("source_hash") or _sha256_file(ohlcv_path)),
            "source_identity": source_validation.get("actual_source_identity", {}),
            "source_identity_validation": source_validation,
            "pit_universe_authority": universe,
            "corporate_action_adjustment_authority": ca_evidence,
        }

    def _submission_evidence_path(self, execution_identity: str) -> Path:
        root = Path(self.runtime_root)
        return root / "runtime_state" / "historical_broker" / self.business_date / f"{execution_identity}.json"

    def _validate_normalized_ohlcv_source_identity(self, ohlcv_path: Path, business_date: str) -> dict[str, Any]:
        asof_path = Path(self.historical_asof_view_path)
        if not str(self.historical_asof_view_path):
            return {
                "status": "PASS",
                "reason": "legacy explicit historical ohlcv path accepted without run-scoped asof view",
                "source_hash": _sha256_file(ohlcv_path),
                "source_identity_contract_version": "legacy_physical_file_hash",
            }
        manifest_path = logical_input_manifest_path_from_asof_view(asof_path, business_date)
        if not manifest_path.exists():
            return {
                "status": "HALT",
                "reason": "historical logical source manifest missing",
                "mismatch_class": "BOUND_SOURCE_MANIFEST_MISSING",
                "root_reason_code": "BOUND_SOURCE_MANIFEST_MISSING",
                "logical_source_id": "normalized_ohlcv",
                "expected_source_path": str(manifest_path),
                "actual_source_path": str(ohlcv_path),
                "expected_hash": "",
                "source_hash": _sha256_file(ohlcv_path),
                "recommended_action": "Run market_refresh/morning for this runtime-test day and use its run-scoped logical_input_manifest.json.",
            }
        manifest = _read_json(manifest_path)
        if str(manifest.get("business_date") or "") != business_date:
            return {
                "status": "HALT",
                "reason": "historical logical source manifest business_date mismatch",
                "mismatch_class": "BUSINESS_DATE_MISMATCH",
                "root_reason_code": "BUSINESS_DATE_MISMATCH",
                "logical_source_id": "normalized_ohlcv",
                "expected_business_date": business_date,
                "actual_business_date": str(manifest.get("business_date") or ""),
                "expected_source_path": str(manifest_path),
                "actual_source_path": str(ohlcv_path),
                "recommended_action": "Regenerate the historical logical input manifest for the submit business_date.",
            }
        if str(manifest.get("status") or "") != "PASS":
            return {
                "status": "HALT",
                "reason": "historical logical source manifest not PASS",
                "mismatch_class": "BOUND_SOURCE_MANIFEST_NOT_PASS",
                "root_reason_code": "BOUND_SOURCE_MANIFEST_NOT_PASS",
                "logical_source_id": "normalized_ohlcv",
                "expected_source_path": str(manifest_path),
                "actual_source_path": str(ohlcv_path),
                "recommended_action": "Repair the historical logical source materialization before submit.",
            }
        expected_identity = build_identity_from_logical_manifest(
            manifest_path,
            logical_source_id="normalized_ohlcv",
            business_date=business_date,
        )
        return validate_bound_source_identity(
            expected_identity=expected_identity,
            actual_path=ohlcv_path,
            logical_source_id="normalized_ohlcv",
            business_date=business_date,
            source_manifest_path=manifest_path,
        )


@dataclass(frozen=True)
class HistoricalExecutionSnapshotProvider:
    """Historical execution snapshot provider that fails closed by default."""

    broker_environment: str = "historical_simulated"
    runtime_root: Path | str = ".runtime"
    business_date: str = ""

    def __call__(self, *, mode: str, snapshot_path: Path | str, report_path: Path | str) -> Any:
        if mode != "historical":
            raise EnvironmentCompositionError("historical snapshot provider cannot run outside historical mode")
        snapshot = Path(snapshot_path)
        report = Path(report_path)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        evidence_items = self._submission_evidence()
        cash_available = self._projected_cash_available(evidence_items)
        positions = self._projected_position_payloads(evidence_items)
        payload = {
            "schema_version": "runtime_v2_historical_execution_snapshot_v1",
            "status": "PASS",
            "reason": "historical execution snapshot built from accepted submission evidence",
            "environment": "historical",
            "broker_environment": self.broker_environment,
            "generated_at": self.business_date or "",
            "simulation": True,
            "historical_replay": True,
            "broker_write": False,
            "production_equivalent": False,
            "acceptance_only": False,
            "external_delivery": False,
            "orders": [_order_payload(item) for item in evidence_items],
            "executions": [_execution_payload(item) for item in evidence_items],
            "positions": positions,
            "buying_power": {
                "cash_ref": f"historical-cash-{self.business_date or 'unknown'}",
                "cash_available": str(cash_available),
                "buying_power": str(cash_available),
                "currency": "JPY",
            },
        }
        _write_json(snapshot, payload)
        _write_json(report, payload)
        return type("HistoricalSnapshotResult", (), {"status": "PASS"})()

    def _submission_evidence(self) -> list[dict[str, Any]]:
        root = Path(self.runtime_root)
        evidence_dir = root / "runtime_state" / "historical_broker" / self.business_date
        if not evidence_dir.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(evidence_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("status") == "ACCEPTED":
                records.append(payload)
        return records

    def _projected_cash_available(self, evidence_items: list[dict[str, Any]]) -> float:
        state = _read_json(Path(self.runtime_root) / "persistent_ledger" / "state.json")
        if "cash" not in state or state.get("cash") in (None, ""):
            raise EnvironmentCompositionError("historical current cash missing; no runtime_evaluation_capital fallback")
        starting_cash = _number(state.get("cash"))
        cash_effect = sum(
            _number(item.get("cash_effect"))
            for item in evidence_items
            if not self._execution_already_applied(item)
        )
        return starting_cash + cash_effect

    def _projected_position_payloads(self, evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        state = _read_json(Path(self.runtime_root) / "persistent_ledger" / "state.json")
        positions: dict[str, dict[str, Any]] = {
            str(item.get("symbol") or ""): dict(item)
            for item in state.get("positions") or ()
            if str(item.get("symbol") or "")
        }
        for item in evidence_items:
            already_applied = self._execution_already_applied(item)
            symbol = str(item.get("symbol") or "")
            if not symbol:
                continue
            side = str(item.get("side") or "").upper()
            quantity = _number(item.get("quantity"))
            fill_price = _number(item.get("fill_price"))
            current = positions.get(symbol)
            if side == "BUY":
                if already_applied:
                    continue
                previous_quantity = _number((current or {}).get("quantity"))
                previous_cost = previous_quantity * _number((current or {}).get("average_price"))
                new_quantity = previous_quantity + quantity
                average_price = (previous_cost + quantity * fill_price) / new_quantity if new_quantity else fill_price
                positions[symbol] = {
                    "symbol": symbol,
                    "position_key": symbol,
                    "quantity": new_quantity,
                    "average_price": average_price,
                    "market_value": new_quantity * fill_price,
                    "as_of": self.business_date,
                }
            elif side == "SELL":
                if already_applied:
                    continue
                if current is None:
                    continue
                previous_quantity = _number(current.get("quantity"))
                remaining = max(previous_quantity - quantity, 0.0)
                if remaining <= 0:
                    positions.pop(symbol, None)
                    continue
                average_price = _number(current.get("average_price"))
                current_market_value = _number(current.get("market_value"))
                market_price = current_market_value / previous_quantity if previous_quantity else fill_price
                positions[symbol] = {
                    "symbol": symbol,
                    "position_key": symbol,
                    "quantity": remaining,
                    "average_price": average_price,
                    "market_value": remaining * market_price,
                    "as_of": self.business_date,
                }
        for item in positions.values():
            item["valuation_as_of"] = self.business_date
            item.setdefault("as_of", self.business_date)
        return [_position_payload(item) for item in positions.values() if _number(item.get("quantity")) > 0]

    def _execution_already_applied(self, item: dict[str, Any]) -> bool:
        order_hash = _normalizer_hash_ref(item.get("order_identity"))
        path = Path(self.runtime_root) / "persistent_ledger" / "executions.jsonl"
        if not path.exists():
            return False
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("execution_evidence_type") or "") != "execution_equivalent":
                continue
            if str(row.get("source_broker_order_hash") or row.get("order_id") or "") == order_hash:
                return True
        return False


@dataclass(frozen=True)
class RuntimeEnvironmentComposition:
    runtime_mode: str
    run_type: str
    broker_environment: str
    submit_adapter: Any | None
    execution_snapshot_provider: Callable[..., Any] | None
    simulation: bool
    historical_replay: bool
    broker_write: bool
    production_equivalent: bool
    acceptance_only: bool
    external_delivery: bool
    tachibana_readonly: bool
    tachibana_demo_write: bool
    tachibana_production_write: bool

    def manifest_fields(
        self,
        *,
        runtime_root: Path | str,
        environment_id: str,
        run_id: str,
        business_date: str,
        evaluation_time: str,
    ) -> dict[str, Any]:
        return {
            "run_type": self.run_type,
            "runtime_mode": self.runtime_mode,
            "broker_environment": self.broker_environment,
            "simulation": self.simulation,
            "historical_replay": self.historical_replay,
            "broker_write": self.broker_write,
            "production_equivalent": self.production_equivalent,
            "acceptance_only": self.acceptance_only,
            "external_delivery": self.external_delivery,
            "tachibana_readonly": self.tachibana_readonly,
            "tachibana_demo_write": self.tachibana_demo_write,
            "tachibana_production_write": self.tachibana_production_write,
            "runtime_root": str(runtime_root),
            "environment_id": environment_id,
            "run_id": run_id,
            "business_date": business_date,
            "evaluation_time": evaluation_time,
        }


def resolve_environment_composition(
    *,
    mode: str,
    runtime_root: Path | str = ".runtime",
    broker_environment: str | None = None,
    external_delivery: bool = False,
    broker_write: bool | None = None,
    business_date: str | None = None,
    evaluation_time: str | None = None,
    historical_asof_view_path: Path | str = "",
) -> RuntimeEnvironmentComposition:
    if mode == "simulation":
        raise EnvironmentCompositionError("simulation is not a formal Runtime environment; use --mode historical")
    if mode == "historical":
        return _historical(
            runtime_root=runtime_root,
            broker_environment=broker_environment,
            external_delivery=external_delivery,
            broker_write=broker_write,
            business_date=business_date,
            evaluation_time=evaluation_time,
            historical_asof_view_path=historical_asof_view_path,
        )
    if mode == "demo":
        if broker_environment not in {None, "tachibana_demo"}:
            raise EnvironmentCompositionError("demo mode requires broker_environment=tachibana_demo")
        if broker_write is True:
            # Write permission is still controlled by submit flags and guards;
            # composition only rejects cross-environment broker misuse.
            pass
        return RuntimeEnvironmentComposition(
            runtime_mode="demo",
            run_type="DEMO",
            broker_environment="tachibana_demo",
            submit_adapter=None,
            execution_snapshot_provider=None,
            simulation=False,
            historical_replay=False,
            broker_write=bool(broker_write),
            production_equivalent=False,
            acceptance_only=False,
            external_delivery=external_delivery,
            tachibana_readonly=True,
            tachibana_demo_write=bool(broker_write),
            tachibana_production_write=False,
        )
    if mode == "production":
        if broker_environment not in {None, "tachibana_production"}:
            raise EnvironmentCompositionError("production mode requires broker_environment=tachibana_production")
        return RuntimeEnvironmentComposition(
            runtime_mode="production",
            run_type="PRODUCTION",
            broker_environment="tachibana_production",
            submit_adapter=None,
            execution_snapshot_provider=None,
            simulation=False,
            historical_replay=False,
            broker_write=bool(broker_write),
            production_equivalent=True,
            acceptance_only=False,
            external_delivery=external_delivery,
            tachibana_readonly=True,
            tachibana_demo_write=False,
            tachibana_production_write=bool(broker_write),
        )
    raise EnvironmentCompositionError(f"unsupported runtime mode: {mode}")


def _historical(
    *,
    runtime_root: Path | str,
    broker_environment: str | None,
    external_delivery: bool,
    broker_write: bool | None,
    business_date: str | None,
    evaluation_time: str | None,
    historical_asof_view_path: Path | str = "",
) -> RuntimeEnvironmentComposition:
    if not business_date:
        raise EnvironmentCompositionError("historical mode requires explicit business_date")
    if not evaluation_time:
        raise EnvironmentCompositionError("historical mode requires explicit evaluation_time")
    if broker_environment not in {None, "historical_simulated"}:
        raise EnvironmentCompositionError("historical mode requires broker_environment=historical_simulated")
    if external_delivery:
        raise EnvironmentCompositionError("historical mode requires external_delivery=false")
    if broker_write:
        raise EnvironmentCompositionError("historical mode requires broker_write=false")
    submit_authority_paths = _historical_submit_authority_paths(
        historical_asof_view_path=historical_asof_view_path,
        business_date=business_date,
    )
    return RuntimeEnvironmentComposition(
        runtime_mode="historical",
        run_type="HISTORICAL",
        broker_environment="historical_simulated",
        submit_adapter=HistoricalSubmitAdapter(
            runtime_root=runtime_root,
            business_date=business_date,
            evaluation_time=evaluation_time,
            historical_asof_view_path=historical_asof_view_path,
            ohlcv_path=submit_authority_paths.get(
                "normalized_ohlcv",
                ".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet",
            ),
            listed_issues_path=submit_authority_paths.get(
                "listed_issues",
                ".runtime/operations/jquants/raw/jquants/listed_issues/data.parquet",
            ),
            raw_ohlcv_path=submit_authority_paths.get(
                "raw_ohlcv",
                ".runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet",
            ),
        ),
        execution_snapshot_provider=HistoricalExecutionSnapshotProvider(
            runtime_root=runtime_root,
            business_date=business_date,
        ),
        simulation=True,
        historical_replay=True,
        broker_write=False,
        production_equivalent=False,
        acceptance_only=False,
        external_delivery=False,
        tachibana_readonly=False,
        tachibana_demo_write=False,
        tachibana_production_write=False,
    )


def _historical_submit_authority_paths(
    *,
    historical_asof_view_path: Path | str,
    business_date: str,
) -> dict[str, str]:
    if not str(historical_asof_view_path):
        return {}
    asof_view_path = Path(historical_asof_view_path)
    manifest_path = (
        asof_view_path.parent
        / "inputs"
        / "historical_asof"
        / business_date
        / "logical_input_manifest.json"
    )
    if not manifest_path.exists():
        return {}
    manifest = _read_json(manifest_path)
    if str(manifest.get("business_date") or "") != business_date:
        return _missing_historical_submit_authority_paths(manifest_path)
    if str(manifest.get("status") or "") != "PASS":
        return _missing_historical_submit_authority_paths(manifest_path)
    logical_paths = manifest.get("logical_paths")
    if not isinstance(logical_paths, dict):
        return _missing_historical_submit_authority_paths(manifest_path)
    resolved: dict[str, str] = {}
    for key in ("normalized_ohlcv", "raw_ohlcv", "listed_issues"):
        value = str(logical_paths.get(key) or "")
        resolved[key] = value or _missing_historical_submit_authority_paths(manifest_path)[key]
    return resolved


def _missing_historical_submit_authority_paths(manifest_path: Path) -> dict[str, str]:
    missing_root = manifest_path.parent / "__missing_historical_logical_authority__"
    return {
        "normalized_ohlcv": str(
            missing_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
        ),
        "raw_ohlcv": str(missing_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"),
        "listed_issues": str(missing_root / "raw" / "jquants" / "listed_issues" / "data.parquet"),
    }


def _blocked(reason: str) -> RuntimeV2SubmitResult:
    return RuntimeV2SubmitResult(
        status="BLOCKED",
        submitted=False,
        accepted=False,
        blocked=True,
        review_required=False,
        broker_api_called=False,
        reason=reason,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _classification(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "simulation": True,
        "historical_replay": True,
        "broker_write": False,
        **extra,
    }


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalizer_hash_ref(value: object) -> str:
    encoded = json.dumps(str(value), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_source_hash(manifest_path: Path, business_date: str, key: str) -> str:
    if not manifest_path.exists():
        return ""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    for entry in manifest.get("entries") or ():
        if str(entry.get("business_date")) == business_date:
            return str((entry.get("source_hashes") or {}).get(key) or "")
    return ""


def _expected_source_hash_from_asof_view(
    asof_view_path: Path,
    business_date: str,
    *,
    authority: str,
    source_path: Path,
) -> str:
    if not asof_view_path.exists() or not asof_view_path.is_file():
        return ""
    try:
        view = json.loads(asof_view_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    if str(view.get("business_date") or "") != business_date:
        return ""
    for entry in view.get("authorities") or ():
        if str(entry.get("authority") or "") != authority:
            continue
        if str(entry.get("business_date") or "") != business_date:
            continue
        if Path(str(entry.get("physical_source_path") or "")) != source_path:
            continue
        return str(entry.get("physical_source_hash") or "")
    return ""


def _resolve_symbol_in_pit_universe(
    *,
    runtime_root: Path,
    historical_asof_view_path: Path,
    legacy_listed_path: Path,
    symbol: str,
    business_date: str,
    listed_info: dict[str, Any] | None,
    broker_environment: str,
) -> dict[str, Any]:
    source = _listed_issues_universe_source(
        runtime_root=runtime_root,
        historical_asof_view_path=historical_asof_view_path,
        legacy_listed_path=legacy_listed_path,
        business_date=business_date,
        broker_environment=broker_environment,
    )
    if source["status"] != "PASS":
        return source
    resolution = _symbol_in_pit_universe(
        listed_path=Path(str(source["selected_snapshot_path"])),
        symbol=symbol,
        business_date=business_date,
        listed_info=listed_info,
        source=source,
    )
    return resolution


def _listed_issues_universe_source(
    *,
    runtime_root: Path,
    historical_asof_view_path: Path,
    legacy_listed_path: Path,
    business_date: str,
    broker_environment: str,
) -> dict[str, Any]:
    if broker_environment != "historical_simulated":
        return {
            "status": "HALT",
            "reason": "historical PIT universe requires broker_environment=historical_simulated",
            "pit_universe_authority_type": "UNAVAILABLE",
        }
    asof_authority = _listed_issues_authority_from_asof_view(historical_asof_view_path, business_date)
    if asof_authority:
        return asof_authority
    snapshot_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "listed_issues"
    if (snapshot_root / "index.json").is_file():
        resolution = resolve_listed_issues_snapshot(
            snapshot_root=snapshot_root,
            business_date=business_date,
            mode="historical",
        )
        if resolution.status != "PASS":
            return {
                "status": "HALT",
                "reason": resolution.reason,
                "pit_universe_authority_type": "HISTORICAL_LISTED_ISSUES_SNAPSHOT",
                "selected_snapshot_date": resolution.selected_snapshot_date,
                "selected_snapshot_path": resolution.selected_snapshot_path,
                "selected_manifest_path": resolution.selected_manifest_path,
                "selected_content_hash": resolution.selected_content_hash,
                "selected_schema_hash": resolution.selected_schema_hash,
                "selection_policy": resolution.selection_policy,
                "future_snapshot_used": resolution.future_snapshot_used,
            }
        return {
            "status": "PASS",
            "reason": "historical_listed_issues_snapshot_resolved_for_submit_guard",
            "pit_universe_authority_type": "HISTORICAL_LISTED_ISSUES_SNAPSHOT",
            "selected_snapshot_date": resolution.selected_snapshot_date,
            "selected_snapshot_path": resolution.selected_snapshot_path,
            "selected_manifest_path": resolution.selected_manifest_path,
            "selected_content_hash": resolution.selected_content_hash,
            "selected_schema_hash": resolution.selected_schema_hash,
            "selection_policy": resolution.selection_policy,
            "snapshot_age_days": resolution.snapshot_age_days,
            "future_snapshot_used": resolution.future_snapshot_used,
            "content_hash_verified": resolution.content_hash_verified,
        }
    return {
        "status": "PASS",
        "reason": "legacy_listed_issues_path_used_for_submit_guard_fixture",
        "pit_universe_authority_type": "LEGACY_EXPLICIT_LISTED_ISSUES_PATH",
        "selected_snapshot_date": "",
        "selected_snapshot_path": str(legacy_listed_path),
        "selected_manifest_path": "",
        "selected_content_hash": _sha256_file(legacy_listed_path),
        "selected_schema_hash": "",
        "selection_policy": "legacy_explicit_path",
        "future_snapshot_used": False,
        "content_hash_verified": bool(_sha256_file(legacy_listed_path)),
    }


def _listed_issues_authority_from_asof_view(asof_view_path: Path, business_date: str) -> dict[str, Any]:
    if not asof_view_path.exists() or not asof_view_path.is_file():
        return {}
    try:
        view = json.loads(asof_view_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if str(view.get("business_date") or "") != business_date:
        return {
            "status": "HALT",
            "reason": "historical_asof_view_business_date_mismatch",
            "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
            "selected_snapshot_path": "",
        }
    for entry in view.get("authorities") or ():
        if str(entry.get("authority") or "") != "listed_issues":
            continue
        selected_path = str(entry.get("physical_source_path") or "")
        selected_hash = str(entry.get("physical_source_hash") or "")
        if str(entry.get("status") or "") != "PASS":
            return {
                "status": "HALT",
                "reason": str(entry.get("reason") or "historical_asof_listed_issues_not_ready"),
                "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
                "selected_snapshot_date": str(entry.get("selected_snapshot_date") or ""),
                "selected_snapshot_path": selected_path,
                "selected_content_hash": selected_hash,
            }
        actual_hash = _sha256_file(Path(selected_path))
        if not selected_path or not Path(selected_path).is_file():
            return {
                "status": "HALT",
                "reason": "historical_asof_listed_issues_path_missing",
                "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
                "selected_snapshot_path": selected_path,
            }
        if selected_hash and actual_hash != selected_hash:
            return {
                "status": "HALT",
                "reason": "historical_asof_listed_issues_hash_mismatch",
                "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
                "selected_snapshot_path": selected_path,
                "selected_content_hash": actual_hash,
                "expected_content_hash": selected_hash,
            }
        selected_snapshot_date = str(entry.get("selected_snapshot_date") or entry.get("logical_max_date") or "")
        if selected_snapshot_date and selected_snapshot_date > business_date:
            return {
                "status": "HALT",
                "reason": "historical_asof_listed_issues_future_snapshot_rejected",
                "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
                "selected_snapshot_date": selected_snapshot_date,
                "selected_snapshot_path": selected_path,
            }
        return {
            "status": "PASS",
            "reason": "historical_asof_listed_issues_authority_resolved_for_submit_guard",
            "pit_universe_authority_type": "HISTORICAL_ASOF_LISTED_ISSUES",
            "selected_snapshot_date": selected_snapshot_date,
            "selected_snapshot_path": selected_path,
            "selected_manifest_path": str(entry.get("manifest_path") or ""),
            "selected_content_hash": actual_hash,
            "expected_content_hash": selected_hash,
            "selected_schema_hash": str(entry.get("schema_hash") or ""),
            "selection_policy": str(entry.get("selection_policy") or "latest_snapshot_not_after_business_date"),
            "snapshot_age_days": entry.get("snapshot_age_days"),
            "future_snapshot_used": False,
            "content_hash_verified": bool(selected_hash and actual_hash == selected_hash),
            "row_count": int(entry.get("physical_row_count") or 0),
        }
    return {}


def _symbol_in_pit_universe(
    *,
    listed_path: Path,
    symbol: str,
    business_date: str,
    listed_info: dict[str, Any] | None,
    source: dict[str, Any],
) -> dict[str, Any]:
    normalized_symbol = _normalize_listed_issue_code(symbol)
    listed_info_code = _normalize_listed_issue_code((listed_info or {}).get("code") or "")
    if listed_info_code and listed_info_code != normalized_symbol:
        return {
            **source,
            "status": "HALT",
            "reason": "pending_listed_info_code_mismatch",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "pending_listed_info_code": listed_info_code,
            "lineage_match": False,
        }
    if not listed_path.exists():
        return {
            **source,
            "status": "HALT",
            "reason": "listed_issues_universe_path_missing",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "lineage_match": False,
        }
    try:
        import pandas as pd

        frame = pd.read_parquet(listed_path)
    except Exception:
        return {
            **source,
            "status": "HALT",
            "reason": "listed_issues_universe_unreadable",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "lineage_match": False,
        }
    frame = frame.copy()
    frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    pit = frame[frame["Date_s"] <= business_date]
    if pit.empty:
        return {
            **source,
            "status": "HALT",
            "reason": "listed_issues_snapshot_has_no_rows_not_after_business_date",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "row_count": int(len(frame)),
            "pit_row_count": 0,
            "lineage_match": False,
        }
    as_of = pit["Date_s"].max()
    code_column = "Code" if "Code" in frame.columns else "code" if "code" in frame.columns else ""
    if not code_column:
        return {
            **source,
            "status": "HALT",
            "reason": "listed_issues_code_column_missing",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "row_count": int(len(frame)),
            "pit_row_count": int(len(pit)),
            "lineage_match": False,
        }
    normalized_codes = frame[code_column].map(_normalize_listed_issue_code)
    rows = frame[(frame["Date_s"] == as_of) & (normalized_codes == normalized_symbol)]
    if rows.empty:
        return {
            **source,
            "status": "HALT",
            "reason": "symbol_missing_from_pit_universe",
            "requested_symbol": str(symbol),
            "normalized_symbol": normalized_symbol,
            "row_count": int(len(frame)),
            "pit_row_count": int(len(pit)),
            "resolved_as_of_date": str(as_of),
            "lineage_match": False,
        }
    return {
        **source,
        "status": "PASS",
        "reason": "symbol_found_in_pit_universe",
        "requested_symbol": str(symbol),
        "normalized_symbol": normalized_symbol,
        "row_count": int(len(frame)),
        "pit_row_count": int(len(pit)),
        "resolved_as_of_date": str(as_of),
        "matched_row_count": int(len(rows)),
        "lineage_match": True,
    }


def _normalize_listed_issue_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _corporate_action_status(raw_ohlcv_path: Path, business_date: str, symbol: str) -> str:
    return str(
        _corporate_action_evidence(
            raw_ohlcv_path=raw_ohlcv_path,
            business_date=business_date,
            symbol=symbol,
        ).get("corporate_action_status")
        or "MISSING"
    )


def _corporate_action_evidence(raw_ohlcv_path: Path, business_date: str, symbol: str) -> dict[str, Any]:
    base = {
        "corporate_action_guard_version": "historical_submit_adjfactor_guard_v2",
        "corporate_action_artifact_path": str(raw_ohlcv_path),
        "corporate_action_source": "jquants_raw_equities_bars_daily_adjfactor",
        "corporate_action_business_date": business_date,
        "corporate_action_symbol": str(symbol),
        "corporate_action_type": "UNKNOWN_ADJFACTOR_IMPACT",
        "corporate_action_type_authority": "not_available_from_adjfactor_only",
        "corporate_action_effective_date": business_date,
        "corporate_action_record_date": "",
        "corporate_action_adjustment_factor": None,
        "corporate_action_old_symbol": str(symbol),
        "corporate_action_new_symbol": str(symbol),
        "corporate_action_old_quantity": None,
        "corporate_action_new_quantity": None,
        "corporate_action_old_price": None,
        "corporate_action_new_price": None,
        "corporate_action_listing_continuity_status": "UNKNOWN_FROM_OHLCV_ADJFACTOR",
        "corporate_action_status": "MISSING",
        "corporate_action_reason": "raw_ohlcv_missing",
        "corporate_action_rows": [],
        "corporate_action_observability_status": "DETAIL_AVAILABLE",
    }
    if not raw_ohlcv_path.exists():
        return base
    try:
        import pandas as pd

        frame = pd.read_parquet(raw_ohlcv_path)
    except Exception:
        return {
            **base,
            "corporate_action_status": "UNREADABLE",
            "corporate_action_reason": "raw_ohlcv_unreadable",
        }
    frame = frame.copy()
    frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    code_column = "Code" if "Code" in frame.columns else "code" if "code" in frame.columns else ""
    if not code_column:
        return {
            **base,
            "corporate_action_status": "MISSING_CODE",
            "corporate_action_reason": "raw_ohlcv_code_column_missing",
        }
    normalized_symbol = _normalize_listed_issue_code(symbol)
    rows = frame[
        (frame["Date_s"] == business_date)
        & (frame[code_column].map(_normalize_listed_issue_code) == normalized_symbol)
    ]
    if rows.empty:
        return {
            **base,
            "corporate_action_status": "MISSING",
            "corporate_action_reason": "target_symbol_raw_ohlcv_row_missing",
        }
    if "AdjFactor" not in rows.columns:
        return {
            **base,
            "corporate_action_status": "MISSING_ADJFACTOR",
            "corporate_action_reason": "target_symbol_adjfactor_missing",
            "corporate_action_rows": _corporate_action_rows(rows),
        }
    factors = sorted({float(value) for value in rows["AdjFactor"].dropna().unique()})
    first = rows.iloc[0]
    factor = factors[0] if len(factors) == 1 else None
    raw_close = _optional_float(first.get("C"))
    adjusted_close = _optional_float(first.get("AdjC"))
    raw_open = _optional_float(first.get("O"))
    adjusted_open = _optional_float(first.get("AdjO"))
    status = "PASS" if factors == [1.0] else "IMPACT_DETECTED"
    return {
        **base,
        "corporate_action_status": status,
        "corporate_action_reason": "adjfactor_is_one"
        if status == "PASS"
        else "target_symbol_adjfactor_not_one",
        "corporate_action_adjustment_factor": factor,
        "corporate_action_adjustment_factors": factors,
        "corporate_action_old_price": raw_close if raw_close is not None else raw_open,
        "corporate_action_new_price": adjusted_close if adjusted_close is not None else adjusted_open,
        "corporate_action_rows": _corporate_action_rows(rows),
        "corporate_action_impact_detected_condition": "target_date_target_symbol_adjfactor_not_1",
    }


def _corporate_action_rows(rows: Any) -> list[dict[str, Any]]:
    fields = ("Date", "Code", "O", "H", "L", "C", "AdjFactor", "AdjO", "AdjH", "AdjL", "AdjC", "AdjVo")
    payload: list[dict[str, Any]] = []
    for row in rows.to_dict("records"):
        payload.append({field: _json_scalar(row.get(field)) for field in fields if field in row})
    return payload


def _runtime_current_quantity(runtime_root: Path, symbol: str) -> float | None:
    state = _read_json(runtime_root / "persistent_ledger" / "state.json")
    normalized = _normalize_listed_issue_code(symbol)
    quantity = 0.0
    matched = False
    for position in state.get("positions") or ():
        if not isinstance(position, dict):
            continue
        position_symbol = _normalize_listed_issue_code(position.get("symbol") or position.get("issue_code"))
        if position_symbol != normalized:
            continue
        matched = True
        quantity += _number(position.get("quantity"))
    return quantity if matched else None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_scalar(value: Any) -> Any:
    if value in (None, ""):
        return value
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _trading_unit_from_listed_info(listed_info: dict[str, Any] | None) -> float | None:
    if not listed_info:
        return None
    for key in ("trading_unit", "TradingUnit", "tradingUnit", "unit"):
        value = listed_info.get(key)
        if value not in (None, ""):
            unit = float(value)
            return unit if unit > 0 else None
    return None


def _order_payload(item: dict[str, Any]) -> dict[str, Any]:
    lineage = item.get("strategy_authority_lineage") if isinstance(item.get("strategy_authority_lineage"), dict) else {}
    return {
        "order_ref": item["order_identity"],
        "pending_plan_id": item["pending_plan_id"],
        "pending_item_id": item["pending_item_id"],
        "strategy_authority_lineage": lineage,
        "strategy_authority_lineage_hash": item.get("strategy_authority_lineage_hash") or "",
        "source_decision_id": (
            item.get("source_decision_id")
            or item.get("source_pm_decision_id")
            or lineage.get("source_decision_id")
            or lineage.get("source_pm_decision_id")
            or ""
        ),
        "source_decision_type": item.get("source_decision_type") or lineage.get("source_decision_type") or "",
        "source_pm_decision_id": item.get("source_pm_decision_id") or lineage.get("source_pm_decision_id") or "",
        "source_pm_business_date": item.get("source_pm_business_date") or lineage.get("source_pm_business_date") or "",
        "source_position_symbol": item.get("source_position_symbol") or lineage.get("source_position_symbol") or "",
        "position_campaign_id": item.get("position_campaign_id") or lineage.get("position_campaign_id") or "",
        "symbol": item["symbol"],
        "side": item["side"],
        "quantity": item["quantity"],
        "order_status": "filled",
        "filled_quantity": item["quantity"],
        "remaining_quantity": 0,
        "accepted_at": item["fill_datetime"],
        "updated_at": item["fill_datetime"],
    }


def _execution_payload(item: dict[str, Any]) -> dict[str, Any]:
    lineage = item.get("strategy_authority_lineage") if isinstance(item.get("strategy_authority_lineage"), dict) else {}
    return {
        "execution_ref": item["execution_identity"],
        "order_ref": item["order_identity"],
        "execution_key": item["execution_identity"],
        "strategy_authority_lineage": lineage,
        "strategy_authority_lineage_hash": item.get("strategy_authority_lineage_hash") or "",
        "source_decision_id": (
            item.get("source_decision_id")
            or item.get("source_pm_decision_id")
            or lineage.get("source_decision_id")
            or lineage.get("source_pm_decision_id")
            or ""
        ),
        "source_decision_type": item.get("source_decision_type") or lineage.get("source_decision_type") or "",
        "source_pm_decision_id": item.get("source_pm_decision_id") or lineage.get("source_pm_decision_id") or "",
        "source_pm_business_date": item.get("source_pm_business_date") or lineage.get("source_pm_business_date") or "",
        "source_position_symbol": item.get("source_position_symbol") or lineage.get("source_position_symbol") or "",
        "position_campaign_id": item.get("position_campaign_id") or lineage.get("position_campaign_id") or "",
        "symbol": item["symbol"],
        "side": item["side"],
        "quantity": item["quantity"],
        "price": item["fill_price"],
        "executed_at": item["fill_datetime"],
    }


def _position_payload(item: dict[str, Any]) -> dict[str, Any]:
    quantity = float(item["quantity"])
    average_price = float(item.get("average_price") or item.get("fill_price") or 0.0)
    market_value = float(item.get("market_value") or average_price * quantity)
    as_of = str(item.get("valuation_as_of") or item.get("as_of") or item.get("fill_date") or "")
    return {
        "position_ref": f"historical-position-{item['symbol']}-{as_of}" if as_of else f"historical-position-{item['symbol']}",
        "position_key": item["symbol"],
        "symbol": item["symbol"],
        "quantity": quantity,
        "average_price": average_price,
        "market_value": market_value,
    }
