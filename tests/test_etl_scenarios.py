"""Kiểm thử ETL theo đáp án biết trước của nguồn mock (kịch bản RP-S001..RP-S006).

Test đọc thẳng PostgreSQL (schema core, staging). Tự bỏ qua nếu không kết nối được
database hoặc nếu chưa nạp mock ngày 1-4 vào pipeline.
"""
import pytest

pytest.importorskip("psycopg2")

from etl.load_raw import connect


@pytest.fixture(scope="module")
def conn():
    try:
        connection = connect()
    except Exception as exc:  # không có .env, Docker tắt...
        pytest.skip(f"Không kết nối được PostgreSQL: {exc}")
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('core.fact_listing_snapshot')")
        if cur.fetchone()[0] is None:
            connection.close()
            pytest.skip("Chưa tạo bảng core (chạy sql/005 và sql/006)")
    yield connection
    connection.close()


def day(n):
    return f"2026-11-0{n}"


def history(conn, listing_id):
    """Lịch sử (ngày, giá) của một tin mock trong Core, theo thứ tự ngày."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.snapshot_date, f.price_vnd
            FROM core.fact_listing_snapshot f
            JOIN core.listing_source ls USING (listing_key)
            WHERE ls.source = 'mock' AND ls.listing_id = %s
            ORDER BY f.snapshot_date
            """,
            (listing_id,),
        )
        return [(d.isoformat(), None if p is None else int(p)) for d, p in cur.fetchall()]


@pytest.fixture(scope="module", autouse=True)
def scenarios_loaded(conn):
    if not history(conn, "RP-S001"):
        pytest.skip("Chưa nạp mock ngày 1-4 vào pipeline")


def test_tin_a_price_rises_disappears_and_returns(conn):
    assert history(conn, "RP-S001") == [
        (day(1), 3_500_000), (day(2), 4_000_000), (day(4), 4_000_000),
    ]


def test_price_drops_on_day_3(conn):
    assert history(conn, "RP-S002") == [
        (day(1), 8_000_000), (day(2), 8_000_000), (day(3), 7_500_000), (day(4), 7_500_000),
    ]


def test_negotiable_becomes_priced_on_day_3(conn):
    assert history(conn, "RP-S003") == [
        (day(1), None), (day(2), None), (day(3), 5_000_000), (day(4), 5_000_000),
    ]


def test_removed_listing_stops_on_day_3(conn):
    assert history(conn, "RP-S004") == [(day(1), 3_000_000), (day(2), 3_000_000)]


def test_repost_starts_on_day_3_with_new_id(conn):
    assert history(conn, "RP-S005") == [(day(3), 3_000_000), (day(4), 3_000_000)]


def test_repost_has_same_address_as_original(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT listing_id, street_raw FROM staging.listings "
            "WHERE source = 'mock' AND listing_id IN ('RP-S004', 'RP-S005')"
        )
        streets = dict(cur.fetchall())
    assert streets["RP-S004"] is not None
    assert streets["RP-S004"] == streets["RP-S005"]


def test_control_listing_never_changes(conn):
    assert history(conn, "RP-S006") == [(day(n), 15_000_000) for n in (1, 2, 3, 4)]


def test_only_mock_listings_are_flagged_simulated(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM core.listing_source WHERE (source = 'mock') <> is_simulated")
        assert cur.fetchone()[0] == 0