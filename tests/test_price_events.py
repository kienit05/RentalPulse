"""Test dựng event price_changed từ một dòng của core.v_price_history."""
import datetime as dt
import json
from decimal import Decimal

from etl.publish_price_changes import build_price_event, to_number


def make_row(**overrides):
    row = {
        "source": "mock",
        "listing_id": "RP-000028",
        "is_simulated": True,
        "snapshot_date": dt.date(2026, 11, 2),
        "prev_snapshot_date": dt.date(2026, 11, 1),
        "prev_price_vnd": Decimal("9000000"),
        "price_vnd": Decimal("8100000"),
        "change_vnd": Decimal("-900000"),
        "change_pct": Decimal("-10.0"),
        "change_type": "decrease",
    }
    row.update(overrides)
    return row


def test_event_key_and_id_are_stable():
    message_key, event = build_price_event(make_row())
    assert message_key == "mock:RP-000028"
    assert event["event_id"] == "price_changed:mock:RP-000028:2026-11-02"
    assert event["event_type"] == "price_changed"


def test_event_values_are_json_friendly():
    _, event = build_price_event(make_row())
    assert event["old_price_vnd"] == 9000000
    assert event["new_price_vnd"] == 8100000
    assert event["change_vnd"] == -900000
    assert event["change_pct"] == -10.0
    assert event["snapshot_date"] == "2026-11-02"
    assert event["prev_snapshot_date"] == "2026-11-01"
    json.dumps(event)  # không được ném lỗi (không còn Decimal hay date)


def test_decimal_with_fraction_zero_becomes_int():
    assert to_number(Decimal("8000000.0")) == 8000000
    assert isinstance(to_number(Decimal("8000000.0")), int)


def test_decimal_with_real_fraction_stays_float():
    assert to_number(Decimal("-6.3")) == -6.3


def test_none_stays_none():
    assert to_number(None) is None


def test_increase_event():
    _, event = build_price_event(
        make_row(prev_price_vnd=Decimal("8000000"), price_vnd=Decimal("9000000"),
                 change_vnd=Decimal("1000000"), change_pct=Decimal("12.5"), change_type="increase")
    )
    assert event["change_type"] == "increase"
    assert event["change_vnd"] == 1000000