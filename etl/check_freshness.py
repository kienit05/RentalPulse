"""Kiểm tra độ mới: mỗi nguồn thật phải có dữ liệu của ngày hôm nay (giờ Việt Nam).

Thoát mã 1 nếu thiếu, để task Airflow đỏ và người vận hành biết ngay.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
from dotenv import load_dotenv

REAL_SOURCES = ("nhatot", "batdongsan")


def connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def main() -> int:
    load_dotenv()
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT source, MAX(snapshot_date) FROM raw.listings "
            "WHERE source = ANY(%s) GROUP BY source",
            (list(REAL_SOURCES),),
        )
        latest = dict(cur.fetchall())

    for s in REAL_SOURCES:
        print(f"{s}: dữ liệu mới nhất = {latest.get(s)} (hôm nay = {today})")
    stale = [s for s in REAL_SOURCES if latest.get(s) != today]
    if stale:
        print(f"THIẾU dữ liệu hôm nay cho: {', '.join(stale)}")
        return 1
    print("Dữ liệu đủ và mới.")
    return 0


if __name__ == "__main__":
    sys.exit(main())