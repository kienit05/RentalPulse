"""Đọc các batch trong Bronze (RustFS) và gửi mỗi tin thành một event lên Kafka.

Mỗi event: key = "source:listing_id", value = JSON listing_observed.
Chạy từ máy Windows nên dùng cổng ngoài localhost:29092.
"""
import argparse
import json
import logging
import os

from confluent_kafka import Producer
from dotenv import load_dotenv

from etl.load_raw import list_batch_keys, read_batch
from storage.rustfs import get_bucket, get_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("publish_batch")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC_LISTINGS", "listing.events")


def build_event(key, batch, record_no, record):
    """Dựng event listing_observed. Trả về (message_key, event) hoặc None nếu thiếu listing_id."""
    listing_id = record.get("listing_id")
    if listing_id in (None, ""):
        return None
    source = batch["source"]
    event = {
        "event_id": f"{batch['batch_id']}:{record_no}",
        "event_type": "listing_observed",
        "source": source,
        "listing_id": str(listing_id),
        "snapshot_date": batch["snapshot_date"],
        "batch_id": batch["batch_id"],
        "bronze_key": key,
        "payload": record,
    }
    return f"{source}:{listing_id}", event


def make_producer():
    return Producer(
        {
            "bootstrap.servers": BOOTSTRAP,
            # acks=all + idempotence: broker xác nhận đủ và không ghi trùng khi producer retry
            "acks": "all",
            "enable.idempotence": True,
        }
    )


def publish_batch(producer, key, batch, stats):
    def on_delivery(err, msg):
        if err is not None:
            stats["failed"] += 1
            log.error("Gửi lỗi: %s", err)
        else:
            stats["delivered"] += 1

    for record_no, record in enumerate(batch["records"], start=1):
        built = build_event(key, batch, record_no, record)
        if built is None:
            stats["skipped"] += 1
            log.warning("%s: dòng %d thiếu listing_id, bỏ qua", key, record_no)
            continue
        message_key, event = built
        producer.produce(
            TOPIC,
            key=message_key,
            value=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            on_delivery=on_delivery,
        )
        # poll(0) xử lý callback, tránh đầy hàng đợi nội bộ khi batch lớn
        producer.poll(0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gửi Bronze lên Kafka")
    parser.add_argument("--source", help="Chỉ gửi một nguồn: mock, batdongsan hoặc nhatot")
    args = parser.parse_args(argv)

    client = get_client()
    bucket = get_bucket()
    keys = list_batch_keys(client, bucket, args.source)
    log.info("Tìm thấy %d batch trong Bronze, gửi tới topic %s", len(keys), TOPIC)

    producer = make_producer()
    stats = {"delivered": 0, "failed": 0, "skipped": 0}
    for key in keys:
        batch = read_batch(client, bucket, key)
        publish_batch(producer, key, batch, stats)

    remaining = producer.flush(30)
    if remaining:
        log.error("Còn %d message chưa được xác nhận sau 30 giây", remaining)
        raise SystemExit(1)

    log.info(
        "Xong: gửi %d, lỗi %d, bỏ qua %d",
        stats["delivered"], stats["failed"], stats["skipped"],
    )
    if stats["failed"] or stats["skipped"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()