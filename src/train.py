"""Separate data into train/test, fit only on train, evaluate on held-out test."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["distance_km", "traffic_level", "weather", "restaurant_prep_min", "courier_experience_years"]
TARGET = "delivery_time_min"
CATEGORIES = {"traffic_level": {"Low", "Medium", "High"}, "weather": {"Clear", "Rainy", "Stormy"}}


def validate_frame(frame):
    missing = set(FEATURES + [TARGET]) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame[FEATURES + [TARGET]].isnull().any().any():
        raise ValueError("Dataset contains missing values")
    for column in ["distance_km", "restaurant_prep_min", "courier_experience_years", TARGET]:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"{column} must be numeric")
    if (frame["distance_km"] < 0).any() or (frame[TARGET] <= 0).any():
        raise ValueError("Distance cannot be negative, and delivery time must be positive")
    for column, accepted in CATEGORIES.items():
        if not set(frame[column].unique()).issubset(accepted):
            raise ValueError(f"Unexpected category in {column}")
    if len(frame) < 50:
        raise ValueError("Need at least 50 records for this teaching exercise")


def train(data_path, artifact_dir, max_mae=6.0, use_mlflow=False):
    frame = pd.read_csv(data_path)
    validate_frame(frame)
    # Important: Split BEFORE model/pipeline fitting to avoid test leakage.
    train_frame, test_frame = train_test_split(frame, test_size=0.20, random_state=42)
    numeric = ["distance_km", "restaurant_prep_min", "courier_experience_years"]
    categorical = ["traffic_level", "weather"]
    transform = ColumnTransformer(transformers=[
        ("numbers", "passthrough", numeric),
        ("categories", OneHotEncoder(handle_unknown="ignore"), categorical),
    ])
    model = Pipeline(steps=[
        ("preprocessing", transform),
        ("regressor", RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=1)),
    ])
    model.fit(train_frame[FEATURES], train_frame[TARGET])
    predictions = model.predict(test_frame[FEATURES])
    mae = float(mean_absolute_error(test_frame[TARGET], predictions))
    rmse = float(mean_squared_error(test_frame[TARGET], predictions) ** 0.5)
    r2 = float(r2_score(test_frame[TARGET], predictions))
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # These files help the class SEE which records were used for training vs testing.
    train_frame.to_csv(artifact_dir / "train_rows.csv", index=False)
    test_frame.to_csv(artifact_dir / "test_rows.csv", index=False)
    sample = test_frame.copy()
    sample["predicted_delivery_time_min"] = predictions.round(2)
    sample["absolute_error_min"] = abs(sample[TARGET] - predictions).round(2)
    sample.head(15).to_csv(artifact_dir / "prediction_examples.csv", index=False)
    metadata = {
        "training_rows": int(len(train_frame)),
        "testing_rows": int(len(test_frame)),
        "total_rows": int(len(frame)),
        "random_state": 42,
        "test_fraction": 0.20,
        "mae_minutes": round(mae, 4),
        "rmse_minutes": round(rmse, 4),
        "r2": round(r2, 4),
        "max_allowed_mae_minutes": max_mae,
        "passed_quality_gate": mae <= max_mae,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "data_source": "synthetic_food_delivery_lab",
    }
    (artifact_dir / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    joblib.dump(model, artifact_dir / "model.joblib")
    print(f"TOTAL={len(frame)} | TRAIN={len(train_frame)} (80%) | TEST={len(test_frame)} (20%)")
    print(f"MAE={mae:.3f} min | RMSE={rmse:.3f} min | R2={r2:.3f}")
    print(f"See: {artifact_dir / 'train_rows.csv'} and {artifact_dir / 'test_rows.csv'}")
    if use_mlflow:
        import mlflow
        mlflow.set_tracking_uri((ROOT / "mlruns").as_uri())
        mlflow.set_experiment("food-delivery-training")
        with mlflow.start_run(run_name="random-forest-80-20-split"):
            mlflow.log_params({"test_fraction": 0.20, "seed": 42, "trees": 120})
            mlflow.log_metrics({"mae_minutes": mae, "rmse_minutes": rmse, "r2": r2})
            mlflow.log_artifact(str(artifact_dir / "metrics.json"))
            mlflow.log_artifact(str(artifact_dir / "prediction_examples.csv"))
            mlflow.log_artifact(str(artifact_dir / "model.joblib"))
        print("Experiment logged to local MLflow directory: ./mlruns")
    if mae > max_mae:
        raise SystemExit(f"MODEL REJECTED: MAE {mae:.3f} exceeds {max_mae:.3f} minutes")
    print("MODEL ACCEPTED: quality gate passed")
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "food_delivery.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--max-mae", type=float, default=6.0)
    parser.add_argument("--mlflow", action="store_true", help="Optional local MLflow logging")
    args = parser.parse_args()
    train(args.data, args.output, max_mae=args.max_mae, use_mlflow=args.mlflow)


if __name__ == "__main__":
    main()
