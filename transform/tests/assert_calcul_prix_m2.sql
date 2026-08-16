-- Vérifie que le calcul du prix au m² est mathématiquement correct (avec une tolérance d'erreur d'arrondi)
SELECT 
    listing_id,
    price_mad,
    surface_m2,
    price_per_sqm_calculated
FROM {{ ref('stg_housing_listings') }}
WHERE surface_m2 > 0 
  AND ABS((price_mad / surface_m2) - price_per_sqm_calculated) > 2