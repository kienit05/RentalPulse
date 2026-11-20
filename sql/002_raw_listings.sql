CREATE TABLE IF NOT EXISTS raw.listings (
    raw_id        BIGSERIAL PRIMARY KEY,
    batch_id      TEXT        NOT NULL,
    source        TEXT        NOT NULL,
    snapshot_date DATE        NOT NULL,
    bronze_key    TEXT        NOT NULL,
    record_no     INTEGER     NOT NULL,
    payload       JSONB       NOT NULL,
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_raw_listings_batch_record UNIQUE (batch_id, record_no)
);

CREATE INDEX IF NOT EXISTS ix_raw_listings_source_date
    ON raw.listings (source, snapshot_date);