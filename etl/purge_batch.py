"""Xóa một batch khỏi Bronze (RustFS) và raw.listings, ví dụ batch nạp nhầm hoặc nạp thử.

    python -m etl.purge_batch 20261120T172318Z-28a9d0          # xem trước, chưa xóa gì
    python -m etl.purge_batch 20261120T172318Z-28a9d0 --yes    # xóa thật

Sau khi xóa, chạy: python -m etl.run_pipeline --rebuild
(staging và core chỉ thêm/cập nhật nên cần dựng lại để bỏ dữ liệu của batch đã xóa).
"""
import argparse
import logging
import re

from etl import load_raw
from storage.rustfs import get_bucket, get_client

BATCH_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{6}$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("purge")


def find_bronze_keys(client, bucket, batch_id):
    """Các object Bronze thuộc đúng batch_id này (khớp cả đoạn 'batch_id=<id>/')."""
    marker = f"/batch_id={batch_id}/"
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            if marker in "/" + obj["Key"]:
                keys.append(obj["Key"])
    return keys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Xóa một batch khỏi Bronze và raw")
    parser.add_argument("batch_id", help="Mã batch, ví dụ 20261120T172318Z-28a9d0")
    parser.add_argument("--yes", action="store_true", help="Xóa thật (mặc định chỉ xem trước)")
    args = parser.parse_args(argv)

    if not BATCH_ID.match(args.batch_id):
        log.error("Mã batch không đúng dạng YYYYMMDDTHHMMSSZ-xxxxxx: %s", args.batch_id)
        raise SystemExit(1)

    client, bucket = get_client(), get_bucket()
    keys = find_bronze_keys(client, bucket, args.batch_id)
    conn = load_raw.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM raw.listings WHERE batch_id = %s", (args.batch_id,))
            raw_rows = cur.fetchone()[0]
        log.info("Batch %s: %d object trong Bronze, %d dòng trong raw", args.batch_id, len(keys), raw_rows)
        for key in keys:
            log.info("  Bronze: %s", key)
        if not keys and not raw_rows:
            log.error("Không tìm thấy batch này")
            raise SystemExit(1)
        if not args.yes:
            log.info("Chỉ xem trước. Thêm --yes để xóa thật.")
            return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM raw.listings WHERE batch_id = %s", (args.batch_id,))
            for key in keys:
                client.delete_object(Bucket=bucket, Key=key)
            conn.commit()
        except Exception:
            conn.rollback()
            log.exception("Xóa thất bại, raw được hoàn tác")
            raise SystemExit(1)
        log.info("Đã xóa. Chạy tiếp: python -m etl.run_pipeline --rebuild")
    finally:
        conn.close()


if __name__ == "__main__":
    main()