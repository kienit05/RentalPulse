-- Sổ ghi nhớ các event đã phát lên Kafka, để không phát lại.
CREATE TABLE IF NOT EXISTS analytics.published_events (
    event_id     TEXT PRIMARY KEY,
    topic        TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);