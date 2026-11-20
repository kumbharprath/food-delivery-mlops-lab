# Day 5 — Complete Beginner Trainer Guide: Explain **Every File**, Train/Test Data, and Build a Real CI/CD Pipeline

**Project:** Food Delivery Time Prediction | **Audience:** instructor with little MLOps experience | **Workstation:** Windows / VS Code / PowerShell | **AWS:** Mumbai `ap-south-1`, profile `workshop` | **Deployment:** GitHub Actions → Amazon S3 + ECR → Docker on EC2 via Systems Manager (SSM)

> **Start here.** This guide is written against the files inside the accompanying `Day5_FoodDelivery_Practical` folder. All snippets and filenames were checked against that actual source. You do **not** need to write all the code from memory: each source file is provided. You will open it, explain it, run it, and then set up the GitHub Actions deployment. Do not run AWS deletion commands or deploy to an unrelated EC2 instance.

## The answer to “Are we creating the CI/CD pipeline?”

**YES.** The pipeline file is already provided as `.github/workflows/ml-cicd.yml`. You will **create the GitHub repository, include this file in the repository, push the code, configure AWS and GitHub, run the workflow, and verify the running API on EC2**. The CI and CD jobs are real jobs, not just a diagram. No AWS resources have been created by the provided file kit; cloud setup is a hands-on prerequisite.

- **CI:** A code push causes GitHub Actions to install Python, run five automated tests, train using 80% of the data, evaluate on the other 20%, reject an unsuitable model, and publish the successful training files as GitHub Actions artifacts.
- **CD:** Only when CI passes and the event is a push to `main` (or manual run on `main`), the job downloads that **same trained model**, authenticates to AWS using OIDC, archives the model/metrics in S3, builds and pushes a versioned Docker image to ECR, and deploys it to a designated EC2 instance using SSM. The EC2 host then checks `/health`.
- **Not automated in this starter workflow:** Continuous retraining on new real customer data, MLflow logging in GitHub Actions, automated model registry promotion, CloudWatch agent/dashboard setup, or a production-grade zero-downtime rollout. Explain these as future extensions, not as things this kit already implements.

### Suggested teaching order and time (10:00 AM–4:30 PM)

| Time | Show on screen | Main learner outcome |
|---|---|---|
| 10:00–10:20 | Project tree, README, data CSV | Identify project files, features vs target |
| 10:20–11:10 | `src/generate_data.py`, `src/train.py`, generated train/test CSVs | Understand 600 → 480 train / 120 test, leakage and evaluation |
| 11:10–11:25 | Tests + deliberately failed quality gate | Understand automation and why a model can be rejected |
| 11:25–11:40 | Break | |
| 11:40–12:15 | `app/main.py`, `/docs`, `Dockerfile` | Run prediction API and understand a Docker image |
| 12:15–12:45 | `.github/workflows/ml-cicd.yml` line by line | Understand GitHub CI/CD pipeline before triggering it |
| 12:45–1:30 | Lunch | |
| 1:30–2:20 | AWS role, EC2, ECR, S3, SSM readiness and GitHub vars | Prepare secure target for real deployment |
| 2:20–3:00 | Git push → GitHub Actions job → S3 / ECR / EC2 | Run deployment and observe each stage |
| 3:00–3:10 | Break | |
| 3:10–3:50 | Remote API test, controlled failed PR validation, logs | Prove deployment, prove safety gate |
| 3:50–4:30 | Review every key file, Q&A, resource ownership and cleanup | Students can explain and safely operate pipeline |

**Teaching reality:** Cloud role creation and target EC2/SSM setup may take longer than this schedule. Pre-configure AWS/GitHub before class if possible; keep the local training/test lesson as your guaranteed outcome.

## 1. Read this project folder like a book

```text
Day5_FoodDelivery_Practical/
├── README.md                         # First page / quick-start instructions
├── .gitignore                        # Files Git must not track
├── .dockerignore                     # Files Docker must not copy into build context
├── requirements.txt                  # Python packages + pinned versions
├── requirements-mlflow.txt           # Optional MLflow extra packages
├── data/
│   └── food_delivery.csv            # 600 synthetic orders (inputs and actual delivery time)
├── src/
│   ├── __init__.py                  # Marks src as importable Python package
│   ├── generate_data.py             # Creates synthetic orders reproducibly
│   └── train.py                     # Validate → split → train → evaluate → save
├── tests/
│   ├── test_data.py                 # Tests data validity and missing columns
│   ├── test_training.py             # Tests train/test sizes and artifact
│   └── test_api.py                  # Tests API and invalid input
├── app/
│   ├── __init__.py                  # Marks app as importable package
│   └── main.py                      # FastAPI application + model loader
├── artifacts/
│   └── .gitkeep                     # Empty folder marker checked into Git
│   # model.joblib, metrics.json, train_rows.csv, etc. are GENERATED after training
├── Dockerfile                        # Instructions to package API + trained model
├── .github/
│   └── workflows/
│       └── ml-cicd.yml             # The actual GitHub Actions CI/CD pipeline
├── scripts/
│   ├── ssm_deploy.py                # Ask AWS SSM to execute deployment remotely
│   └── ec2_deploy.sh                # Run Docker + health check on EC2
├── aws/
│   ├── github-oidc-trust-policy.template.json       # WHO may use AWS role
│   └── github-deploy-permissions.template.json      # WHAT AWS role can do
└── docs/
    ├── 01_TRAINER_STEP_BY_STEP.md
    ├── 02_STUDENT_CHEATSHEET.md
    ├── 03_TROUBLESHOOTING_AND_CLEANUP.md
    └── 04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md
```

**Important for students:** A *folder* groups files, a `.py` file is Python code, a `.csv` stores tabular data, `.json` stores structured values, `.yml` defines automation settings, `.sh` is a Linux shell script, and `.md` is Markdown documentation. A `Dockerfile` describes how Docker builds the container image.

**Instructor script:** “We will first understand what each file does. Then we will run a model locally. Finally, we will push the same project to GitHub and watch GitHub Actions create a deployment on EC2.”

## 2. First setup: Windows + PowerShell + VS Code

**Install/verify:** Python 3.11, VS Code, Git, Docker Desktop (Linux engine), AWS CLI v2, and a GitHub account. The **training exercise** needs only Python and the project; Docker and AWS are needed later.

1. Extract the ZIP. Open the **inner** `Day5_FoodDelivery_Practical` folder in VS Code. Every command below assumes the terminal is inside the folder containing `requirements.txt`.
2. In VS Code use **Terminal → New Terminal**, select **PowerShell**.
3. Confirm the working directory and tools:

```powershell
Get-Location
Get-ChildItem -Force
py -3.11 --version
git --version
docker version
aws --version
```

4. Create and activate an isolated Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pandas, sklearn, fastapi; print('Libraries are ready')"
```

If the activation script is restricted, use `& .\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `& .\.venv\Scripts\python.exe -m src.train --max-mae 6` instead. Avoid changing system-wide execution policy. If `py -3.11` is missing, install Python 3.11 or, when `python --version` is 3.11, run `python -m venv .venv`.

**Expected result:** `Libraries are ready`. There should be no GitHub/AWS operations yet.

## 3. LIVE LAB A — Training and testing data (start here, before CI/CD)

### Step A1 — Show the raw CSV

In VS Code open `data/food_delivery.csv`. Read its first rows. The **first five columns** are features (inputs) and `delivery_time_min` is the target (answer):

| Column | Type | Student-friendly meaning |
|---|---|---|
| `distance_km` | Number | Distance to customer; e.g. 5.5 km |
| `traffic_level` | Category | `Low`, `Medium`, `High` |
| `weather` | Category | `Clear`, `Rainy`, `Stormy` |
| `restaurant_prep_min` | Number | Restaurant preparation time |
| `courier_experience_years` | Number | Experience of delivery person |
| `delivery_time_min` | Number | Actual time; the value we want the model to predict |

```powershell
python -c "import pandas as pd; d=pd.read_csv('data/food_delivery.csv'); print(d.head(5).to_string(index=False)); print('Total rows:',len(d))"
```

**Expected:** 600 synthetic orders. **Say:** “A model learns how input details relate to actual historical delivery times.” This is teaching data, not real food-delivery company records.

### Step A2 — Explain 80/20 train/test using an exam analogy

In `src/train.py` locate:

```python
train_frame, test_frame = train_test_split(frame, test_size=0.20, random_state=42)
```

- `frame` = all 600 data rows.
- `test_size=0.20` = reserve 20% (120 rows) to test the model.
- Remaining 80% (480 rows) are shown to the model during fitting.
- `random_state=42` makes the random split reproducible.

**Say:** “Training data is like practice questions; test data is the exam. If the model learns from the exam questions first, the score is misleading.”

**Technical accuracy:** Here the test subset is never fitted by the training pipeline. For real model tuning, use a separate validation strategy and keep a final untouched test set; this beginner example uses a fixed acceptance threshold on the holdout for demonstration.

### Step A3 — Run the real training program

```powershell
python -m src.train --max-mae 6
```

**Checked on this supplied dataset:**

```text
TOTAL=600 | TRAIN=480 (80%) | TEST=120 (20%)
MAE=2.560 min | RMSE=3.244 min | R2=0.929
MODEL ACCEPTED: quality gate passed
```

Numbers can vary slightly if environments differ. `6` is the **maximum allowed average absolute error in minutes** for this demo; the measured MAE was approximately `2.56`, so it passed.

### Step A4 — Open these five generated files together

