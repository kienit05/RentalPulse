from collectors.mock_source import snapshot

EXPECTED_FIELDS = {
    "listing_id", "title", "property_type", "price_raw", "area_raw",
    "district_raw", "address_raw", "posted_at", "snapshot_date", "source",
}


def test_every_record_has_exactly_the_expected_fields():
    for day in (1, 2, 5):
        for record in snapshot(day):
            assert set(record) == EXPECTED_FIELDS


def test_raw_value_types_are_consistent():
    for record in snapshot(5):
        assert isinstance(record["price_raw"], str)
        assert record["area_raw"] is None or isinstance(record["area_raw"], str)
        assert record["source"] == "mock"