-- Bảo toàn số tin: active(t) = active(t-1) + mới + quay lại - biến mất. Dòng trả về = vi phạm.
with ordered as (
    select
        source,
        snapshot_date,
        active_listings,
        new_listings,
        returned_listings,
        disappeared_listings,
        lag(active_listings) over (partition by source order by snapshot_date) as prev_active
    from {{ ref('mart_daily_listing_flow') }}
)
select
    source,
    snapshot_date,
    prev_active,
    new_listings,
    returned_listings,
    disappeared_listings,
    active_listings
from ordered
where prev_active is not null
  and active_listings <> prev_active + new_listings + returned_listings - disappeared_listings