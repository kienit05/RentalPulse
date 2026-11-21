"""In ra số ngày mock tiếp theo cần thu thập, dựa trên dữ liệu mock đã nạp trong raw.listings.

Ví dụ: mock đã có tới ngày 4 (2026-11-04) thì in ra 5. Chưa có gì thì in ra 1.
Chỉ in đúng một số ra stdout để shell dùng được: DAY=$(python -m etl.next_mock_day)
"""
from datetime import date, datetime

from collectors.mock_source import START_DATE
from etl.load_raw import connect


def as_date(value):
    return value.date() if isinstance(value, datetime) else value


def next_mock_day(max_snapshot_date, start_date):
    """Ngày mô phỏng kế tiếp. start_date là ngày của mock ngày 1."""
    if max_snapshot_date is None:
        return 1
    return (as_date(max_snapshot_date) - as_date(start_date)).days + 2


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT max(snapshot_date) FROM raw.listings WHERE source = 'mock'")
            max_date = cur.fetchone()[0]
    finally:
        conn.close()
    print(next_mock_day(max_date, START_DATE))


if __name__ == "__main__":
    main()