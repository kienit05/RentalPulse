"""Nạp các trang HTML đã lưu tay trong data/inbox vào Bronze, rồi chạy chuỗi ETL.

Quy ước tên file: <nguồn>_<YYYY-MM-DD>.html, ví dụ nhatot_2026-11-21.html
(nguồn là batdongsan hoặc nhatot; ngày là ngày bạn lưu trang).

    python -m etl.ingest_inbox                # nạp mọi file trong inbox rồi chạy ETL
    python -m etl.ingest_inbox --no-pipeline  # chỉ nạp Bronze, chưa chạy ETL

File nạp thành công được chuyển sang data/processed để không bị nạp hai lần.
File lỗi ở nguyên trong inbox để bạn sửa rồi chạy lại.
"""
import argparse
import logging
import re
import shutil
from datetime import date
from pathlib import Path

from collectors import collector
from etl import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"
PROCESSED = ROOT / "data" / "processed"
NAME = re.compile(r"^(batdongsan|nhatot)_(\d{4}-\d{2}-\d{2})\.html$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest")


def parse_name(name):
    """'nhatot_2026-11-21.html' -> ('nhatot', '2026-11-21'); tên sai quy ước -> None."""
    match = NAME.match(name)
    if match is None:
        return None
    source, day = match.groups()
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    return source, day


def find_pending(inbox):
    """Danh sách (đường dẫn, nguồn, ngày) hợp lệ trong inbox, theo ngày rồi theo nguồn."""
    pending = []
    for path in inbox.glob("*.html"):
        parsed = parse_name(path.name)
        if parsed is None:
            log.warning("Bỏ qua %s: tên không đúng dạng <nguồn>_<YYYY-MM-DD>.html", path.name)
            continue
        pending.append((path, *parsed))
    return sorted(pending, key=lambda item: (item[2], item[1]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nạp trang đã lưu trong data/inbox")
    parser.add_argument("--no-pipeline", action="store_true", help="Chỉ nạp Bronze, không chạy ETL")
    args = parser.parse_args(argv)

    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pending = find_pending(INBOX)
    if not pending:
        log.info("Không có file hợp lệ trong %s", INBOX)
        return

    ingested = failed = 0
    for path, source, day in pending:
        log.info("Nạp %s (nguồn %s, ngày %s)", path.name, source, day)
        try:
            collector.main(["--source", source, "--html-file", str(path), "--snapshot-date", day])
        except SystemExit as exc:
            if exc.code:
                failed += 1
                log.error("Lỗi khi nạp %s, giữ nguyên trong inbox", path.name)
                continue
        shutil.move(str(path), str(PROCESSED / path.name))
        ingested += 1

    log.info("Đã nạp %d file, %d file lỗi", ingested, failed)
    if ingested and not args.no_pipeline:
        run_pipeline.main([])
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()