select
    city,
    count(*) as total_listings,
    avg(price_mad) as avg_price,
    avg(price_per_sqm_calculated) as avg_price_per_sqm,
    avg(surface_m2) as avg_surface,
    min(price_mad) as min_price,
    max(price_mad) as max_price
from {{ ref('stg_housing_listings') }}
where city is not null
group by city
order by city