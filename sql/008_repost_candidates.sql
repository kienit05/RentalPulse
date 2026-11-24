-- Ứng viên "đăng lại": một tin biến mất, rồi trong vòng 14 ngày có tin MỚI (mã khác) cùng nguồn
-- với cùng địa chỉ, quận, loại, diện tích. Chỉ so tin chưa quay lại bằng chính mã cũ.
CREATE OR REPLACE VIEW core.v_repost_candidates AS
WITH attrs AS (
    -- thuộc tính ở lần chụp gần nhất của mỗi tin
    SELECT DISTINCT ON (ls.listing_key)
           ls.listing_key,
           lower(btrim(regexp_replace(s.street_raw, '\s+', ' ', 'g'))) AS address_key,
           s.district_norm, s.property_type, s.area_m2
    FROM staging.listings s
    JOIN core.listing_source ls ON ls.source = s.source AND ls.listing_id = s.listing_id
    ORDER BY ls.listing_key, s.snapshot_date DESC
),
gone AS (
    SELECT e.listing_key, e.source, e.listing_id, e.event_date AS gone_date
    FROM core.v_listing_events e
    WHERE e.event_type = 'disappeared'
      AND NOT EXISTS (
          SELECT 1 FROM core.v_listing_events r
          WHERE r.listing_key = e.listing_key AND r.event_type = 'returned'
            AND r.event_date > e.event_date)
),
fresh AS (
    SELECT e.listing_key, e.source, e.listing_id, e.event_date AS fresh_date
    FROM core.v_listing_events e
    WHERE e.event_type = 'first_seen'
)
SELECT g.source,
       g.listing_id AS old_listing_id,
       f.listing_id AS new_listing_id,
       g.gone_date,
       f.fresh_date,
       f.fresh_date - g.gone_date AS gap_days,
       a.address_key
FROM gone g
JOIN fresh f ON f.source = g.source
            AND f.listing_key <> g.listing_key
            AND f.fresh_date >= g.gone_date
            AND f.fresh_date - g.gone_date <= 14
JOIN attrs a ON a.listing_key = g.listing_key
JOIN attrs b ON b.listing_key = f.listing_key
WHERE a.address_key IS NOT NULL
  AND a.address_key   = b.address_key
  AND a.district_norm IS NOT DISTINCT FROM b.district_norm
  AND a.property_type IS NOT DISTINCT FROM b.property_type
  -- thiếu diện tích ở một bên nghĩa là "chưa biết", không phải "khác nhau"
  AND (a.area_m2 IS NULL OR b.area_m2 IS NULL OR a.area_m2 = b.area_m2);
  