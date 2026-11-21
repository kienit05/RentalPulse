"""Chất lượng bộ ghép tin đăng lại trên mock có đáp án: precision và recall không được tụt."""
import psycopg2
import pytest

from etl.load_raw import connect

MIN_PCT = 90.0


@pytest.fixture(scope="module")
def evaluation():
    try:
        conn = connect()
    except psycopg2.OperationalError:
        pytest.skip("Không kết nối được PostgreSQL")
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT proposed, expected, correct, precision_pct, recall_pct "
                    "FROM analytics.v_repost_eval"
                )
            except psycopg2.errors.UndefinedTable:
                pytest.skip("Chưa tạo view (chạy python -m etl.run_pipeline --init)")
            row = cur.fetchone()
    finally:
        conn.close()
    proposed, expected, correct, precision, recall = row
    if expected == 0:
        pytest.skip("Chưa có tin đăng lại nào trong mock")
    return {"proposed": proposed, "expected": expected, "correct": correct,
            "precision": precision, "recall": recall}


def test_recall_does_not_drop(evaluation):
    assert evaluation["recall"] is not None and evaluation["recall"] >= MIN_PCT, evaluation


def test_precision_does_not_drop(evaluation):
    assert evaluation["precision"] is not None and evaluation["precision"] >= MIN_PCT, evaluation