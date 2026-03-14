
# AutoDataset Platform

AutoDataset is a self-hosted automated dataset engineering platform that constructs machine-learning-ready datasets from existing web, API, and public data sources based on user-defined requirements.

## Quickstart
1. Define the dataset requirements.
2. The platform performs pipeline transformations (validating, cleaning, transformation, etc).
=======
# OPAL-TOOL
OPAL  is a self-hosted data engineering platform that automatically converts raw data into machine-learning-ready datasets using a modular pipeline architecture.

# OPAL AutoDataset Platform

AutoDataset is a dataset engineering platform that automatically transforms raw data into machine-learning-ready datasets using a modular pipeline architecture.

## Features

- Dataset specification engine
- Automated data ingestion
- Schema validation
- Data cleaning
- Feature engineering
- Automated labeling
- Dataset quality analysis
- Dataset artifact generation
- REST API interface

## Architecture

User
 ↓
FastAPI API
 ↓
Workflow Orchestrator
 ↓
Pipeline Modules
 ├─ Ingestion
 ├─ Cleaning
 ├─ Transformation
 ├─ Labeling
 ├─ Quality Analysis
 ↓
Dataset Repository

src/autodataset/
│
├── api              → REST API endpoints
├── orchestrator     → pipeline execution engine
├── ingestion        → raw data ingestion
├── cleaner          → data cleaning
├── transformer      → feature engineering
├── labeling         → automated labeling
├── balancer         → class balancing
├── quality          → dataset validation
├── repository       → dataset storage
└── schema_validator → schema validation
