"""FastAPI model server. A single model is baked into each Docker image."""
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("food_delivery")
ROOT = Path(__file__).resolve().parents[1]


class PredictionRequest(BaseModel):
    distance_km: float = Field(ge=0, le=100)
    traffic_level: Literal["Low", "Medium", "High"]
    weather: Literal["Clear", "Rainy", "Stormy"]
    restaurant_prep_min: float = Field(ge=0, le=180)
    courier_experience_years: float = Field(ge=0, le=60)


class PredictionResponse(BaseModel):
    predicted_delivery_time_min: float
    model_version: str
    latency_ms: float


def create_app(model_path=None, metrics_path=None):
    model_file = Path(model_path) if model_path else Path(os.getenv("MODEL_PATH", str(ROOT / "artifacts" / "model.joblib")))
    metrics_file = Path(metrics_path) if metrics_path else Path(os.getenv("METRICS_PATH", str(ROOT / "artifacts" / "metrics.json")))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not model_file.is_file():
            raise RuntimeError(f"Model missing: {model_file}. Run python -m src.train first.")
        app.state.model = joblib.load(model_file)  # Only load our own trusted artifact.
        app.state.model_version = os.getenv("MODEL_VERSION", "local-demo")
        if metrics_file.is_file():
            app.state.metadata = json.loads(metrics_file.read_text(encoding="utf-8"))
        else:
            app.state.metadata = {}
        log.info("Model loaded version=%s", app.state.model_version)
        yield

    api = FastAPI(title="Food Delivery Time Predictor", version="1.0", lifespan=lifespan)

    @api.get("/health")
    def health():
        return {"status": "ok", "model_loaded": True, "model_version": api.state.model_version}

    @api.get("/version")
    def version():
        return {"model_version": api.state.model_version, "metrics": api.state.metadata}

    @api.post("/predict", response_model=PredictionResponse)
    def predict(request: PredictionRequest):
        start = time.perf_counter()
        try:
            import pandas as pd
            example = pd.DataFrame([request.model_dump()])
            value = float(api.state.model.predict(example)[0])
            latency = round((time.perf_counter() - start) * 1000, 2)
            log.info("Prediction succeeded version=%s latency_ms=%.2f", api.state.model_version, latency)
            return PredictionResponse(predicted_delivery_time_min=round(value, 2), model_version=api.state.model_version, latency_ms=latency)
        except Exception:
            log.exception("Prediction failure")
            raise HTTPException(status_code=500, detail="Prediction failed")

    return api

app = create_app()
