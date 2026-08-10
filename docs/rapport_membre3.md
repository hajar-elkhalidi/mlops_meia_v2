# Partie Membre 3 — Data Engineer 1 : Ingestion

## 1. Source de données

Pour l'Observatoire Intelligent des Prix Immobiliers, la source retenue est le dataset Kaggle **Housing Data in Morocco** de Yassine Sadiki.

Le fichier fourni contient 4 675 annonces immobilières et 14 colonnes. Les informations couvrent notamment le prix, la description, l'adresse, le nombre de chambres et salles de bains, la surface, l'ascenseur, l'étage, la terrasse, le parking, le type de bien, la ville et le quartier.

Le dataset contient quatre types de biens principaux : appartement, studio, villa et bureau.

## 2. Pipeline d'ingestion

Le pipeline est développé avec **dlt** et utilise **DuckDB** comme destination analytique.

Le flux est :

**Dataset Kaggle → fichier CSV → normalisation → ressource dlt → DuckDB**

La ressource `housing_listings` lit les lignes du CSV et transforme les noms de colonnes en noms normalisés compatibles avec les traitements SQL et Python.

Exemples :
- `new_price` devient `price_mad`
- `surface` devient `surface_m2`
- `chambres` devient `bedrooms`
- `salles de bains` devient `bathrooms`
- `Type` devient `property_type`
- `City` devient `city`
- `Nighberd` devient `neighborhood`

Une colonne `source` est ajoutée afin de conserver la provenance des données.

## 3. Stratégie d'identification et de chargement

La colonne `Unnamed: 0` du fichier source est utilisée comme identifiant de l'annonce et devient `listing_id`.

Le pipeline dlt utilise :
- `primary_key="listing_id"`
- `write_disposition="merge"`

Ce choix permet de relancer le pipeline sans recréer systématiquement les mêmes annonces.

Les champs numériques sont convertis en entiers lorsque cela est possible, notamment :
- prix ;
- surface ;
- chambres ;
- salles de bains ;
- étage.

## 4. DuckDB

DuckDB constitue la cible de l'ingestion. Les données sont organisées dans le dataset logique `raw_immobilier`.

La table principale produite est :

`raw_immobilier.housing_listings`

Cette table représente la couche **raw/ingestion** qui sera utilisée par le Data Engineer 2 pour la transformation dbt.

## 5. Refresh et credentials

Le projet contient un workflow GitHub Actions permettant de lancer l'ingestion manuellement ou selon une planification.

Pour un dataset Kaggle statique, la planification relance le pipeline à partir du fichier présent dans le dépôt. Pour récupérer automatiquement une nouvelle version publiée sur Kaggle, il faudra ajouter une étape de téléchargement avec les credentials Kaggle stockés dans GitHub Secrets.

Les fichiers `.env` et les credentials ne doivent jamais être commités.

## 6. Interface avec les autres membres

La sortie de mon travail est la table `raw_immobilier.housing_listings`.

Le membre 4 peut utiliser cette table comme source dbt pour créer les couches :
- staging ;
- intermediate ;
- marts.

Le membre 5 pourra ensuite appliquer les contrôles de qualité et documenter la provenance des données.

## 7. Résultat

La partie ingestion fournit donc une chaîne reproductible :

**Kaggle → CSV → dlt → DuckDB → dbt**

Elle prépare une base propre et structurée pour les étapes suivantes du projet : transformation, contrôle qualité, modélisation ML, orchestration et déploiement.
