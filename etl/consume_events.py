"""Đọc event listing_observed từ Kafka và ghi vào raw.listings.

At-least-once: chỉ commit offset sau khi DB đã commit. Trùng lặp được chặn bởi
UNIQUE (batch_id, record_no) + ON CONFLICT DO NOTHING. Event hỏng đi sang DLQ.
"""
import argparse
import json
import logging
import os
import time

from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

from etl.load_raw import INSERT_SQL, connect

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("consume_events")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC_LISTINGS", "listing.events")
DLQ_TOPIC = os.getenv("KAFKA_TOPIC_DLQ", "listing.events.dlq")
GROUP_ID = os.getenv("KAFKA_GROUP_RAW_LOADER", "raw-loader")

REQUIRED = ("event_id", "source", "listing_id", "snapshot_date", "batch_id", "bronze_key", "payload")


def parse_event(raw_value):
    """Trả về (row, None) nếu hợp lệ, hoặc (None, lý_do) nếu phải đưa vào DLQ."""
    try:
        event = json.loads(raw_value)
    except (ValueError, TypeError):
        return None, "không phải JSON hợp lệ"
    if not isinstance(event, dict):
        return None, "event không phải object"
    if event.get("event_type") != "listing_observed":
        return None, f"event_type không hỗ trợ: {event.get('event_type')!r}"
    missing = [f for f in REQUIRED if event.get(f) in (None, "")]
    if missing:
        return None, f"thiếu trường: {', '.join(missing)}"
    try:
        batch_id, record_no_text = event["event_id"].rsplit(":", 1)
        record_no = int(record_no_text)
    except ValueError:
        return None, f"event_id sai định dạng: {event['event_id']!r}"
    row = (
        batch_id,
        event["source"],
        event["snapshot_date"],
        event["bronze_key"],
        record_no,
        Json(event["payload"], dumps=lambda obj: json.dumps(obj, ensure_ascii=False)),
    )
    return row, None


def send_to_dlq(dlq_producer, msg, reason):
    dlq_producer.produce(
        DLQ_TOPIC,
        key=msg.key(),
        value=msg.value(),
        headers=[("error", reason.encode("utf-8"))],
    )


def insert_rows(conn, rows):
    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, rows, page_size=len(rows))
        return cur.rowcount


def process_messages(conn, dlq_producer, messages):
    """Xử lý một mẻ message. Trả về (số dòng thêm, số dòng trùng, số event vào DLQ)."""
    rows, bad = [], 0
    for msg in messages:
        if msg.error():
            log.error("Lỗi Kafka: %s", msg.error())
            continue
        row, reason = parse_event(msg.value())
        if row is None:
            bad += 1
            log.warning("Đưa vào DLQ (partition %d, offset %d): %s", msg.partition(), msg.offset(), reason)
            send_to_dlq(dlq_producer, msg, reason)
        else:
            rows.append(row)

    inserted = 0
    if rows:
        try:
            inserted = insert_rows(conn, rows)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    dlq_producer.flush(10)
    return inserted, len(rows) - inserted, bad


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kafka -> raw.listings")
    parser.add_argument("--once", action="store_true", help="Đọc hết rồi thoát")
    parser.add_argument("--idle-seconds", type=float, default=5.0, help="Với --once: chờ bao lâu không có tin thì thoát")
    args = parser.parse_args(argv)

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # tự commit sau khi DB commit
        }
    )
    consumer.subscribe([TOPIC])
    dlq_producer = Producer({"bootstrap.servers": BOOTSTRAP})
    conn = connect()

    total_new = total_dup = total_bad = 0
    last_message_at = time.monotonic()
    try:
        while True:
            messages = consumer.consume(num_messages=200, timeout=1.0)
            if not messages:
                if args.once and time.monotonic() - last_message_at >= args.idle_seconds:
                    break
                continue
            last_message_at = time.monotonic()
            new, dup, bad = process_messages(conn, dlq_producer, messages)
            consumer.commit(asynchronous=False)  # chỉ commit offset sau khi DB đã commit
            total_new += new
            total_dup += dup
            total_bad += bad
            log.info("Mẻ %d message: thêm %d, trùng %d, DLQ %d", len(messages), new, dup, bad)
    except KeyboardInterrupt:
        log.info("Dừng theo yêu cầu")
    finally:
        consumer.close()
        conn.close()

    log.info("Xong: thêm %d, trùng %d, DLQ %d", total_new, total_dup, total_bad)


if __name__ == "__main__":
    main()