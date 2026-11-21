"""Test hàm SQL staging.parse_area_m2 (cần PostgreSQL, tự bỏ qua nếu không có)."""
from decimal import Decimal

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


def parse(conn, text):
    with conn.cursor() as cur:
        cur.execute("SELECT staging.parse_area_m2(%s)", (text,))
        return cur.fetchone()[0]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("30", "30"),          # số trần (dạng mock)
        ("18m2", "18"),
        ("84 m²", "84"),
        ("12,5 m²", "12.5"),
        ("30,5", "30.5"),      # số trần có dấu phẩy
        ("  45  ", "45"),
        ("1000", "1000"),      # biên trên còn hợp lệ
        ("1", "1"),            # biên dưới còn hợp lệ
    ],
)
def test_valid_areas(conn, text, expected):
    assert parse(conn, text) == Decimal(expected)


@pytest.mark.parametrize("text", [None, "", "abc", "Liên hệ", "0", "0m2", "1001", "5000", "30 phòng"])
def test_invalid_or_implausible_areas_are_null(conn, text):
    assert parse(conn, text) is None