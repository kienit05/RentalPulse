WITH ranked AS (
    SELECT batch_id, source, snapshot_date, bronze_key, payload,
           payload->>'listing_id' AS listing_id,
           row_number() OVER (
               PARTITION BY source, payload->>'listing_id', snapshot_date
               ORDER BY batch_id DESC
           ) AS rn
    FROM raw.listings
    WHERE source IN ('batdongsan', 'nhatot', 'mock')
),
typed AS (
    SELECT source, listing_id, snapshot_date, batch_id, bronze_key,
           payload->>'title'                          AS title,
           payload->>'price_raw'                      AS price_raw,
           COALESCE((payload->>'price_vnd')::numeric,
                    staging.parse_price_vnd(payload->>'price_raw'))  AS price_vnd,
           (payload->>'original_price_vnd')::numeric  AS original_price_vnd,
           COALESCE((payload->>'area_m2')::numeric,
                    staging.parse_area_m2(payload->>'area_raw'))     AS area_m2,
           payload->>'property_type'                  AS property_type,
           payload->>'province_raw'                   AS province_raw,
           payload->>'district_raw'                   AS district_raw,
           payload->>'ward_raw'                       AS ward_raw,
           COALESCE(payload->>'street_raw', payload->>'address_raw') AS street_raw,
           (payload->>'latitude')::double precision   AS latitude,
           (payload->>'longitude')::double precision  AS longitude,
           (payload->>'deposit_vnd')::numeric         AS deposit_vnd,
           CASE
               WHEN payload->>'posted_at' IS NULL THEN NULL
               WHEN payload->>'posted_at' ~ '(Z|[+-][0-9]{2}:?[0-9]{2})$'
                   THEN (payload->>'posted_at')::timestamptz
               ELSE (payload->>'posted_at')::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh'
           END                                        AS posted_at,
           (payload->>'posted_date')::date            AS posted_date_src
    FROM ranked
    WHERE rn = 1 AND listing_id IS NOT NULL
)
INSERT INTO staging.listings (
    source, listing_id, snapshot_date, title, price_raw, price_vnd, original_price_vnd,
    area_m2, property_type, province_raw, district_raw, district_norm, ward_raw, street_raw,
    latitude, longitude, deposit_vnd, posted_at, posted_date, is_simulated, batch_id, bronze_key)
SELECT source, listing_id, snapshot_date, title, price_raw, price_vnd, original_price_vnd,
       area_m2, property_type, province_raw, district_raw,
       staging.normalize_district(district_raw), ward_raw, street_raw,
       latitude, longitude, deposit_vnd, posted_at,
       COALESCE(posted_date_src, (posted_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date),
       (source = 'mock'), batch_id, bronze_key
FROM typed
ON CONFLICT (source, listing_id, snapshot_date) DO UPDATE SET
    title = EXCLUDED.title, price_raw = EXCLUDED.price_raw, price_vnd = EXCLUDED.price_vnd,
    original_price_vnd = EXCLUDED.original_price_vnd, area_m2 = EXCLUDED.area_m2,
    property_type = EXCLUDED.property_type, province_raw = EXCLUDED.province_raw,
    district_raw = EXCLUDED.district_raw, district_norm = EXCLUDED.district_norm,
    ward_raw = EXCLUDED.ward_raw, street_raw = EXCLUDED.street_raw,
    latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
    deposit_vnd = EXCLUDED.deposit_vnd, posted_at = EXCLUDED.posted_at,
    posted_date = EXCLUDED.posted_date, is_simulated = EXCLUDED.is_simulated,
    batch_id = EXCLUDED.batch_id, bronze_key = EXCLUDED.bronze_key, loaded_at = now();