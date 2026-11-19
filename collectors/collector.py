"""Collector: lấy snapshot từ nguồn (mock) rồi lưu bản gốc vào Bronze (RustFS)."""
import argparse
import logging
import uuid
from datetime import datetime, timezone

from collectors.mock_source import day_to_date, snapshot
from storage.rustfs import ensure_bucket, get_bucket, get_client, put_json

SOURCE = "mock"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("collector")


def new_batch_id():
    """Mã duy nhất cho mỗi lần chạy: thời gian UTC cộng 6 ký tự ngẫu nhiên."""
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"


def bronze_key(source, snapshot_date, batch_id):
    """Đường dẫn của file trong Bronze."""
    return f"source={source}/dt={snapshot_date}/batch_id={batch_id}/listings.json"


def collect(day, seed):
    """Lấy một snapshot từ nguồn và gói thành một batch (chưa lưu đi đâu)."""
    records = snapshot(day, seed=seed)
    if not records:
        raise ValueError("Nguồn không trả về tin đăng nào")
    return {
        "batch_id": new_batch_id(),
        "source": SOURCE,
        "day": day,
        "snapshot_date": day_to_date(day).isoformat(),
        "seed": seed,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description="Thu thập tin đăng (mock) vào Bronze")
    parser.add_argument("--day", type=int, default=1, help="Ngày mô phỏng: 1, 2, 3, ...")
    parser.add_argument("--seed", type=int, default=42, help="Hạt giống của mô phỏng")
    args = parser.parse_args()

    try:
        batch = collect(args.day, args.seed)
        log.info("Batch %s: ngày %d, %d tin", batch["batch_id"], args.day, batch["record_count"])

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