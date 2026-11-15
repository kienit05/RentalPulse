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
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    client = boto3.client(
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
    bucket = os.getenv("RUSTFS_BUCKET")
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket)
        else:
            raise
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