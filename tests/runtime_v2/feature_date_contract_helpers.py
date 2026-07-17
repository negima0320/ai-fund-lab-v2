from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    resolve_feature_date_contract,
    write_feature_date_contract,
)


def materialize_feature_date_contract(
    runtime_root: Path,
    *,
    business_date: str,
    selected_feature_date: str,
) -> Path:
    operations_root = runtime_root / "operations"
    contract = resolve_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=business_date,
        latest_available_market_date=selected_feature_date,
    )
    return write_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=business_date,
        contract=contract,
    )