1. `artifacts/train_rows.csv` — the 480 rows used to train the model.
2. `artifacts/test_rows.csv` — the 120 rows held back for testing; not used in fitting.
3. `artifacts/prediction_examples.csv` — 15 test examples with actual and predicted minutes, plus absolute error.
4. `artifacts/metrics.json` — counts, MAE, RMSE, R², maximum allowed MAE and pass/fail.
5. `artifacts/model.joblib` — saved fitted preprocessing plus Random Forest model; **binary**, do not open as readable text.

**Demo:** Point at one record in `prediction_examples.csv`. Compute `absolute_error_min = abs(delivery_time_min - predicted_delivery_time_min)`. Explain: “MAE is the average of these absolute errors across **all 120 test rows**.” The 15-row CSV is just a display sample.

### Step A5 — Show one failure and recovery

```powershell
python -m src.train --max-mae 0.1
```

**Expected:** A nonzero exit with `MODEL REJECTED`. The script still writes local training artifacts; the important behavior is the process exit code, which a CI job treats as failure.

Restore the passing training run before using FastAPI and Docker:

```powershell
python -m src.train --max-mae 6
python -m pytest -q
```

**Expected:** `5 passed` and `MODEL ACCEPTED`. Do not leave a deliberately rejected local model as the supposed “approved” demo.

### Step A6 — Optional broken dataset demonstration

```powershell
python -c "import pandas as pd; d=pd.read_csv('data/food_delivery.csv'); d.drop(columns=['distance_km']).to_csv('data/broken_delivery.csv',index=False)"
python -m src.train --data data/broken_delivery.csv --max-mae 6
```

**Expected:** `ValueError: Missing columns: ['distance_km']`. Explain this is good because validation blocked missing inputs. Cleanup:

```powershell
Remove-Item data/broken_delivery.csv
```

### Step A7 — Optional MLflow recap (not part of default CI/CD)

```powershell
python -m pip install -r requirements-mlflow.txt
python -m src.train --max-mae 6 --mlflow
mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000` and show the recorded run. Stop UI using Ctrl+C. `--mlflow` is an **opt-in local feature**, not enabled in `.github/workflows/ml-cicd.yml`.

## 4. LIVE LAB B — FastAPI and Docker, only after training

### Step B1 — Run the app from the project root

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Open `http://127.0.0.1:8000/docs` for interactive Swagger UI.
- `http://127.0.0.1:8000/health` returns service/model loaded status.
- `http://127.0.0.1:8000/version` returns model version and training metadata.

### Step B2 — Send one prediction from a SECOND PowerShell terminal

```powershell
$body = @{
  distance_km = 5.5
  traffic_level = 'High'
  weather = 'Rainy'
  restaurant_prep_min = 12
  courier_experience_years = 2
} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/predict' -Method Post -ContentType 'application/json' -Body $body
```

**Expected shape:** JSON with `predicted_delivery_time_min`, `model_version`, `latency_ms` (exact predicted number depends on model). Explain the endpoint predicts *minutes*, not an exact arrival clock time. Test invalid distance by setting `distance_km = -10`; FastAPI should return HTTP **422**.

Stop Uvicorn in the FIRST terminal (Ctrl+C).

### Step B3 — Build and run the same app in Docker

Ensure Docker Desktop is running and a passing `artifacts/model.joblib` exists:

```powershell
docker build -t food-delivery-api:local .
docker run -d --name food-delivery-local -p 8000:8000 food-delivery-api:local
docker ps
docker logs food-delivery-local
Invoke-RestMethod 'http://127.0.0.1:8000/health'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/predict' -Method Post -ContentType 'application/json' -Body $body
```

**Expected:** Health succeeds and prediction works inside the container. Cleanup local demonstration:

```powershell
docker rm -f food-delivery-local
```

**Explain:** “Docker makes a repeatable package containing the Python service and the specific approved trained model. The same package can run locally and on EC2.”

## 5. LIVE LAB C — Create and execute the GitHub Actions CI/CD pipeline

### Step C1 — Show the pipeline file in VS Code FIRST

In the Explorer open `.github` → `workflows` → `ml-cicd.yml`. It is already in the kit: **do not type it from scratch unless you're teaching how to create a YAML file**. If you demonstrate creating it manually, make a `.github/workflows` folder inside the project root, create `ml-cicd.yml`, then copy the contents of the supplied file. The filename must end in `.yml` and remain in `.github/workflows/` or GitHub Actions will not discover it.

**Say:** “A GitHub workflow is a recipe. Every time we push code, GitHub reads this file and runs the listed jobs.”

### Step C2 — Read the actual pipeline BEFORE triggering any deployment

Open `.github/workflows/ml-cicd.yml`. The first job is `ml-ci`:

```yaml
jobs:
  ml-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run automated tests
        run: python -m pytest -q
      - name: Train on 80%, test on held-out 20%
        run: python -m src.train --max-mae 6
```

**Explain line by line:** `jobs` groups tasks. `ml-ci` is the CI job. `runs-on` requests a temporary GitHub-hosted Linux machine. `checkout` downloads repository code. `setup-python` installs/selects Python 3.11; `cache: pip` helps speed installs. `run` executes a shell command. `pytest` verifies code behavior. `src.train` performs the real split and training and **exits nonzero** if model quality fails. GitHub then marks the step/job as failed.

The second job is `deploy`:

```yaml
  deploy:
    needs: ml-ci
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    environment: workshop-production
```

**Explain:** `needs: ml-ci` ensures deployment waits for CI **and only proceeds if CI succeeds**. The condition restricts deployments to `main` branch events, excluding PRs. `id-token: write` lets GitHub request an OIDC identity token. `environment: workshop-production` ties this deployment to the named GitHub environment, which matches the IAM trust policy.

**Important:** The workflow tags the image with `${{ github.sha }}`: the exact Git commit identity. Its `actions/upload-artifact` and `actions/download-artifact` steps carry the trained model **from the CI job to the deployment job**. That avoids training a second, different model in the deploy job.

### Step C3 — Verify the AWS identity and choose a dedicated EC2 target

From **local Windows PowerShell**:

```powershell
aws configure list-profiles
aws sts get-caller-identity --profile workshop
aws ec2 describe-instances --region ap-south-1 --profile workshop --query 'Reservations[].Instances[].[InstanceId,State.Name]' --output table
```

Choose a **dedicated workshop instance** and record its exact `i-...` ID. If you already have a suitable server, you may reuse it **only if no unrelated application will be disturbed**. This script replaces a Docker container named `food-delivery-api` and uses host port 8000.

If you need a new EC2 instance, in AWS Console select region **Mumbai (`ap-south-1`)**, launch **Amazon Linux 2023 x86_64**, a small appropriate type such as `t3.micro` (charges may apply), a public subnet, with **port 8000 restricted to your current IPv4 address**. You do not need port 22 when using SSM. Give the instance an IAM instance profile whose EC2 role has `AmazonSSMManagedInstanceCore` and `AmazonEC2ContainerRegistryPullOnly`; attach it via **EC2 → instance → Actions → Security → Modify IAM role**. The instance needs outbound HTTPS to reach SSM and ECR. Note: your GitHub role is a **different role** from the EC2 role.

Enter **Systems Manager → Fleet Manager → Managed nodes** and verify that this EC2 instance is online. Optionally use **Session Manager** to connect and install/start Docker:

```bash
cat /etc/os-release
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo docker version
aws --version
sudo systemctl status amazon-ssm-agent --no-pager
```

**Stop if not online in SSM:** `scripts/ssm_deploy.py` cannot reach an unmanaged instance. Do not bypass this using hard-coded AWS keys or broad IAM permissions.

### Step C4 — Create or verify an ECR repo and a private S3 bucket

On your **Windows** PowerShell (still project root):

```powershell
$Profile = 'workshop'
$Region = 'ap-south-1'
$AccountId = aws sts get-caller-identity --profile $Profile --query Account --output text
$Bucket = "food-delivery-mlops-$AccountId-ap-south-1"
$RepoName = 'food-delivery-api'
Write-Host "AWS account: $AccountId"
Write-Host "S3 bucket: $Bucket"
aws ecr describe-repositories --repository-names $RepoName --region $Region --profile $Profile
```

If ECR reports `RepositoryNotFoundException`, create only this repository:

```powershell
aws ecr create-repository --repository-name $RepoName --image-scanning-configuration scanOnPush=true --region $Region --profile $Profile
```

Check ownership/existence of the bucket:

```powershell
aws s3api head-bucket --bucket $Bucket --profile $Profile
```

If the bucket is truly absent and its name is available (not merely AccessDenied), create and block public access:

```powershell
aws s3api create-bucket --bucket $Bucket --region $Region --profile $Profile --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api put-public-access-block --bucket $Bucket --profile $Profile --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**Say:** “S3 stores the approved model artifact and metrics; ECR stores the Docker image that contains the same model. The EC2 host actually runs that image.” AWS usage may incur costs.

### Step C5 — Configure GitHub OIDC identity provider ONCE in AWS

In AWS Console → IAM → Identity providers, look for `token.actions.githubusercontent.com`. If absent, **Add provider** → OpenID Connect → provider URL `https://token.actions.githubusercontent.com` → audience `sts.amazonaws.com`. Do not create duplicate providers or remove a provider used by other projects.

**Explain:** “GitHub provides a signed identity token to AWS. AWS checks that token against our trust policy and grants short-lived credentials to our deploy job. We never put permanent AWS keys in GitHub.”

