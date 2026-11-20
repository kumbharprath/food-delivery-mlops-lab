from fastapi.testclient import TestClient
from app.main import create_app
from src.generate_data import generate_dataset
from src.train import train


def test_api_prediction_and_validation(tmp_path):
    data = tmp_path / "orders.csv"
    generate_dataset(rows=100).to_csv(data, index=False)
    out = tmp_path / "output"
    train(data, out, max_mae=100)
    app = create_app(model_path=out / "model.joblib", metrics_path=out / "metrics.json")
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        valid = {"distance_km": 5.5, "traffic_level": "High", "weather": "Rainy", "restaurant_prep_min": 12, "courier_experience_years": 2}
        result = client.post("/predict", json=valid)
        assert result.status_code == 200
        assert result.json()["predicted_delivery_time_min"] > 0
        valid["distance_km"] = -10
        assert client.post("/predict", json=valid).status_code == 422
