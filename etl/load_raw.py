"""Nạp các batch trong Bronze (RustFS) vào PostgreSQL, bảng raw.listings."""
import argparse
import json
import logging
import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

from storage.rustfs import get_bucket, get_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("load_raw")

INSERT_SQL = """
    INSERT INTO raw.listings (batch_id, source, snapshot_date, bronze_key, record_no, payload)
    VALUES %s
    ON CONFLICT (batch_id, record_no) DO NOTHING
"""


def connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def list_batch_keys(client, bucket, source=None):
    """Mọi file listings.json trong Bronze, theo thứ tự tên. source lọc theo nguồn."""
    prefix = f"source={source}/" if source else ""
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("/listings.json"):
                keys.append(obj["Key"])
    return sorted(keys)


def read_batch(client, bucket, key):
    body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    return json.loads(body)


def load_batch(conn, key, batch):
    """Chèn các tin của một batch. Trả về số dòng thật sự được thêm (bỏ qua dòng đã có)."""
    rows = [
        (
            batch["batch_id"],
            batch["source"],
            batch["snapshot_date"],
            key,
            record_no,
            Json(record, dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
        )
        for record_no, record in enumerate(batch["records"], start=1)
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        # page_size = số dòng để cả batch đi trong một câu lệnh, rowcount mới đếm đúng
        execute_values(cur, INSERT_SQL, rows, page_size=len(rows))
        return cur.rowcount


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nạp Bronze vào raw.listings")
    parser.add_argument("--source", help="Chỉ nạp một nguồn: mock, batdongsan hoặc nhatot")
    args = parser.parse_args(argv)

    client = get_client()
    bucket = get_bucket()
    keys = list_batch_keys(client, bucket, args.source)
    log.info("Tìm thấy %d batch trong Bronze", len(keys))

    conn = connect()
    total_new = 0
    failed = 0
    try:
        for key in keys:
            try:
                batch = read_batch(client, bucket, key)
                inserted = load_batch(conn, key, batch)
                conn.commit()
            except Exception:
                conn.rollback()
                failed += 1
                log.exception("Lỗi khi nạp %s", key)
                continue
            skipped = len(batch["records"]) - inserted
            total_new += inserted
            log.info("%s: thêm %d, bỏ qua %d (đã có)", key, inserted, skipped)
    finally:
        conn.close()

    log.info("Xong: thêm %d dòng mới, %d batch lỗi", total_new, failed)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()