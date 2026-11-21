"""Kiểm tra nhanh Kafka: gửi 1 event rồi đọc lại.

Chạy từ máy Windows nên dùng cổng ngoài localhost:29092.
"""
import json
import sys
import uuid

from confluent_kafka import Consumer, Producer

BOOTSTRAP = "localhost:29092"
TOPIC = "listing.events"


def main() -> int:
    marker = uuid.uuid4().hex[:8]
    key = f"smoke:{marker}"
    event = {"type": "smoke_test", "marker": marker}

    producer = Producer({"bootstrap.servers": BOOTSTRAP})
    delivered = {}

    def on_delivery(err, msg):
        if err is not None:
            print(f"Gửi lỗi: {err}")
        else:
            delivered["partition"] = msg.partition()
            delivered["offset"] = msg.offset()

    producer.produce(
        TOPIC,
        key=key,
        value=json.dumps(event).encode("utf-8"),
        on_delivery=on_delivery,
    )
    producer.flush(10)
    if not delivered:
        print("Không nhận được xác nhận từ broker (kiểm tra cổng 29092).")
        return 1
    print(f"Đã gửi: partition={delivered['partition']} offset={delivered['offset']}")

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": f"smoke-{marker}",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([TOPIC])
    try:
        for _ in range(30):
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            if msg.key() and msg.key().decode("utf-8") == key:
                print(f"Đã đọc lại: {msg.value().decode('utf-8')}")
                return 0
        print("Không đọc lại được event trong 30 giây.")
        return 1
    finally:
        consumer.close()


if __name__ == "__main__":
    sys.exit(main())