from collectors.mock_source import snapshot


def ids(day):
    return {r["listing_id"] for r in snapshot(day)}


def by_id(day):
    return {r["listing_id"]: r for r in snapshot(day)}


def without_date(record):
    return {k: v for k, v in record.items() if k != "snapshot_date"}


def test_tin_a_disappears_on_day_3_and_returns_on_day_4():
    assert "RP-S001" in ids(2)
    assert "RP-S001" not in ids(3)
    assert "RP-S001" in ids(4)


def test_tin_a_price_text_changes_only_when_price_changes():
    assert by_id(1)["RP-S001"]["price_raw"] != by_id(2)["RP-S001"]["price_raw"]
    assert by_id(2)["RP-S001"]["price_raw"] == by_id(4)["RP-S001"]["price_raw"]


def test_control_listing_never_changes():
    first = without_date(by_id(1)["RP-S006"])
    for day in range(2, 8):
        assert without_date(by_id(day)["RP-S006"]) == first


def test_repost_has_new_id_but_same_address():
    old = by_id(2)["RP-S004"]
    new = by_id(3)["RP-S005"]
    assert old["listing_id"] != new["listing_id"]
    assert old["address_raw"] == new["address_raw"]
    assert "RP-S004" not in ids(3)