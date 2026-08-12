# Membre 3 — Data Engineer 1 : Ingestion multi-sources

## Objectif

Ingestionner automatiquement deux sources immobilières dans DuckDB avec `dlt` :

1. `data/housing_data.csv` — dataset immobilier Maroc.
2. `data/casa_housing.csv` — dataset immobilier spécifique à Casablanca.

Les deux sources sont normalisées vers une table commune :

`raw_immobilier.housing_listings`

## Architecture

```text
housing_data.csv ───────┐
                        ├──> normalization ──> dlt ──> DuckDB
casa_housing.csv ───────┘                         │
                                                 ▼
                                      raw_immobilier.housing_listings
```

## Schéma unifié

| Colonne | Description |
|---|---|
| `listing_id` | Identifiant global (`morocco_1`, `casa_1`, ...) |
| `source_listing_id` | Identifiant de la ligne dans la source |
| `price_mad` | Prix |
| `surface_m2` | Surface |
| `price_m2` | Prix au m² |
| `rooms` | Nombre de pièces |
| `bedrooms` | Chambres |
| `bathrooms` | Salles de bain |
| `floor` | Étage |
| `address` | Adresse si disponible |
| `localisation` | Quartier/localisation |
| `elevator` | Ascenseur si disponible |
| `terrace` | Terrasse si disponible |
| `parking` | Parking si disponible |
| `other_tags` | Tags complémentaires si disponibles |
| `property_type` | Type de bien |
| `city` | Ville |
| `source` | Source de l'annonce |

La colonne `desc` du dataset Maroc est volontairement ignorée.

## Pourquoi un identifiant global ?

Les deux datasets peuvent avoir des IDs de lignes identiques (`1`, `2`, ...). Pour éviter les collisions avec `merge`, `listing_id` devient :

- `morocco_1`, `morocco_2`, ...
- `casa_1`, `casa_2`, ...

`listing_id` est donc la clé primaire globale de la table.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copier `.env.example` vers `.env` :

```bash
cp .env.example .env
```

Vérifier :

```env
MOROCCO_DATA_FILE=data/housing_data.csv
CASA_DATA_FILE=data/casa_housing.csv
DUCKDB_PATH=morocco_housing_ingestion.duckdb
DLT_DATASET_NAME=raw_immobilier
```

## Exécution

```bash
python ingestion/pipeline.py
```

Puis :

```bash
python ingestion/check.py
```

Le script de contrôle affiche :

- les tables DuckDB ;
- le nombre total d'annonces ;
- le nombre d'annonces par source ;
- les colonnes ;
- un échantillon.

## Refresh

Le pipeline utilise :

```python
write_disposition="merge"
primary_key="listing_id"
```

Un nouveau chargement met donc à jour une annonce ayant le même `listing_id` au lieu de créer un doublon.

Pour un refresh complet avec les fichiers locaux :

```bash
python ingestion/pipeline.py
```

## Note sur les sources

Le pipeline ne scrape pas directement les sites web. Il ingère les deux fichiers CSV fournis dans le projet. Le dataset Casablanca et le dataset Maroc peuvent être remplacés par de nouveaux exports sans changer la structure de la destination.

## Livrable membre 3

Cette implémentation couvre :

- identification de deux sources ;
- ingestion automatisée avec dlt ;
- normalisation multi-sources ;
- chargement dans DuckDB ;
- clé primaire et stratégie de merge ;
- traçabilité de la source ;
- vérification du nombre de lignes ;
- préparation d'une table raw exploitable par dbt.



## 📊 Transformation des données (dbt) — Membre 4

### Objectif
Nettoyer et structurer les données immobilières brutes (issues de l'ingestion) pour les rendre exploitables par le modèle de Machine Learning.

### Architecture dbt
La transformation suit une architecture en couches (médailion) :

1. **Staging** (`stg_housing_listings`) : Nettoyage des données brutes
   - Filtrage des prix et surfaces invalides (valeurs <= 0 ou NULL)
   - Recalcul du prix au m² (`price_per_sqm_calculated`)
   - Standardisation des colonnes

2. **Intermédiaires** (`int_housing_by_city`, `int_housing_by_type`)
   - Agrégations des moyennes, minimums, maximums par ville et par type de bien
   - Calcul du nombre total d'annonces par catégorie

3. **Marts (produits finaux)** :
   - `mart_price_by_city` : Prix moyen, min et max par ville
   - `mart_price_per_sqm_by_city` : Classement des villes par prix au m²
   - `mart_price_by_type` : Prix moyen par type de bien (Appartement, Villa, etc.)

### Qualité des données
17 tests automatisés ont été mis en place via dbt :
- **`not_null`** : Vérifie l'absence de valeurs nulles sur les colonnes critiques (prix, surface, ville, ID).
- **`unique`** : Garantit l'unicité des identifiants et des clés d'agrégation.
- **`accepted_values`** : Contrôle que les types de biens sont valides (Appartement, Villa, Bureau, etc.).

**Résultat** : ✅ 17/17 tests passants.

### Documentation
La documentation complète du pipeline est générée automatiquement avec :
```bash
cd transform
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .  # (utiliser --port 8081 si le port 8080 est occupé)
