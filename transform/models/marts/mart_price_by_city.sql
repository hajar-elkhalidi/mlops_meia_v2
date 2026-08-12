select
    city,
    avg_price,
    min_price,
    max_price,
    total_listings
from {{ ref('int_housing_by_city') }}
order by avg_price desc