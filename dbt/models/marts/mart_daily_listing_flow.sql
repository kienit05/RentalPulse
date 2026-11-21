{{ config(materialized='table') }}

-- Dòng chảy của tin theo nguồn và ngày chụp: đang hoạt động, mới, biến mất, quay lại, đổi giá.
with active as (
    select ls.source, ls.is_simulated, f.snapshot_date, count(*) as active_listings
    from {{ source('core', 'fact_listing_snapshot') }} as f
    join {{ source('core', 'listing_source') }} as ls using (listing_key)
    group by 1, 2, 3
),

events as (
    select
        source,
        event_date as snapshot_date,
        count(*) filter (where event_type = 'initial')     as initial_listings,
        count(*) filter (where event_type = 'first_seen')  as new_listings,
        count(*) filter (where event_type = 'disappeared') as disappeared_listings,
        count(*) filter (where event_type = 'returned')    as returned_listings
    from {{ source('core', 'v_listing_events') }}
    group by 1, 2
),

price_moves as (
    select
        source,
        snapshot_date,
        count(*) filter (where change_type = 'increase') as price_increases,
        count(*) filter (where change_type = 'decrease') as price_decreases
    from {{ source('core', 'v_price_history') }}
    group by 1, 2
)

select
    a.source,
    a.is_simulated,
    a.snapshot_date,
    a.active_listings,
    coalesce(e.initial_listings, 0)     as initial_listings,
    coalesce(e.new_listings, 0)         as new_listings,
    coalesce(e.disappeared_listings, 0) as disappeared_listings,
    coalesce(e.returned_listings, 0)    as returned_listings,
    coalesce(p.price_increases, 0)      as price_increases,
    coalesce(p.price_decreases, 0)      as price_decreases
from active as a
left join events as e using (source, snapshot_date)
left join price_moves as p using (source, snapshot_date)