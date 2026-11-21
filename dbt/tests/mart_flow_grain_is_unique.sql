-- Mỗi (nguồn, ngày) chỉ có một dòng. Dòng trả về = vi phạm.
select source, snapshot_date, count(*) as n_rows
from {{ ref('mart_daily_listing_flow') }}
group by 1, 2
having count(*) > 1