import os
from dotenv import load_dotenv

load_dotenv()  # đọc các biến trong file .env


def check_postgres():
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("Postgres OK:", cur.fetchone()[0][:40])
    conn.close()


def check_object_storage():
    from minio import Minio
    client = Minio(
        os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ROOT_USER"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
        secure=False,
    )
    bucket = os.getenv("MINIO_BUCKET")
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    print("Object storage OK: bucket", bucket)


def check_kafka():
    from confluent_kafka.admin import AdminClient, NewTopic
    admin = AdminClient({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS")})
    topic = os.getenv("KAFKA_TOPIC")
    md = admin.list_topics(timeout=10)
    if topic not in md.topics:
        admin.create_topics([NewTopic(topic, num_partitions=3, replication_factor=1)])[topic].result()
    print("Kafka OK: topic", topic)


for fn in (check_postgres, check_object_storage, check_kafka):
    try:
        fn()
    except Exception as e:
        print(f"{fn.__name__} FAILED:", e)