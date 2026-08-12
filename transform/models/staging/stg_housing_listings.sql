with source as (
    select * from {{ source('raw_immobilier', 'housing_listings') }}
)

select
    -- Identifiants
    listing_id,
    source_listing_id,
    source,

    -- Colonnes nettoyées (on vire les prix et surfaces invalides)
    case 
        when price_mad is not null and price_mad > 0 
        then price_mad 
        else null 
    end as price_mad,

    case 
        when surface_m2 is not null and surface_m2 > 0 
        then surface_m2 
        else null 
    end as surface_m2,

    -- On recalcule le prix au m² pour être sûr (plutôt que de prendre la colonne brute)
    case 
        when (price_mad > 0 and surface_m2 > 0) 
        then price_mad / surface_m2 
        else null 
    end as price_per_sqm_calculated,

    -- Autres colonnes utiles
    rooms,
    bedrooms,
    bathrooms,
    floor,
    address,
    localisation,
    elevator,
    terrace,
    parking,
    property_type,
    city,
    other_tags,

    -- Date de chargement (pour le monitoring)
    current_timestamp as loaded_at

from source

-- On filtre pour ne garder que les lignes qui ont au moins un prix et une surface valides
where price_mad is not null 
  and surface_m2 is not null
  and price_mad > 0
  and surface_m2 > 0