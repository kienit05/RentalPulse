{{ config(materialized='table') }}

-- Giá thuê theo nguồn, quận, ngày chụp. Batdongsan chỉ có tỉnh nên quận là "Không rõ".
select
    ls.source,
    ls.is_simulated,
    f.snapshot_date,
    coalesce(f.district_norm, 'Không rõ')                                     as district,
    count(*)                                                                  as n_listings,
    count(f.price_vnd)                                                        as n_priced,
    round(avg(f.price_vnd))                                                   as avg_price_vnd,
    round((percentile_cont(0.5) within group (order by f.price_vnd))::numeric) as median_price_vnd,
    round(avg(f.price_vnd / nullif(f.area_m2, 0)))                            as avg_price_per_m2_vnd
from {{ source('core', 'fact_listing_snapshot') }} as f
join {{ source('core', 'listing_source') }} as ls using (listing_key)
group by 1, 2, 3, 4