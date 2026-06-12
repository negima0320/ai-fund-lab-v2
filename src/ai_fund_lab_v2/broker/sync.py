from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.models import BrokerBalanceSnapshot, utc_now_iso
from ai_fund_lab_v2.broker.normalizer import (
    normalize_balance_summary,
    normalize_buying_power,
    normalize_cash_positions,
    normalize_margin_positions,
    normalize_order_list,
)
from ai_fund_lab_v2.broker.sanitizer import sanitize_text
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.snapshot_writer import BrokerSnapshotWriteResult, BrokerSnapshotWriter
from ai_fund_lab_v2.broker.sync_result import BrokerSyncResult
from ai_fund_lab_v2.broker.transport import MockBrokerTransport


@dataclass(frozen=True)
class BrokerSyncRunner:
    client: TachibanaReadOnlyClient
    writer: BrokerSnapshotWriter

    def run(self) -> BrokerSyncResult:
        started_at = utc_now_iso()
        try:
            balance_summary = self.client.get_balance_summary()
            buying_power = self.client.get_buying_power()
            cash_positions = self.client.get_cash_positions()
            margin_positions = self.client.get_margin_positions()
            order_list = self.client.get_order_list()

            balance_snapshots = [
                normalize_balance_summary(balance_summary),
                normalize_buying_power(buying_power),
            ]
            positions = normalize_cash_positions(cash_positions) + normalize_margin_positions(margin_positions)
            orders = normalize_order_list(order_list)

            write_results = [
                self.writer.write_balance(_merge_balance_snapshots(balance_snapshots)),
                self.writer.write_positions(positions),
                self.writer.write_orders(orders),
            ]
            warnings = _collect_warnings(balance_snapshots, positions, orders)
            return _success_result(
                started_at=started_at,
                balance_count=1,
                position_count=len(positions),
                order_count=len(orders),
                write_results=write_results,
                warnings=warnings,
            )
        except Exception as exc:  # pragma: no cover - exercised through behavior, kept defensive for sync summary.
            return BrokerSyncResult(
                started_at=started_at,
                finished_at=utc_now_iso(),
                status="error",
                errors=(sanitize_text(str(exc)),),
            )


def build_mock_broker_sync_runner(writer: BrokerSnapshotWriter) -> BrokerSyncRunner:
    transport = build_default_mock_transport()
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="mock-auth-id"), transport)
    return BrokerSyncRunner(client=client, writer=writer)


def build_default_mock_transport() -> MockBrokerTransport:
    transport = MockBrokerTransport()
    for clmid, response in _default_fixture_responses().items():
        transport.register_response(clmid, response)
    return transport


def _default_fixture_responses() -> dict[str, dict[str, Any]]:
    return {
        "CLMZanKaiSummary": {
            "sCLMID": "CLMZanKaiSummary",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "sGenkinZandaka": "1000000",
            "sGenbutuKabuKaituke": "800000",
            "sSyukkinKanougaku": "700000",
            "sHyokaGakuGoukei": "1250000",
        },
        "CLMZanKaiKanougaku": {
            "sCLMID": "CLMZanKaiKanougaku",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "sKanougaku": "800000",
        },
        "CLMGenbutuKabuList": {
            "sCLMID": "CLMGenbutuKabuList",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "positions": [
                {
                    "sIssueCode": "7203",
                    "sIssueName": "TOYOTA",
                    "sZanKabuSuu": "100",
                    "sUritukeKanouSuu": "100",
                    "sBokaTanka": "2500",
                    "sGenzaine": "2600",
                    "sHyokaGaku": "260000",
                    "sHyokaSoneki": "10000",
                }
            ],
        },
        "CLMShinyouTategyokuList": {
            "sCLMID": "CLMShinyouTategyokuList",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "positions": [],
        },
        "CLMOrderList": {
            "sCLMID": "CLMOrderList",
            "sResultCode": "0",
            "as_of": "2026-06-12T00:00:00+00:00",
            "orders": [
                {
                    "sOrderNo": "MOCK-ORDER-001",
                    "sIssueCode": "7203",
                    "sIssueName": "TOYOTA",
                    "sBaibaiKubun": "1",
                    "sOrderPriceKubun": "limit",
                    "sOrderSuryou": "100",
                    "sYakujouSuryou": "0",
                    "sOrderZanSuryou": "100",
                    "sOrderPrice": "2500",
                    "sOrderStatus": "open",
                    "sOrderDatetime": "2026-06-12T09:00:00+09:00",
                    "sSikkouDay": "2026-06-12",
                }
            ],
        },
    }


def _merge_balance_snapshots(snapshots: list[BrokerBalanceSnapshot]) -> BrokerBalanceSnapshot:
    summary = snapshots[0]
    buying_power = snapshots[1] if len(snapshots) > 1 else summary
    return BrokerBalanceSnapshot(
        source="mock",
        as_of=summary.as_of,
        currency=summary.currency,
        cash_available=summary.cash_available,
        buying_power=buying_power.buying_power or summary.buying_power,
        withdrawable_cash=summary.withdrawable_cash,
        total_assets=summary.total_assets,
        raw_clmid=f"{summary.raw_clmid}+{buying_power.raw_clmid}",
        raw_result_code=summary.raw_result_code,
        warnings=summary.warnings + buying_power.warnings,
    )


def _success_result(
    *,
    started_at: str,
    balance_count: int,
    position_count: int,
    order_count: int,
    write_results: list[BrokerSnapshotWriteResult],
    warnings: tuple[str, ...],
) -> BrokerSyncResult:
    return BrokerSyncResult(
        started_at=started_at,
        finished_at=utc_now_iso(),
        status="success",
        balance_snapshot_count=balance_count,
        position_snapshot_count=position_count,
        order_snapshot_count=order_count,
        snapshot_paths=tuple(str(result.data_path) for result in write_results),
        manifest_paths=tuple(str(result.manifest_path) for result in write_results),
        warnings=tuple(sanitize_text(warning) for warning in warnings),
    )


def _collect_warnings(*snapshot_groups: Any) -> tuple[str, ...]:
    warnings: list[str] = []
    for group in snapshot_groups:
        for snapshot in group:
            warnings.extend(snapshot.warnings)
    return tuple(warnings)
