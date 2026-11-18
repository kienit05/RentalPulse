# RentalPulse

Data pipeline theo dõi tin đăng thuê nhà: thu thập, lưu trữ, làm sạch, phân tích biến động giá và vòng đời tin đăng.

> Dự án đang được xây dựng theo từng giai đoạn. Dữ liệu hiện tại là dữ liệu giả lập (mock) mô phỏng tin đăng thật.

## Mục tiêu

- Theo dõi lịch sử giá của cùng một tin đăng, không ghi đè dữ liệu cũ.
- Phát hiện vòng đời tin: tin mới, đổi giá, biến mất, xuất hiện lại.
- Ghép các tin đăng cùng một căn phòng giữa các nguồn khác nhau.
- Kiểm tra chất lượng dữ liệu và theo dõi trạng thái pipeline.

## Trạng thái

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 0 | Chuẩn hóa môi trường | Gần xong |
| 1 | Thu thập dữ liệu và tầng Bronze | Đang làm |
| 2 | PostgreSQL và mô hình dữ liệu | Chưa bắt đầu |
| 3 | Batch ETL | Chưa bắt đầu |
| 4 | Lịch sử giá và entity resolution | Chưa bắt đầu |
| 5 | Kafka streaming | Chưa bắt đầu |
| 6 | Airflow, dbt, data quality | Chưa bắt đầu |
| 7 | Dashboard và portfolio | Chưa bắt đầu |

Kafka đã được dựng nhưng chưa có dữ liệu chảy qua, Airflow đã khai báo trong `docker-compose.yml` nhưng chưa dùng.

## Công nghệ

| Thành phần | Vai trò |
|---|---|
| Python | Collector và các bước nạp dữ liệu |
| RustFS | Kho đối tượng chuẩn S3, lưu dữ liệu thô (Bronze) |
| PostgreSQL | Kho dữ liệu đã xử lý |
| Kafka | Truyền sự kiện (Giai đoạn 5) |
| Airflow, dbt | Điều phối và biến đổi dữ liệu (Giai đoạn 6) |
| Power BI | Dashboard (Giai đoạn 7) |
| Docker Compose | Dựng toàn bộ hạ tầng |

## Yêu cầu

Docker Desktop (WSL 2, nên cấp từ 4 GB RAM), Python 3.10 và Git.

## Chạy nhanh

```powershell
copy .env.example .env
docker compose up -d postgres rustfs kafka kafka-ui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\check_env.py
```
Thu thập một ngày dữ liệu mô phỏng vào Bronze (ngày 1, 2, 3...):

```powershell
python -m collectors.collector --day 1
```
## Cấu trúc

| Thư mục | Vai trò |
|---|---|
| `collectors/mock_source.py` | Sinh dữ liệu mô phỏng theo ngày |
| `collectors/collector.py` | Điều phối: lấy snapshot, đóng gói batch, gọi storage |
| `storage/rustfs.py` | Client RustFS (boto3) |
| `scripts/check_env.py` | Kiểm tra kết nối PostgreSQL, RustFS, Kafka |

Đường dẫn trong Bronze: `source=<nguồn>/dt=<ngày dữ liệu>/batch_id=<mã lần chạy>/listings.json`

Mở `.env` và điền các giá trị còn trống trước khi chạy Docker. Kết quả mong đợi của `check_env.py` là ba dòng `OK` (Postgres, Object storage, Kafka).

## Cấu hình `.env`

| Biến | Ý nghĩa |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Tài khoản và tên database của PostgreSQL |
| `POSTGRES_HOST`, `POSTGRES_PORT` | Địa chỉ PostgreSQL khi truy cập từ máy bạn |
| `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY` | Tài khoản của RustFS |
| `RUSTFS_ENDPOINT` | Địa chỉ API của RustFS, ví dụ `localhost:9000` |
| `RUSTFS_BUCKET` | Tên bucket chứa dữ liệu thô |
| `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC` | Địa chỉ Kafka và tên topic |

## Địa chỉ dịch vụ

| Dịch vụ | Địa chỉ |
|---|---|
| RustFS Console | http://localhost:9001/rustfs/console/ |
| RustFS S3 API | http://localhost:9000 |
| Kafka UI | http://localhost:8080 |
| PostgreSQL | `localhost:5432` |
| Kafka (từ máy host) | `localhost:29092` |

## Giao diện RustFS

![RustFS - bucket rental-bronze](image.png)