"""Collector: lấy dữ liệu từ nguồn (mock) rồi lưu bản gốc vào RustFS (tầng Bronze)."""
import io
import json
import logging
import os
import time
from datetime import datetime
import urllib3

from dotenv import load_dotenv
from minio import Minio

from mock_source import generate_batch

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("collector")

MAX_RETRIES = 3     # thử tối đa 3 lần
WAIT_SECONDS = 2    # lần 1 thất bại đợi 2s, lần 2 đợi 4s


def get_client():
    """Tạo kết nối tới kho lưu file (RustFS) bằng thông tin trong .env."""
    http = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=3, read=15),  # chờ nối tối đa 3 giây
        retries=urllib3.Retry(total=1),               # thư viện chỉ thử lại 1 lần
    )
    return Minio(
        os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ROOT_USER"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
        secure=False,
        http_client=http,
    )


def with_retry(func, *args, **kwargs):
    """Chạy func; nếu lỗi thì đợi rồi thử lại, hết số lần thì báo lỗi lên trên."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.warning("Lần thử %d/%d thất bại: %s", attempt, MAX_RETRIES, e)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(WAIT_SECONDS * attempt)


def save_to_bronze(client, records, source="mock"):
    """Lưu một đợt tin đăng thành 1 file JSON, trả về đường dẫn file."""
    bucket = os.getenv("MINIO_BUCKET")
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    now = datetime.now()
    payload = {
        "source": source,
        "collected_at": now.isoformat(),
        "record_count": len(records),
        "records": records,  # dữ liệu gốc, KHÔNG sửa gì
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    object_name = f"{source}/dt={now:%Y-%m-%d}/listings_{now:%H%M%S}.json"
    client.put_object(
        bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type="application/json",
    )
    return object_name


def main():
    try:
        records = generate_batch(50)
        if not records:
            raise ValueError("Nguồn không trả về tin đăng nào")
        log.info("Lấy được %d tin từ nguồn", len(records))

        client = get_client()
        path = with_retry(save_to_bronze, client, records)
        log.info("Đã lưu %d tin vào %s/%s", len(records), os.getenv("MINIO_BUCKET"), path)
    except Exception:
        log.exception("Collector thất bại")
        raise SystemExit(1)  # mã thoát 1 = có lỗi


if __name__ == "__main__":
    main()