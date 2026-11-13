# RentalPulse

Data pipeline cho tin đăng thuê nhà: thu thập, lưu trữ, làm sạch, phân tích.

## Công nghệ
Python, Kafka, RustFS (S3-compatible), PostgreSQL, Airflow, dbt, Power BI, Docker Compose.

## Chạy môi trường
1. Sao chép `.env.example` thành `.env` và điền mật khẩu.
2. `docker compose up -d postgres rustfs kafka`
3. `python -m venv .venv`, kích hoạt rồi `pip install -r requirements.txt`
4. `python scripts/check_env.py`

## GUI RustFS
![alt text](image.png)