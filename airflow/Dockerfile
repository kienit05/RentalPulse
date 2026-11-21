FROM apache/airflow:2.10.5

# dbt nằm trong virtualenv riêng để không xung đột thư viện với Airflow
RUN python -m venv /home/airflow/dbt_venv \
 && /home/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-core==1.12.7 dbt-postgres==1.11.0

# Thư viện cho code của dự án (chạy trong môi trường Airflow; boto3 và psycopg2 đã có sẵn)
RUN pip install --no-cache-dir confluent-kafka==2.16.1 beautifulsoup4==4.15.0 python-dotenv==1.2.4