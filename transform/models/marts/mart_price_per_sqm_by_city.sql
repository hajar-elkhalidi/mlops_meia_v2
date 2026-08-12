select
    city,
    avg_price_per_sqm,
    total_listings
from {{ ref('int_housing_by_city') }}
where avg_price_per_sqm is not null
order by avg_price_per_sqm desc