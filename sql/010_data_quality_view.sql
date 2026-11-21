-- Chất lượng dữ liệu theo nguồn và ngày chụp: số tin mỗi tầng, tin rơi rụng, tỉ lệ thiếu trường.
CREATE OR REPLACE VIEW analytics.v_data_quality_daily AS
WITH raw_counts AS (
    SELECT source, snapshot_date,
           count(DISTINCT payload->>'listing_id') AS raw_listings
    FROM raw.listings
    GROUP BY source, snapshot_date
),
stg AS (
    SELECT source, snapshot_date,
           count(*) AS staging_listings,
           count(*) FILTER (WHERE price_vnd IS NULL)     AS price_null,
           count(*) FILTER (WHERE area_m2 IS NULL)       AS area_null,
           count(*) FILTER (WHERE district_norm IS NULL) AS district_null,
           count(*) FILTER (WHERE posted_date IS NULL)   AS posted_date_null
    FROM staging.listings
    GROUP BY source, snapshot_date
),
core_counts AS (
    SELECT ls.source, f.snapshot_date, count(*) AS core_snapshots
    FROM core.fact_listing_snapshot f
    JOIN core.listing_source ls USING (listing_key)
    GROUP BY ls.source, f.snapshot_date
)
SELECT
    r.source,
    r.snapshot_date,
    r.raw_listings,
    COALESCE(s.staging_listings, 0)                          AS staging_listings,
    COALESCE(c.core_snapshots, 0)                            AS core_snapshots,
    r.raw_listings - COALESCE(s.staging_listings, 0)         AS lost_raw_to_staging,
    COALESCE(s.staging_listings, 0) - COALESCE(c.core_snapshots, 0) AS lost_staging_to_core,
    COALESCE(s.price_null, 0)       AS price_null,
    COALESCE(s.area_null, 0)        AS area_null,
    COALESCE(s.district_null, 0)    AS district_null,
    COALESCE(s.posted_date_null, 0) AS posted_date_null,
    round(100.0 * COALESCE(s.price_null, 0)  / NULLIF(s.staging_listings, 0), 1) AS price_null_pct,
    round(100.0 * COALESCE(s.area_null, 0)   / NULLIF(s.staging_listings, 0), 1) AS area_null_pct
FROM raw_counts r
LEFT JOIN stg s          USING (source, snapshot_date)
LEFT JOIN core_counts c  USING (source, snapshot_date);