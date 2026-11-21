{{ config(severity='warn') }}

-- Trả về các tin có giá ngoài khoảng hợp lý (300.000 - 300.000.000 đ). Không có dòng nào = đạt.
select
    ls.source,
    ls.listing_id,
    f.snapshot_date,
    f.price_vnd
from {{ source('core', 'fact_listing_snapshot') }} as f
join {{ source('core', 'listing_source') }} as ls using (listing_key)
where f.price_vnd is not null
  and (f.price_vnd < 300000 or f.price_vnd > 300000000)