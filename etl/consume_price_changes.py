"""Đọc event price_changed từ Kafka và ghi vào analytics.price_change_events.

At-least-once: chỉ commit offset sau khi DB đã commit. Trùng lặp được chặn bởi
PRIMARY KEY (event_id) + ON CONFLICT DO NOTHING. Event hỏng đi sang DLQ.
"""
import argparse
import json
import logging
import os
import time

from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from etl.load_raw import connect

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("consume_price_changes")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC_PRICE_CHANGES", "listing.price_changes")
DLQ_TOPIC = os.getenv("KAFKA_TOPIC_DLQ", "listing.events.dlq")
GROUP_ID = os.getenv("KAFKA_GROUP_PRICE_LOADER", "price-change-loader")

REQUIRED = (
    "event_id", "source", "listing_id", "snapshot_date", "prev_snapshot_date",
    "old_price_vnd", "new_price_vnd", "change_vnd", "change_type",
)

INSERT_SQL = """
    INSERT INTO analytics.price_change_events
        (event_id, source, listing_id, is_simulated, snapshot_date, prev_snapshot_date,
         old_price_vnd, new_price_vnd, change_vnd, change_pct, change_type)
    VALUES %s
    ON CONFLICT (event_id) DO NOTHING
"""


def parse_price_event(raw_value):
    """Trả về (row, None) nếu hợp lệ, hoặc (None, lý_do) nếu phải đưa vào DLQ."""
    try:
        event = json.loads(raw_value)
    except (ValueError, TypeError):
        return None, "không phải JSON hợp lệ"
    if not isinstance(event, dict):
        return None, "event không phải object"
    if event.get("event_type") != "price_changed":
        return None, f"event_type không hỗ trợ: {event.get('event_type')!r}"
    missing = [f for f in REQUIRED if event.get(f) in (None, "")]
    if missing:
        return None, f"thiếu trường: {', '.join(missing)}"
    if event["change_type"] not in ("increase", "decrease"):
        return None, f"change_type không hợp lệ: {event['change_type']!r}"
    row = (
        event["event_id"],
        event["source"],
        event["listing_id"],
        bool(event.get("is_simulated", False)),
        event["snapshot_date"],
        event["prev_snapshot_date"],
        event["old_price_vnd"],
        event["new_price_vnd"],
        event["change_vnd"],
        event.get("change_pct"),
        event["change_type"],
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
        row, reason = parse_price_event(msg.value())
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
    parser = argparse.ArgumentParser(description="Kafka listing.price_changes -> analytics.price_change_events")
    parser.add_argument("--once", action="store_true", help="Đọc hết rồi thoát")
    parser.add_argument("--idle-seconds", type=float, default=5.0,
                        help="Với --once: chờ bao lâu không có tin thì thoát")
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