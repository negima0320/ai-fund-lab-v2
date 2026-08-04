from __future__ import annotations

import json

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from tests.runtime_v2.phase15by_buy_origin_e2e import run_phase15by_buy_origin_e2e
from tests.runtime_v2.phase15by2_authority_cleanup import run_phase15by2_authority_cleanup
def test_phase15by2_normalizer_keeps_production_records_production_equivalent():
    production = normalize_broker_readonly_payload(
        environment="production",
        source="runtime_v2_execution_readonly",
        as_of="2026-07-14T09:00:00+09:00",
        orders=(),
        executions=(),
        positions=(),
        cash=None,
    )
    simulation = normalize_broker_readonly_payload(
        environment="demo",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2026-07-14T09:00:00+09:00",
        orders=(),
        executions=(),
        positions=(),
        cash=None,
    )

    assert production.production_equivalent is True
    assert simulation.production_equivalent is False
