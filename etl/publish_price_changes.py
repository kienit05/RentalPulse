"""Phát event price_changed lên Kafka, lấy từ view core.v_price_history.

Chỉ lấy các dòng giá tăng hoặc giảm thật sự, và chỉ phát những event chưa có trong
sổ analytics.published_events. Chỉ ghi sổ SAU KHI Kafka xác nhận đã nhận (at-least-once).
"""
import argparse
import json
import logging
import os
from decimal import Decimal

from confluent_kafka import Producer
from dotenv import load_dotenv
from psycopg2.extras import execute_values

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


def filter_unpublished(events, published_ids):
    """events: danh sách (message_key, event). Giữ lại event chưa có trong sổ."""
    return [(key, event) for key, event in events if event["event_id"] not in published_ids]


def fetch_changes(conn, since=None):
    with conn.cursor() as cur:
        cur.execute(QUERY, {"since": since})
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, values)) for values in cur.fetchall()]


def load_published_ids(conn, event_ids):
    if not event_ids:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_id FROM analytics.published_events WHERE event_id = ANY(%s)",
            (list(event_ids),),
        )
        return {row[0] for row in cur.fetchall()}


def record_published(conn, event_ids):
    if not event_ids:
        return
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO analytics.published_events (event_id, topic) VALUES %s "
            "ON CONFLICT (event_id) DO NOTHING",
            [(event_id, TOPIC) for event_id in event_ids],
        )
    conn.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Phát event price_changed lên Kafka")
    parser.add_argument("--since", help="Chỉ lấy thay đổi từ ngày này trở đi (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    conn = connect()
    try:
        events = [build_price_event(row) for row in fetch_changes(conn, args.since)]
        published = load_published_ids(conn, [event["event_id"] for _, event in events])
        pending = filter_unpublished(events, published)
        log.info(
            "Tìm thấy %d thay đổi giá, đã phát trước đó %d, cần phát %d (topic %s)",
            len(events), len(events) - len(pending), len(pending), TOPIC,
        )

        producer = Producer(
            {"bootstrap.servers": BOOTSTRAP, "acks": "all", "enable.idempotence": True}
        )
        delivered = set()
        stats = {"failed": 0}

        def make_callback(event_id):
            def on_delivery(err, msg):
                if err is not None:
                    stats["failed"] += 1
                    log.error("Gửi lỗi: %s", err)
                else:
                    delivered.add(event_id)
            return on_delivery

        for message_key, event in pending:
            producer.produce(
                TOPIC,
                key=message_key,
                value=json.dumps(event, ensure_ascii=False).encode("utf-8"),
                on_delivery=make_callback(event["event_id"]),
            )
            producer.poll(0)

        remaining = producer.flush(30)
        record_published(conn, delivered)  # chỉ ghi sổ những event đã được xác nhận
        if remaining:
            log.error("Còn %d message chưa được xác nhận", remaining)
            raise SystemExit(1)
        log.info("Xong: gửi %d, lỗi %d", len(delivered), stats["failed"])
        if stats["failed"]:
            raise SystemExit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()