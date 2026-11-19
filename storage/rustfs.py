"""Storage client: nói chuyện với RustFS (kho đối tượng chuẩn S3) bằng boto3."""
import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()  # nạp biến trong .env khi module được import


def get_client():
    """Tạo client nối tới RustFS bằng thông tin trong .env."""
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


def ensure_bucket(client, bucket):
    """Tạo bucket nếu chưa có. Các lỗi khác (sai mật khẩu...) được ném lên tiếp."""
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket)
        else:
            raise


def put_json(client, bucket, key, payload):
    """Ghi một đối tượng Python thành file JSON. Trả về số byte đã ghi."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return len(body)


def get_json(client, bucket, key):
    """Tải một file JSON về và đổi lại thành đối tượng Python."""
    obj = client.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def list_keys(client, bucket, prefix=""):
    """Liệt kê mọi tên file có tiền tố `prefix` (tự phân trang khi quá 1000 file)."""
    paginator = client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return keys

def get_bucket():
    """Tên bucket Bronze lấy từ .env."""
    return os.getenv("RUSTFS_BUCKET")