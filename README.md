# Morocco Housing — End-to-End MLOps Project

An end-to-end **MLOps project for the Moroccan real-estate market**, covering the complete machine learning lifecycle: data ingestion, transformation, model training, experiment tracking, orchestration, API serving, monitoring, drift detection, testing, containerization, and CI/CD.

The project is designed as a reproducible and automated MLOps pipeline using modern open-source tools.

---

## Project Overview

The objective of this project is to build a machine learning system capable of working with **Moroccan housing data** while applying MLOps best practices.

The pipeline covers:

```text
Raw Housing Data
       │
       ▼
   Data Ingestion
      (dlt)
       │
       ▼
     DuckDB
       │
       ▼
 Data Transformation
      (dbt)
       │
       ▼
 Feature Engineering
       │
       ▼
 Model Training
  (scikit-learn)
       │
       ├──────────► MLflow
       │          Experiment Tracking
       ▼
   Model Artifact
       │
       ▼
 FastAPI Prediction API
       │
       ▼
 Monitoring & Drift Detection
       │
       ▼
 Continuous MLOps Workflow
     (Dagster)
```

---

## Tech Stack

| Component            | Technology                          |
| -------------------- | ----------------------------------- |
| Programming Language | Python                              |
| Data Ingestion       | dlt                                 |
| Database             | DuckDB                              |
| Data Transformation  | dbt                                 |
| Machine Learning     | scikit-learn                        |
| Experiment Tracking  | MLflow                              |
| Orchestration        | Dagster                             |
| API                  | FastAPI                             |
| Data Processing      | Pandas                              |
| Monitoring           | Custom monitoring / drift detection |
| Testing              | Pytest                              |
| Containerization     | Docker / Docker Compose             |
| CI/CD                | GitHub Actions                      |
| Version Control      | Git / GitHub                        |

---

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── CI/CD workflows
│
├── api/
│   └── FastAPI prediction service
│
├── data/
│   └── Housing datasets
│
├── docs/
│   └── Project documentation
│
├── ingestion/
│   └── dlt data ingestion pipeline
│
├── ml/
│   └── Machine learning training and prediction
│
├── monitoring/
│   └── Model monitoring and drift detection
│
├── orchestration/
│   └── Dagster pipelines and assets
│
├── tests/
│   └── Automated tests
│
├── transform/
│   └── dbt transformations
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── .dockerignore
├── morocco_housing_ingestion.duckdb
├── Rapport_OIPI__Mlops-MEIA-v2.pdf
└── Présentation_OIPI__Mlops-MEIA-v2.pdf
```

---

# MLOps Pipeline

## 1. Data Ingestion

The ingestion layer uses **dlt (data load tool)** to load Moroccan housing data into DuckDB.

The ingestion process:

* Reads the source housing data.
* Validates and processes the input.
* Loads the data into DuckDB.
* Creates the raw data layer used by downstream transformations.

Main components:

```text
ingestion/
    └── dlt pipeline
```

The resulting database is:

```text
morocco_housing_ingestion.duckdb
```

---

## 2. Data Storage

**DuckDB** is used as the analytical database for storing the ingested housing data.

The raw data is stored in the database before being transformed.

Example logical structure:

```text
DuckDB
└── raw_immobilier
    └── housing_listings
```

---

## 3. Data Transformation

The transformation layer uses **dbt** to transform raw housing data into datasets suitable for machine learning.

The transformation stage is responsible for:

* Cleaning the data
* Handling missing values
* Selecting relevant columns
* Transforming variables
* Preparing ML-ready data

```text
Raw Data
   │
   ▼
dbt transformations
   │
   ▼
Clean / ML-ready dataset
```

The transformation logic is located in:

```text
transform/
```

---

# Machine Learning

The `ml/` directory contains the machine learning components of the project.

The ML pipeline covers:

1. Loading the transformed dataset
2. Preparing features and target variables
3. Training the model
4. Evaluating the model
5. Saving the trained model
6. Tracking experiments with MLflow

```text
Processed Data
      │
      ▼
Feature Preparation
      │
      ▼
Model Training
      │
      ▼
Evaluation
      │
      ▼
MLflow Tracking
      │
      ▼
Model Artifact
```

---

# MLflow

**MLflow** is used for experiment tracking and model management.

It allows the project to keep track of:

* Experiments
* Model parameters
* Evaluation metrics
* Model artifacts
* Different training runs

This makes model experimentation reproducible and easier to compare.

---

# Dagster Orchestration

**Dagster** is used to orchestrate the different stages of the MLOps pipeline.

The orchestration layer connects the different components:

```text
Ingestion
    ↓
