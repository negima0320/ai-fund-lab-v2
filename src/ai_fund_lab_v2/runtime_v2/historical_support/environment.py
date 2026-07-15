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
        }

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
        price = self._resolve_open_price(command.symbol, command.target_session_date)
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

    def _resolve_open_price(self, symbol: str, target_session_date: str) -> dict[str, Any]:
        ohlcv_path = Path(self.ohlcv_path)
        expected_hash = _expected_source_hash(Path(self.pit_manifest_path), target_session_date, "ohlcv_normalized")
        asof_expected = _expected_source_hash_from_asof_view(
            Path(self.historical_asof_view_path),
            target_session_date,
            authority="normalized_ohlcv",
            source_path=ohlcv_path,
        )
        if asof_expected:
            expected_hash = asof_expected
        actual_hash = _sha256_file(ohlcv_path)
        if expected_hash and actual_hash != expected_hash:
            return _classification("HALT", "source hash mismatch", source_hash=actual_hash, expected_hash=expected_hash)
        if not _symbol_in_pit_universe(Path(self.listed_issues_path), symbol, target_session_date):
            return _classification("HALT", "symbol missing from PIT universe")
        ca_status = _corporate_action_status(Path(self.raw_ohlcv_path), target_session_date)
        if ca_status != "PASS":
            return _classification("HALT", "corporate action guard failed", corporate_action_status=ca_status)
        try:
            import pandas as pd

            frame = pd.read_parquet(ohlcv_path).copy()
        except Exception as exc:
            return _classification("HALT", f"ohlcv source unreadable: {exc}")
        frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        rows = frame[
            (frame["Date_s"] == target_session_date)
            & (frame["Code"].astype(str).str.strip() == str(symbol).strip())
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
            "source_hash": actual_hash,
        }

    def _submission_evidence_path(self, execution_identity: str) -> Path:
        root = Path(self.runtime_root)
        return root / "runtime_state" / "historical_broker" / self.business_date / f"{execution_identity}.json"


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
            "positions": [_position_payload(item) for item in evidence_items if item.get("side") == "BUY"],
            "buying_power": {
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
        starting_cash = _number(state.get("cash") or state.get("runtime_evaluation_capital"))
        cash_effect = sum(_number(item.get("cash_effect")) for item in evidence_items)
        return starting_cash + cash_effect


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
    return RuntimeEnvironmentComposition(
        runtime_mode="historical",
        run_type="HISTORICAL",
        broker_environment="historical_simulated",
        submit_adapter=HistoricalSubmitAdapter(
            runtime_root=runtime_root,
            business_date=business_date,
            evaluation_time=evaluation_time,
            historical_asof_view_path=historical_asof_view_path,
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


def _symbol_in_pit_universe(listed_path: Path, symbol: str, business_date: str) -> bool:
    if not listed_path.exists():
        return False
    try:
        import pandas as pd

        frame = pd.read_parquet(listed_path)
    except Exception:
        return False
    frame = frame.copy()
    frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    pit = frame[frame["Date_s"] <= business_date]
    if pit.empty:
        return False
    as_of = pit["Date_s"].max()
    rows = frame[(frame["Date_s"] == as_of) & (frame["Code"].astype(str).str.strip() == str(symbol).strip())]
    return not rows.empty


def _corporate_action_status(raw_ohlcv_path: Path, business_date: str) -> str:
    if not raw_ohlcv_path.exists():
        return "MISSING"
    try:
        import pandas as pd

        frame = pd.read_parquet(raw_ohlcv_path)
    except Exception:
        return "UNREADABLE"
    frame = frame.copy()
    frame["Date_s"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    rows = frame[frame["Date_s"] == business_date]
    if rows.empty:
        return "MISSING"
    if "AdjFactor" not in rows.columns:
        return "MISSING_ADJFACTOR"
    factors = sorted({float(value) for value in rows["AdjFactor"].dropna().unique()})
    return "PASS" if factors == [1.0] else "IMPACT_DETECTED"


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
    return {
        "order_ref": item["order_identity"],
        "pending_plan_id": item["pending_plan_id"],
        "pending_item_id": item["pending_item_id"],
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
    return {
        "execution_ref": item["execution_identity"],
        "order_ref": item["order_identity"],
        "execution_key": item["execution_identity"],
        "symbol": item["symbol"],
        "side": item["side"],
        "quantity": item["quantity"],
        "price": item["fill_price"],
        "executed_at": item["fill_datetime"],
    }


def _position_payload(item: dict[str, Any]) -> dict[str, Any]:
    market_value = float(item["fill_price"]) * float(item["quantity"])
    return {
        "position_ref": f"historical-position-{item['symbol']}",
        "position_key": item["symbol"],
        "symbol": item["symbol"],
        "quantity": item["quantity"],
        "average_price": item["fill_price"],
        "market_value": market_value,
    }
