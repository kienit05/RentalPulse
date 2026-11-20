-- Cột bổ sung cho staging.listings
ALTER TABLE staging.listings ADD COLUMN IF NOT EXISTS district_norm TEXT;
ALTER TABLE staging.listings ADD COLUMN IF NOT EXISTS is_simulated BOOLEAN NOT NULL DEFAULT false;

-- Chuỗi giá ("3400k", "1tr3", "18.4 triệu/tháng", "9,6 triệu", "3.400.000 đ", "3400000") -> số VND.
-- Định dạng lạ hoặc "Thỏa thuận" -> NULL (không đoán).
CREATE OR REPLACE FUNCTION staging.parse_price_vnd(txt TEXT)
RETURNS NUMERIC LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    s TEXT;
    m TEXT[];
BEGIN
    IF txt IS NULL THEN RETURN NULL; END IF;
    s := lower(btrim(txt));
    s := btrim(regexp_replace(s, '\s*/\s*(tháng|thang|th)\s*$', ''));

    m := regexp_match(s, '^(\d+)\s*tr\s*(\d+)?$');            -- 1tr3, 2tr, 1tr35
    IF m IS NOT NULL THEN
        RETURN (m[1]::numeric + COALESCE(('0.' || m[2])::numeric, 0)) * 1000000;
    END IF;

    m := regexp_match(s, '^(\d+(?:[.,]\d+)?)\s*(k|nghìn|triệu|tr|tỷ|tỉ)$');   -- 3400k, 9,6 triệu
    IF m IS NOT NULL THEN
        RETURN replace(m[1], ',', '.')::numeric * CASE m[2]
            WHEN 'k' THEN 1000 WHEN 'nghìn' THEN 1000
            WHEN 'triệu' THEN 1000000 WHEN 'tr' THEN 1000000
            ELSE 1000000000 END;
    END IF;

    m := regexp_match(s, '^(\d{1,3}(?:[.,]\d{3})+)\s*(đ|d|vnd|vnđ)?$');         -- 3.400.000 đ
    IF m IS NOT NULL THEN
        RETURN regexp_replace(m[1], '[.,]', '', 'g')::numeric;
    END IF;

    m := regexp_match(s, '^(\d{6,})\s*(đ|d|vnd|vnđ)?$');                        -- 3400000, 3400000đ
    IF m IS NOT NULL THEN
        RETURN m[1]::numeric;
    END IF;

    RETURN NULL;
END $$;

-- Diện tích ("18m2", "84 m²", "12,5 m²") -> số m2. Lạ -> NULL.
CREATE OR REPLACE FUNCTION staging.parse_area_m2(txt TEXT)
RETURNS NUMERIC LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    m TEXT[];
BEGIN
    IF txt IS NULL THEN RETURN NULL; END IF;
    m := regexp_match(lower(btrim(txt)), '^(\d+(?:[.,]\d+)?)\s*(m2|m²|m)$');
    IF m IS NULL THEN RETURN NULL; END IF;
    RETURN replace(m[1], ',', '.')::numeric;
END $$;

-- Quận: bỏ tiền tố, chuẩn hóa chữ hoa/thường ("THANH XUÂN", "Quận Thanh Xuân", "Q. Thanh Xuân" -> "Thanh Xuân")
CREATE OR REPLACE FUNCTION staging.normalize_district(txt TEXT)
RETURNS TEXT LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    s TEXT;
BEGIN
    IF txt IS NULL OR btrim(txt) = '' THEN RETURN NULL; END IF;
    s := btrim(regexp_replace(txt, '\s+', ' ', 'g'));
    s := regexp_replace(s, '^(quận|huyện|thị xã|thành phố)\s+', '', 'i');   -- Quận Hà Đông
    s := regexp_replace(s, '^(q|h|tx|tp)\.\s*', '', 'i');                   -- Q. Hà Đông, Q.Hà Đông
    RETURN initcap(lower(s));
END $$;