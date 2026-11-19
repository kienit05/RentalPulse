import pytest
from botocore.exceptions import EndpointConnectionError

from collectors.collector import bronze_key, collect
from storage.rustfs import ensure_bucket, get_bucket, get_client, get_json, put_json

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def s3():
    client = get_client()
    try:
        client.list_buckets()
    except EndpointConnectionError:
        pytest.skip("RustFS không chạy, bỏ qua test tích hợp")
    return client


def test_batch_survives_a_write_read_roundtrip(s3):
    bucket = get_bucket()
    ensure_bucket(s3, bucket)
    batch = collect(day=3, seed=42)
    # nguồn "pytest" dành riêng cho test, xóa ngay sau khi kiểm tra xong
    key = bronze_key("pytest", batch["snapshot_date"], batch["batch_id"])
    try:
        put_json(s3, bucket, key, batch)
        assert get_json(s3, bucket, key) == batch
    finally:
        s3.delete_object(Bucket=bucket, Key=key)