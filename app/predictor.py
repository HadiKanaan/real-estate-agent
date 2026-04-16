import json
from pathlib import Path

import joblib
import pandas as pd

from app.schemas import HouseFeatures

MODEL_PATH = Path(__file__).parent / "model" / "pipeline.joblib"
STATS_PATH = Path(__file__).parent / "model" / "train_stats.json"

# Load artifacts at module import time so FastAPI startup pays this cost once.
# This keeps request latency low because each request reuses the loaded objects.
pipeline = joblib.load(MODEL_PATH)
with open(STATS_PATH, encoding="utf-8") as f:
    train_stats = json.load(f)

# These names and order must match the training pipeline input contract exactly.
FEATURE_COLUMNS = [
    "GrLivArea",
    "BedroomAbvGr",
    "FullBath",
    "HalfBath",
    "TotalBsmtSF",
    "GarageArea",
    "OverallQual",
    "YearBuilt",
    "Neighborhood",
    "HouseStyle",
]

# These are training-informed defaults used only after user review.
# Stage 1 extraction must keep missing fields as null and report them.
FALLBACKS = {
    "GrLivArea": 1464.0,
    "BedroomAbvGr": 3,
    "FullBath": 2,
    "HalfBath": 0,
    "TotalBsmtSF": 991.0,
    "GarageArea": 480.0,
    "OverallQual": 6,
    "YearBuilt": 1973,
    "Neighborhood": "NAmes",
    "HouseStyle": "1Story",
}


def predict(features: HouseFeatures) -> float:
    """
    Convert validated features to a single-row DataFrame and predict SalePrice.

    Steps:
    1) Convert HouseFeatures to dict
    2) Fill remaining nulls with FALLBACKS
    3) Build DataFrame with exact FEATURE_COLUMNS order
    4) Call pipeline.predict
    5) Return Python float
    """
    data = features.model_dump()

    for col, fallback in FALLBACKS.items():
        if data.get(col) is None:
            data[col] = fallback
            # Keep explicit logs so demos show where defaults were applied.
            print(f"[predictor] Using fallback for {col}: {fallback}")

    df = pd.DataFrame([data])[FEATURE_COLUMNS]
    prediction = pipeline.predict(df)[0]
    return float(prediction)
