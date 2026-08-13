SELECT 
    listing_id, 
    property_type, 
    surface_m2
FROM {{ ref('stg_housing_listings') }}
WHERE surface_m2 <= 0 
   OR (property_type = 'Appartement' AND surface_m2 < 9)