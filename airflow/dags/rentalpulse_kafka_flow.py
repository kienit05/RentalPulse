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
    schedule="0 1 * * *",  # 01:00 UTC mỗi ngày = 08:00 sáng giờ Việt Nam
    catchup=False,
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

    collect_mock >> publish_batches >> load_raw >> build_layers
    # Sau khi Staging/Core xong, hai nhánh chạy song song: phát sự kiện đổi giá, và dbt
    build_layers >> [publish_price_changes, dbt_run]
    dbt_run >> dbt_test