# Rapport — Membre 3 : Data Engineer 1 — Ingestion

## 1. Sources de données

Deux datasets immobiliers sont utilisés. Le premier couvre des annonces immobilières au Maroc (`housing_data.csv`). Le second est spécialisé sur Casablanca (`casa_housing.csv`).

Cette approche permet de conserver une source nationale et une source plus détaillée pour Casablanca.

## 2. Pipeline d'ingestion

Le pipeline Python utilise `dlt` et DuckDB. Chaque fichier CSV est lu avec `csv.DictReader`, puis transformé vers un schéma commun avant d'être envoyé à la ressource `housing_listings`.

Les deux sources sont chargées dans une seule table raw :

`raw_immobilier.housing_listings`

La colonne `source` permet de distinguer les origines.

## 3. Normalisation

Les noms de colonnes diffèrent entre les deux datasets. Le pipeline les harmonise vers un schéma commun :

- `new_price` / `Price` → `price_mad`
- `surface` / `Area` → `surface_m2`
- `chambres` / `Bedrooms` → `bedrooms`
- `salles de bains` / `Bathrooms` → `bathrooms`
- `Type` → `property_type`
- `City` / valeur Casablanca → `city`
- `Nighberd` / `Localisation` → `localisation`

La colonne `desc` du dataset Maroc est volontairement exclue.

Le prix au m² est conservé lorsqu'il existe dans la source Casablanca et calculé pour la source Maroc lorsque le prix et la surface sont disponibles.

## 4. Gestion des identifiants

Les deux fichiers peuvent avoir des numéros de lignes identiques. Une clé globale est donc construite :

- `morocco_1`, `morocco_2`, ...
- `casa_1`, `casa_2`, ...

Cela permet d'utiliser `listing_id` comme clé primaire sans collision lors des opérations `merge`.

## 5. Destination DuckDB

La destination est :

`morocco_housing_ingestion.duckdb`

avec le dataset :

`raw_immobilier`

et la table :

`housing_listings`

Les métadonnées dlt (`_dlt_load_id`, `_dlt_id`) sont conservées automatiquement par dlt.

## 6. Refresh

La ressource utilise :

```python
write_disposition="merge"
primary_key="listing_id"
```

Ainsi, une annonce ayant le même identifiant global peut être mise à jour lors d'un nouveau chargement.

## 7. Validation

Le script `ingestion/check.py` vérifie :

- l'existence de la table ;
- le nombre total d'annonces ;
- le nombre d'annonces par source ;
- les colonnes ;
- un échantillon.

## 8. Interface avec le membre 4

La table `raw_immobilier.housing_listings` constitue l'entrée du travail dbt. Le membre 4 peut créer les modèles `staging`, `intermediate` et `marts` à partir de cette table unifiée.
