"""Collector: lấy snapshot từ một nguồn (mock hoặc Batdongsan) rồi lưu vào Bronze (RustFS)."""
import argparse
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from collectors import batdongsan_parser, nhatot_parser
from collectors.fetcher import PoliteFetcher
from collectors.mock_source import day_to_date, snapshot
from storage.rustfs import ensure_bucket, get_bucket, get_client, put_json

SOURCE = "mock"
BATDONGSAN = "batdongsan"
NHATOT = "nhatot"
BATDONGSAN_LIST_URL = "https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro"
NHATOT_LIST_URL = "https://www.nhatot.com/thue-phong-tro-ha-noi"
VN_TZ = timezone(timedelta(hours=7))  # ngày dữ liệu tính theo giờ Việt Nam

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("collector")


def new_batch_id():
    """Mã duy nhất cho mỗi lần chạy: thời gian UTC cộng 6 ký tự ngẫu nhiên."""
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


def bronze_key(source, snapshot_date, batch_id):
    """Đường dẫn của file trong Bronze."""
    return f"source={source}/dt={snapshot_date}/batch_id={batch_id}/listings.json"


def _make_batch(source, snapshot_date, records, **meta):
    """Đóng gói các bản ghi thành một batch. meta là thông tin riêng của từng nguồn."""
    if not records:
        raise ValueError(f"Nguồn {source} không trả về tin đăng nào")
    return {
        "batch_id": new_batch_id(),
        "source": source,
        "snapshot_date": snapshot_date,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        **meta,
        "records": records,
    }


def collect(day, seed):
    """Nguồn mock: lấy snapshot của một ngày mô phỏng."""
    return _make_batch(
        SOURCE, day_to_date(day).isoformat(), snapshot(day, seed=seed), day=day, seed=seed
    )


def _html_batch(source, parse_page, html, url, method, snapshot_date=None):
    """Tách tin từ HTML của một nguồn, gắn nguồn và ngày chụp, đóng gói.
    method ghi lại cách lấy HTML (http hay manual_save)."""
    snapshot_date = snapshot_date or datetime.now(VN_TZ).date().isoformat()
    records = parse_page(html)
    for record in records:
        record["source"] = source
        record["snapshot_date"] = snapshot_date
    return _make_batch(source, snapshot_date, records, url=url, method=method)


def collect_batdongsan(url, fetcher):
    """Batdongsan, tải trực tiếp (thường bị site chặn)."""
    return _html_batch(BATDONGSAN, batdongsan_parser.parse_list_page, fetcher.fetch(url), url, "http")


def collect_batdongsan_html(html, url, snapshot_date=None):
    """Batdongsan, từ trang do người dùng tự mở và lưu lại bằng trình duyệt."""
    return _html_batch(BATDONGSAN, batdongsan_parser.parse_list_page, html, url, "manual_save", snapshot_date)


def collect_nhatot_html(html, url, snapshot_date=None):
    """Nhà Tốt, từ trang do người dùng tự mở và lưu lại bằng trình duyệt."""
    return _html_batch(NHATOT, nhatot_parser.parse_list_page, html, url, "manual_save", snapshot_date)


def build_parser():
    parser = argparse.ArgumentParser(description="Thu thập tin đăng vào Bronze")
    parser.add_argument("--source", choices=[SOURCE, BATDONGSAN, NHATOT], default=SOURCE)
    parser.add_argument("--day", type=int, default=1, help="Chỉ cho mock: ngày mô phỏng 1, 2, 3, ...")
    parser.add_argument("--seed", type=int, default=42, help="Chỉ cho mock: hạt giống")
    parser.add_argument("--url", help="Trang danh sách của nguồn thật (mặc định theo nguồn)")
    parser.add_argument("--html-file", help="Nguồn thật: đọc từ file HTML đã lưu thay vì tải")
    parser.add_argument("--snapshot-date", help="Chỉ cho --html-file: ngày lưu trang (YYYY-MM-DD), mặc định hôm nay")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        if args.source == NHATOT and not args.html_file:
            raise ValueError("Nhà Tốt chỉ hỗ trợ --html-file (không tải tự động)")
        if args.source == SOURCE and args.html_file:
            raise ValueError("--html-file chỉ dùng cho nguồn thật, không dùng cho mock")
        if args.html_file:
            if args.snapshot_date:
                date.fromisoformat(args.snapshot_date)  # sai định dạng thì báo lỗi ngay
            html = Path(args.html_file).read_text(encoding="utf-8")
            if args.source == NHATOT:
                batch = collect_nhatot_html(html, args.url or NHATOT_LIST_URL, args.snapshot_date)
            else:
                batch = collect_batdongsan_html(html, args.url or BATDONGSAN_LIST_URL, args.snapshot_date)
        elif args.source == BATDONGSAN:
            batch = collect_batdongsan(args.url or BATDONGSAN_LIST_URL, PoliteFetcher())
        else:
            batch = collect(args.day, args.seed)
        log.info("Batch %s: nguồn %s, %d tin", batch["batch_id"], batch["source"], batch["record_count"])

        client = get_client()
        bucket = get_bucket()
        ensure_bucket(client, bucket)
        key = bronze_key(batch["source"], batch["snapshot_date"], batch["batch_id"])
        size = put_json(client, bucket, key, batch)
        log.info("Đã lưu %d byte vào %s/%s", size, bucket, key)
    except Exception:
        log.exception("Collector thất bại")
        raise SystemExit(1)


if __name__ == "__main__":
    main()