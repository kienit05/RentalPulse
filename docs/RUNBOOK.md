# RentalPulse — Hướng dẫn chạy một vòng dự án

Một vòng chạy đưa tin thuê trọ Hà Nội từ trang danh sách đến dashboard Power BI:
Bronze (RustFS) → Kafka → PostgreSQL (Raw → Staging → Core) → dbt → Power BI.
Mọi lệnh chạy trong PowerShell tại **thư mục gốc của repo** (thư mục có `docker-compose.yml`), với `.venv` đã kích hoạt.

## Việc hằng ngày (khi hệ thống đã chạy)

1. Lưu đủ 6 trang mỗi web vào `data/inbox/raw/` **trước 12:00 trưa** (xem Bước 2).
2. 12:00, Airflow tự chạy toàn bộ phần còn lại.
3. Mở Airflow (http://localhost:8081) xem mọi task xanh, rồi Refresh Power BI.

## Chuẩn bị (lần đầu, sau khi clone)

Cần có: Git, Docker Desktop (đang chạy), Python 3.10+, Power BI Desktop (chỉ cho bước dashboard).

```powershell
git clone https://github.com/kienit05/RentalPulse.git
cd RentalPulse
Copy-Item .env.example .env          # rồi mở .env, điền POSTGRES_PASSWORD, RUSTFS_ACCESS_KEY, RUSTFS_SECRET_KEY
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force data\inbox, data\processed
```

- `.env` và `data/` không có trong Git (chứa mật khẩu và dữ liệu), nên mỗi máy tự tạo.
- Mật khẩu tự đặt, chỉ dùng trong máy của bạn; Docker dùng chính các giá trị trong `.env`.
- Những lần sau chỉ cần `cd` vào thư mục repo và `.venv\Scripts\Activate.ps1`.

| Dịch vụ | Container | Địa chỉ |
| --- | --- | --- |
| PostgreSQL | rental-postgres | localhost:5432 |
| RustFS (Bronze) | rental-rustfs | API :9000, giao diện http://localhost:9001 |
| Kafka | rental-kafka | localhost:29092 |
| Kafka UI | rental-kafka-ui | http://localhost:8080 |
| Airflow | rental-airflow-web | http://localhost:8081 (admin / admin) |

## Bước 1. Khởi động hạ tầng

```powershell
docker compose up -d --build
docker compose ps
python scripts/check_env.py
python -m etl.run_pipeline --skip-bronze --init
```

- Mọi dịch vụ ở trạng thái `running`; riêng `rental-airflow-init` chạy xong rồi thoát là đúng.
- `--init` tạo schema, bảng, hàm, view. Chạy lại an toàn; cần chạy lại mỗi khi thêm file vào `sql/`.
- Kiểm tra DAG nạp được:

```powershell
docker exec rental-airflow-scheduler airflow dags list-import-errors
docker exec rental-airflow-scheduler airflow tasks list rentalpulse_kafka_flow
```

## Bước 2. Lưu trang dữ liệu thật vào inbox

Mở từng trang, Ctrl+S, chọn **"Webpage, HTML Only"**, lưu vào `data/inbox/raw/`.
Không cần tự đặt tên: lúc 12:00 task `name_inbox` nhận ra nguồn, đánh số trang theo thứ tự lưu
và lấy ngày từ trang 1 (giờ Việt Nam), rồi chuyển vào `data/inbox/` với tên đúng quy ước.

| Nguồn | Trang 1 | Trang 2–6 |
| --- | --- | --- |
| Nhà Tốt | `https://www.nhatot.com/thue-phong-tro-ha-noi` | thêm `?page=N` |
| Batdongsan | `https://batdongsan.com.vn/cho-thue-nha-tro-phong-tro-ha-noi?sortValue=8` | `.../cho-thue-nha-tro-phong-tro-ha-noi/pN?sortValue=8` |

- **Lưu đúng thứ tự trang 1, 2, 3, … của từng web**, vì thứ tự đánh số dựa vào thời gian lưu.
- `sortValue=8` là "Tin mới nhất": cột "Đăng …" trên trang phải giảm dần.
- Đúng danh mục **phòng trọ** (`cho-thue-nha-tro-phong-tro-ha-noi`), không phải "nhà đất cho thuê"
  (lẫn văn phòng, kho, nhà mặt phố).
- Thư mục `*_files` đi kèm khi bạn lưu trang không ảnh hưởng gì; `name_inbox` chỉ đọc file `.htm*`.

Nguyên tắc giữ dữ liệu sạch:

- Mỗi ngày đủ 6 trang mỗi nguồn (12 trang), cùng thứ tự sắp xếp. Thiếu hoặc thừa trang, hoặc hai trang
  chứa cùng tin (lưu trùng, sai thứ tự) thì `name_inbox` dừng và không đổi tên file nào.
- Lưu cả 12 trang trong một lần ngồi, vì tin mới liên tục đẩy tin cũ sang trang sau.
- "Biến mất" trên dashboard nghĩa là tin đã rơi khỏi khoảng 120 tin mới nhất của nguồn,
  không chắc là đã cho thuê xong.
- Việc lưu trang là thủ công. Airflow chỉ tự động hóa phần xử lý từ `name_inbox` trở đi.

## Bước 3. Pipeline tự chạy bằng Airflow

DAG `rentalpulse_kafka_flow` chạy lúc **12:00 trưa giờ Việt Nam** (`0 5 * * *` UTC),
mỗi lần một run (`max_active_runs=1`), thử lại 1 lần sau 2 phút.

| Thứ tự | Task | Việc làm |
| --- | --- | --- |
| 1 | `name_inbox` → `ingest_inbox` | Đặt tên trang trong `data/inbox/raw/`, rồi nạp vào Bronze; mỗi (nguồn, ngày) phải đủ 6 trang |
| 2 | `publish_new_batches` | Bronze → Kafka `listing.events`, chỉ batch mới; chạy cả khi bước 1 báo lỗi |
| 3 | `consume_into_raw` | Kafka → `raw.listings` (message lỗi vào `listing.events.dlq`) |
| 4 | `build_staging_and_core` | Raw → Staging → Core |
| 5 | `publish_price_changes` → `consume_price_changes` | Phát event đổi giá lên `listing.price_changes`, rồi ghi vào `analytics.price_change_events` |
| 5 | `dbt_run` → `dbt_test` | Dựng và kiểm thử các mart trong schema `analytics` |
| 6 | `log_pipeline_run` | Ghi `analytics.pipeline_runs`, chạy cả khi bước trước lỗi |
| 7 | `check_freshness` | Báo đỏ nếu thiếu dữ liệu ngày hôm nay (bắt lỗi "xanh mà không nạp") |
| 8 | `pipeline_verdict` | Task cuối: đỏ nếu bất kỳ task nào trước đó đã lỗi, để trạng thái cả lần chạy phản ánh đúng |

Mock không còn chạy trong DAG; code và test mock vẫn giữ để thử logic vòng đời khi cần.

Cổng đủ trang: nếu một nguồn trong ngày thiếu trang, `ingest_inbox` chuyển đỏ và ghi rõ trang nào thiếu;
các file của nhóm đó nằm lại `data/inbox/`. Lưu bổ sung trang thiếu rồi chạy lại. File nạp xong chuyển
sang `data/processed/`.

Khi `data/inbox/` rỗng (chưa lưu trang, hoặc dữ liệu hôm nay đã nạp rồi), `name_inbox` và `ingest_inbox` vẫn xanh vì không có gì chờ nạp. Việc báo thiếu dữ liệu thuộc về `check_freshness`.

Chạy ngay, không chờ 12:00:

```powershell
docker exec rental-airflow-scheduler airflow dags trigger rentalpulse_kafka_flow
docker exec rental-airflow-scheduler airflow dags list-runs -d rentalpulse_kafka_flow
docker exec rental-airflow-scheduler airflow dags next-execution rentalpulse_kafka_flow
```

### Chạy tay (khi cần gỡ lỗi)

```powershell
python -m scripts.name_inbox
python -m etl.ingest_inbox --no-pipeline --expect-pages 6
python -m etl.run_kafka_flow
cd dbt; dbt run --profiles-dir .; dbt test --profiles-dir .; cd ..
python -m etl.log_run --run-id manual-YYYY-MM-DD
```

Không chạy `python -m etl.ingest_inbox` thiếu `--no-pipeline`: lệnh đó nạp thẳng Bronze → raw, bỏ qua Kafka.

## Bước 4. Kiểm tra kết quả

Một vòng đạt khi mọi task xanh (kể cả `pipeline_verdict`), run-log có dòng mới với `last_snapshot_date` đúng ngày lưu trang,
và DLQ không tăng.

```powershell
python -m pytest -q
docker exec -it rental-postgres psql -U rental -d rentalpulse
```

```sql
-- mỗi lần chạy thêm bao nhiêu dòng
SELECT * FROM analytics.v_pipeline_runs ORDER BY logged_at DESC LIMIT 5;
-- số tin và tỉ lệ thiếu giá/diện tích/quận theo nguồn, theo ngày
SELECT * FROM analytics.v_data_quality_daily ORDER BY snapshot_date DESC, source;
-- dòng chảy tin mỗi ngày (dbt)
SELECT * FROM analytics.mart_daily_listing_flow ORDER BY snapshot_date DESC LIMIT 10;
```

- Mỗi nguồn thật một ngày nên có khoảng 120 tin (6 trang × 20 tin). Ít hơn nhiều nghĩa là
  thiếu trang hoặc lưu nhầm danh mục.
- Kafka UI (http://localhost:8080): topic `listing.events.dlq` không có message mới.

## Bước 5. Dashboard

Mở `docs/powerbi/rentalpulse.pbix`, bấm **Làm mới** (Refresh). File nối Import vào `localhost:5432`,
database `rentalpulse`, chỉ đọc schema `analytics`. Trang tổng quan lọc `is_simulated = False` để chỉ
hiện dữ liệu thật. Ghi nguồn "Batdongsan.com.vn" và "Nhà Tốt" trên dashboard.

## Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| `relation analytics.… does not exist` | File SQL mới chưa chạy DDL | `python -m etl.run_pipeline --skip-bronze --init` |
| DAG không hiện trong Airflow | Lỗi Python trong file DAG | `airflow dags list-import-errors` (lệnh ở Bước 1) |
| `ingest_inbox` đỏ, log "Thiếu trang …" | Chưa đủ 6 trang một nguồn | Lưu bổ sung trang thiếu, trigger lại DAG |
| `Không có file hợp lệ trong …inbox` | Chưa lưu trang hoặc sai tên file | Đặt tên `<nguồn>_<YYYY-MM-DD>[_pN].html` |
| dbt báo `__dbt_backup already exists` | Hai lần `dbt run` chạy cùng lúc | Đợi run kia xong; DAG đã đặt `max_active_runs=1` |
| Batdongsan ra tin văn phòng, kho | Lưu nhầm danh mục "nhà đất cho thuê" | Dùng link `cho-thue-nha-tro-phong-tro-ha-noi?sortValue=8` |
| Power BI không kết nối được | Container Postgres chưa chạy | `docker compose ps`, rồi `docker compose up -d postgres` |
| `name_inbox` đỏ, báo không thấy module `scripts` | Thư mục `scripts/` chưa được mount vào container Airflow | Kiểm tra volume `./scripts` trong `docker-compose.yml`, rồi `docker compose up -d` |
| `name_inbox` đỏ, log "có N trang, cần đúng 6" hoặc "trùng tin với trang …" | Thiếu, thừa trang hoặc lưu sai thứ tự | Sửa `data/inbox/raw/` cho đúng 6 trang mỗi nguồn theo thứ tự, rồi trigger lại DAG |
| Cả lần chạy đỏ nhưng các task trước đều xanh | `pipeline_verdict` phát hiện task lỗi hoặc `check_freshness` đỏ | Mở log `pipeline_verdict`: nó liệt kê task lỗi |
| DAG xanh nhưng không có dữ liệu mới | Trang chưa nằm trong `data/inbox/raw/` nên không có gì để nạp | Xem task `check_freshness`: đỏ nghĩa là thiếu dữ liệu hôm nay |

## Tắt hệ thống

```powershell
docker compose down
```

Dữ liệu vẫn giữ trong volume. Chỉ dùng `docker compose down -v` khi muốn xóa sạch Postgres, RustFS
và Kafka để làm lại từ đầu.
