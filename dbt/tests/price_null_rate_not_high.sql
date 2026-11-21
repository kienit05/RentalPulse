{{ config(severity='warn') }}

-- Ngày chụp nào có hơn 25% tin không đọc được giá thì cảnh báo.
select
    source,
    snapshot_date,
    price_null_pct
from {{ source('analytics', 'v_data_quality_daily') }}
where price_null_pct > 25