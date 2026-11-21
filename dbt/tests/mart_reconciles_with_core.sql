-- Đối soát: tổng n_listings của mart theo (nguồn, ngày) phải bằng số dòng trong core.fact_listing_snapshot.
with mart as (
    select source, snapshot_date, sum(n_listings) as n
    from {{ ref('mart_price_by_district_daily') }}
    group by 1, 2
),
core_counts as (
    select ls.source, f.snapshot_date, count(*) as n
    from {{ source('core', 'fact_listing_snapshot') }} as f
    join {{ source('core', 'listing_source') }} as ls using (listing_key)
    group by 1, 2
)
select
    source,
    snapshot_date,
    mart.n as mart_n,
    core_counts.n as core_n
from mart
full join core_counts using (source, snapshot_date)
where coalesce(mart.n, 0) <> coalesce(core_counts.n, 0)