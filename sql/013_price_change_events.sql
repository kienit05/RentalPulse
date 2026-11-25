-- Event đổi giá đã được consumer đọc từ Kafka (topic listing.price_changes).
CREATE TABLE IF NOT EXISTS analytics.price_change_events (
    event_id           TEXT        PRIMARY KEY,
    source             TEXT        NOT NULL,
    listing_id         TEXT        NOT NULL,
    is_simulated       BOOLEAN     NOT NULL,
    snapshot_date      DATE        NOT NULL,
    prev_snapshot_date DATE        NOT NULL,
    old_price_vnd      NUMERIC     NOT NULL,
    new_price_vnd      NUMERIC     NOT NULL,
    change_vnd         NUMERIC     NOT NULL,
    change_pct         NUMERIC,
    change_type        TEXT        NOT NULL CHECK (change_type IN ('increase', 'decrease')),
    consumed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_price_change_events_date
    ON analytics.price_change_events (snapshot_date);