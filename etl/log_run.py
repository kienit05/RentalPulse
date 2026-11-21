"""Ghi một dòng 'sổ chạy' vào analytics.pipeline_runs.

Chạy cuối mỗi lần chạy DAG: chụp số dòng của từng tầng và số tin trong DLQ.
Ghi theo run_id nên chạy lại không tạo dòng trùng.
"""
import argparse
import os

import psycopg2
from dotenv import load_dotenv

COUNTS_SQL = """
SELECT
    (SELECT count(*) FROM raw.listings),
    (SELECT count(*) FROM staging.listings),
    (SELECT count(*) FROM core.fact_listing_snapshot),
    (SELECT count(*) FROM core.listing_source),
    (SELECT max(snapshot_date) FROM core.fact_listing_snapshot),
    (SELECT count(*) FROM analytics.published_events)
"""

UPSERT_SQL = """
INSERT INTO analytics.pipeline_runs
    (run_id, raw_rows, staging_rows, core_snapshots, core_listings,
     last_snapshot_date, price_events_total, dlq_messages)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (run_id) DO UPDATE SET
    logged_at          = now(),
    raw_rows           = EXCLUDED.raw_rows,
    staging_rows       = EXCLUDED.staging_rows,
    core_snapshots     = EXCLUDED.core_snapshots,
    core_listings      = EXCLUDED.core_listings,
    last_snapshot_date = EXCLUDED.last_snapshot_date,
    price_events_total = EXCLUDED.price_events_total,
    dlq_messages       = EXCLUDED.dlq_messages
"""


def count_dlq_messages():
    """Số tin còn lưu trong topic DLQ (high - low watermark, cộng mọi partition).

    Trả về None nếu không đọc được Kafka: thiếu số liệu vẫn tốt hơn ghi sai.
    """
    try:
        from confluent_kafka import Consumer, TopicPartition

        topic = os.getenv("KAFKA_TOPIC_DLQ", "listing.events.dlq")
        consumer = Consumer({
            "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "localhost:29092"),
            "group.id": "run-log-reader",
        })
        try:
            meta = consumer.list_topics(topic, timeout=10)
            if topic not in meta.topics or meta.topics[topic].error is not None:
                return 0
            total = 0
            for partition in meta.topics[topic].partitions:
                low, high = consumer.get_watermark_offsets(
                    TopicPartition(topic, partition), timeout=10
                )
                total += high - low
            return total
        finally:
            consumer.close()
    except Exception as exc:  # noqa: BLE001 - sổ chạy không được làm hỏng pipeline
        print(f"Không đọc được DLQ: {exc}")
        return None


def connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    load_dotenv()
    dlq = count_dlq_messages()

    with connect() as conn, conn.cursor() as cur:
        cur.execute(COUNTS_SQL)
        raw, staging, snapshots, listings, last_date, price_events = cur.fetchone()
        cur.execute(
            UPSERT_SQL,
            (args.run_id, raw, staging, snapshots, listings, last_date, price_events, dlq),
        )

    print(
        f"Đã ghi sổ {args.run_id}: raw={raw} staging={staging} "
        f"core_snapshots={snapshots} ngày_mới_nhất={last_date} dlq={dlq}"
    )


if __name__ == "__main__":
    main()