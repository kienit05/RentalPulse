"""Collector: lấy snapshot từ một nguồn (mock hoặc Batdongsan) rồi lưu vào Bronze (RustFS)."""
import argparse
import logging
import uuid
from datetime import datetime, timedelta, timezone

from collectors.batdongsan_parser import parse_list_page
from collectors.fetcher import PoliteFetcher
from collectors.mock_source import day_to_date, snapshot
from storage.rustfs import ensure_bucket, get_bucket, get_client, put_json

SOURCE = "mock"
BATDONGSAN = "batdongsan"
BATDONGSAN_LIST_URL = "https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro"
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


def collect_batdongsan(url, fetcher):
    """Nguồn thật: tải một trang danh sách, tách tin, gắn nguồn và ngày chụp."""
    html = fetcher.fetch(url)
    snapshot_date = datetime.now(VN_TZ).date().isoformat()
    records = parse_list_page(html)
    for record in records:
        record["source"] = BATDONGSAN
        record["snapshot_date"] = snapshot_date
    return _make_batch(BATDONGSAN, snapshot_date, records, url=url)


def main():
    parser = argparse.ArgumentParser(description="Thu thập tin đăng vào Bronze")
    parser.add_argument("--source", choices=[SOURCE, BATDONGSAN], default=SOURCE)
    parser.add_argument("--day", type=int, default=1, help="Chỉ cho mock: ngày mô phỏng 1, 2, 3, ...")
    parser.add_argument("--seed", type=int, default=42, help="Chỉ cho mock: hạt giống")
    parser.add_argument("--url", default=BATDONGSAN_LIST_URL, help="Chỉ cho batdongsan: trang danh sách")
    args = parser.parse_args()

    try:
        if args.source == BATDONGSAN:
            batch = collect_batdongsan(args.url, PoliteFetcher())
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