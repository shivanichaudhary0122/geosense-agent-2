"""
GeoSense - BMC Phase 1
Complete ML + Suitability Workflow

INPUT
-----
candidate_features_final.gpkg

FEATURES
--------
dist_road_m
dist_hospital_m
pop_dens
elevation_m
flood_risk

OUTPUT
------
1. Cleaned feature dataset
2. Reference suitability score
3. Reference suitability class
4. Random Forest model
5. XGBoost model
6. Model metrics
7. Feature importance
8. SHAP analysis
9. Final candidate suitability score
10. Suitability GeoPackage
11. Suitability CSV
12. Suitability map
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import geopandas as gpd

import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

from xgboost import XGBClassifier

import shap
import joblib


# ============================================================
# 1. PATHS
# ============================================================

ROOT = r"C:\Users\shiva\GeoSense_Agent"

INPUT = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_features_final.gpkg"
)

OUTPUT_DIR = os.path.join(
    ROOT,
    "outputs"
)

MAP_DIR = os.path.join(
    OUTPUT_DIR,
    "maps"
)

REPORT_DIR = os.path.join(
    OUTPUT_DIR,
    "reports"
)

MODEL_DIR = os.path.join(
    ROOT,
    "models",
    "saved"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# 2. SETTINGS
# ============================================================

FEATURES = [
    "dist_road_m",
    "dist_hospital_m",
    "pop_dens",
    "elevation_m",
    "flood_risk"
]

RANDOM_STATE = 42


# ============================================================
# 3. LOAD DATA
# ============================================================

print("\n" + "=" * 75)
print("GEOSENSE - BMC PHASE 1 ML WORKFLOW")
print("=" * 75)

print("\nLoading candidate features...")

gdf = gpd.read_file(
    INPUT,
    layer="candidate_features_final"
)

print("Candidates:", len(gdf))
print("CRS:", gdf.crs)


# ============================================================
# 4. CHECK FEATURES
# ============================================================

missing_features = [
    f for f in FEATURES
    if f not in gdf.columns
]

if missing_features:
    raise RuntimeError(
        f"Missing features: {missing_features}"
    )

print("\nRequired features:")
for f in FEATURES:
    print("  ✓", f)


# ============================================================
# 5. CLEAN DATA
# ============================================================

print("\nCleaning data...")

# Convert to numeric
for f in FEATURES:
    gdf[f] = pd.to_numeric(
        gdf[f],
        errors="coerce"
    )

# Fill missing values with median
for f in FEATURES:

    missing = gdf[f].isna().sum()

    if missing > 0:

        median_value = gdf[f].median()

        print(
            f"  {f}: filling {missing} "
            f"missing value(s) with median "
            f"{median_value:.4f}"
        )

        gdf[f] = gdf[f].fillna(
            median_value
        )

print(
    "\nRemaining missing values:",
    gdf[FEATURES].isna().sum().sum()
)


# ============================================================
# 6. NORMALIZATION
# ============================================================

print("\nNormalizing features...")

X_raw = gdf[FEATURES].copy()


def minmax(series):

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    )


# Accessibility:
# Lower distance = better
road_access = 1 - minmax(
    X_raw["dist_road_m"]
)

hospital_access = 1 - minmax(
    X_raw["dist_hospital_m"]
)

# Population:
# Higher population density = higher demand
population_score = minmax(
    X_raw["pop_dens"]
)

# Elevation:
# Use normalized elevation as a relative factor.
# No absolute elevation threshold is imposed.
elevation_score = minmax(
    X_raw["elevation_m"]
)

# Flood:
# Lower flood risk = better
flood_safety = 1 - minmax(
    X_raw["flood_risk"]
)


# ============================================================
# 7. REFERENCE SUITABILITY SCORE
# ============================================================

print("\nCalculating reference suitability score...")

# Equal weighting because no validated empirical weights
# are currently available.

REFERENCE_WEIGHTS = {
    "road": 0.20,
    "hospital": 0.20,
    "population": 0.20,
    "elevation": 0.20,
    "flood": 0.20
}

reference_score = (
    REFERENCE_WEIGHTS["road"]
    * road_access

    + REFERENCE_WEIGHTS["hospital"]
    * hospital_access

    + REFERENCE_WEIGHTS["population"]
    * population_score

    + REFERENCE_WEIGHTS["elevation"]
    * elevation_score

    + REFERENCE_WEIGHTS["flood"]
    * flood_safety
)

gdf["reference_suitability"] = (
    reference_score
)


# ============================================================
# 8. CREATE REFERENCE TARGET
# ============================================================

# Median split creates a balanced binary reference class.
# This is a pseudo-label, NOT observed ground truth.

threshold = gdf[
    "reference_suitability"
].median()

gdf["reference_class"] = (
    gdf["reference_suitability"]
    >= threshold
).astype(int)

print(
    "\nReference suitability threshold:",
    round(threshold, 4)
)

print("\nReference classes:")

print(
    gdf["reference_class"]
    .value_counts()
    .sort_index()
)


# ============================================================
# 9. PREPARE ML DATA
# ============================================================

X = gdf[FEATURES].copy()

y = gdf["reference_class"].copy()


# ------------------------------------------------------------
# Standardize features
# ------------------------------------------------------------

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)

joblib.dump(
    scaler,
    os.path.join(
        MODEL_DIR,
        "feature_scaler.pkl"
    )
)


# ============================================================
# 10. TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled,
    y,
    test_size=0.20,
    stratify=y,
    random_state=RANDOM_STATE
)

print("\nTraining samples:", len(X_train))
print("Testing samples :", len(X_test))


# ============================================================
# 11. RANDOM FOREST
# ============================================================

print("\n" + "-" * 75)
print("TRAINING RANDOM FOREST")
print("-" * 75)

rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=8,
    min_samples_leaf=3,
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

rf.fit(
    X_train,
    y_train
)

rf_pred = rf.predict(
    X_test
)

rf_prob = rf.predict_proba(
    X_test
)[:, 1]


# ============================================================
# 12. XGBOOST
# ============================================================

print("\n" + "-" * 75)
print("TRAINING XGBOOST")
print("-" * 75)

xgb = XGBClassifier(
    n_estimators=250,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=RANDOM_STATE,
    n_jobs=-1
)

xgb.fit(
    X_train,
    y_train
)

xgb_pred = xgb.predict(
    X_test
)

xgb_prob = xgb.predict_proba(
    X_test
)[:, 1]


# ============================================================
# 13. MODEL EVALUATION
# ============================================================

def evaluate_model(
    name,
    y_true,
    prediction,
    probability
):

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        prediction
    ).ravel()

    return {
        "model": name,
        "accuracy": accuracy_score(
            y_true,
            prediction
        ),
        "precision": precision_score(
            y_true,
            prediction,
            zero_division=0
        ),
        "recall": recall_score(
            y_true,
            prediction,
            zero_division=0
        ),
        "f1": f1_score(
            y_true,
            prediction,
            zero_division=0
        ),
        "roc_auc": roc_auc_score(
            y_true,
            probability
        ),
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }


metrics = pd.DataFrame([
    evaluate_model(
        "Random Forest",
        y_test,
        rf_pred,
        rf_prob
    ),

    evaluate_model(
        "XGBoost",
        y_test,
        xgb_pred,
        xgb_prob
    )
])

print("\nMODEL PERFORMANCE")
print(metrics.to_string(index=False))


metrics.to_csv(
    os.path.join(
        REPORT_DIR,
        "model_metrics.csv"
    ),
    index=False
)


# ============================================================
# 14. SAVE MODELS
# ============================================================

joblib.dump(
    rf,
    os.path.join(
        MODEL_DIR,
        "random_forest_bmc.pkl"
    )
)

joblib.dump(
    xgb,
    os.path.join(
        MODEL_DIR,
        "xgboost_bmc.pkl"
    )
)


# ============================================================
# 15. FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame({
    "feature": FEATURES,

    "random_forest_importance":
        rf.feature_importances_,

    "xgboost_importance":
        xgb.feature_importances_
})

importance.to_csv(
    os.path.join(
        REPORT_DIR,
        "feature_importance.csv"
    ),
    index=False
)

print("\nFEATURE IMPORTANCE")
print(
    importance.to_string(
        index=False
    )
)


# ============================================================
# 16. SHAP ANALYSIS - XGBOOST
# ============================================================

print("\nCalculating SHAP values...")

X_all_scaled = scaler.transform(
    X
)

X_all_df = pd.DataFrame(
    X_all_scaled,
    columns=FEATURES
)

explainer = shap.TreeExplainer(
    xgb
)

shap_values = explainer.shap_values(
    X_all_df
)


# ------------------------------------------------------------
# SHAP summary plot
# ------------------------------------------------------------

plt.figure(
    figsize=(9, 6)
)

shap.summary_plot(
    shap_values,
    X_all_df,
    show=False
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        REPORT_DIR,
        "shap_summary.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 17. SHAP MEAN ABSOLUTE IMPORTANCE
# ============================================================

mean_abs_shap = np.abs(
    shap_values
).mean(axis=0)

shap_importance = pd.DataFrame({
    "feature": FEATURES,
    "mean_abs_shap": mean_abs_shap
})

shap_importance = (
    shap_importance
    .sort_values(
        "mean_abs_shap",
        ascending=False
    )
)

shap_importance.to_csv(
    os.path.join(
        REPORT_DIR,
        "shap_feature_importance.csv"
    ),
    index=False
)

print("\nSHAP IMPORTANCE")
print(
    shap_importance.to_string(
        index=False
    )
)


# ============================================================
# 18. GENERATE FINAL ML SUITABILITY SCORE
# ============================================================

print("\nGenerating final suitability score...")

# XGBoost probability of reference suitability
ml_probability = xgb.predict_proba(
    X_all_scaled
)[:, 1]

# Combine reference score and ML probability.
#
# This is a composite suitability indicator, not
# an independently validated probability.

final_score = (
    0.50 * gdf["reference_suitability"].values
    +
    0.50 * ml_probability
)

gdf["ml_probability"] = (
    ml_probability
)

gdf["final_suitability"] = (
    np.clip(
        final_score,
        0,
        1
    )
)


# ============================================================
# 19. SUITABILITY CLASS
# ============================================================

q1 = gdf[
    "final_suitability"
].quantile(0.25)

q2 = gdf[
    "final_suitability"
].quantile(0.50)

q3 = gdf[
    "final_suitability"
].quantile(0.75)


def classify(value):

    if value <= q1:
        return "Low"

    elif value <= q2:
        return "Moderate"

    elif value <= q3:
        return "High"

    else:
        return "Very High"


gdf["suitability_class"] = (
    gdf["final_suitability"]
    .apply(classify)
)


# ============================================================
# 20. SAVE FINAL GEOPACKAGE
# ============================================================

FINAL_GPKG = os.path.join(
    OUTPUT_DIR,
    "BMC_Phase1_Suitability.gpkg"
)

gdf.to_file(
    FINAL_GPKG,
    layer="BMC_Suitability",
    driver="GPKG"
)


# ============================================================
# 21. SAVE FINAL CSV
# ============================================================

FINAL_CSV = os.path.join(
    OUTPUT_DIR,
    "BMC_Phase1_Suitability.csv"
)

csv_output = gdf.copy()

csv_output = csv_output.drop(
    columns="geometry"
)

csv_output.to_csv(
    FINAL_CSV,
    index=False
)


# ============================================================
# 22. CREATE SUITABILITY MAP
# ============================================================

print("\nCreating suitability map...")

fig, ax = plt.subplots(
    figsize=(10, 10)
)

gdf.plot(
    ax=ax,
    column="final_suitability",
    cmap="viridis",
    markersize=20,
    legend=True
)

ax.set_title(
    "Bhubaneswar Municipal Corporation\n"
    "Candidate Site Suitability"
)

ax.set_xlabel(
    "Easting (m)"
)

ax.set_ylabel(
    "Northing (m)"
)

plt.tight_layout()

MAP_OUTPUT = os.path.join(
    MAP_DIR,
    "BMC_candidate_suitability.png"
)

plt.savefig(
    MAP_OUTPUT,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 23. SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("PHASE 1 COMPLETE")
print("=" * 75)

print("\nCandidates:", len(gdf))

print(
    "\nFinal suitability statistics:"
)

print(
    gdf[
        "final_suitability"
    ].describe()
)

print(
    "\nSuitability classes:"
)

print(
    gdf[
        "suitability_class"
    ].value_counts()
)

print("\nOUTPUTS")
print("-" * 75)

print(
    "Final GeoPackage:"
)

print(
    FINAL_GPKG
)

print(
    "\nFinal CSV:"
)

print(
    FINAL_CSV
)

print(
    "\nModel metrics:"
)

print(
    os.path.join(
        REPORT_DIR,
        "model_metrics.csv"
    )
)

print(
    "\nFeature importance:"
)

print(
    os.path.join(
        REPORT_DIR,
        "feature_importance.csv"
    )
)

print(
    "\nSHAP importance:"
)

print(
    os.path.join(
        REPORT_DIR,
        "shap_feature_importance.csv"
    )
)

print(
    "\nSHAP plot:"
)

print(
    os.path.join(
        REPORT_DIR,
        "shap_summary.png"
    )
)

print(
    "\nSuitability map:"
)

print(
    MAP_OUTPUT
)

print("\n" + "=" * 75)