"""Phát event price_changed lên Kafka, lấy từ view core.v_price_history.

Chỉ lấy các dòng giá tăng hoặc giảm thật sự. event_id ổn định theo
(source, listing_id, snapshot_date) nên gửi lại không tạo ra sự kiện mới về mặt ý nghĩa.
"""
import argparse
import json
import logging
import os
from decimal import Decimal

from confluent_kafka import Producer
from dotenv import load_dotenv

from etl.load_raw import connect

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("publish_price_changes")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC_PRICE_CHANGES", "listing.price_changes")

QUERY = """
    SELECT source, listing_id, is_simulated, snapshot_date,
           prev_snapshot_date, prev_price_vnd, price_vnd,
           change_vnd, change_pct, change_type
    FROM core.v_price_history
    WHERE change_type IN ('increase', 'decrease')
      AND (%(since)s::date IS NULL OR snapshot_date >= %(since)s::date)
    ORDER BY snapshot_date, source, listing_id
"""


def to_number(value):
    """Decimal từ DB -> int nếu là số nguyên, ngược lại float. JSON không có Decimal."""
    if value is None:
        return None
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    return float(value)


def build_price_event(row):
    """row: dict các cột của v_price_history. Trả về (message_key, event)."""
    source = row["source"]
    listing_id = row["listing_id"]
    snapshot_date = row["snapshot_date"].isoformat()
    event = {
        "event_id": f"price_changed:{source}:{listing_id}:{snapshot_date}",
        "event_type": "price_changed",
        "source": source,
        "listing_id": listing_id,
        "is_simulated": bool(row["is_simulated"]),
        "snapshot_date": snapshot_date,
        "prev_snapshot_date": row["prev_snapshot_date"].isoformat(),
        "old_price_vnd": to_number(row["prev_price_vnd"]),
        "new_price_vnd": to_number(row["price_vnd"]),
        "change_vnd": to_number(row["change_vnd"]),
        "change_pct": to_number(row["change_pct"]),
        "change_type": row["change_type"],
    }
    return f"{source}:{listing_id}", event


def fetch_changes(conn, since=None):
    with conn.cursor() as cur:
        cur.execute(QUERY, {"since": since})
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, values)) for values in cur.fetchall()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Phát event price_changed lên Kafka")
    parser.add_argument("--since", help="Chỉ lấy thay đổi từ ngày này trở đi (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    conn = connect()
    try:
        changes = fetch_changes(conn, args.since)
    finally:
        conn.close()
    log.info("Tìm thấy %d thay đổi giá, gửi tới topic %s", len(changes), TOPIC)

    producer = Producer(
        {"bootstrap.servers": BOOTSTRAP, "acks": "all", "enable.idempotence": True}
    )
    stats = {"delivered": 0, "failed": 0}

    def on_delivery(err, msg):
        if err is not None:
            stats["failed"] += 1
            log.error("Gửi lỗi: %s", err)
        else:
            stats["delivered"] += 1

    for row in changes:
        message_key, event = build_price_event(row)
        producer.produce(
            TOPIC,
            key=message_key,
            value=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            on_delivery=on_delivery,
        )
        producer.poll(0)

    remaining = producer.flush(30)
    if remaining:
        log.error("Còn %d message chưa được xác nhận", remaining)
        raise SystemExit(1)
    log.info("Xong: gửi %d, lỗi %d", stats["delivered"], stats["failed"])
    if stats["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()