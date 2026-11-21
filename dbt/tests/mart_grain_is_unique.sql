-- Mức chi tiết (grain) của mart: một dòng cho mỗi (nguồn, ngày, quận). Dòng trả về = vi phạm.
select source, snapshot_date, district, count(*) as n_rows
from {{ ref('mart_price_by_district_daily') }}
group by 1, 2, 3
having count(*) > 1