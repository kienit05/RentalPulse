-- core.listing_source: mỗi (nguồn, mã tin) đúng một dòng, có khóa thay thế listing_key.
CREATE TABLE IF NOT EXISTS core.listing_source (
    listing_key     BIGSERIAL PRIMARY KEY,
    source          TEXT    NOT NULL,
    listing_id      TEXT    NOT NULL,
    first_seen_date DATE    NOT NULL,
    last_seen_date  DATE    NOT NULL,
    is_simulated    BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT uq_listing_source UNIQUE (source, listing_id),
    CONSTRAINT ck_seen_order CHECK (first_seen_date <= last_seen_date)
);

-- core.fact_listing_snapshot: mỗi tin mỗi ngày chụp đúng một dòng.
-- Đây là nền cho lịch sử giá và vòng đời tin ở Giai đoạn 4.
CREATE TABLE IF NOT EXISTS core.fact_listing_snapshot (
    listing_key        BIGINT  NOT NULL REFERENCES core.listing_source (listing_key),
    snapshot_date      DATE    NOT NULL,
    title              TEXT,
    price_vnd          NUMERIC,
    original_price_vnd NUMERIC,
    area_m2            NUMERIC,
    property_type      TEXT,
    province_raw       TEXT,
    district_norm      TEXT,
    latitude           DOUBLE PRECISION,
    longitude          DOUBLE PRECISION,
    posted_date        DATE,
    batch_id           TEXT    NOT NULL,
    loaded_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (listing_key, snapshot_date),
    CONSTRAINT ck_price_not_negative CHECK (price_vnd IS NULL OR price_vnd >= 0)
);

CREATE INDEX IF NOT EXISTS ix_fact_snapshot_date ON core.fact_listing_snapshot (snapshot_date);