import pytest

pytest.importorskip("psycopg2")

from etl.load_raw import connect


@pytest.fixture(scope="module")
def conn():
    try:
        connection = connect()
    except Exception as exc:
        pytest.skip(f"Không kết nối được PostgreSQL: {exc}")
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('core.v_listing_events'), to_regclass('core.v_price_history')")
        if None in cur.fetchone():
            connection.close()
            pytest.skip("Chưa tạo view lịch sử (chạy sql/007_history_views.sql)")
        cur.execute("SELECT count(*) FROM core.listing_source WHERE listing_id = 'RP-S001'")
        if cur.fetchone()[0] == 0:
            connection.close()
            pytest.skip("Chưa nạp mock ngày 1-4 vào pipeline")
    yield connection
    connection.close()


def events(conn, listing_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_date, event_type FROM core.v_listing_events "
            "WHERE source = 'mock' AND listing_id = %s "
            "AND event_date <= DATE '2026-11-04' ORDER BY event_date",
            (listing_id,),
        )
        return [(d.isoformat(), t) for d, t in cur.fetchall()]


def changes(conn, listing_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT snapshot_date, change_type FROM core.v_price_history "
            "WHERE source = 'mock' AND listing_id = %s "
            "AND snapshot_date <= DATE '2026-11-04' ORDER BY snapshot_date",
            (listing_id,),
        )
        return [(d.isoformat(), t) for d, t in cur.fetchall()]


def test_tin_a_lifecycle_initial_disappeared_returned(conn):
    assert events(conn, "RP-S001") == [
        ("2026-11-01", "initial"), ("2026-11-03", "disappeared"), ("2026-11-04", "returned"),
    ]


def test_removed_listing_disappears_on_day_3(conn):
    assert events(conn, "RP-S004") == [("2026-11-01", "initial"), ("2026-11-03", "disappeared")]


def test_repost_is_first_seen_on_day_3(conn):
    assert events(conn, "RP-S005") == [("2026-11-03", "first_seen")]


def test_control_listing_has_no_events_after_initial(conn):
    assert events(conn, "RP-S006") == [("2026-11-01", "initial")]


def test_tin_a_price_increase_is_detected_once(conn):
    assert changes(conn, "RP-S001") == [
        ("2026-11-01", "first"), ("2026-11-02", "increase"), ("2026-11-04", "unchanged"),
    ]


def test_price_drop_is_detected(conn):
    assert changes(conn, "RP-S002") == [
        ("2026-11-01", "first"), ("2026-11-02", "unchanged"),
        ("2026-11-03", "decrease"), ("2026-11-04", "unchanged"),
    ]


def test_negotiable_to_priced_is_price_appeared(conn):
    assert changes(conn, "RP-S003") == [
        ("2026-11-01", "first"), ("2026-11-02", "no_price"),
        ("2026-11-03", "price_appeared"), ("2026-11-04", "unchanged"),
    ]