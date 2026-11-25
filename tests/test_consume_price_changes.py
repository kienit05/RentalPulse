import json
from datetime import date
from decimal import Decimal

from etl.consume_price_changes import parse_price_event
from etl.publish_price_changes import build_price_event


def _row():
    return {
        "source": "nhatot",
        "listing_id": "123",
        "is_simulated": False,
        "snapshot_date": date(2026, 11, 25),
        "prev_snapshot_date": date(2026, 11, 24),
        "prev_price_vnd": Decimal("4000000"),
        "price_vnd": Decimal("3800000"),
        "change_vnd": Decimal("-200000"),
        "change_pct": Decimal("-5.0"),
        "change_type": "decrease",
    }


def test_published_event_is_accepted_by_consumer():
    _, event = build_price_event(_row())
    row, reason = parse_price_event(json.dumps(event))
    assert reason is None
    assert row[0] == "price_changed:nhatot:123:2026-11-25"
    assert row[-1] == "decrease"


def test_bad_json_goes_to_dlq():
    row, reason = parse_price_event(b"not json")
    assert row is None and "JSON" in reason


def test_wrong_event_type_goes_to_dlq():
    row, reason = parse_price_event(json.dumps({"event_type": "listing_observed"}))
    assert row is None and "event_type" in reason


def test_missing_field_goes_to_dlq():
    _, event = build_price_event(_row())
    del event["new_price_vnd"]
    row, reason = parse_price_event(json.dumps(event))
    assert row is None and "new_price_vnd" in reason


def test_invalid_change_type_goes_to_dlq():
    _, event = build_price_event(_row())
    event["change_type"] = "same"
    row, reason = parse_price_event(json.dumps(event))
    assert row is None and "change_type" in reason