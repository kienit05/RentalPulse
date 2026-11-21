-- Bất biến: mỗi tin xuất hiện lần đầu đúng một lần.
-- Tổng (initial + first_seen) theo nguồn phải bằng số tin của nguồn trong core.listing_source.
with flow as (
    select source, sum(initial_listings + new_listings) as first_seen_total
    from {{ ref('mart_daily_listing_flow') }}
    group by 1
),
listings as (
    select source, count(*) as listing_total
    from {{ source('core', 'listing_source') }}
    group by 1
)
select source, flow.first_seen_total, listings.listing_total
from flow
full join listings using (source)
where coalesce(flow.first_seen_total, 0) <> coalesce(listings.listing_total, 0)