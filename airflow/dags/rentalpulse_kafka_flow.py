"""DAG: luồng Kafka của RentalPulse.

Mock -> Bronze -> Kafka -> raw.listings -> Staging/Core -> (sự kiện đổi giá | dbt).
Mỗi bước là một task riêng để thấy rõ bước nào lỗi và chạy lại đúng bước đó.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator

PROJECT_DIR = "/opt/airflow/project"
DBT_DIR = "/opt/airflow/dbt"
DBT = "/home/airflow/dbt_venv/bin/dbt"  # dbt nằm trong virtualenv riêng

default_args = {
    "owner": "kevin",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

def assert_run_ok(**context):
    """Task cuối: đỏ nếu bất kỳ task nào khác trong lần chạy này đã lỗi."""
    me = context["ti"].task_id
    bad = sorted(
        ti.task_id
        for ti in context["dag_run"].get_task_instances()
        if ti.task_id != me and ti.state in ("failed", "upstream_failed")
    )
    if bad:
        raise AirflowFailException("Task lỗi: " + ", ".join(bad))

with DAG(
    dag_id="rentalpulse_kafka_flow",
    description="Inbox -> Bronze -> Kafka -> Raw -> Staging/Core -> price_changes + dbt",
    start_date=datetime(2026, 11, 21),
    schedule="0 5 * * *",  # 05:00 UTC mỗi ngày = 12:00 trưa giờ Việt Nam
    catchup=False,
    max_active_runs=1,  # không cho hai lần chạy chồng nhau (tránh đua nhau ở dbt)
    default_args=default_args,
    tags=["rentalpulse"],
) as dag:

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

    consume_price_changes = BashOperator(
        task_id="consume_price_changes",
        bash_command=f"cd {PROJECT_DIR} && python -m etl.consume_price_changes --once",
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

    verdict = PythonOperator(
        task_id="pipeline_verdict",
        python_callable=assert_run_ok,
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

    # 1. Luồng dữ liệu thật: đặt tên trang đã lưu, rồi nạp vào Bronze
    name_inbox >> ingest_real >> publish_batches

    # 2. Các bước sau
    publish_batches >> load_raw >> build_layers
    build_layers >> [publish_price_changes, dbt_run]
    dbt_run >> dbt_test
    publish_price_changes >> consume_price_changes
    [consume_price_changes, dbt_test] >> log_run

    log_run >> check_fresh >> verdict