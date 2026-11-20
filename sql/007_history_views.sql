-- Lịch sử giá: mỗi dòng là một ảnh chụp của một tin, kèm giá lần chụp trước và loại thay đổi.
CREATE OR REPLACE VIEW core.v_price_history AS
SELECT t.*,
       t.price_vnd - t.prev_price_vnd AS change_vnd,
       CASE WHEN t.prev_price_vnd > 0
            THEN round(100.0 * (t.price_vnd - t.prev_price_vnd) / t.prev_price_vnd, 1)
       END AS change_pct,
       CASE
           WHEN t.prev_snapshot_date IS NULL                          THEN 'first'
           WHEN t.price_vnd IS NULL AND t.prev_price_vnd IS NULL      THEN 'no_price'
           WHEN t.prev_price_vnd IS NULL                              THEN 'price_appeared'
           WHEN t.price_vnd IS NULL                                   THEN 'price_removed'
           WHEN t.price_vnd > t.prev_price_vnd                        THEN 'increase'
           WHEN t.price_vnd < t.prev_price_vnd                        THEN 'decrease'
           ELSE 'unchanged'
       END AS change_type
FROM (
    SELECT ls.listing_key, ls.source, ls.listing_id, ls.is_simulated,
           f.snapshot_date, f.price_vnd,
           LAG(f.price_vnd)     OVER w AS prev_price_vnd,
           LAG(f.snapshot_date) OVER w AS prev_snapshot_date
    FROM core.fact_listing_snapshot f
    JOIN core.listing_source ls USING (listing_key)
    WINDOW w AS (PARTITION BY f.listing_key ORDER BY f.snapshot_date)
) t;

-- Vòng đời tin: sự kiện xuất hiện, biến mất, quay lại.
-- "Ngày chụp" của một nguồn là ngày nguồn đó có ít nhất một tin trong Core.
-- Tin vắng mặt ở một ngày chụp của nguồn mình = đã biến mất ngày đó.
-- 'initial' = tin có ở ngày chụp đầu tiên của nguồn (chưa biết lúc nào thật sự xuất hiện).
CREATE OR REPLACE VIEW core.v_listing_events AS
WITH source_dates AS (
    SELECT DISTINCT ls.source, f.snapshot_date
    FROM core.fact_listing_snapshot f
    JOIN core.listing_source ls USING (listing_key)
),
dates AS (
    SELECT source, snapshot_date,
           MIN(snapshot_date) OVER (PARTITION BY source) AS first_source_date
    FROM source_dates
),
grid AS (
    SELECT ls.listing_key, ls.source, ls.listing_id, ls.is_simulated,
           d.snapshot_date, d.first_source_date,
           (f.listing_key IS NOT NULL) AS present
    FROM core.listing_source ls
    JOIN dates d ON d.source = ls.source AND d.snapshot_date >= ls.first_seen_date
    LEFT JOIN core.fact_listing_snapshot f
           ON f.listing_key = ls.listing_key AND f.snapshot_date = d.snapshot_date
),
seq AS (
    SELECT *, LAG(present) OVER (PARTITION BY listing_key ORDER BY snapshot_date) AS prev_present
    FROM grid
)
SELECT listing_key, source, listing_id, is_simulated,
       snapshot_date AS event_date,
       CASE
           WHEN prev_present IS NULL AND snapshot_date = first_source_date THEN 'initial'
           WHEN prev_present IS NULL                                       THEN 'first_seen'
           WHEN prev_present AND NOT present                               THEN 'disappeared'
           ELSE 'returned'
       END AS event_type
FROM seq
WHERE prev_present IS NULL OR prev_present <> present;