Transformation
    ↓
ML Pipeline
    ↓
Model
    ↓
Monitoring
```

Dagster provides a centralized way to execute and monitor the pipeline.

The orchestration code is located in:

```text
orchestration/
```

---

# FastAPI Prediction Service

The project provides a **FastAPI** service for model inference.

The API loads the trained ML model and exposes prediction endpoints.

Main API component:

```text
api/
```

Typical endpoints include:

```text
GET  /health
POST /predict
```

### Health Check

The health endpoint verifies that the API is running correctly.

### Prediction

The prediction endpoint receives housing information and returns the model prediction.

Example request:

```json
{
  "area": 100,
  "rooms": 3,
  "bedrooms": 2
}
```

> The exact request fields depend on the features used by the final trained model.

---

# Monitoring & Drift Detection

The project includes a persistent monitoring component for the deployed ML system.

The monitoring layer is responsible for observing model/data behavior over time and detecting potential **data drift**.

The monitoring components are located in:

```text
monitoring/
```

The monitoring workflow can be represented as:

```text
Production Data
      │
      ▼
Monitoring
      │
      ▼
Drift Detection
      │
      ├── No significant drift
      │
      └── Drift detected
              │
              ▼
        Investigation /
        Model Retraining
```

This helps identify changes in the incoming data that could affect model performance.

---

# Testing

Automated tests are located in:

```text
tests/
```

The project uses **pytest** for testing.

Tests cover important components of the pipeline to help ensure that changes do not break existing functionality.

Run the tests with:

```bash
pytest
```

---

# Docker

The complete project can be containerized using Docker.

The repository contains:

```text
Dockerfile
docker-compose.yml
```

Docker allows the different services to run in a reproducible environment without requiring every dependency to be installed manually on the host machine.

---

## Run with Docker Compose

Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

Create the environment file:

```bash
cp .env.example .env
```

Then start the services:

```bash
docker compose up --build
```

To run in detached mode:

```bash
docker compose up -d --build
```

To stop the services:

```bash
docker compose down
```

---

# Local Installation

If you want to run the project without Docker:

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate it

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Update the variables according to your environment.

---

# CI/CD

The project uses **GitHub Actions** for continuous integration.

The workflows are located in:

```text
.github/workflows/
```

The CI pipeline helps automatically validate the project when changes are pushed to the repository.

Typical validation includes:

```text
Code changes
     │
     ▼
GitHub Actions
     │
     ├── Install dependencies
     ├── Run tests
     └── Validate project
```

This helps maintain code quality and reduce regressions.

---

# Environment Configuration

Environment-specific configuration is managed using environment variables.

A template is provided in:

```text
.env.example
```

Create your local `.env` file from the template:

```bash
cp .env.example .env
```

Sensitive credentials and environment-specific values should **not** be committed to Git.

---

# Documentation

Additional project documentation is available in:

```text
docs/
```

The project also includes:

* 📄 [Project Report](Rapport_OIPI__Mlops-MEIA-v2.pdf)
* 📊 [Project Presentation](Présentation_OIPI__Mlops-MEIA-v2.pdf)

---

# MLOps Architecture

The complete architecture combines the different technologies into one automated workflow:

```text
                    ┌──────────────────┐
                    │   Housing Data   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │       dlt        │
                    │ Data Ingestion   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │      DuckDB      │
                    │   Raw Storage    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │       dbt        │
                    │ Transformation   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   ML Pipeline    │
                    │   scikit-learn   │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    ▼                  ▼
             ┌─────────────┐    ┌─────────────┐
             │   MLflow    │    │   Dagster   │
             │  Tracking   │    │Orchestration│
             └─────────────┘    └─────────────┘
                    │
                    ▼
             ┌─────────────┐
             │   FastAPI   │
             │  Prediction │
             └──────┬──────┘
                    │
                    ▼
             ┌─────────────┐
             │  Monitoring │
             │    & Drift  │
             └─────────────┘
```

---

# Team

**MLOps / MEIA Project — OIPI**

This project was developed as part of an academic MLOps project, with responsibilities distributed across the team covering:

* Data Engineering
* Data Transformation
* Machine Learning
* MLOps
* API Development
* Monitoring
* Testing
* Documentation

---

# 📄 License

This project was developed for academic purposes as part of the **MLOps / MEIA** project.
