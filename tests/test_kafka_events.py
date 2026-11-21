"""Test hai hàm thuần của Kafka: build_event (producer) và parse_event (consumer)."""
import json

import pytest

from etl.consume_events import parse_event
from etl.publish_batch import build_event

BATCH = {
    "batch_id": "20261121T030000Z-abc123",
    "source": "nhatot",
    "snapshot_date": "2026-11-21",
}
KEY = "source=nhatot/dt=2026-11-21/batch_id=20261121T030000Z-abc123/listings.json"


def make_event(**overrides):
    event = {
        "event_id": "20261121T030000Z-abc123:7",
        "event_type": "listing_observed",
        "source": "nhatot",
        "listing_id": "123",
        "snapshot_date": "2026-11-21",
        "batch_id": "20261121T030000Z-abc123",
        "bronze_key": KEY,
        "payload": {"listing_id": "123", "title": "Phòng trọ Cầu Giấy"},
    }
    event.update(overrides)
    return event


def test_build_event_key_and_event_id():
    message_key, event = build_event(KEY, BATCH, 7, {"listing_id": "123", "title": "x"})
    assert message_key == "nhatot:123"
    assert event["event_id"] == "20261121T030000Z-abc123:7"
    assert event["event_type"] == "listing_observed"
    assert event["payload"]["title"] == "x"


def test_build_event_listing_id_becomes_text():
    _, event = build_event(KEY, BATCH, 1, {"listing_id": 123})
    assert event["listing_id"] == "123"


@pytest.mark.parametrize("record", [{}, {"listing_id": None}, {"listing_id": ""}])
def test_build_event_without_listing_id_returns_none(record):
    assert build_event(KEY, BATCH, 1, record) is None


def test_parse_event_valid_gives_row_for_raw_listings():
    row, reason = parse_event(json.dumps(make_event()).encode("utf-8"))
    assert reason is None
    batch_id, source, snapshot_date, bronze_key, record_no, payload = row
    assert (batch_id, source, snapshot_date) == ("20261121T030000Z-abc123", "nhatot", "2026-11-21")
    assert bronze_key == KEY
    assert record_no == 7
    assert payload.adapted["title"] == "Phòng trọ Cầu Giấy"


def test_producer_event_is_accepted_by_consumer():
    """Hợp đồng hai phía: event producer dựng ra phải qua được consumer."""
    _, event = build_event(KEY, BATCH, 3, {"listing_id": "9", "title": "t"})
    row, reason = parse_event(json.dumps(event).encode("utf-8"))
    assert reason is None
    assert row[4] == 3


@pytest.mark.parametrize(
    "raw_value, expected_reason",
    [
        (b"khong phai json", "không phải JSON"),
        (b"[1, 2]", "không phải object"),
        (json.dumps({"type": "smoke_test"}).encode(), "event_type không hỗ trợ"),
        (json.dumps(make_event(listing_id="")).encode(), "thiếu trường: listing_id"),
        (json.dumps(make_event(event_id="khong-co-so")).encode(), "event_id sai định dạng"),
        (json.dumps(make_event(event_id="abc:xyz")).encode(), "event_id sai định dạng"),
    ],
)
def test_parse_event_bad_input_goes_to_dlq(raw_value, expected_reason):
    row, reason = parse_event(raw_value)
    assert row is None
    assert expected_reason in reason