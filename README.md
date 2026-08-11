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
