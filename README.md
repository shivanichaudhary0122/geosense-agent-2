# GeoSense Agent 2.0

An AI-Driven Geospatial Analysis Framework for Urban Planning and Spatial Suitability Assessment

## Project Overview

GeoSense Agent 2.0 is a geospatial analysis project that integrates Geographic Information Systems (GIS), remote sensing, spatial databases, and machine learning to support data-driven urban planning.

The initial study area is Bhubaneswar Municipal Corporation (BMC), Odisha, India.

The project is being developed in multiple phases. Currently, Phase 1, Machine Learning-Based Spatial Suitability Assessment, is available in this repository.

## Phase 1: Geospatial Suitability Analysis

Phase 1 integrates spatial datasets and machine learning to evaluate candidate locations within the Bhubaneswar Municipal Corporation area.

### Key Components

- Preparation of geospatial datasets using GIS and Python.
- Processing of elevation, population, roads, buildings, land use, and hospital locations.
- Generation of candidate locations and extraction of spatial features.
- Development of Random Forest and XGBoost models.
- Evaluation of model performance and feature importance.
- Generation of final suitability results, GIS layers, and maps.

### Technologies Used

- Python
- GeoPandas, Rasterio, Pandas, and NumPy
- Scikit-learn and XGBoost
- SHAP
- PostgreSQL and PostGIS
- QGIS
- Git and GitHub

## Repository Structure

```text
geosense-agent-2/
├── data/
│   └── processed/
│       └── bhubaneswar/
├── outputs/
│   ├── maps/
│   └── reports/
├── src/
│   └── phase1_ml/
├── BMC.qgz
├── .gitignore
└── README.md
```

## Main Outputs

`BMC_Phase1_Suitability.csv` contains the final candidate suitability results in CSV format.

`BMC_Phase1_Suitability.gpkg` contains the GIS-compatible suitability layer.

`BMC_candidate_suitability.png` shows the candidate suitability map.

`model_metrics.csv` contains the machine learning performance metrics.

`feature_importance.csv` contains the model feature importance results.

`shap_feature_importance.csv` contains the SHAP feature importance results.

## Database Configuration

Database credentials are managed through environment variables and should not be committed to GitHub.

Create a local `.env` file in the project root with your database settings.

```env
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
```

Replace the example values with your own database credentials. The `.env` file is excluded from Git tracking.

## Project Status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | GIS-based spatial suitability analysis using machine learning | Completed |
| Phase 2 | Deep learning and satellite imagery analysis | Under development |
| Phase 3 | LiDAR-based analysis | Planned |
| Phase 4 | Agent-based geospatial integration | Planned |

Only Phase 1 files are currently published. Subsequent phases will be added after development and validation.

## Notes

The flood-risk feature used in Phase 1 is an exploratory proxy rather than a calibrated flood-hazard assessment. Suitability predictions should not be interpreted as independently validated planning decisions.

## Author

Shivani Chaudhary

GitHub: [https://github.com/shivanichaudhary0122](https://github.com/shivanichaudhary0122)