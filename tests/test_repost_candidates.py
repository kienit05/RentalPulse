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
        cur.execute("SELECT to_regclass('core.v_repost_candidates')")
        if cur.fetchone()[0] is None:
            connection.close()
            pytest.skip("Chưa tạo view (chạy sql/008_repost_candidates.sql)")
        cur.execute("SELECT count(*) FROM core.listing_source WHERE listing_id = 'RP-S004'")
        if cur.fetchone()[0] == 0:
            connection.close()
            pytest.skip("Chưa nạp mock ngày 1-4 vào pipeline")
    yield connection
    connection.close()


def pairs(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT old_listing_id, new_listing_id FROM core.v_repost_candidates WHERE source = 'mock'")
        return set(cur.fetchall())


def test_scripted_repost_pair_is_found(conn):
    assert ("RP-S004", "RP-S005") in pairs(conn)


def test_tin_a_that_returned_is_not_treated_as_repost(conn):
    assert all(old != "RP-S001" for old, _ in pairs(conn))


def test_control_listing_is_never_matched(conn):
    assert all("RP-S006" not in pair for pair in pairs(conn))


def test_a_listing_is_never_matched_with_itself(conn):
    assert all(old != new for old, new in pairs(conn))