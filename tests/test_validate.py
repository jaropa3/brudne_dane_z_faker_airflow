import pandas as pd
import pytest

from src.validate import REQUIRED_COLUMNS, validate


def _row(**overrides):
    base = {
        "order_id": "1",
        "customer_id": "10",
        "product_id": "100",
        "quantity": "2",
        "amount": "9.99",
        "order_date": "2024-01-15",
        "status": "paid",
    }
    base.update(overrides)
    return base


def test_happy_path_one_valid_row():
    df = pd.DataFrame([_row()])
    valid, quarantine, duplicates = validate(df)
    assert len(valid) == 1
    assert len(quarantine) == 0
    assert len(duplicates) == 0


def test_missing_column_raises():
    df = pd.DataFrame([{c: "x" for c in REQUIRED_COLUMNS if c != "status"}])
    with pytest.raises(ValueError, match="Missing columns"):
        validate(df)


def test_invalid_status_goes_to_quarantine_with_flag():
    df = pd.DataFrame([_row(status="totally-fake")])
    valid, quarantine, _ = validate(df)
    assert len(valid) == 0
    assert len(quarantine) == 1
    assert quarantine.iloc[0]["fail_valid_status"]


def test_negative_quantity_quarantined():
    df = pd.DataFrame([_row(quantity="-3")])
    valid, quarantine, _ = validate(df)
    assert len(valid) == 0
    assert quarantine.iloc[0]["fail_positive_qty"]


def test_future_date_quarantined():
    df = pd.DataFrame([_row(order_date="2999-01-01")])
    valid, quarantine, _ = validate(df)
    assert len(valid) == 0
    assert quarantine.iloc[0]["fail_not_future_date"]


def test_unparseable_date_quarantined_without_double_flag():
    df = pd.DataFrame([_row(order_date="not-a-date")])
    valid, quarantine, _ = validate(df)
    assert len(valid) == 0
    row = quarantine.iloc[0]
    assert row["fail_valid_date"]
    # not_future_date must be cleared when valid_date already failed
    assert not row["fail_not_future_date"]


def test_duplicate_order_id_keeps_last_by_date():
    df = pd.DataFrame([
        _row(order_id="5", order_date="2024-01-01"),
        _row(order_id="5", order_date="2024-06-01"),
    ])
    valid, _, duplicates = validate(df)
    assert len(valid) == 1
    assert len(duplicates) == 1
    assert valid.iloc[0]["order_date"] == pd.Timestamp("2024-06-01")
