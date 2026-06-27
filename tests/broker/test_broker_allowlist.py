import pytest

from ai_fund_lab_v2.broker import FORBIDDEN_CLMIDS, READ_ONLY_CLMIDS, BrokerAllowlistError, ensure_read_only_clmid, is_read_only_clmid


def test_read_only_clmids_are_allowed() -> None:
    for clmid in READ_ONLY_CLMIDS:
        assert ensure_read_only_clmid(clmid) == clmid
        assert is_read_only_clmid(clmid)


def test_forbidden_order_clmids_are_rejected() -> None:
    for clmid in FORBIDDEN_CLMIDS:
        with pytest.raises(BrokerAllowlistError, match="forbidden in Phase10-C"):
            ensure_read_only_clmid(clmid)


def test_unknown_clmid_is_rejected() -> None:
    with pytest.raises(BrokerAllowlistError, match="not in the Phase10 read-only allowlist"):
        ensure_read_only_clmid("CLMUnknownRead")
