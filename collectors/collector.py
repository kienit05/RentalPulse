"""Collector: lấy dữ liệu từ nguồn (mock) rồi lưu bản gốc vào RustFS (tầng Bronze)."""
import json
import logging
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from mock_source import generate_batch

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

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
    return boto3.client(
        "s3",
        endpoint_url="http://" + os.getenv("RUSTFS_ENDPOINT"),
        aws_access_key_id=os.getenv("RUSTFS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("RUSTFS_SECRET_KEY"),
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=15,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
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
    bucket = os.getenv("RUSTFS_BUCKET")
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket)
        else:
            raise

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
        Bucket=bucket,
        Key=object_name,
        Body=data,
        ContentType="application/json",
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
        log.info("Đã lưu %d tin vào %s/%s", len(records), os.getenv("RUSTFS_BUCKET"), path)
    except Exception:
        log.exception("Collector thất bại")
        raise SystemExit(1)  # mã thoát 1 = có lỗi


if __name__ == "__main__":
    main()