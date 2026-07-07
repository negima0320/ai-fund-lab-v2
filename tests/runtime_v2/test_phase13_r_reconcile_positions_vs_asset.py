from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import (
    normalize_broker_readonly_payload,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerCashRecord, LedgerPositionRecord
from ai_fund_lab_v2.runtime_v2.reconcile.checks import (
    check_broker_cash_vs_asset_state,
    check_broker_positions_vs_asset_state,
)


def test_asset_state_missing_requires_review_for_positions():
    findings = check_broker_positions_vs_asset_state(
        broker_positions=_broker_bundle().positions,
        asset_state=None,
    )

    assert _has_finding(findings, "ASSET_STATE_MISSING_FOR_POSITION_CHECK")


def test_broker_position_not_in_asset_requires_review():
    findings = check_broker_positions_vs_asset_state(
        broker_positions=_broker_bundle().positions,
        asset_state=_asset_state(positions=()),
    )

    assert _has_finding(findings, "BROKER_POSITION_MISSING_IN_ASSET")


def test_asset_position_not_in_broker_requires_review():
    findings = check_broker_positions_vs_asset_state(
        broker_positions=(),
        asset_state=_asset_state(),
    )

    assert _has_finding(findings, "ASSET_POSITION_MISSING_IN_BROKER")


def test_position_quantity_mismatch_requires_review():
    findings = check_broker_positions_vs_asset_state(
        broker_positions=_broker_bundle(quantity=50).positions,
        asset_state=_asset_state(),
    )

    assert _has_finding(findings, "POSITION_QUANTITY_MISMATCH")


def test_matching_positions_clean():
    findings = check_broker_positions_vs_asset_state(
        broker_positions=_broker_bundle().positions,
        asset_state=_asset_state(),
    )

    assert findings == ()


def test_broker_cash_missing_requires_review():
    findings = check_broker_cash_vs_asset_state(
        broker_cash=None,
        asset_state=_asset_state(),
    )

    assert _has_finding(findings, "BROKER_CASH_MISSING")


def test_cash_and_buying_power_mismatch_require_review():
    findings = check_broker_cash_vs_asset_state(
        broker_cash=_broker_bundle(cash=1, buying_power=2).cash,
        asset_state=_asset_state(),
    )

    assert _has_finding(findings, "CASH_MISMATCH")
    assert _has_finding(findings, "BUYING_POWER_MISMATCH")


def test_matching_cash_clean():
    findings = check_broker_cash_vs_asset_state(
        broker_cash=_broker_bundle().cash,
        asset_state=_asset_state(),
    )

    assert findings == ()


def _broker_bundle(quantity=100, cash=100000, buying_power=50000):
    return normalize_broker_readonly_payload(
        environment="demo",
        source="broker_readonly",
        as_of="2026-07-07",
        positions=(
            {
                "position_ref": "POS-1",
                "position_key": "7203",
                "symbol": "7203",
                "quantity": quantity,
                "average_price": 2500,
                "market_value": 250000,
            },
        ),
        cash={"cash_ref": "CASH-1", "cash": cash, "buying_power": buying_power},
    )


def _asset_state(positions=None):
    if positions is None:
        positions = (
            LedgerPositionRecord(
                record_id="pos-1",
                record_type="position",
                schema_version="1",
                environment="demo",
                source="broker_positions",
                created_at="2026-07-07",
                dedup_key="pos-1",
                position_key="7203",
                symbol="7203",
                quantity=100,
                average_price=2500,
                market_value=250000,
                as_of="2026-07-07",
            ),
        )
    return build_current_asset_state(
        environment="demo",
        positions=positions,
        cash_records=(
            LedgerCashRecord(
                record_id="cash-1",
                record_type="cash",
                schema_version="1",
                environment="demo",
                source="broker_cash",
                created_at="2026-07-07",
                dedup_key="cash-1",
                cash_key="cash-1",
                cash=100000,
                buying_power=50000,
                as_of="2026-07-07",
            ),
        ),
        source="broker_positions",
        as_of="2026-07-07",
    )


def _has_finding(findings, finding_type: str) -> bool:
    return any(finding.finding_type == finding_type for finding in findings)

