"""Đặt tên và xếp trang đã lưu: bạn chỉ cần Ctrl+S, đặt tên file là số trang.

Lưu các trang vào data/inbox/raw/ theo ĐÚNG THỨ TỰ trang 1, 2, 3, ... của từng web.
Script nhận ra nguồn từ nội dung trang, đánh số trang theo thời gian lưu, lấy ngày từ
trang 1 (giờ Việt Nam), rồi chuyển sang data/inbox/ với tên đúng quy ước.

    python -m scripts.name_inbox --expect-pages 6

Dừng, không đổi tên gì, nếu: không nhận ra nguồn, thiếu trang, thừa trang, hoặc hai
trang chứa cùng một tin (nghĩa là lưu trùng hoặc sai thứ tự).
"""
import argparse
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collectors import batdongsan_parser, nhatot_parser

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "inbox"
RAW = INBOX / "raw"
VN = timezone(timedelta(hours=7))
PARSERS = {"batdongsan": batdongsan_parser.parse_list_page, "nhatot": nhatot_parser.parse_list_page}
MARKERS = {"batdongsan": "batdongsan.com.vn", "nhatot": "nhatot.com"}

log = logging.getLogger("name_inbox")


def detect_source(html):
    """'batdongsan' | 'nhatot' | None, theo link canonical (hoặc og:url) của trang."""
    head = html[:200_000]
    for key in ('rel="canonical" href="', 'property="og:url" content="'):
        start = head.find(key)
        if start != -1:
            url = head[start + len(key): start + len(key) + 120]
            for source, marker in MARKERS.items():
                if marker in url:
                    return source
    return None


def plan(files, expect_pages):
    """files: [(path, mtime)]. Trả (kế hoạch [(path, tên mới)], danh sách lỗi)."""
    groups, errors = {}, []
    for path, mtime in sorted(files, key=lambda f: f[1]):
        html = path.read_text(encoding="utf-8", errors="replace")
        source = detect_source(html)
        if source is None:
            errors.append(f"{path.name}: không nhận ra nguồn (không phải trang Nhà Tốt/Batdongsan?)")
            continue
        ids = {r["listing_id"] for r in PARSERS[source](html) if r.get("listing_id")}
        groups.setdefault(source, []).append((path, mtime, ids))

    renames = []
    for source, pages in groups.items():
        if len(pages) != expect_pages:
            errors.append(f"{source}: có {len(pages)} trang, cần đúng {expect_pages}")
            continue
        day = datetime.fromtimestamp(pages[0][1], tz=VN).date().isoformat()
        seen = {}
        for number, (path, _, ids) in enumerate(pages, start=1):
            if not ids:
                errors.append(f"{source} trang {number} ({path.name}): không đọc được tin nào")
            for other, other_ids in seen.items():
                if len(ids & other_ids) >= 5:
                    errors.append(f"{source} trang {number} ({path.name}) trùng tin với trang {other}: "
                                  "lưu trùng hoặc sai thứ tự")
                    break
            seen[number] = ids
            suffix = "" if number == 1 else f"_p{number}"
            renames.append((path, f"{source}_{day}{suffix}.html"))
    return renames, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Đặt tên trang đã lưu trong data/inbox/raw")
    parser.add_argument("--expect-pages", type=int, default=6)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    RAW.mkdir(parents=True, exist_ok=True)
    files = [(p, p.stat().st_mtime) for p in RAW.glob("*.htm*")]
    if not files:
        log.info("Không có trang nào trong %s", RAW)
        return 0
    renames, errors = plan(files, args.expect_pages)
    if errors:
        for line in errors:
            log.error(line)
        log.error("Chưa đổi tên file nào. Sửa rồi chạy lại.")
        return 1
    for path, new_name in renames:
        if (INBOX / new_name).exists():
            log.error("%s đã có trong inbox, dừng.", new_name)
            return 1
    for path, new_name in renames:
        shutil.move(str(path), str(INBOX / new_name))
    log.info("Đã chuyển %d trang vào %s", len(renames), INBOX)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())