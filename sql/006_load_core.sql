-- 1) Danh sách tin: thêm tin mới, cập nhật khoảng ngày đã thấy.
INSERT INTO core.listing_source (source, listing_id, first_seen_date, last_seen_date, is_simulated)
SELECT source, listing_id, min(snapshot_date), max(snapshot_date), bool_or(is_simulated)
FROM staging.listings
GROUP BY source, listing_id
ON CONFLICT (source, listing_id) DO UPDATE SET
    first_seen_date = LEAST(core.listing_source.first_seen_date, EXCLUDED.first_seen_date),
    last_seen_date  = GREATEST(core.listing_source.last_seen_date, EXCLUDED.last_seen_date),
    is_simulated    = EXCLUDED.is_simulated;

-- 2) Ảnh chụp mỗi ngày của mỗi tin.
INSERT INTO core.fact_listing_snapshot (
    listing_key, snapshot_date, title, price_vnd, original_price_vnd, area_m2,
    property_type, province_raw, district_norm, latitude, longitude, posted_date, batch_id)
SELECT ls.listing_key, s.snapshot_date, s.title, s.price_vnd, s.original_price_vnd, s.area_m2,
       s.property_type, s.province_raw, s.district_norm, s.latitude, s.longitude,
       s.posted_date, s.batch_id
FROM staging.listings s
JOIN core.listing_source ls ON ls.source = s.source AND ls.listing_id = s.listing_id
ON CONFLICT (listing_key, snapshot_date) DO UPDATE SET
    title = EXCLUDED.title, price_vnd = EXCLUDED.price_vnd,
    original_price_vnd = EXCLUDED.original_price_vnd, area_m2 = EXCLUDED.area_m2,
    property_type = EXCLUDED.property_type, province_raw = EXCLUDED.province_raw,
    district_norm = EXCLUDED.district_norm, latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude, posted_date = EXCLUDED.posted_date,
    batch_id = EXCLUDED.batch_id, loaded_at = now();