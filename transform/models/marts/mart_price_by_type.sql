select
    property_type,
    avg_price,
    avg_price_per_sqm,
    total_listings
from {{ ref('int_housing_by_type') }}
order by avg_price desc