# Membre 3 — Data Engineer 1 : Ingestion

## Objectif

Mettre en place l'ingestion du dataset Kaggle **Housing Data in Morocco** vers DuckDB avec **dlt**.

Source :
https://www.kaggle.com/datasets/yassinesadiki/housing-data-in-morocco

Dataset fourni : `data/housing_data.csv`
- 4 675 annonces
- 14 colonnes source
- aucun champ manquant dans le fichier fourni

Types observés :
- Appartement : 2 244
- Studio : 1 683
- Villa : 561
- Bureau : 187

Villes observées :
Casablanca, Marrakech, Meknès, Fès, Mohammadia, Dar Bouazza, Tanger.

## Architecture

```text
Kaggle CSV
    |
    v
housing_data.csv
    |
    v
normalisation Python
    |
    v
dlt resource: housing_listings
    |
    | merge / primary_key=listing_id
    v
DuckDB
    |
    v
raw_immobilier.housing_listings
```

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

## Exécution

Depuis la racine du projet :

```bash
python ingestion/pipeline.py
```

Le pipeline :
1. lit le CSV ;
2. normalise les noms de colonnes ;
3. convertit les champs numériques ;
4. ajoute `source=kaggle_morocco_housing` ;
5. charge les données dans DuckDB ;
6. utilise `listing_id` comme clé primaire ;
7. utilise `merge` pour éviter les doublons lors d'un refresh.

Vérification :

```bash
python ingestion/check.py
```

## Mapping des colonnes

| Source Kaggle | Colonne cible |
|---|---|
| Unnamed: 0 | listing_id |
| new_price | price_mad |
| desc | description |
| address | address |
| chambres | bedrooms |
| salles de bains | bathrooms |
| surface | surface_m2 |
| ascenseur | elevator |
| floor | floor |
| terrasse | terrace |
| parking | parking |
| Type | property_type |
| City | city |
| Nighberd | neighborhood |

## Pourquoi `merge` ?

Le pipeline est prévu pour être relancé. `listing_id` identifie l'annonce dans le dataset fourni et permet à dlt de mettre à jour une annonce existante au lieu de créer systématiquement une nouvelle ligne.

## Refresh

Le workflow `.github/workflows/ingestion.yml` lance l'ingestion automatiquement sur `schedule` ou manuellement (`workflow_dispatch`).

> Pour un dataset Kaggle statique, le refresh n'ajoute de nouvelles données que si le fichier source est remplacé par une version actualisée. Le workflow constitue donc la structure d'automatisation ; une récupération automatique depuis Kaggle nécessiterait des credentials/API Kaggle et un téléchargement du nouveau dataset.

## Secrets

Ne jamais committer `.env` ou une clé API.

Si votre équipe automatise le téléchargement Kaggle, les credentials doivent être stockés dans **GitHub Actions Secrets**, pas dans le dépôt.

## Interface avec le membre 4

La sortie d'ingestion est la table :

`raw_immobilier.housing_listings`

Le membre 4 peut ensuite construire avec dbt :

```text
raw_immobilier.housing_listings
        |
        +--> staging
        |
        +--> intermediate
        |
        +--> marts
```

La colonne `source` permet également de conserver la provenance des données.
