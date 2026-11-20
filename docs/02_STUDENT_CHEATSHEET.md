# Student Cheat Sheet — Food Delivery MLOps

Start in the project root in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## What is the dataset?

- Features (X): `distance_km`, `traffic_level`, `weather`, `restaurant_prep_min`, `courier_experience_years`.
- Target (y): `delivery_time_min`.
- 600 synthetic rows → **480 train** + **120 test**.

## Train and inspect

```powershell
python -m src.train --max-mae 6
python -m pytest -q
```

Open `artifacts/train_rows.csv`, `artifacts/test_rows.csv`, `artifacts/prediction_examples.csv`, and `artifacts/metrics.json`.

**MAE** = average absolute difference between predicted and actual delivery minutes; lower is better.

Fail gate on purpose, then recover:

```powershell
python -m src.train --max-mae 0.1
python -m src.train --max-mae 6
```

## Run FastAPI

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs`, `/health`, `/version`; press Ctrl+C to stop before Docker.

## Test one prediction (second PowerShell terminal)

```powershell
$body = @{ distance_km=5.5; traffic_level='High'; weather='Rainy'; restaurant_prep_min=12; courier_experience_years=2 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -ContentType 'application/json' -Body $body
```

## Docker

```powershell
docker build -t food-delivery-api:local .
docker run -d --name food-delivery-local -p 8000:8000 food-delivery-api:local
docker ps
docker logs food-delivery-local
Invoke-RestMethod http://127.0.0.1:8000/health
docker rm -f food-delivery-local
```

## GitHub Actions idea

`Push → pytest → train 80% → test 20% → MAE gate → S3 + ECR → EC2 → health check`

CI on pull requests does **not** deploy. Deployment from `main` needs an approved AWS OIDC role and workshop environment.

## Key terms

- **Train set:** records the model fits on.
- **Test set:** records never used in fitting; measure prediction error.
- **Preprocessing:** convert raw input columns into numeric form for the model.
- **Data leakage:** test information sneaks into model fitting or selection.
- **Model artifact:** saved trained model (`model.joblib`).
- **CI:** tests/validation after code changes.
- **CD:** ships a passing release to an environment.
- **S3:** stores model archives; **ECR:** stores Docker images; **EC2:** runs the container.
