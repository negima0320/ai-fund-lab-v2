from ai_fund_lab_v2.runtime_v2.notification.delivery_ledger import (
    DeliveryLedgerRecord,
    DeliveryStatus,
    is_duplicate_delivery,
)


def test_same_payload_hash_channel_target_date_is_duplicate():
    record = _record()

    assert is_duplicate_delivery(
        existing_records=(record,),
        payload_hash="hash-1",
        channel="discord",
        target_date="2026-07-07",
    )


def test_different_channel_is_not_duplicate():
    record = _record()

    assert not is_duplicate_delivery(
        existing_records=(record,),
        payload_hash="hash-1",
        channel="line",
        target_date="2026-07-07",
    )


def test_different_target_date_is_not_duplicate():
    record = _record()

    assert not is_duplicate_delivery(
        existing_records=(record,),
        payload_hash="hash-1",
        channel="discord",
        target_date="2026-07-08",
    )


def test_post_send_unknown_status_can_be_represented():
    record = _record(status=DeliveryStatus.POST_SEND_UNKNOWN)

    assert record.status == DeliveryStatus.POST_SEND_UNKNOWN
    assert record.review_required is True


def test_delivery_ledger_has_no_sender_method():
    assert not hasattr(DeliveryLedgerRecord, "send")


def _record(status=DeliveryStatus.SENT):
    return DeliveryLedgerRecord(
        delivery_id="delivery-1",
        payload_hash="hash-1",
        channel="discord",
        target_date="2026-07-07",
        status=status,
        sent_at="2026-07-07T00:00:00Z" if status == DeliveryStatus.SENT else "",
        retry_allowed=False,
        review_required=status == DeliveryStatus.POST_SEND_UNKNOWN,
        created_at="2026-07-07",
    )

