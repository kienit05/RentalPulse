"""DAG: luồng Kafka của RentalPulse.

Mock -> Bronze -> Kafka -> raw.listings -> Staging/Core -> (sự kiện đổi giá | dbt).
Mỗi bước là một task riêng để thấy rõ bước nào lỗi và chạy lại đúng bước đó.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/project"
DBT_DIR = "/opt/airflow/dbt"
DBT = "/home/airflow/dbt_venv/bin/dbt"  # dbt nằm trong virtualenv riêng

default_args = {
    "owner": "kevin",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="rentalpulse_kafka_flow",
    description="Mock -> Bronze -> Kafka -> Raw -> Staging/Core -> price_changes + dbt",
    start_date=datetime(2026, 11, 21),
    schedule="0 5 * * *",  # 05:00 UTC mỗi ngày = 12:00 trưa giờ Việt Nam
    catchup=False,
    max_active_runs=1,  # không cho hai lần chạy chồng nhau (tránh đua nhau ở dbt và ở next_mock_day)
    default_args=default_args,
    tags=["rentalpulse"],
) as dag:

    collect_mock = BashOperator(
        task_id="collect_mock",
        # Hỏi DB xem mock đã tới ngày nào, rồi thu thập ngày kế tiếp
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "DAY=$(python -m etl.next_mock_day) && "
            'echo "Thu thập mock ngày $DAY" && '
            "python -m collectors.collector --day $DAY"
        ),
    )

    publish_batches = BashOperator(
        task_id="publish_new_batches",
        bash_command=f"cd {PROJECT_DIR} && python -m etl.publish_batch --only-new",
        trigger_rule="all_done",  # chạy cả khi ingest_inbox báo thiếu trang
    )

    load_raw = BashOperator(
        task_id="consume_into_raw",
        bash_command=f"cd {PROJECT_DIR} && python -m etl.consume_events --once",
    )

    build_layers = BashOperator(
        task_id="build_staging_and_core",
        bash_command=f"cd {PROJECT_DIR} && python -m etl.run_pipeline --skip-bronze",
    )

    publish_price_changes = BashOperator(
        task_id="publish_price_changes",
        # Đã có sổ analytics.published_events nên chỉ phát event chưa từng phát
        bash_command=f"cd {PROJECT_DIR} && python -m etl.publish_price_changes",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {DBT} run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && {DBT} test --profiles-dir .",
    )

    log_run = BashOperator(
        task_id="log_pipeline_run",
        # run_id do Airflow điền vào; ghi sổ cả khi task trước đó lỗi
        bash_command=f'cd {PROJECT_DIR} && python -m etl.log_run --run-id "{{{{ run_id }}}}"',
        trigger_rule="all_done",
    )

    check_fresh = BashOperator(
        task_id="check_freshness",
        bash_command=f"cd {PROJECT_DIR} && python -m etl.check_freshness",
        trigger_rule="all_done",
    )

    ingest_real = BashOperator(
        task_id="ingest_inbox",
        # Nạp trang thật bạn đã lưu vào data/inbox; thiếu trang thì task đỏ, nhóm đó chờ lần sau
        bash_command=f"cd {PROJECT_DIR} && python -m etl.ingest_inbox --no-pipeline --expect-pages 6",
        trigger_rule="all_done",
    )

    name_inbox = BashOperator(
        task_id="name_inbox",
        # Nhận diện thứ tự trang trong data/inbox/raw, đặt tên rồi chuyển vào data/inbox
        bash_command=f"cd {PROJECT_DIR} && TZ=Asia/Ho_Chi_Minh python -m scripts.name_inbox",
    )

    # 1. Chạy song song: Tạo mock và nạp dữ liệu thật
    collect_mock >> publish_batches

    name_inbox >> ingest_real
    
    # 2. Luồng dữ liệu thật: ingest_inbox nạp các trang bạn đã lưu vào data/inbox
    ingest_real >> publish_batches
    
    # 3. Các bước sau giữ nguyên
    publish_batches >> load_raw >> build_layers
    build_layers >> [publish_price_changes, dbt_run]
    dbt_run >> dbt_test
    [publish_price_changes, dbt_test] >> log_run

    log_run >> check_fresh