from etl.publish_price_changes import filter_unpublished


def make(event_id):
    return (f"key-{event_id}", {"event_id": event_id})


def test_keeps_only_events_not_in_ledger():
    events = [make("a"), make("b"), make("c")]
    result = filter_unpublished(events, {"b"})
    assert [e["event_id"] for _, e in result] == ["a", "c"]


def test_empty_ledger_keeps_everything():
    events = [make("a"), make("b")]
    assert filter_unpublished(events, set()) == events


def test_everything_published_leaves_nothing():
    assert filter_unpublished([make("a")], {"a"}) == []


def test_order_is_preserved():
    events = [make("c"), make("a"), make("b")]
    result = filter_unpublished(events, {"a"})
    assert [e["event_id"] for _, e in result] == ["c", "b"]