### Step C6 — Decide the exact GitHub repository name (BEFORE making the IAM trust policy)

Create an **empty** GitHub repository, e.g. `food-delivery-mlops-lab` (don't auto-create README). Record exact OWNER and REPO names as shown in GitHub URL. The deployment role will be restricted to **that repo AND the `workshop-production` environment**.

Set values in Windows PowerShell. Replace example strings with real values:

```powershell
$Owner = 'YOUR_GITHUB_USERNAME_OR_ORG'
$Repo = 'food-delivery-mlops-lab'
$InstanceId = 'i-REPLACE_WITH_REAL_ID'
```

### Step C7 — Generate the IAM trust and permissions policy files

The two JSON **template** files already exist under `aws/` (explained individually in Section 6). Generate actual JSON **without angle-bracket placeholders**:

```powershell
$Trust = (Get-Content 'aws/github-oidc-trust-policy.template.json' -Raw).Replace('<ACCOUNT_ID>', $AccountId).Replace('<GITHUB_OWNER>', $Owner).Replace('<REPO>', $Repo)
$Policy = (Get-Content 'aws/github-deploy-permissions.template.json' -Raw).Replace('<ACCOUNT_ID>', $AccountId).Replace('<S3_BUCKET>', $Bucket).Replace('<EC2_INSTANCE_ID>', $InstanceId)
$Trust | Set-Content -Encoding utf8 'aws/github-oidc-trust-policy.generated.json'
$Policy | Set-Content -Encoding utf8 'aws/github-deploy-permissions.generated.json'
Get-Content 'aws/github-oidc-trust-policy.generated.json'
Get-Content 'aws/github-deploy-permissions.generated.json'
```

**Check:** The generated trust `sub` matches `repo:$Owner/$Repo:environment:workshop-production`, and all account, bucket and instance placeholders have been replaced. The generated files are ignored by `.gitignore` and should not be committed. If GitHub's actual OIDC subject differs (e.g. an organization-specific immutable subject), configure an equally restrictive matching trust policy; do **not** use `repo:*` or wildcard the account's entire GitHub access.

### Step C8 — Create the GitHub deployment role (not the EC2 instance role)

In Windows PowerShell:

```powershell
aws iam create-role --role-name food-delivery-github-deploy --assume-role-policy-document file://aws/github-oidc-trust-policy.generated.json --profile $Profile
aws iam put-role-policy --role-name food-delivery-github-deploy --policy-name food-delivery-deploy-privileges --policy-document file://aws/github-deploy-permissions.generated.json --profile $Profile
aws iam get-role --role-name food-delivery-github-deploy --profile $Profile
```

If role already exists, inspect before changing anything. Permissions allow ECR publishing, S3 model archival, and SSM command execution **only for the specified workshop target** (with the necessary wider scope for ECR login and SSM invocation reads). The `ssm:SendCommand` permission means the role can execute shell scripts on that EC2 instance; keep the role and instance tightly restricted.

### Step C9 — Configure the GitHub environment and variables before your first main push

In GitHub repository:

1. **Settings → Environments → New environment → `workshop-production`**. If available, require a deployment reviewer; that can help prevent accidental deployments.
2. **Settings → Secrets and variables → Actions → Variables** → add the following **repository variables**:

| GitHub variable name (exact spelling) | Value |
|---|---|
| `AWS_REGION` | `ap-south-1` |
| `AWS_ROLE_ARN` | `arn:aws:iam::YOUR_ACCOUNT_ID:role/food-delivery-github-deploy` (replace number) |
| `ECR_REPOSITORY` | `food-delivery-api` |
| `S3_BUCKET` | Actual bucket name from `$Bucket` |
| `EC2_INSTANCE_ID` | Actual `i-...` from `$InstanceId` |

**No access-key secrets are required.** If variable names are misspelled, deploy can fail even though CI passes. The `workflow_dispatch` manual trigger allows restarting a chosen branch in Actions; run CD only from `main`.

### Step C10 — Add the workflow to Git, push your repository, and WATCH the real pipeline

Before committing, confirm files were extracted correctly:

```powershell
Test-Path '.github/workflows/ml-cicd.yml'
Get-Content '.github/workflows/ml-cicd.yml' -TotalCount 15
git status
```

If this is a fresh project folder without a `.git` directory, run:

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Add food delivery ML training and EC2 CI CD pipeline"
git remote add origin "https://github.com/$Owner/$Repo.git"
git push -u origin main
```

**Review `git status` before commit:** it should include source files and `.github/workflows/ml-cicd.yml`, but **not** `.venv`, generated model artifacts, `.pem` keys, AWS credentials or generated IAM JSON. If Git asks for your identity, set `git config user.name 'Your Name'` and `git config user.email 'your-email@example.com'` to your own information. If a remote already exists, use `git remote -v` instead of adding it again. If GitHub asks for authentication, use its supported browser authentication or credential manager; do not paste passwords into source files.

**GitHub navigation:** GitHub repo → **Actions** tab → **Food Delivery - ML CI and AWS CD** → newest run. Click `ml-ci` first. You should see checkout, Python setup, pip, five passing tests, 600/480/120 training output, and artifact upload. Only after this succeeds does `deploy` begin. Open `deploy` to show OIDC role assumption, S3 upload, ECR build and push, SSM deployment, and EC2 health check.

### Step C11 — Verify the cloud outputs and prediction endpoint

From Windows PowerShell:

```powershell
aws s3 ls "s3://$Bucket/models/" --recursive --profile $Profile
aws ecr describe-images --repository-name food-delivery-api --region $Region --profile $Profile --query 'imageDetails[].imageTags' --output json
```

Get **the current EC2 public IPv4** (it can change after stop/start) from the console. Your **security group must allow TCP 8000 from your current IPv4 address**. Then:

```powershell
$PublicIp = 'REPLACE_WITH_CURRENT_PUBLIC_IPV4'
Invoke-RestMethod "http://${PublicIp}:8000/health"
Invoke-RestMethod "http://${PublicIp}:8000/version"
Invoke-RestMethod -Uri "http://${PublicIp}:8000/predict" -Method Post -ContentType 'application/json' -Body $body
```

**Expected:** `/health` status `ok`; model version is a long Git commit SHA; `/predict` returns estimated minutes and latency. `http://PUBLIC_IP:8000/docs` shows interactive API docs if the port is reachable. **For class only:** direct HTTP on port 8000 is not a secure public production architecture; use private services/HTTPS and managed ingress in production.

### Step C12 — Demonstrate why CI protects deployment

**Safe method: pull request (PR).** Locally on a new branch, edit `.github/workflows/ml-cicd.yml` so the CI training line temporarily says `python -m src.train --max-mae 0.1` (do not change `main`), then push branch and open a PR into `main`:

```powershell
git switch -c demo/fail-ml-gate
# Edit only the CI command in .github/workflows/ml-cicd.yml (6 -> 0.1)
git add '.github/workflows/ml-cicd.yml'
git commit -m "demo: intentionally reject low quality model"
git push -u origin demo/fail-ml-gate
```

In GitHub create a PR from `demo/fail-ml-gate` into `main`. The PR runs `ml-ci`: tests pass, training completes, quality gate **fails**, and the `deploy` job is **skipped**. Do not merge this PR. Close it after explaining. The `main` version still uses `--max-mae 6` and has not been changed. To return to main locally:

```powershell
git switch main
```

**Ask students:** “If CI failed, should we ever push that new model automatically?” Expected answer: **No**.

### Step C13 — Explain rollback with the provided EC2 script

Open `scripts/ec2_deploy.sh`. If the new container fails to pass `/health`, the script stops it and attempts to start the previous image. This is a **simple classroom rollback**, with temporary downtime. It does not guarantee zero-downtime deployments, nor does `/health` prove model accuracy. Do not deliberately damage a shared server to show rollback.

### Step C14 — Safe end-of-class cleanup

Use `docs/03_TROUBLESHOOTING_AND_CLEANUP.md`. Verify resource ownership and IDs before stopping/terminating EC2 or deleting S3/ECR/IAM resources. **Never** run an unscoped AWS delete against an account containing unrelated workshop resources. The EC2 instance, EBS storage, public IPv4, S3 and ECR can incur charges.

## 6. FILE-BY-FILE SOURCE WALKTHROUGH (read with each actual file open in VS Code)

Use these notes when explaining **each and every file**. Line numbers refer to the provided source files, not a different tutorial. Students do not have to memorize every import; point out the **inputs → important operations → outputs**, and demonstrate the corresponding command.

### File 01: `README.md` — how to start the project

**Why:** This is the first file to read when someone receives a project. It contains the name, summary, quick-start commands, reference to the training guide, and AWS caution.

**What is inside:**
- Heading and brief description of the dataset, the 80/20 split, FastAPI, and AWS pipeline.
- A PowerShell sequence: create venv → activate → install requirements → run pytest → train → launch API.
- `/docs` location, security advice, and links to the `.md` documentation.

**Show:** `README.md` at the top-level in VS Code. **Say:** “README is the project instruction manual, not executable code.” **Common mistake:** running a command from the wrong directory; tell students to check `Get-Location`.

### File 02: `.gitignore` — keep temporary and sensitive files out of Git

**Read these patterns:**

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
mlruns/
mlartifacts/
artifacts/*
!artifacts/.gitkeep
.env
aws/*.generated.json
aws/*-generated.json
aws/*-policy.generated.json
```

**Explain each grouping:**
- `.venv/`: installed local packages should not be committed; CI installs its own.
- `__pycache__/`, `.pytest_cache/`, `*.pyc`: temporary Python/test cache files.
- `mlruns/`, `mlartifacts/`: local MLflow run/artifact directories.
- `artifacts/*`: generated models and split CSVs are ignored; CI rebuilds them.
- `!artifacts/.gitkeep`: the empty artifact folder marker is **not** ignored, so the directory is present after clone.
- `.env`: commonly contains environment variables/secrets; never commit credentials.
- `aws/*.generated.json` and similar: locally generated IAM policy files with real account/repo values do not need to be committed.

**Demo:** Run `git status` after training; the generated `artifacts/model.joblib` should not be staged by `git add .`. Gitignore prevents *new untracked* files from being added; it does not remove already-tracked secrets. **Say:** “Git stores reproducible source; not every file on my laptop.”

### File 03: `.dockerignore` — keep the Docker build context small

**Read these patterns:** `.git`, `.github`, `.venv`, `__pycache__`, `.pytest_cache`, `mlruns`, `mlartifacts`, `tests`, `docs`, `aws`, `scripts`, `data`, `*.md`.

**Why:** They tell Docker not to send Git history, local Python packages, credentials-related configs, documentation, tests and training CSVs into the Docker build context.

**Key distinction:** `.gitignore` controls Git commits; `.dockerignore` controls which files are sent to `docker build`. They are not interchangeable. **Important:** `.dockerignore` deliberately does **not** exclude `artifacts/model.joblib` or `artifacts/metrics.json`, because the Dockerfile copies them into the image.

### File 04: `requirements.txt` — exact Python dependencies

| Line/package | What it does here |
|---|---|
| `numpy==2.1.3` | Array/numerical operations under the ML stack |
| `pandas==2.2.3` | Read, check, split and save CSV/DataFrame records |
| `scikit-learn==1.6.1` | Preprocessing, Random Forest, train/test split, evaluation |
| `joblib==1.4.2` | Save and load the fitted model pipeline |
| `fastapi==0.115.12` | Define `/health`, `/version`, `/predict` HTTP endpoints |
| `uvicorn==0.34.2` | Start the ASGI web server for FastAPI |
| `pydantic==2.11.3` | Validate request fields and outgoing prediction responses |
| `httpx==0.28.1` | HTTP client dependency used by FastAPI testing |
| `pytest==8.3.5` | Run automated tests |

**Explain:** `==` asks pip for a specific version; this reduces unplanned differences across machines. This is a workshop dependency list, **not** a security audit or a complete lockfile of transitive dependencies.

**Command:** `python -m pip install -r requirements.txt` means “install everything listed in this file.”

### File 05: `requirements-mlflow.txt` — optional experiment tracking

```text
-r requirements.txt
mlflow>=2.20,<4
```

**Explain:** `-r requirements.txt` first installs the standard app dependencies. `mlflow>=2.20,<4` allows a compatible MLflow version within that interval. The tracking feature is optional because MLflow can add significant installation time. **Do not claim MLflow is automatically run in GitHub Actions**; that workflow calls `python -m src.train --max-mae 6` *without* `--mlflow`.

### File 06: `data/food_delivery.csv` — the teaching dataset

**What is present:** one header row plus 600 synthetic delivery-order rows. The header is:

```csv
distance_km,traffic_level,weather,restaurant_prep_min,courier_experience_years,delivery_time_min
```

**How to read one row:** For example `4.75,High,Rainy,10,6,42.7` means 4.75 km, high traffic, rainy weather, 10 minutes preparation, six years courier experience, and 42.7 minutes actual total delivery time. This row is an example from the bundled CSV; it is **not a live prediction**.

**Why it matters:** The first five values are the inputs `X`; `delivery_time_min` is the answer `y` used during supervised training. During inference you send only the five input features; the actual time is unknown until delivery finishes.

**Command:** `python -c "import pandas as pd; print(pd.read_csv('data/food_delivery.csv').shape)"` → `(600, 6)`.

### File 07: `src/__init__.py` — Python package marker

**Contents:** completely empty. **Why it exists:** makes it clear `src` is an importable package, so commands like `python -m src.train` and test imports like `from src.train import train` work in a conventional project structure. **Say:** “Empty does not mean useless; it helps organize Python modules.”

### File 08: `src/generate_data.py` — synthetic dataset generator

**Walk through the actual code in order:**

| Lines | What is happening | How to explain it |
|---|---|---|
| 1–7 | Docstring, `Path`, `random`, `pandas`; output path `data/food_delivery.csv` | The file knows where to save the CSV |
| 10–11 | `generate_dataset(rows=600, seed=42)` and `random.Random(seed)` | Default 600 rows and repeatable random numbers |
| 12–14 | Create list; define extra delays for traffic/weather | Higher traffic / storms add time in synthetic formula |
| 15–20 | Generate one distance, traffic, weather, preparation time and experience for each order | Each loop makes one fake delivery order |
| 21–23 | Compute `duration` from those features plus random noise | This is the artificial rule behind the training target |
| 24–31 | Store five inputs plus `delivery_time_min` in a dictionary | Each dictionary becomes one CSV row |
| 32 | Return a pandas DataFrame | Convert rows into a table |
| 35–40 | `main()` creates folder, writes CSV, prints preview | Running this module creates the file |
| 43–44 | `if __name__ == '__main__'` | Run `main()` only when launched directly/as a module |

**Explain the formula without mathematics:** “Longer distance, high traffic, bad weather and longer preparation generally increase time. Courier experience slightly decreases it. Random noise makes examples less perfectly predictable.”

**Command:**

```powershell
python -m src.generate_data
```

**Expected:** Prints `Created 600 synthetic orders...` and five preview rows. This command **overwrites the synthetic source CSV** with the same seeded version; do not use it on a real customer dataset.

### File 09: `src/train.py` — THE MOST IMPORTANT ML FILE (full block-by-block explanation)

This file has five tasks: **validate input → split data → fit a pipeline → evaluate on unseen test rows → save artifacts and accept/reject**.

| Actual source lines | Code / concept | Explanation for beginners |
|---|---|---|
| 1–14 | `argparse`, `json`, `Path`, `datetime`, joblib, pandas, sklearn imports | Bring in tools for CLI arguments, dataset reading, preprocessing, training, scoring and saving |
| 16–19 | `ROOT`, `FEATURES`, `TARGET`, `CATEGORIES` | Define project path, five input names, actual output name and allowed categories |
| 22–25 | Detect missing required columns | Fail early if someone removed `distance_km` or another required column |
| 26–30 | Reject missing values/non-numeric number columns | A model cannot safely use arbitrary empty/text values as numbers |
| 31–37 | Reject negative distance/nonpositive target, unknown categories or too few rows | Data quality rules stop known bad training input |
| 40–42 | `train(data_path, artifact_dir, max_mae, use_mlflow)`; read CSV; validate | Start the pipeline with a checked dataset |
| **43–44** | `train_test_split(frame, test_size=0.20, random_state=42)` | **600 orders → 480 training + 120 testing**, repeatably |
| 45–50 | Numeric columns passthrough; categorical columns encoded with `OneHotEncoder` | A model expects numeric features; categories such as `High` must be converted into numeric indicator columns |
| 51–54 | scikit-learn `Pipeline`; `RandomForestRegressor(n_estimators=120, ...)` | Package preprocessing + a 120-tree regression model as one fitted unit |
| **55** | `model.fit(train_frame[FEATURES], train_frame[TARGET])` | Learn *only from the training rows* (no fitting on held-out test rows) |
| **56** | `model.predict(test_frame[FEATURES])` | Predict the answers for the 120 unseen test orders |
| 57–59 | `mean_absolute_error`, RMSE, `r2_score` | Calculate performance by comparing predicted versus real target values on the test set |
| 60–68 | `artifacts/` folder; save training set, test set, prediction preview, per-row errors | Create visible evidence students can open and compare |
| 69–83 | Construct `metadata` dictionary | Record row counts, test percentage, MAE, RMSE, R², threshold, timestamp, features and data source |
| 84–85 | Write `metrics.json` and `model.joblib` | Save human-readable evaluation record + binary fitted model/pipeline |
| 86–88 | Print train/test sizes and metrics | Easy terminal feedback for the classroom |
| 89–99 | Optional MLflow tracking when `--mlflow` is used | Log one experiment locally; the default CI run does **not** enable it |
| **100–102** | If MAE exceeds allowed maximum, raise `SystemExit` | Reject poor model with nonzero exit so CI cannot deploy it |
| 106–117 | Parse CLI flags and call `train(...)` | Makes `python -m src.train --max-mae 6` work |

**Important fragments to highlight:**

```python
train_frame, test_frame = train_test_split(frame, test_size=0.20, random_state=42)
model.fit(train_frame[FEATURES], train_frame[TARGET])
predictions = model.predict(test_frame[FEATURES])
mae = float(mean_absolute_error(test_frame[TARGET], predictions))
if mae > max_mae:
    raise SystemExit(f"MODEL REJECTED: MAE {mae:.3f} exceeds {max_mae:.3f} minutes")
```

**Say this slowly:** “Split FIRST, train on 480, test on 120, calculate how wrong predictions were, and allow the model to proceed only if it satisfies the quality rule.”

**Clarify terms:** A *regressor* predicts a number (minutes). Random Forest is a group of decision trees whose predictions are combined. `OneHotEncoder` converts `Low`, `Medium`, `High` into numeric indicator columns. `Pipeline` ensures the same preprocessing is applied during training and when FastAPI later receives new requests. **Only load trusted `joblib` models**, because the format uses Python pickle-related deserialization.

**Why not use MAE from training rows?** The model has already seen them. Held-out test metrics give a more realistic early estimate of performance on new orders.

**Subtle limitation:** The script saves model files before checking/rejecting MAE. That is deliberate for debugging; it does **not** deploy them when CI fails. Do not tell students that a rejected `model.joblib` file is an approved production release.

### File 10: `tests/test_data.py` — test dataset rules

**What it contains:** `pytest`, `generate_dataset`, `validate_frame` imports and three tests:

1. `test_generated_dataset_has_required_fields`: generate 100 rows, validate and confirm 100 rows/positive target.
2. `test_missing_feature_is_rejected`: remove `distance_km`, then assert validation raises `ValueError` containing `Missing columns`.
3. `test_negative_distance_is_rejected`: set one distance to -3, assert validation raises `ValueError`.

**Explain:** “Tests are intentionally trying both good and bad input. We want correct data to pass and incorrect data to be stopped.” Command: `python -m pytest -q tests/test_data.py`.

### File 11: `tests/test_training.py` — verify the split and model artifact

**What it contains:** One `pytest` test creates 100 synthetic rows in a temporary folder (`tmp_path`), calls the real `train(...)` function with a generous quality threshold, checks `training_rows == 80`, `testing_rows == 20`, reads generated CSVs and asserts `model.joblib` exists.

**Why 100 instead of 600?** Short, isolated test data makes tests quick and reliable; it checks the same 80/20 behavior as the full 600-row lab. `tmp_path` prevents tests from overwriting your classroom demo files in `artifacts/`.

**Run:** `python -m pytest -q tests/test_training.py`.

### File 12: `tests/test_api.py` — verify API behavior without a cloud server

**What it contains:** One test generates 100 records, trains in a temporary folder, calls `create_app(...)` using that temporary model, opens `TestClient`, checks `/health` is OK, posts a complete valid JSON request to `/predict` and checks a positive prediction, then replaces distance with `-10` and expects **HTTP 422**.

**Explain:** “HTTP 200 means the prediction request worked; HTTP 422 means FastAPI/Pydantic rejected invalid input correctly.” No EC2 instance is required to test this. **Run:** `python -m pytest -q tests/test_api.py`.

### File 13: `app/__init__.py` — importable API folder marker

**Contents:** Empty file. It makes `app` a conventional Python package so `app.main:app` can be imported by Uvicorn and tests. **Say:** “It is not the API logic; `main.py` is.”

### File 14: `app/main.py` — FastAPI service explained in source order

| Actual source lines | What is inside | Classroom explanation |
|---|---|---|
| 1–16 | Imports (`json`, `logging`, `os`, `time`, `Path`, FastAPI, Pydantic, joblib) and logger setup | Libraries needed to serve HTTP requests, load model, record events |
| 19–24 | `PredictionRequest` schema: five feature names and constraints | What clients **must send**; distance 0–100, recognized traffic/weather values, sensible numeric ranges |
| 27–30 | `PredictionResponse` schema | App returns predicted minutes, model version and latency |
| 33–35 | `create_app(model_path, metrics_path)` resolves file locations (can use env vars `MODEL_PATH`, `METRICS_PATH`) | Locate the approved model file and evaluation metadata |
| 37–48 | Startup `lifespan`: check model exists; `joblib.load`; set `MODEL_VERSION`; load metadata; log startup | Model is loaded **once when the API starts**, not retrained for each request |
| 50 | Create FastAPI application | Create HTTP service |
| 52–54 | `GET /health` | Quick endpoint reporting app/model load status |
| 56–58 | `GET /version` | Reveal model version and associated training metrics |
| 60–72 | `POST /predict`: validate request, build DataFrame, call model.predict, measure elapsed ms, log result, catch errors | This is how the service produces a prediction for new delivery details |
| 74–77 | Return created app, then instantiate `app = create_app()` | Allows Uvicorn to import `app.main:app` |

**Example accepted request:**

```json
{
  "distance_km": 5.5,
  "traffic_level": "High",
  "weather": "Rainy",
  "restaurant_prep_min": 12,
  "courier_experience_years": 2
}
```

**Main lesson:** In production the user does **not** send `delivery_time_min` because that is the unknown value being predicted. The model artifact contains preprocessing learned during training, so the API accepts the same five feature names.

**Limitation:** `/health` checks that the model loaded and an endpoint is responding; it cannot prove prediction quality is still good. The app logs version/latency but does **not** currently export Prometheus metrics or automatically send logs to CloudWatch.

### File 15: `Dockerfile` — package model and API into one image

**Open it and explain literally every instruction:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY artifacts/model.joblib ./artifacts/model.joblib
COPY artifacts/metrics.json ./artifacts/metrics.json
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Instruction | Meaning |
|---|---|
| `FROM` | Start with Python 3.11 Linux image |
| `WORKDIR` | Create/select `/app` as working folder inside container |
| `ENV` | Avoid writing Python bytecode, show logs immediately |
| `COPY requirements.txt` | Make dependency list available inside image |
| `RUN pip install...` | Install dependencies during image build |
| `COPY app` | Add FastAPI source code |
| `COPY artifacts/...` | Add **approved fitted model** and its metrics |
| `EXPOSE 8000` | Document the container's application port; does **not** open a host firewall |
| `HEALTHCHECK` | Run an internal HTTP health test periodically |
| `CMD` | Start Uvicorn on 0.0.0.0:8000 inside container |

**Explain image vs container:** An **image** is the packaged recipe/result. A **container** is a running instance of that image. `docker build` makes an image; `docker run` starts a container. **Important:** `COPY artifacts/model.joblib` will fail if training did not run or CI did not download the model before the build.

### File 16: `artifacts/.gitkeep` — preserve a generated-output directory

**Contents:** Empty file. Git cannot record an otherwise empty directory; `.gitkeep` stays tracked because `.gitignore` allows it. The workflow later writes `artifacts/model.joblib` and other output files into this folder. `.gitkeep` is a convention, not a special command.

### Generated file A: `artifacts/train_rows.csv`

**Created by** `src/train.py`, not hand-written. **Contains** 480 training rows and original 6 columns. **Use it** to prove the model trained on only 80% of the dataset.

### Generated file B: `artifacts/test_rows.csv`

**Created by** `src/train.py`. **Contains** 120 held-out rows with the original 6 columns. **Use it** to explain how an unbiased exam helps estimate generalization (within the limits of synthetic data).

### Generated file C: `artifacts/prediction_examples.csv`

**Created by** `src/train.py`. **Contains** 15 illustrative test rows plus `predicted_delivery_time_min` and `absolute_error_min`. **Use it** to compare actual and predicted numbers. This is **not the full 120-row evaluation table**, only a display preview.

### Generated file D: `artifacts/metrics.json`

**Created by** `src/train.py`. **Contains** metadata keys:

- `training_rows`, `testing_rows`, `total_rows` — dataset size proof.
- `random_state`, `test_fraction` — how splitting happened.
- `mae_minutes`, `rmse_minutes`, `r2` — held-out evaluation scores.
- `max_allowed_mae_minutes`, `passed_quality_gate` — release decision.
- `trained_at_utc`, `features`, `data_source` — basic traceability.

**Explain:** JSON is text in **key: value** form, easy for both humans and programs to read. The CI job uploads it as evidence, and the CD job archives it to S3.

### Generated file E: `artifacts/model.joblib`

**Created by** `joblib.dump(model, ...)`. **Contains** the **fitted** scikit-learn preprocessing-and-regressor pipeline. It is a binary file, not a CSV, image or source code. FastAPI uses `joblib.load` to get the saved model; Docker includes the same file. Only use trusted artifacts; unsafe `joblib` loading can execute code.

### File 17: `.github/workflows/ml-cicd.yml` — ALL stages of the REAL pipeline

Read the file from top to bottom. It is the most important **Day 5 MLOps file** after `src/train.py`.

| Actual lines | YAML element | Explain in plain English |
|---|---|---|
| 1 | `name` | Friendly workflow name displayed in GitHub Actions |
| 2–7 | `on` + `push`, `pull_request`, `workflow_dispatch` | Run on `main` pushes and PRs; support manual run |
| 9–10 | Default `contents: read` | Allow basic source checkout but not repository writes |
| 12–15 | Job `ml-ci`, Ubuntu runner | CI operates on GitHub's temporary Linux server |
| 17–21 | Checkout, setup Python 3.11, pip cache | Make source and Python available |
| 22–25 | Install requirements and run `pytest` | Software/data/ML tests run automatically |
| 26–27 | Run `python -m src.train --max-mae 6` | Full 80/20 training, evaluation and release check |
| 28–38 | `upload-artifact@v4` + five paths; seven-day retention | Save model, metrics, train/test sets, prediction preview **only when preceding steps succeed** |
| **40–43** | `deploy`; `needs: ml-ci`; PR/branch condition | No deployment from PRs, and never deploy after a failed CI job |
| 44–48 | Ubuntu runner, OIDC `id-token: write`, deployment environment | Permit temporary AWS identity token, tie deployment to workshop-production |
| 49–54 | AWS region, ECR repo, S3 bucket, instance ID, Git SHA | Variables identifying exactly where to release; SHA identifies release |
| 56–64 | Checkout, Python, **download-artifact** | Retrieve the exact trained model that CI just approved |
| **65–69** | `configure-aws-credentials@v4` with OIDC role | Assume AWS role for short-lived credentials without permanent access keys |
| 70–74 | Construct `ECR_URI` and write it to `$GITHUB_ENV` | Define registry/repo address for later steps |
| 75–78 | `aws s3 cp ...` model and metrics | Archive approved model and metadata under the commit SHA prefix |
| 79–84 | Docker registry login, build, push | Package that downloaded model with FastAPI, tag image with SHA, publish to ECR |
| 85–88 | Install boto3 and run `scripts/ssm_deploy.py` | Tell preselected EC2 to pull and run the approved image |

**Explain special syntax:**

- `- uses: owner/action@version` means “run a reusable GitHub Action.”
- `- name: ...` is a label for a step; `run: ...` is a terminal command.
- `${{ vars.AWS_REGION }}` reads a **GitHub Actions repository variable**, not a Python variable.
- `${{ github.sha }}` is the source commit hash; it becomes the Docker image tag and S3 archive prefix.
- `env:` provides values to steps via environment variables.
- `path: |` means a multi-line list of artifact file paths.
- `needs: ml-ci` is the important safety dependency: don't deploy if CI failed.
- `if:` controls whether GitHub runs the deployment at all.
- `environment: workshop-production` identifies a deployment environment and can support approval controls.

**Why artifact download matters:** `ml-ci` and `deploy` run on *separate temporary GitHub machines*. They do not share their filesystem by default. `upload-artifact` transfers output out of CI and `download-artifact` retrieves it for the deploy job. This is why the Docker image contains **the model that passed the test**, rather than a newly trained unrelated model.

**Explain the exact stage order:**

```text
PUSH TO main
   |
   v
[CI] checkout → install → pytest → train (480/120) → MAE gate
   |    if failed: job RED, deployment never begins
   |    if passed: upload model/metrics CSV artifact
   v
[CD] download model → assume AWS OIDC role → S3 audit copy
   → docker build → ECR push → SSM Run Command
   → EC2 docker pull/run → GET /health → success or failure
```

**Caution:** PRs do run the `ml-ci` job, but the `deploy` job is skipped. An automatic push to `main` will try to deploy **once the workflow is present**; preconfigure AWS and GitHub variables before the first push if you want an all-green run.

### File 18: `aws/github-oidc-trust-policy.template.json` — WHO can assume the deploy role

**Read the JSON fields in order:**

- `Version: 2012-10-17`: AWS IAM policy language identifier, not the creation date.
- `Effect: Allow`: permit the listed AWS Security Token Service action under the conditions.
- `Principal.Federated`: AWS OIDC provider ARN `arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com`.
- `Action: sts:AssumeRoleWithWebIdentity`: use GitHub's identity token to obtain short-lived role credentials.
- `Condition.StringEquals...aud = sts.amazonaws.com`: token audience must be for AWS STS.
- `Condition.StringLike...sub = repo:<GITHUB_OWNER>/<REPO>:environment:workshop-production`: token subject must match the intended repository/environment.

**Placeholder explanation:** Text inside `<...>` must be replaced with *your own* account ID, GitHub owner and repo name before sending to AWS. **Teach:** “Trust policy asks *who is allowed to enter*.”

### File 19: `aws/github-deploy-permissions.template.json` — WHAT the deploy role is allowed to do

**Explain each IAM action group:**

| IAM action or resource | Why the GitHub deploy job needs it |
|---|---|
| `ecr:GetAuthorizationToken` on `*` | Authenticate Docker to ECR (ECR login action requires the wildcard resource) |
| ECR repository actions on `...:repository/food-delivery-api` | Check/prepare/push layers and push the versioned image to just this repository |
| `s3:PutObject` on `arn:aws:s3:::<S3_BUCKET>/models/*` | Save approved `model.joblib` and `metrics.json` under versioned S3 keys |
| `ssm:SendCommand` on AWS-RunShellScript document + chosen EC2 instance ARN | Tell **that EC2 instance** to perform deployment commands |
| `ssm:GetCommandInvocation` | Read command status, output and errors back into GitHub Actions |

**Explain:** “Permission policy asks *what actions are allowed after the identity has entered*.” This template uses hard-coded `ap-south-1` and ECR repo name, so update it if you change those. ECR login/resource ARNs have AWS-required wildcard nuances; do not make the role an AWS Administrator just to get the lab working.

**Different roles, different jobs:** The **GitHub deploy role** publishes to ECR/S3 and sends SSM commands. The **EC2 instance role** uses `AmazonSSMManagedInstanceCore` to receive commands and `AmazonEC2ContainerRegistryPullOnly` to pull images. The GitHub role is not attached to the EC2 instance.

### File 20: `scripts/ssm_deploy.py` — the bridge from GitHub Actions to EC2

**Inputs:** `AWS_REGION`, `EC2_INSTANCE_ID`, `ECR_URI`, `IMAGE_TAG` are set as environment variables by GitHub workflow. It uses temporary AWS credentials already configured by OIDC.

| Actual lines | What happens | Why it matters |
|---|---|---|
| 1–7 | Imports `os`, `shlex`, `sys`, `time`, `Path`, `boto3` | Read env vars, safely quote shell values, communicate with AWS |
| 9–12 | Verify required environment variables exist | Fail with a clear error if GitHub variables are missing |
| 13–15 | Read `scripts/ec2_deploy.sh`, prefix exported AWS values | Build the complete Linux script to execute remotely |
| 16–23 | `boto3.client('ssm')`, `send_command` with `AWS-RunShellScript` and chosen instance | Send deployment instructions via AWS Systems Manager, **without SSH** |
| 24–25 | Extract and print command ID | A unique handle for the remote operation |
| 26–31 | Poll command invocation up to 75 times, every eight seconds | Wait for EC2 to execute the command and return status |
| 32–39 | Show Success/Failed/TimedOut, print stdout/stderr; exit nonzero on failure | The GitHub deployment job displays actual EC2 outcomes |
| 41–42 | End with timeout error if no terminal result | Avoid silently reporting success when command never completed |

**Explain:** This script does **not itself run Docker on the GitHub runner**; it asks AWS to run the Bash deployment script *on EC2*. `boto3` is the AWS SDK for Python. `SendCommand` is different from `ssh user@server`.

### File 21: `scripts/ec2_deploy.sh` — what Linux executes on EC2

**Inputs:** AWS region, ECR image URI, immutable tag injected by `ssm_deploy.py`.

| Actual lines | What happens | What to say to the class |
|---|---|---|
| 1–2 | Bash script + `set -euo pipefail` | Stop on errors and missing variables rather than hiding failures |
| 3–6 | Require `ECR_URI`, `IMAGE_TAG`, `AWS_REGION`; combine into image address | Choose exactly the image GitHub pushed to ECR |
| 7–8 | Extract registry and set container name `food-delivery-api` | Docker needs correct registry and running container name |
| 10–12 | Get temporary ECR login, pull new image | EC2 downloads the image using its **own IAM instance role** |
| 13–16 | Remember previous container image; remove previous container if present | Make room for the new container on port 8000 |
| 17–18 | `docker run -d --restart unless-stopped -p 8000:8000 -e MODEL_VERSION=...` | Start new API and record Git commit SHA in response metadata |
| 20–27 | Retry `curl /health` up to 20 times, sleeping 3 sec between attempts | Wait for service startup and verify HTTP health |
| 28–36 | If health fails: show logs, remove bad container, try old image, exit 1 | Basic **rollback**, then mark GitHub deployment failed |
| 37–38 | Print successful image and health response | Evidence that EC2 is serving after rollout |

**Important limitations to explain accurately:**
- This is **simple replace-in-place deployment**, so brief downtime can occur.
- Rollback only runs after a failed **health check** and only if the previous Docker image is still available. It does not restore an entire AWS infrastructure state.
- On automatic rollback the previous container is restarted without explicitly restoring its original `MODEL_VERSION` environment variable, so `/version` may fall back to `local-demo`. This is a limitation of the supplied script, not an example of complete production rollback traceability.
- `/health` does not catch subtly bad predictions or data drift. That needs extra monitoring and quality checks.
- A code/script error that exits *before* the health-check section may not execute the rollback branch; treat this as a demonstration, not a complete production deployment controller.

### File 22: `docs/01_TRAINER_STEP_BY_STEP.md` — first trainer practical guide

**What is inside:** time plan, Windows setup, dataset inspection, train/test demonstration, optional MLflow, FastAPI/Docker, AWS OIDC/SSM/ECR/S3, GitHub Actions setup, test, failure, rollback, FAQ, cleanup and official reference links. It is the **hands-on command sequence**.

**How to use it:** Keep it open while doing each command; use this **04** guide in the other tab to explain **why every source file exists and what each block means**.

### File 23: `docs/02_STUDENT_CHEATSHEET.md` — short learner handout

**What is inside:** Python installation commands, features/target, train/test commands, quality gate failure/restore, FastAPI request, Docker commands, one-line CI/CD summary and definitions. Students can use it after your detailed explanation. **It is not a replacement for the instructor guide.**

### File 24: `docs/03_TROUBLESHOOTING_AND_CLEANUP.md` — fix errors and leave AWS tidy

**What is inside:** table of frequent local/AWS/GitHub errors, explanation of failed OIDC, SSM and ECR issues, a security checklist, AWS inventory commands, safely stopping a named Docker container, selectively stopping/terminating EC2 and selectively deleting disposable ECR/S3/IAM resources after verifying ownership. **Never blindly copy a destructive cleanup command.**

### File 25: `docs/04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md` — this guide

**What is inside:** the full training and GitHub CI/CD teaching order, explanation of every file, actual code blocks/line-range explanations, classroom scripts, AWS/GitHub configuration, verification and likely questions. Markdown files have `.md` extensions and are easy to read in VS Code with **Ctrl+Shift+V** (Markdown Preview).

## 7. Explain the end-to-end chain by pointing to each file

This is the key **story** to repeat before and after the practical:

```text
raw rows                data/food_delivery.csv
       |
       v
validate + 80/20 split  src/train.py
       |                  └── src/generate_data.py makes example data
       v
fit preprocessing + ML  src/train.py
       |
       v
test/quality gate        tests/*.py + src/train.py
       |
       v
outputs                 artifacts/model.joblib
                        artifacts/metrics.json
                        artifacts/train_rows.csv
                        artifacts/test_rows.csv
       |
       v
serve the model         app/main.py
       |
       v
package the release     Dockerfile
       |
       v
automate on GitHub      .github/workflows/ml-cicd.yml
       |                     |
       |                 AWS IAM trust/permissions templates
       v
publish model archive   S3: models/<commit-SHA>/model.joblib
publish Docker image    ECR: food-delivery-api:<commit-SHA>
       |
       v
remote deployment       scripts/ssm_deploy.py
       |
       v
on EC2                  scripts/ec2_deploy.sh
       |
       v
live predictions        EC2:8000/predict, :8000/health, :8000/version
```

**Student exercise:** Ask learners to point to the exact file responsible for each arrow, rather than just naming a technology.

## 8. Read GitHub Actions logs like a trainer (exact evidence checklist)

At GitHub **Actions → Food Delivery - ML CI and AWS CD**, open a run:

| Step shown in the UI | What to highlight | Typical result |
|---|---|---|
| Checkout | Source code from specific commit | Green |
| Set up Python | GitHub Linux runner uses Python 3.11 | Green |
| Install dependencies | The `requirements.txt` packages install | Green |
| Run automated tests | Each source file test is run | `5 passed` |
| Train on 80%, test on held-out 20% | Dataset split & MAE score | `TOTAL=600 | TRAIN=480 | TEST=120` |
| Upload training evidence | Trained model and diagnostic CSVs attached to run | `trained-model-and-test-results` |
| Download approved model | CD job loads CI job artifact | Model exists before Docker build |
| Configure short-lived AWS credentials | GitHub assumes exact IAM role | No static access keys |
| Save approved model to S3 | A `models/<SHA>/...` copy | Versioned archive keys |
| Build and push versioned Docker image | ECR image tagged `<SHA>` | Published image |
| Deploy via Systems Manager | Remote `docker pull`/`docker run`/`curl /health` | Success (or visible error) |

**If `ml-ci` fails, there is intentionally no successful deployment.** If CI passes but the deployment job fails, debug the **AWS authorization/network/instance** stage rather than retraining the model randomly.

## 9. Common beginner questions — ready-to-say answers

**Q. Why train on 80% and test on 20%?** A: To evaluate on unseen examples. Training on the test set would make the score unreliable.

**Q. Is 2.56-minute MAE the error for every order?** A: No. It is the average absolute error across all held-out test examples. Individual errors differ.

**Q. Are the 600 rows real customer data?** A: No, this is synthetic teaching data, created using a repeatable formula.

**Q. What is preprocessing?** A: Preparing input columns so the model can use them; the pipeline encodes text categories as numeric indicators.

**Q. What is `model.joblib`?** A: A saved trained model plus preprocessing, loaded by the API without retraining for every request.

**Q. Why use pytest before training in GitHub?** A: It catches basic bugs and invalid behavior early, often faster than a full deployment.

**Q. Why does CI upload an artifact?** A: CI and CD run on different machines. The artifact is how the trained model moves between jobs.

**Q. Isn't S3 the Docker registry?** A: No. S3 stores model files and metrics; ECR stores the Docker image. EC2 runs the image.

**Q. Does EC2 download model.joblib from S3 at startup?** A: **No in this starter project.** The model is already baked into the Docker image. S3 holds an archive copy for audit and traceability.

**Q. Does GitHub Actions automatically log MLflow runs?** A: No. Local MLflow is optional, enabled only with the `--mlflow` flag.

**Q. How does GitHub securely access AWS?** A: OIDC identity token → trusted IAM role → temporary AWS credentials; no permanent IAM access keys stored in GitHub.

**Q. Does clicking `/health` prove prediction accuracy?** A: No. It proves the model-loaded app responds. Model quality requires comparing predictions against actual outcomes when they become available.

**Q. How is a failed model blocked?** A: `src/train.py` raises a nonzero error when MAE exceeds the chosen threshold, causing `ml-ci` to fail; `deploy` depends on that job.

**Q. Can a pull request deploy to EC2?** A: Not in this workflow. PRs run CI but the deploy job condition excludes `pull_request`.

**Q. Does failed deployment automatically restore everything?** A: No. The supplied shell script attempts a limited container rollback after a failed health check. Real production releases need broader controls and monitoring.

## 10. Trouble spots: what to check before asking students to retry

| Issue | First check | Safe next action |
|---|---|---|
| Python `ModuleNotFoundError` | Is `.venv` active? | `python -m pip install -r requirements.txt` |
| `model.joblib` missing | Did `python -m src.train --max-mae 6` pass? | Run successful training before API or Docker |
| `MODEL REJECTED` | Was threshold `0.1` left from demo? | Restore `--max-mae 6` |
| Docker cannot start | Docker Desktop running? Port 8000 free? | Check `docker version`; stop existing local container |
| No workflow shown in GitHub Actions | Is YAML committed at `.github/workflows/ml-cicd.yml`? | `git status`, `git ls-files .github/workflows/ml-cicd.yml` |
| CI passed but deploy skipped | Is event a PR? Does branch match `main`? | Expected behavior for a PR |
| OIDC role cannot be assumed | Owner/repo/env/subject mismatch; trust not created | Check exact IAM trust and GitHub environment; no wildcard trust |
| AWS S3 upload denied | S3 bucket name and PutObject resource? | Compare GitHub vars and IAM permissions |
| ECR push denied | Repo name/region and ECR permissions? | Check ECR repo and policy ARN |
| SSM deploy fails | Is EC2 managed node online? Correct instance ID? | Verify instance role, SSM agent, networking |
| EC2 cannot pull image | EC2 instance role ECR pull? outbound HTTPS? | Attach appropriate pull-only role and verify network |
| GitHub deploy green, laptop cannot reach API | Current public IP and SG port 8000? | Confirm network rule limited to your IP, use Session Manager to curl localhost |
| API returns 422 | Does request contain all five features and legal categories? | Fix JSON fields; inspect `/docs` |

## 11. 2-minute end-of-class explanation (memorize this)

> “We created 600 example food delivery orders. We used 480 orders to train a model and 120 unseen orders to test it. We recorded average prediction error and rejected models that do not meet the quality threshold. We saved the trained model and served predictions through FastAPI. We packaged the app and model into Docker. Next, we pushed our project into GitHub. GitHub Actions automatically ran tests and training; after success, the deployment job used temporary AWS credentials, copied the approved model to S3, pushed the corresponding image to ECR and told EC2 to run it. Finally, we tested the deployed API. This whole process is a basic end-to-end MLOps CI/CD pipeline.”

## 12. Instructor end-of-class checklist

- [ ] Students saw `data/food_delivery.csv` and identified features/target.
- [ ] They saw the split in code and opened **480 training / 120 test** CSVs.
- [ ] They viewed MAE and a prediction example, and saw a deliberate quality-gate failure.
- [ ] `python -m pytest -q` showed five tests passing.
- [ ] FastAPI `/health`, `/predict`, and `/docs` worked locally.
- [ ] Docker build succeeded after a passing train.
- [ ] `.github/workflows/ml-cicd.yml` was **actually committed to GitHub**.
- [ ] The CI job ran; the deploy job was gated on successful CI.
- [ ] If AWS setup was ready: S3 model/metrics, ECR image and EC2 `/health` were verified.
- [ ] Students saw a PR failure that did **not** deploy.
- [ ] Any AWS resources were inventoried and stopped/cleaned only if safely owned by this lab.

---

## Appendix A — Source code as it appears in the supplied kit

The following are verbatim copies of the **key execution files** included in the ZIP, for offline lesson preparation. You can teach from these even when VS Code is unavailable. The other files' contents are explained above and remain in their actual project folders. **Do not edit the appendix to change the running project; edit the real source file instead.**

### `src/generate_data.py` (verbatim source)

```python
"""Create synthetic teaching data. NOT real restaurant/customer data."""
from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "food_delivery.csv"


def generate_dataset(rows: int = 600, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    records = []
    traffic_penalty = {"Low": 2, "Medium": 7, "High": 14}
    weather_penalty = {"Clear": 0, "Rainy": 5, "Stormy": 12}
    for _ in range(rows):
        distance = round(rng.uniform(0.8, 15.0), 2)
        traffic = rng.choices(["Low", "Medium", "High"], weights=[30, 45, 25])[0]
        weather = rng.choices(["Clear", "Rainy", "Stormy"], weights=[65, 28, 7])[0]
        prep = rng.randint(5, 25)
        experience = rng.randint(0, 8)
        duration = (8 + 2.6 * distance + traffic_penalty[traffic]
                    + weather_penalty[weather] + 0.65 * prep
                    - 0.7 * experience + rng.gauss(0, 2.0))
        records.append({
            "distance_km": distance,
            "traffic_level": traffic,
            "weather": weather,
            "restaurant_prep_min": prep,
            "courier_experience_years": experience,
            "delivery_time_min": round(max(5.0, duration), 1),
        })
    return pd.DataFrame.from_records(records)


def main():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_dataset()
    frame.to_csv(DATA_PATH, index=False)
    print(f"Created {len(frame)} synthetic orders at {DATA_PATH}")
    print(frame.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
```

### `src/train.py` (verbatim source)

```python
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
```

### `app/main.py` (verbatim source)

```python
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
```

### `tests/test_data.py` (verbatim source)

```python
import pytest
from src.generate_data import generate_dataset
from src.train import validate_frame


def test_generated_dataset_has_required_fields():
    df = generate_dataset(rows=100)
    validate_frame(df)
    assert len(df) == 100
    assert df["delivery_time_min"].gt(0).all()


def test_missing_feature_is_rejected():
    df = generate_dataset(rows=100).drop(columns=["distance_km"])
    with pytest.raises(ValueError, match="Missing columns"):
        validate_frame(df)


def test_negative_distance_is_rejected():
    df = generate_dataset(rows=100)
    df.loc[0, "distance_km"] = -3
    with pytest.raises(ValueError, match="Distance"):
        validate_frame(df)
```

### `tests/test_training.py` (verbatim source)

```python
import pandas as pd
from src.generate_data import generate_dataset
from src.train import train


def test_train_test_split_and_gate(tmp_path):
    data = tmp_path / "orders.csv"
    generate_dataset(rows=100).to_csv(data, index=False)
    info = train(data, tmp_path / "output", max_mae=100)
    assert info["training_rows"] == 80
    assert info["testing_rows"] == 20
    training = pd.read_csv(tmp_path / "output" / "train_rows.csv")
    testing = pd.read_csv(tmp_path / "output" / "test_rows.csv")
    assert len(training) == 80 and len(testing) == 20
    assert (tmp_path / "output" / "model.joblib").exists()
```

### `tests/test_api.py` (verbatim source)

```python
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
```

### `Dockerfile` (verbatim source)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY artifacts/model.joblib ./artifacts/model.joblib
COPY artifacts/metrics.json ./artifacts/metrics.json
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.github/workflows/ml-cicd.yml` (verbatim source)

```yaml
name: Food Delivery - ML CI and AWS CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  ml-ci:
    name: Test, train and validate model
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run automated tests
        run: python -m pytest -q
      - name: Train on 80%, test on held-out 20%
        run: python -m src.train --max-mae 6
      - name: Upload training evidence
        uses: actions/upload-artifact@v4
        with:
          name: trained-model-and-test-results
          path: |
            artifacts/model.joblib
            artifacts/metrics.json
            artifacts/train_rows.csv
            artifacts/test_rows.csv
            artifacts/prediction_examples.csv
          retention-days: 7

  deploy:
    name: Build image, store model, deploy EC2
    needs: ml-ci
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    environment: workshop-production
    env:
      AWS_REGION: ${{ vars.AWS_REGION }}
      ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
      S3_BUCKET: ${{ vars.S3_BUCKET }}
      EC2_INSTANCE_ID: ${{ vars.EC2_INSTANCE_ID }}
      IMAGE_TAG: ${{ github.sha }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Download approved model from this same CI run
        uses: actions/download-artifact@v4
        with:
          name: trained-model-and-test-results
          path: artifacts
      - name: Configure short-lived AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - name: Determine ECR image address
        shell: bash
        run: |
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          echo "ECR_URI=${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}" >> "$GITHUB_ENV"
      - name: Save approved model to S3 (audit copy)
        run: |
          aws s3 cp artifacts/model.joblib "s3://${S3_BUCKET}/models/${IMAGE_TAG}/model.joblib"
          aws s3 cp artifacts/metrics.json "s3://${S3_BUCKET}/models/${IMAGE_TAG}/metrics.json"
      - name: Build and push versioned Docker image
        shell: bash
        run: |
          aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ECR_URI%%/*}"
          docker build -t "${ECR_URI}:${IMAGE_TAG}" .
          docker push "${ECR_URI}:${IMAGE_TAG}"
      - name: Deploy via Systems Manager (no SSH key in GitHub)
        run: |
          pip install 'boto3>=1.35,<2'
          python scripts/ssm_deploy.py
```

### `scripts/ssm_deploy.py` (verbatim source)

```python
"""Submit a script to one preselected EC2 instance through AWS SSM Run Command."""
import os
import shlex
import sys
import time
from pathlib import Path
import boto3

required = ["AWS_REGION", "EC2_INSTANCE_ID", "ECR_URI", "IMAGE_TAG"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    sys.exit(f"Missing env vars: {', '.join(missing)}")
script = (Path(__file__).parent / "ec2_deploy.sh").read_text(encoding="utf-8")
exports = "\n".join(f"export {name}={shlex.quote(os.environ[name])}" for name in ["AWS_REGION", "ECR_URI", "IMAGE_TAG"])
command = exports + "\n" + script
client = boto3.client("ssm", region_name=os.environ["AWS_REGION"])
response = client.send_command(
    InstanceIds=[os.environ["EC2_INSTANCE_ID"]],
    DocumentName="AWS-RunShellScript",
    Parameters={"commands": [command]},
    TimeoutSeconds=600,
    Comment="Food Delivery workshop Docker deployment",
)
command_id = response["Command"]["CommandId"]
print("SSM command ID:", command_id, flush=True)
for attempt in range(75):
    time.sleep(8)
    try:
        reply = client.get_command_invocation(CommandId=command_id, InstanceId=os.environ["EC2_INSTANCE_ID"])
    except client.exceptions.InvocationDoesNotExist:
        continue
    status = reply["Status"]
    print("Remote status:", status, flush=True)
    if status in {"Success", "Failed", "TimedOut", "Cancelled", "Cancelling"}:
        print("STDOUT:\n", reply.get("StandardOutputContent", ""))
        print("STDERR:\n", reply.get("StandardErrorContent", ""))
        if status != "Success":
            sys.exit(f"Deployment did not succeed: {status}")
        print("EC2 deployment succeeded")
        break
else:
    sys.exit("Timed out waiting for SSM status; inspect Systems Manager Run Command")
```

### `scripts/ec2_deploy.sh` (verbatim source)

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${ECR_URI:?ECR_URI not provided}"
: "${IMAGE_TAG:?IMAGE_TAG not provided}"
: "${AWS_REGION:?AWS_REGION not provided}"
IMAGE="${ECR_URI}:${IMAGE_TAG}"
REGISTRY="${ECR_URI%%/*}"
NAME="food-delivery-api"

# EC2's IAM instance profile retrieves short-lived ECR credentials.
aws ecr get-login-password --region "$AWS_REGION" | sudo docker login --username AWS --password-stdin "$REGISTRY"
sudo docker pull "$IMAGE" # Do not stop the old container until the new image is pulled.
OLD_IMAGE="$(sudo docker inspect --format '{{.Config.Image}}' "$NAME" 2>/dev/null || true)"
if sudo docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  sudo docker rm -f "$NAME"
fi
sudo docker run -d --name "$NAME" --restart unless-stopped -p 8000:8000 \
  -e MODEL_VERSION="$IMAGE_TAG" "$IMAGE"

GOOD=0
for attempt in $(seq 1 20); do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health >/dev/null 2>&1; then
    GOOD=1
    break
  fi
  sleep 3
done
if [ "$GOOD" -ne 1 ]; then
  sudo docker logs --tail 70 "$NAME" || true
  sudo docker rm -f "$NAME" || true
  if [ -n "$OLD_IMAGE" ]; then
    echo "Deployment failed; restoring previous image: $OLD_IMAGE"
    sudo docker run -d --name "$NAME" --restart unless-stopped -p 8000:8000 "$OLD_IMAGE"
  fi
  exit 1
fi
printf 'Deployment successful: %s\n' "$IMAGE"
curl --fail http://127.0.0.1:8000/health
```

### `aws/github-oidc-trust-policy.template.json` (verbatim source)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:<GITHUB_OWNER>/<REPO>:environment:workshop-production"
      }
    }
  }]
}
```

### `aws/github-deploy-permissions.template.json` (verbatim source)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["ecr:BatchCheckLayerAvailability", "ecr:CompleteLayerUpload", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart", "ecr:BatchGetImage"], "Resource": "arn:aws:ecr:ap-south-1:<ACCOUNT_ID>:repository/food-delivery-api"},
    {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": "arn:aws:s3:::<S3_BUCKET>/models/*"},
    {"Effect": "Allow", "Action": ["ssm:SendCommand"], "Resource": ["arn:aws:ssm:ap-south-1::document/AWS-RunShellScript", "arn:aws:ec2:ap-south-1:<ACCOUNT_ID>:instance/<EC2_INSTANCE_ID>"]},
    {"Effect": "Allow", "Action": ["ssm:GetCommandInvocation"], "Resource": "*"}
  ]
}
```

## Appendix B — Trusted documentation to consult if AWS/GitHub behavior changes

- Scikit-learn train/test split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
- GitHub workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub OIDC in AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- AWS configure credentials action: https://github.com/aws-actions/configure-aws-credentials
- AWS Systems Manager Run Command: https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html
- Amazon ECR getting started: https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
- FastAPI docs: https://fastapi.tiangolo.com/

**Guide scope:** This is an explanatory guide for the supplied source, not a claim that AWS/GitHub cloud deployment has been executed. The local tests and synthetic model training were verified; cloud deployment depends on your AWS account/role/network/repository configuration.

