"""Chạy chuỗi ETL: Bronze -> raw -> staging -> core.

    python -m etl.run_pipeline --init    # lần đầu: tạo schema, bảng, hàm, view rồi nạp dữ liệu
    python -m etl.run_pipeline           # các lần sau: chỉ nạp dữ liệu mới
    python -m etl.run_pipeline --skip-bronze   # bỏ bước đọc Bronze, chạy lại từ raw trở đi
    python -m etl.run_pipeline --rebuild # xóa staging và core, dựng lại hoàn toàn từ raw

Mọi bước đều chạy lại được nhiều lần mà không sinh dữ liệu trùng.
"""
import argparse
import logging
import time
from pathlib import Path

from etl import load_raw

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Tạo cấu trúc, theo thứ tự phụ thuộc: schema -> bảng -> hàm -> view.
DDL_FILES = [
    "001_schemas.sql",
    "002_raw_listings.sql",
    "003_staging_listings.sql",
    "003b_staging_functions.sql",
    "005_core_tables.sql",
    "007_history_views.sql",
    "008_repost_candidates.sql",
    "009_published_events.sql",
]
# Nạp dữ liệu: raw -> staging -> core.
LOAD_FILES = [
    "004_load_staging.sql",
    "006_load_core.sql",
]

# Staging và core là tầng dẫn xuất: luôn dựng lại được từ raw. Raw là nguồn sự thật.
REBUILD_SQL = """
TRUNCATE staging.listings, core.fact_listing_snapshot, core.listing_source RESTART IDENTITY;
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pipeline")


def run_sql_file(conn, name):
    """Chạy một file SQL (đọc UTF-8 nên không mất dấu tiếng Việt) trong một giao dịch."""
    sql = (SQL_DIR / name).read_text(encoding="utf-8")
    started = time.monotonic()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    log.info("%s xong (%.2fs)", name, time.monotonic() - started)


def rebuild_derived_layers(conn):
    """Xóa sạch staging và core (giữ nguyên raw và cấu trúc) để nạp lại từ đầu."""
    try:
        with conn.cursor() as cur:
            cur.execute(REBUILD_SQL)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    log.info("Đã xóa staging và core, sẽ dựng lại từ raw")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chạy chuỗi ETL RentalPulse")
    parser.add_argument("--init", action="store_true", help="Tạo schema, bảng, hàm, view trước khi nạp")
    parser.add_argument("--rebuild", action="store_true", help="Xóa staging và core rồi dựng lại từ raw")
    parser.add_argument("--skip-bronze", action="store_true", help="Không đọc Bronze, chạy từ raw trở đi")
    args = parser.parse_args(argv)

    try:
        conn = load_raw.connect()
    except Exception:
        log.exception("Không kết nối được PostgreSQL")
        raise SystemExit(1)

    try:
        if args.init:
            for name in DDL_FILES:
                run_sql_file(conn, name)
        if not args.skip_bronze:
            try:
                load_raw.main([])
            except SystemExit as exc:
                if exc.code:
                    log.error("Nạp Bronze vào raw thất bại, dừng chuỗi")
                    raise
        if args.rebuild:
            rebuild_derived_layers(conn)
        for name in LOAD_FILES:
            run_sql_file(conn, name)
    except SystemExit:
        raise
    except Exception:
        log.exception("Chuỗi ETL thất bại")
        raise SystemExit(1)
    finally:
        conn.close()
    log.info("Chuỗi ETL hoàn tất")


if __name__ == "__main__":
    main()