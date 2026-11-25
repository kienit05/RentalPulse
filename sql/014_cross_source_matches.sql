-- Ghép tin giữa Nhà Tốt và Batdongsan: cùng một phòng đăng trên cả hai web.
-- Hai nguồn không có mã chung, Batdongsan không có địa chỉ đường hay toạ độ, và tên phường
-- hai bên khác nhau, nên ghép theo ngày, quận, diện tích, giá và độ giống tiêu đề.
-- Chỉ nhận cặp duy nhất hai chiều. Không xóa hay gộp dòng nào: đây chỉ là bảng liên kết.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP VIEW IF EXISTS analytics.v_dedup_summary;
DROP VIEW IF EXISTS core.v_cross_source_matches;

CREATE VIEW core.v_cross_source_matches AS
WITH base AS (
    SELECT source, listing_id, snapshot_date, district_norm, area_m2, price_vnd, title
    FROM staging.listings
    WHERE is_simulated = false
      AND source IN ('nhatot', 'batdongsan')
      AND district_norm IS NOT NULL
      AND area_m2 IS NOT NULL
      AND price_vnd IS NOT NULL
      AND title IS NOT NULL
),
cand AS (
    SELECT a.snapshot_date,
           a.listing_id AS nhatot_listing_id,
           b.listing_id AS batdongsan_listing_id,
           a.district_norm,
           a.area_m2   AS nhatot_area_m2,    b.area_m2   AS batdongsan_area_m2,
           a.price_vnd AS nhatot_price_vnd,  b.price_vnd AS batdongsan_price_vnd,
           round(similarity(a.title, b.title)::numeric, 2) AS title_similarity,
           a.title AS nhatot_title, b.title AS batdongsan_title
    FROM base a
    JOIN base b
      ON  a.source = 'nhatot' AND b.source = 'batdongsan'
      AND a.snapshot_date = b.snapshot_date
      AND a.district_norm = b.district_norm
      AND abs(a.area_m2 - b.area_m2) <= 0.5
      AND abs(a.price_vnd - b.price_vnd) <= 0.02 * greatest(a.price_vnd, b.price_vnd)
      AND similarity(a.title, b.title) >= 0.5
),
counted AS (
    SELECT c.*,
           count(*) OVER (PARTITION BY snapshot_date, nhatot_listing_id)     AS per_nhatot,
           count(*) OVER (PARTITION BY snapshot_date, batdongsan_listing_id) AS per_batdongsan
    FROM cand c
)
SELECT snapshot_date, nhatot_listing_id, batdongsan_listing_id, district_norm,
       nhatot_area_m2, batdongsan_area_m2, nhatot_price_vnd, batdongsan_price_vnd,
       title_similarity, nhatot_title, batdongsan_title
FROM counted
WHERE per_nhatot = 1 AND per_batdongsan = 1;

-- Tóm tắt mỗi ngày: số tin hoạt động mỗi nguồn, số cặp ghép được, số phòng sau khi loại trùng.
CREATE VIEW analytics.v_dedup_summary AS
WITH active AS (
    SELECT snapshot_date,
           count(*) FILTER (WHERE source = 'nhatot')     AS nhatot_listings,
           count(*) FILTER (WHERE source = 'batdongsan') AS batdongsan_listings
    FROM staging.listings
    WHERE is_simulated = false AND source IN ('nhatot', 'batdongsan')
    GROUP BY snapshot_date
),
pairs AS (
    SELECT snapshot_date, count(*) AS matched_pairs
    FROM core.v_cross_source_matches
    GROUP BY snapshot_date
)
SELECT a.snapshot_date,
       a.nhatot_listings,
       a.batdongsan_listings,
       coalesce(p.matched_pairs, 0) AS matched_pairs,
       a.nhatot_listings + a.batdongsan_listings - coalesce(p.matched_pairs, 0) AS unique_rooms
FROM active a
LEFT JOIN pairs p USING (snapshot_date);