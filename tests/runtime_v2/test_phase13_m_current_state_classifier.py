from ai_fund_lab_v2.runtime_v2.current_state.classifier import classify_current_state


def test_missing_sets_safe_unknown_flags():
    result = classify_current_state(
        object_type="persistent_ledger_state",
        exists=False,
        validation_ok=False,
        payload=None,
        errors=("current file missing",),
    )

    assert result.classification == "MISSING"
    assert result.state_missing is True
    assert result.current_state_confirmed_empty is False
    assert result.current_positions_unknown is True
    assert result.cash_unknown is True
    assert result.buying_power_unknown is True
    assert result.review_required is True


def test_unknown_sets_positions_cash_and_buying_power_unknown():
    result = classify_current_state(
        object_type="persistent_ledger_state",
        exists=True,
        validation_ok=True,
        payload={
            "schema_version": "1",
            "asset_state_id": "asset-1",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": None,
            "cash": None,
            "buying_power": None,
            "source": "unknown",
            "review_required": False,
        },
        expected_environment="demo",
    )

    assert result.classification == "UNKNOWN"
    assert result.current_positions_unknown is True
    assert result.cash_unknown is True
    assert result.buying_power_unknown is True
    assert result.current_state_confirmed_empty is False


def test_confirmed_empty_requires_explicit_flag_cash_buying_power_and_source():
    result = classify_current_state(
        object_type="persistent_ledger_state",
        exists=True,
        validation_ok=True,
        payload={
            "schema_version": "1",
            "asset_state_id": "asset-empty",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": [],
            "cash": {"amount": 100000},
            "buying_power": {"amount": 100000},
            "cash_confirmed": True,
            "buying_power_confirmed": True,
            "current_state_confirmed_empty": True,
            "source": "broker_positions",
            "review_required": False,
        },
        expected_environment="demo",
    )

    assert result.classification == "CONFIRMED_EMPTY"
    assert result.valid is True
    assert result.current_state_confirmed_empty is True
    assert result.current_positions_unknown is False
    assert result.cash_unknown is False
    assert result.buying_power_unknown is False


def test_confirmed_empty_is_not_inferred_without_explicit_flag():
    result = classify_current_state(
        object_type="persistent_ledger_state",
        exists=True,
        validation_ok=True,
        payload={
            "schema_version": "1",
            "asset_state_id": "asset-empty",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": [],
            "cash": {"amount": 100000},
            "buying_power": {"amount": 100000},
            "cash_confirmed": True,
            "buying_power_confirmed": True,
            "source": "broker_positions",
            "review_required": False,
        },
        expected_environment="demo",
    )

    assert result.classification == "VALID"
    assert result.current_state_confirmed_empty is False


def test_broker_orders_fallback_requires_review():
    result = classify_current_state(
        object_type="persistent_ledger_positions",
        exists=True,
        validation_ok=True,
        payload={
            "schema_version": "1",
            "ledger_record_id": "position-1",
            "position_key": "7203",
            "recorded_at": "2026-07-07T00:00:00Z",
            "environment": "demo",
            "source": "broker_orders_fallback",
            "review_required": False,
        },
        expected_environment="demo",
    )

    assert result.classification == "REVIEW_REQUIRED"
    assert result.review_required is True


def test_production_equivalent_false_requires_review():
    result = classify_current_state(
        object_type="persistent_ledger_positions",
        exists=True,
        validation_ok=True,
        payload={
            "schema_version": "1",
            "ledger_record_id": "position-1",
            "position_key": "7203",
            "recorded_at": "2026-07-07T00:00:00Z",
            "environment": "demo",
            "source": "broker_positions",
            "production_equivalent": False,
            "review_required": False,
        },
        expected_environment="demo",
    )

    assert result.classification == "REVIEW_REQUIRED"
    assert result.review_required is True

