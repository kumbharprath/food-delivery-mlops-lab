# Food Delivery Time Prediction — Day 5 MLOps Teaching Kit

**Start here:** [`docs/01_TRAINER_STEP_BY_STEP.md`](docs/01_TRAINER_STEP_BY_STEP.md) — the full beginner instructor guide.

The project includes a **synthetic 600-row delivery dataset**, reproducible **480/120 train/test split**, scikit-learn training/evaluation, a configurable MAE quality gate, FastAPI inference, Docker container, tests, and GitHub Actions CI/CD for Amazon S3, ECR and EC2 via OIDC + Systems Manager.

## Quick local run (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -m src.train --max-mae 6
python -m uvicorn app.main:app --port 8000
```

Visit `http://127.0.0.1:8000/docs`. Stop Uvicorn before building Docker.

**Use only trusted model artifacts.** All data is synthetic. AWS may incur charges. GitHub deploys automatically on main pushes **only after** AWS OIDC and repository variables are configured; PRs run CI only.

## Documentation

- [`docs/01_TRAINER_STEP_BY_STEP.md`](docs/01_TRAINER_STEP_BY_STEP.md) — complete instructor workflow, explanations of every file, AWS setup and teaching scripts.
- [`docs/02_STUDENT_CHEATSHEET.md`](docs/02_STUDENT_CHEATSHEET.md) — basic commands, concepts and endpoints.
- [`docs/03_TROUBLESHOOTING_AND_CLEANUP.md`](docs/03_TROUBLESHOOTING_AND_CLEANUP.md) — common errors, security and scoped cleanup.
- [`docs/04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md`](docs/04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md) — full file-by-file teaching explanations and real CI/CD creation, AWS setup and verification.
