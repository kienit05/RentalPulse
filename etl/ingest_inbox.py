"""Nạp các trang HTML đã lưu tay trong data/inbox vào Bronze, rồi chạy chuỗi ETL.

Quy ước tên file: <nguồn>_<YYYY-MM-DD>[_p<số trang>].html, ví dụ
    nhatot_2026-11-23.html       (trang 1)
    nhatot_2026-11-23_p2.html    (trang 2)
Nguồn là batdongsan hoặc nhatot; ngày là ngày bạn lưu trang.

    python -m etl.ingest_inbox                                # nạp mọi file rồi chạy ETL
    python -m etl.ingest_inbox --no-pipeline                  # chỉ nạp Bronze (Airflow dùng cách này)
    python -m etl.ingest_inbox --no-pipeline --expect-pages 6

Với --expect-pages N: một (nguồn, ngày) phải có đủ trang 1..N mới được nạp.
Thiếu trang thì cả nhóm đó ở lại inbox và lệnh thoát mã 1, tránh sinh tin "biến mất" giả.
File nạp thành công được chuyển sang data/processed để không bị nạp hai lần.
File lỗi ở nguyên trong inbox để bạn sửa rồi chạy lại.
"""
import argparse
import logging
import re
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

from collectors import collector
from etl import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"
PROCESSED = ROOT / "data" / "processed"
NAME = re.compile(r"^(batdongsan|nhatot)_(\d{4}-\d{2}-\d{2})(?:_p([1-9]\d{0,2}))?\.html$")

# URL gốc của từng trang, chỉ để ghi vào batch (biết batch đến từ trang nào)
PAGE_URL = {
    "nhatot": ("https://www.nhatot.com/thue-phong-tro-ha-noi",
               "https://www.nhatot.com/thue-phong-tro-ha-noi?page={page}"),
    "batdongsan": ("https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro-ha-noi?sortValue=8",
                   "https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro-ha-noi/p{page}?sortValue=8"),
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest")


def parse_name(name):
    """'nhatot_2026-11-23_p2.html' -> ('nhatot', '2026-11-23', 2); thiếu _pN là trang 1.
    Tên sai quy ước -> None."""
    match = NAME.match(name)
    if match is None:
        return None
    source, day, page = match.groups()
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    return source, day, int(page) if page else 1


def page_url(source, page):
    first, other = PAGE_URL[source]
    return first if page == 1 else other.format(page=page)


def find_pending(inbox):
    """Danh sách (đường dẫn, nguồn, ngày, trang) hợp lệ, theo ngày, nguồn rồi số trang."""
    pending = []
    for path in inbox.glob("*.html"):
        parsed = parse_name(path.name)
        if parsed is None:
            log.warning("Bỏ qua %s: tên không đúng dạng <nguồn>_<YYYY-MM-DD>[_pN].html", path.name)
            continue
        pending.append((path, *parsed))
    return sorted(pending, key=lambda item: (item[2], item[1], item[3]))


def incomplete_groups(pending, expect_pages):
    """{(nguồn, ngày): [trang còn thiếu]} cho những nhóm không có đủ trang 1..expect_pages."""
    pages = defaultdict(set)
    for _, source, day, page in pending:
        pages[(source, day)].add(page)
    wanted = set(range(1, expect_pages + 1))
    return {group: sorted(wanted - got) for group, got in pages.items() if not wanted <= got}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nạp trang đã lưu trong data/inbox")
    parser.add_argument("--no-pipeline", action="store_true", help="Chỉ nạp Bronze, không chạy ETL")
    parser.add_argument("--expect-pages", type=int, metavar="N",
                        help="Chỉ nạp (nguồn, ngày) có đủ trang 1..N")
    args = parser.parse_args(argv)

    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pending = find_pending(INBOX)
    if not pending:
        log.info("Không có file hợp lệ trong %s", INBOX)
        return

    incomplete = incomplete_groups(pending, args.expect_pages) if args.expect_pages else {}
    for (source, day), missing in incomplete.items():
        log.error("Thiếu trang %s của %s ngày %s: chưa nạp nhóm này, giữ nguyên trong inbox",
                  missing, source, day)

    ingested = failed = 0
    for path, source, day, page in pending:
        if (source, day) in incomplete:
            continue
        log.info("Nạp %s (nguồn %s, ngày %s, trang %d)", path.name, source, day, page)
        try:
            collector.main(["--source", source, "--html-file", str(path),
                            "--url", page_url(source, page), "--snapshot-date", day])
        except SystemExit as exc:
            if exc.code:
                failed += 1
                log.error("Lỗi khi nạp %s, giữ nguyên trong inbox", path.name)
                continue
        shutil.move(str(path), str(PROCESSED / path.name))
        ingested += 1

    log.info("Đã nạp %d file, %d file lỗi, %d nhóm thiếu trang", ingested, failed, len(incomplete))
    if ingested and not args.no_pipeline:
        run_pipeline.main([])
    if failed or incomplete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()