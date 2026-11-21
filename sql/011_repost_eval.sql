-- Đo chất lượng bộ ghép tin đăng lại trên dữ liệu mock có đáp án.
-- Đáp án: tin mock đăng lại có tiêu đề kết thúc bằng "(đăng lại)" (ký tự '_' khớp một ký tự bất kỳ).
-- Đo ở mức tin mới (new_listing_id): bộ ghép có nhận ra tin này là đăng lại hay không.
CREATE OR REPLACE VIEW analytics.v_repost_eval AS
WITH truth AS (
    SELECT DISTINCT listing_id
    FROM staging.listings
    WHERE source = 'mock' AND title LIKE '%l_i)'
),
cand AS (
    SELECT DISTINCT new_listing_id AS listing_id
    FROM core.v_repost_candidates
    WHERE source = 'mock'
),
counts AS (
    SELECT (SELECT count(*) FROM cand)                           AS proposed,
           (SELECT count(*) FROM truth)                          AS expected,
           (SELECT count(*) FROM cand JOIN truth USING (listing_id)) AS correct
)
SELECT proposed,
       expected,
       correct,
       round(100.0 * correct / NULLIF(proposed, 0), 1) AS precision_pct,
       round(100.0 * correct / NULLIF(expected, 0), 1) AS recall_pct
FROM counts;