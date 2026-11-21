"""Quy tắc bất biến: không tầng nào làm rơi tin của tầng trước."""
import psycopg2
import pytest

from etl.load_raw import connect


@pytest.fixture(scope="module")
def conn():
    try:
        connection = connect()
    except psycopg2.OperationalError:
        pytest.skip("Không kết nối được PostgreSQL")
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def rows(conn):
    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT source, snapshot_date, lost_raw_to_staging, lost_staging_to_core "
                "FROM analytics.v_data_quality_daily"
            )
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            pytest.skip("Chưa tạo view (chạy python -m etl.run_pipeline --init)")
        data = cur.fetchall()
    if not data:
        pytest.skip("Chưa có dữ liệu")
    return data


def test_no_listing_lost_between_raw_and_staging(rows):
    lost = [(s, d, n) for s, d, n, _ in rows if n != 0]
    assert lost == [], f"Tin rơi rụng giữa Raw và Staging: {lost}"


def test_no_listing_lost_between_staging_and_core(rows):
    lost = [(s, d, n) for s, d, _, n in rows if n != 0]
    assert lost == [], f"Tin rơi rụng giữa Staging và Core: {lost}"