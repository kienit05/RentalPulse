CREATE TABLE IF NOT EXISTS analytics.pipeline_runs (
    run_id              TEXT PRIMARY KEY,
    logged_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_rows            BIGINT,
    staging_rows        BIGINT,
    core_snapshots      BIGINT,
    core_listings       BIGINT,
    last_snapshot_date  DATE,
    price_events_total  BIGINT,
    dlq_messages        BIGINT      -- NULL nếu không đọc được Kafka
);

-- Mỗi lần chạy thêm được bao nhiêu so với lần trước
CREATE OR REPLACE VIEW analytics.v_pipeline_runs AS
SELECT
    run_id,
    logged_at,
    last_snapshot_date,
    raw_rows,
    raw_rows       - lag(raw_rows)       OVER w AS raw_added,
    staging_rows   - lag(staging_rows)   OVER w AS staging_added,
    core_snapshots - lag(core_snapshots) OVER w AS core_added,
    price_events_total - lag(price_events_total) OVER w AS price_events_added,
    dlq_messages
FROM analytics.pipeline_runs
WINDOW w AS (ORDER BY logged_at);