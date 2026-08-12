select
    property_type,
    count(*) as total_listings,
    avg(price_mad) as avg_price,
    avg(price_per_sqm_calculated) as avg_price_per_sqm,
    avg(surface_m2) as avg_surface
from {{ ref('stg_housing_listings') }}
where property_type is not null
group by property_type
order by property_type