# Day 5 Instructor's Complete Practical — Food Delivery Time Prediction

> **For a line-by-line explanation of every supplied file, including `.github/workflows/ml-cicd.yml` and both deployment scripts, read [`04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md`](04_DETAILED_FILE_BY_FILE_AND_PIPELINE_TRAINER_GUIDE.md). This companion also walks through creating/running the real GitHub Actions pipeline.**


**Audience:** beginners in MLOps and a trainer with no assumed experience.  
**Operating system:** Windows 10/11, VS Code PowerShell.  
**AWS region:** Mumbai, `ap-south-1`. **AWS CLI profile:** `workshop` (change if yours is different).  
**Recommended sequence:** Lab A (training/test split) FIRST; then Lab B (API/Docker); then Lab C (GitHub Actions → ECR/S3 → EC2).  
**Expected session:** 10:00 AM to 4:30 PM, including breaks.  
**Important:** All delivery data in this kit is **synthetic teaching data**, not real restaurant data. Do not claim the model is production-grade.

## 0. What students should understand by the end

1. A dataset contains input features (distance, traffic, weather, restaurant preparation time, courier experience) and a target (actual delivery minutes).
2. Training data **teaches** the model. Test data **checks** how it predicts records not used in fitting.
3. The training code fits preprocessing **only on training data**, reducing data leakage.
4. MAE is the average absolute prediction error, expressed in minutes.
5. A model must pass an automated quality threshold before publishing.
6. GitHub Actions tests and trains; Docker packages; ECR stores images; S3 stores a versioned audit copy; EC2 serves predictions; SSM deploys without SSH keys in GitHub.

## 1. Day 5 time plan (10:00 AM–4:30 PM)

| Time | What to do | Expected outcome |
|---|---|---|
| 10:00–10:15 | Introduce food delivery prediction and features/target | Students understand prediction problem |
| 10:15–11:10 | **Lab A:** Show CSV, train/test split, train model, evaluate | `train_rows.csv`, `test_rows.csv`, `metrics.json` |
| 11:10–11:30 | Quality gate failure demo; explain leakage | Students see a blocked model |
| 11:30–11:45 | Break | |
| 11:45–12:25 | **Lab B:** FastAPI endpoints and validation | Working `/health`, `/docs`, `/predict` |
| 12:25–12:45 | Docker build and local smoke test | Running local Docker container |
| 12:45–1:30 | Lunch | |
| 1:30–2:00 | CI/CD concept and show workflow YAML | Students recognize test→train→deploy jobs |
| 2:00–3:00 | **Lab C:** Configure AWS/GitHub, run GitHub Actions | Versioned Docker image and archived model |
| 3:00–3:10 | Break | |
| 3:10–3:50 | Check EC2 prediction API, GitHub logs, rollback discussion | Remote `/health` and `/predict` |
| 3:50–4:15 | Demonstrate bad dataset/failed threshold; Q&A | Failed checks block deployment |
| 4:15–4:30 | Recap and cloud cleanup | No unintended continuing charges |

**Reality check:** The AWS account, IAM permissions, EC2, ECR, S3, and GitHub repo setup should be prepared **before class**. If not, cloud setup may take more than one hour. Use the local project as the guaranteed teaching outcome and demonstrate the cloud pipeline from a pre-configured account.

---

# LAB A — DATA, TRAINING SET, TEST SET, MODEL EVALUATION

## 2. First-time tool installation on Windows

Install **Python 3.11 (64-bit)** from https://www.python.org/downloads/ (check **Add Python to PATH** during setup); **VS Code** from https://code.visualstudio.com/; **Git** from https://git-scm.com/downloads/win; **Docker Desktop** from https://www.docker.com/products/docker-desktop/ and start it; **AWS CLI v2** from https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html. You need an AWS account with permissions for the later cloud steps.

Open **VS Code → File → Open Folder**, select the extracted `Day5_FoodDelivery_Practical` folder. Open **Terminal → New Terminal** and select **PowerShell**.

Run these one by one:

```powershell
python --version
# Should show Python 3.11.x (or use 'py -3.11' if needed)
git --version
docker version
aws --version
```

If `docker version` cannot reach the server, start Docker Desktop and select its Linux containers engine. If PowerShell blocks venv activation, use the `python` executable within `.venv` directly or select Command Prompt; avoid changing machine-wide execution policies just for this lab.

## 3. Create an isolated Python virtual environment

From the **project root** (the folder containing `requirements.txt`):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**What each command means:** `venv` creates a private Python environment; activation tells the terminal to use it; `pip` installs the libraries for this particular workshop.

**Verify:**

```powershell
python -c "import pandas, sklearn, fastapi; print('Libraries imported successfully')"
```

> If `py -3.11` is unavailable but `python --version` shows Python 3.11, use `python -m venv .venv`. If `Activate.ps1` is blocked, run `& .\.venv\Scripts\python.exe -m pip install -r requirements.txt`, then use that Python path for the rest of the commands.

## 4. Open and explain the dataset — BEFORE training

In VS Code click `data/food_delivery.csv`. It contains **600 synthetic orders**, with columns:

| Column | Meaning | Example |
|---|---|---|
| `distance_km` | Restaurant-to-customer distance in km | `5.5` |
| `traffic_level` | Amount of traffic | `High` |
| `weather` | Weather condition | `Rainy` |
| `restaurant_prep_min` | Food preparation time | `12` |
| `courier_experience_years` | Courier experience (years) | `2` |
| `delivery_time_min` | **Actual delivery time**, which we want to predict | `42` |

**Say to students:** “The first five columns are **features X**. The last column is the **target y**. The computer learns relationships between X and y from historical example orders.”

Optional inspection:

```powershell
python -c "import pandas as pd; x=pd.read_csv('data/food_delivery.csv'); print(x.head()); print('Rows:',len(x)); print('Columns:',list(x.columns))"
```

**File explanation — `src/generate_data.py`:** Creates the **same** fake dataset every time using a fixed random seed. This is useful when no real customer dataset is available. A real MLOps project would have data governance, privacy, and representative historical data.

Regenerate only if necessary:

```powershell
python -m src.generate_data
```

## 5. Explain training vs testing with a real split

Use this classroom analogy:

> “We give students 80% of the practice questions to learn from. We keep 20% of the questions unseen until the final exam. If we test using the exact questions used to teach, the score can be misleading.”

Our code contains:

```python
train_frame, test_frame = train_test_split(
    frame, test_size=0.20, random_state=42
)
```

Read each part:

- `frame` = all 600 rows.
- `test_size=0.20` = hold out 20% for testing (120 rows).
- The remaining 80% (480 rows) is used for model training.
- `random_state=42` = repeatable split.
- The preprocessing pipeline is **fitted only on training rows**. The test rows are transformed using the already-fitted pipeline.

**Critical ML principle:** Test records must not be used to fit preprocessing or tune a model. For more advanced tuning you should also have a separate validation set or cross-validation; this beginner lab uses a fixed threshold on a holdout set purely to illustrate the acceptance process. Avoid repeatedly tuning against the final test set in a real production evaluation.

## 6. Run the training program live

```powershell
python -m src.train --max-mae 6
```

**Expected shape of terminal output (numbers may change slightly with dependency versions):**

```text
TOTAL=600 | TRAIN=480 (80%) | TEST=120 (20%)
MAE=... min | RMSE=... min | R2=...
See: .../artifacts/train_rows.csv and .../artifacts/test_rows.csv
MODEL ACCEPTED: quality gate passed
```

**Now open these four files in VS Code:**

1. `artifacts/train_rows.csv`: 480 orders shown to the model during training.
2. `artifacts/test_rows.csv`: 120 orders held back from model fitting.
3. `artifacts/prediction_examples.csv`: a few unseen test orders, predictions, and their errors.
4. `artifacts/metrics.json`: numeric quality metrics and the decision about acceptance.

**Trainer demonstration:** Compare `train_rows.csv` and `test_rows.csv` to point out different records. Show the prediction and actual-delivery columns side-by-side in `prediction_examples.csv`.

**File explanation — `src/train.py`:** Reads the CSV, rejects invalid input columns, splits the dataset, creates preprocessing for number/categorical columns, trains a random forest, evaluates on held-out test rows, saves `model.joblib`, prints metrics, and stops the workflow if MAE exceeds a chosen threshold. The model is packaged with preprocessing to avoid inconsistent training and serving transformations.

## 7. Explain the three evaluation metrics (do not overcomplicate)

- **MAE — Mean Absolute Error:** Average absolute difference between predicted and actual delivery time. **MAE = 3 minutes** means predictions are off by 3 minutes on average across the evaluated test cases.
- **RMSE — Root Mean Squared Error:** Like MAE but penalizes large mistakes more strongly. Smaller is better.
- **R² — Coefficient of determination:** A score summarizing how much variation in delivery time the model explains relative to a constant baseline; bigger is generally better, although it can be negative.

**Example:** Actual time = 40 minutes; predicted = 36 minutes; absolute error = 4 minutes. Repeat across all held-out test records and average errors to obtain MAE.

**Explain:** The synthetic data is designed to be learnable. A high test score here is **not proof** the app is accurate on actual food deliveries.

## 8. Demonstrate the quality gate FAILING (very important)

Run:

```powershell
python -m src.train --max-mae 0.1
```

You should see `MODEL REJECTED`, and the process exits with a nonzero status. The model artifacts may still be written locally for inspection, but an automated deployment step must **not** run when the training job fails.

**Immediately restore a passing training run:**

```powershell
python -m src.train --max-mae 6
```

**Say:** “The exact threshold is a teaching choice, not a universally correct business threshold. In real systems we choose it from historical model performance, user expectations and business risk.”

## 9. Show automated tests and a deliberately broken dataset

```powershell
python -m pytest -q
```

Expected: `5 passed`. Tests check the schema, negative distances, train/test split and FastAPI request validation.

**To show invalid data without modifying the original CSV:**

```powershell
python -c "import pandas as pd; d=pd.read_csv('data/food_delivery.csv'); d=d.drop(columns=['distance_km']); d.to_csv('data/broken_delivery.csv',index=False)"
python -m src.train --data data/broken_delivery.csv --max-mae 6
```

Expected: `ValueError: Missing columns: ['distance_km']`. This is good: the pipeline correctly **rejects invalid training data**. Clean the temporary file:

```powershell
Remove-Item data/broken_delivery.csv
```

## 10. Optional: Show local MLflow experiment tracking (only if time allows)

MLflow adds packages, so it is optional and **not required** for GitHub Actions deployment in this project.

```powershell
pip install -r requirements-mlflow.txt
python -m src.train --max-mae 6 --mlflow
mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000` in your browser. Select `food-delivery-training`, inspect the run's parameters (`test_fraction`, `seed`, `trees`), metrics (MAE, RMSE, R²), and artifacts (model file, sample predictions, metrics JSON).

**File explanation — `requirements-mlflow.txt`:** Adds MLflow to the base Python dependencies. `src/train.py` logs a run only when `--mlflow` is supplied; it deliberately does not require an external MLflow tracking server.

To stop the MLflow UI, return to PowerShell and press **Ctrl+C**.

---

# LAB B — FASTAPI, PREDICTIONS, AND DOCKER

## 11. Start the Food Delivery Prediction API locally

You must have run **successful training** first (Step 6 or 8), because FastAPI loads `artifacts/model.joblib` on startup.

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open these URLs in a web browser:

- `http://127.0.0.1:8000/docs` — interactive FastAPI documentation.
- `http://127.0.0.1:8000/health` — checks whether the model loaded.
- `http://127.0.0.1:8000/version` — shows the model version and training metadata.

**File explanation — `app/main.py`:** Defines input schema `PredictionRequest`, output schema `PredictionResponse`, loads our trained preprocessing+model pipeline, validates JSON, returns prediction time and measured processing latency, and logs successes/errors. It avoids logging complete incoming order details.

## 12. Send a prediction using PowerShell (open a SECOND terminal)

Leave Uvicorn running in the first terminal. In the second VS Code PowerShell terminal, run:

```powershell
$body = @{
  distance_km = 5.5
  traffic_level = 'High'
  weather = 'Rainy'
  restaurant_prep_min = 12
  courier_experience_years = 2
} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Body $body -ContentType 'application/json'
```

You should get JSON containing `predicted_delivery_time_min`, `model_version`, and `latency_ms`. The precise predicted number may vary.

**Incorrect input demonstration:**

```powershell
$bad = @{distance_km=-3;traffic_level='High';weather='Rainy';restaurant_prep_min=12;courier_experience_years=2} | ConvertTo-Json
try { Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Body $bad -ContentType 'application/json' } catch { Write-Host 'Rejected invalid distance (expected):' $_.Exception.Message }
```

FastAPI should return HTTP **422** (validation error) because distance cannot be negative.

Stop the API with **Ctrl+C** before running Docker, to free port 8000.

## 13. Build and run the Docker image locally

Ensure Docker Desktop is running, then:

```powershell
docker build -t food-delivery-api:local .
docker run -d --name food-delivery-local -p 8000:8000 -e MODEL_VERSION=local-v1 food-delivery-api:local
docker ps
docker logs food-delivery-local
Invoke-RestMethod http://127.0.0.1:8000/health
```

Test the same prediction request from Step 12. When finished:

```powershell
docker rm -f food-delivery-local
```

**File explanation — `Dockerfile`:** Installs pinned Python packages, copies the FastAPI source and the **trained model artifact** into the image, and starts Uvicorn. This is a deliberately simple approach: each immutable image contains the approved model version. The workflow **also** stores the artifact in S3 as an audit/archive copy; the running container does not download its model from S3.

**File explanation — `.dockerignore`:** Excludes `.venv`, datasets, local MLflow data and unrelated files from the Docker build context. **File explanation — `.gitignore`:** Stops transient local model files and credentials from being committed to Git.

---

# LAB C — CI/CD: GITHUB ACTIONS → S3 + ECR → EC2

## 14. Simple architecture to draw for the class

```text
GitHub repository (code + versioned synthetic CSV)
                    |
                    v
           GitHub Actions CI job
           - install packages
           - pytest automated tests
           - train model (80% data)
           - evaluate on held-out 20%
           - fail if MAE > 6 min
                    |
              only if PASS
                    v
           GitHub Actions CD job
           - download trained artifact
           - assume short-lived AWS role via OIDC
           - upload model + metrics to S3 under commit SHA
           - build immutable Docker image containing approved model
           - push image tagged with Git commit SHA to ECR
           - send deployment command through AWS Systems Manager
                    |
                    v
           Amazon Linux EC2 + Docker
                    |
                    v
              FastAPI /predict
```

**Definition:** **CI** checks whether a change is good enough. **CD** delivers a passing release. **OIDC** allows GitHub to request temporary AWS credentials without storing access-key secrets. **SSM Run Command** tells an already-configured EC2 instance to execute a deployment script without putting an SSH private key into GitHub.

## 15. AWS prerequisites — verify account, region and existing EC2

**IMPORTANT COST/SAFETY WARNING:** This project can create billable EC2, EBS, public IPv4, S3 and ECR resources. Identify existing workshop resources before creating anything. You previously had an EC2 server and other instances; do not terminate other instances or blindly create duplicates.

In PowerShell:

```powershell
aws configure list-profiles
aws sts get-caller-identity --profile workshop
aws ec2 describe-instances --region ap-south-1 --profile workshop --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' --output table
```

Confirm the correct AWS account and record the **INSTANCE ID** (such as `i-0123456789abcdef0`) of **your workshop server**. Do not copy example IDs literally.

If you already have a working Amazon Linux 2023 EC2 instance, you can **reuse it**, provided it is safe to change its Docker containers and role policies. You do **not** need to create a second server. If you do not have one, create it with the next step.

## 16. If needed: launch one new EC2 server (console method)

In AWS Console, switch to **Asia Pacific (Mumbai), `ap-south-1`**. Go to **EC2 → Instances → Launch instances**:

1. Name: `food-delivery-day5-server`.
2. AMI: **Amazon Linux 2023, x86_64**.
3. Type: **t3.micro** (costs may apply; confirm your account eligibility/pricing).
4. Key pair: **Proceed without key pair** if using SSM exclusively; otherwise choose an existing workshop key only if needed for optional SSH troubleshooting. Never upload a `.pem` key to GitHub.
5. Network: use your default VPC with a public subnet and public IPv4 for this classroom example. Real production deployments should use private networking and a proper ingress design.
6. Security group: allow **TCP 8000 only from your instructor/public IP (`My IP`)**, not from `0.0.0.0/0`. Do not open SSH if using Systems Manager. The instance must be able to reach AWS SSM/ECR endpoints via outbound HTTPS (or private endpoints).
7. Storage: 8 GiB gp3 (or the minimum supported by the selected AMI).
8. **Advanced details → IAM instance profile**: attach an EC2 role with the AWS managed policies `AmazonSSMManagedInstanceCore` and `AmazonEC2ContainerRegistryPullOnly` (create the role in IAM first if missing; see Step 17).
9. Launch and note the instance ID and public IPv4.

**Teacher explanation:** A security group is the instance's virtual firewall. The instance role grants AWS API permissions to EC2 without putting secrets on the machine.

## 17. EC2 IAM role + SSM readiness

AWS Console → **IAM → Roles → Create role**. Select **AWS service → EC2** and attach two AWS-managed policies:

- `AmazonSSMManagedInstanceCore`: permits management via SSM.
- `AmazonEC2ContainerRegistryPullOnly`: permits Docker image pulls from ECR.

Name it `food-delivery-ec2-role`, create it, then attach it using **EC2 → Instances → your instance → Actions → Security → Modify IAM role**. If you are reusing an existing IAM role (e.g. `day3-ec2-ecr-role`), you can attach `AmazonSSMManagedInstanceCore` instead of creating a duplicate role; keep other users' roles unchanged.

With the role attached and network connectivity available, go to **AWS Systems Manager → Fleet Manager → Managed nodes** and verify the instance is listed as online (this may take several minutes). **Systems Manager → Session Manager → Start session** lets you open a terminal on the instance without SSH. On Amazon Linux 2023, SSM Agent is often present but still verify that it is installed and running.

Inside the **EC2 Linux shell**, run:

```bash
cat /etc/os-release
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo docker version
aws --version
sudo systemctl status amazon-ssm-agent --no-pager
```

If SSM Agent is missing or the instance is not online, follow the official AWS SSM setup documentation; verify instance profile, outbound HTTPS access, agent service and target region. **Do not proceed to GitHub deployment until Systems Manager can reach the instance.**

## 18. Create an ECR repository and private S3 bucket

On your **Windows PowerShell** (not the EC2 shell), with AWS profile configured:

```powershell
$Region = 'ap-south-1'
$Profile = 'workshop'
$AccountId = aws sts get-caller-identity --profile $Profile --query Account --output text
$Bucket = "food-delivery-mlops-$AccountId-ap-south-1"
Write-Host "Account ID: $AccountId"
Write-Host "Bucket: $Bucket"
```

Record these names. Create resources if they **do not already exist**:

```powershell
aws ecr describe-repositories --repository-names food-delivery-api --region $Region --profile $Profile
# If RepositoryNotFoundException, create it:
aws ecr create-repository --repository-name food-delivery-api --region $Region --profile $Profile --image-scanning-configuration scanOnPush=true
```

```powershell
aws s3api head-bucket --bucket $Bucket --profile $Profile
# If bucket does not exist, create it:
aws s3api create-bucket --bucket $Bucket --region $Region --profile $Profile --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api put-public-access-block --bucket $Bucket --profile $Profile --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**CAUTION:** If `head-bucket` returns an access-denied error, don't assume the bucket is safe to create; confirm ownership first. S3 names must be globally unique. Amazon S3 enables baseline server-side encryption by default, and this demo uses commit-SHA object keys rather than bucket versioning. AWS data-transfer and storage charges can apply.

## 19. Configure GitHub as an OIDC identity provider in AWS

**Instructor should do this before class.** This is a one-time AWS account-level identity integration. Confirm no existing provider is already configured before creating a new one.

AWS Console → **IAM → Identity providers → Add provider**:

1. Provider type: **OpenID Connect**.
2. Provider URL: `https://token.actions.githubusercontent.com`.
3. Audience: `sts.amazonaws.com`.
4. Complete provider creation.

This lets AWS verify identity tokens minted by GitHub Actions. It does **not** grant any permission by itself; we still create an IAM role restricted to the correct repository and deployment context.

**2026 note:** GitHub has introduced immutable OIDC subject claim options for some newer repositories. The included template illustrates the traditional `repo:OWNER/REPO:environment:workshop-production` subject. If your GitHub repo emits a different subject, follow current GitHub AWS OIDC documentation and set an equally restrictive claim for **that exact repository/environment**. Do not fix failed assumptions by trusting every GitHub repository.

## 20. Create the GitHub deployment IAM role and policy

Choose your GitHub repo owner (personal user or org) and repo name, for example `your-user/food-delivery-mlops-lab`. Your actual `OWNER/REPO` must be substituted.

Read these supplied files:

- `aws/github-oidc-trust-policy.template.json`: **who may assume the deployment role** (your GitHub repo/environment).
- `aws/github-deploy-permissions.template.json`: **what that role may do** (push to one ECR repo, put model artifacts to one S3 prefix, send SSM commands to one EC2 instance).

From PowerShell in the project root, copy and replace placeholders automatically:

```powershell
$Owner = 'REPLACE_WITH_YOUR_GITHUB_USERNAME_OR_ORG'
$Repo = 'REPLACE_WITH_YOUR_REPOSITORY_NAME'
$InstanceId = 'REPLACE_WITH_YOUR_EC2_INSTANCE_ID'
$Trust = (Get-Content aws/github-oidc-trust-policy.template.json -Raw).Replace('<ACCOUNT_ID>', $AccountId).Replace('<GITHUB_OWNER>', $Owner).Replace('<REPO>', $Repo)
$Policy = (Get-Content aws/github-deploy-permissions.template.json -Raw).Replace('<ACCOUNT_ID>', $AccountId).Replace('<S3_BUCKET>', $Bucket).Replace('<EC2_INSTANCE_ID>', $InstanceId)
$Trust | Set-Content -Encoding utf8 aws/github-oidc-trust-policy.generated.json
$Policy | Set-Content -Encoding utf8 aws/github-deploy-permissions.generated.json
Get-Content aws/github-oidc-trust-policy.generated.json
```

**Check names carefully**, then create the role using your instructor's permitted account:

```powershell
aws iam create-role --role-name food-delivery-github-deploy --assume-role-policy-document file://aws/github-oidc-trust-policy.generated.json --profile $Profile
aws iam put-role-policy --role-name food-delivery-github-deploy --policy-name food-delivery-deploy-privileges --policy-document file://aws/github-deploy-permissions.generated.json --profile $Profile
```

If the role already exists, **inspect its trust and permission policies first** rather than overwriting blindly. An organizational account may restrict IAM creation: ask your AWS administrator for a suitable preconfigured deployment role instead.

**Important security:** These role privileges are teaching-oriented and targeted to one repo, bucket prefix and instance. SSM Run Command gives the deployment role the ability to execute shell commands on that instance, so use a **dedicated, non-sensitive workshop instance**, not a shared server. The policy's `GetCommandInvocation` read scope is broad because the API response is not easily resource-scoped; restrict other actions and role trust as tightly as possible. SSM audit/logging is recommended for real environments.

## 21. Push the project to a new GitHub repository

Go to https://github.com/new and create a **new empty repository** named `food-delivery-mlops-lab` (leave it empty: no README/license/gitignore checked). If you already have a repository, use your existing repo name and adjust the role trust values accordingly.

Run from VS Code PowerShell (replace the owner in URL):

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Add food delivery training, API, ML CI and EC2 deployment"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/food-delivery-mlops-lab.git
git push -u origin main
```

**Before `git add .`:** Confirm `git status` does **not** list private key files, AWS credentials, `.venv` or generated IAM policy JSON. Generated IAM JSON is not a secret by itself, but these files contain account identifiers; keeping them out of Git is cleaner. For already-initialized repositories skip `git init` and add the workflow to an appropriate branch.

**On the first push:** CI runs automatically. Deploy will attempt to run on `main`, so **configure GitHub repository variables and IAM role first** if you want the first deployment to succeed. For teaching, a failed first deploy can be confusing. If you prefer, configure the GitHub repo and AWS resources before pushing, then push once.

## 22. Configure GitHub Actions Variables and Environment

In your GitHub repository open **Settings → Environments → New environment**, name it **`workshop-production`**. If your GitHub plan permits it, add required reviewers to approve deployments; otherwise use a separate workshop repository and carefully control writes to `main`.

Go to **Settings → Secrets and variables → Actions → Variables → New repository variable** and add:

| Variable | Exact example/value |
|---|---|
| `AWS_REGION` | `ap-south-1` |
| `AWS_ROLE_ARN` | `arn:aws:iam::<YOUR_ACCOUNT_ID>:role/food-delivery-github-deploy` |
| `ECR_REPOSITORY` | `food-delivery-api` |
| `S3_BUCKET` | the exact `$Bucket` from Step 18 |
| `EC2_INSTANCE_ID` | exact `i-...` instance ID |

These are **configuration values**, not long-lived access keys. **Do not create `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` secrets** for this workflow. The `id-token: write` permission and OIDC role assume mechanism provide temporary credentials.

**Important:** GitHub's environment controls or environment-level OIDC subject must match the IAM trust policy. The workflow explicitly declares `environment: workshop-production` in the deploy job.

## 23. Read the GitHub Actions workflow line by line

Open `.github/workflows/ml-cicd.yml`.

- `on.push.branches: [main]`: push to main triggers CI/CD.
- `on.pull_request`: pull requests run checks, but **never deploy**.
- `ml-ci`: runs `pytest`, trains the model, checks MAE <= 6 and uploads the approved model plus split/sample files as a GitHub artifact.
- `needs: ml-ci`: deploy cannot start unless CI succeeds.
- `if: ...`: only main-branch non-PR events may deploy.
- `configure-aws-credentials`: exchanges a GitHub OIDC token for temporary AWS credentials.
- `aws s3 cp`: archives the model and metrics under `models/<commitSHA>/`.
- `docker build`, `docker push`: publishes an image containing the **same approved model from the CI job**, tagged with the commit SHA.
- `scripts/ssm_deploy.py`: sends deployment commands to the specific EC2 instance and waits for a success/failure result.

**Why no separate test dataset upload to S3?** This workshop focuses on safe model release; data splits and prediction samples are GitHub Actions teaching artifacts with seven-day retention. A production system would need appropriate data lineage and retention controls.

## 24. Run the pipeline and observe results

GitHub → repository → **Actions** → `Food Delivery - ML CI and AWS CD`.

Either push a change to `main` or select **Run workflow** (if available):

```powershell
# Harmless change so learners can see a new commit trigger CI/CD
Add-Content README.md "`nWorkshop rerun: training and deployment."
git add README.md
git commit -m "docs: trigger food delivery ML pipeline"
git push
```

Open the CI job and show the sequence: automated tests pass → 480/120 split → MAE → quality gate passes. Open the deploy job and show: OIDC assumption → S3 archive → Docker ECR push → SSM command → EC2 smoke test.

**Note:** GitHub may use immutable newer OIDC subject claims for your repository. If role assumption fails, consult the role trust and GitHub's OIDC docs; don't add permanent AWS keys as a shortcut.

## 25. Check S3, ECR and EC2 deployment

On **local PowerShell**, first check archived model versions and container tags:

```powershell
aws s3 ls "s3://$Bucket/models/" --recursive --profile $Profile
aws ecr describe-images --repository-name food-delivery-api --region $Region --profile $Profile --query 'imageDetails[].[imageTags,imageDigest]' --output table
```

Find the **public IPv4 address** of your known workshop instance in EC2 Console. Do not assume an old IP still applies after a stop/start.

From your laptop, if the EC2 security group allows TCP 8000 from your current IP:

```powershell
$PublicIp = 'REPLACE_WITH_YOUR_CURRENT_EC2_PUBLIC_IP'
Invoke-RestMethod "http://${PublicIp}:8000/health"
Invoke-RestMethod "http://${PublicIp}:8000/version"
Invoke-RestMethod -Uri "http://${PublicIp}:8000/predict" -Method Post -Body $body -ContentType 'application/json'
```

Expect `/health` to show a model version with the **Git commit SHA**. If remote health is unreachable but the GitHub job says deployment succeeded, check security group IPv4 port 8000, instance public IP, OS firewall, and whether Docker is listening on port 8000. Plain HTTP is used for controlled classroom demonstration only; use HTTPS with a proper ingress layer for real deployments.

## 26. Demonstrate a pipeline failure WITHOUT breaking AWS

**Preferred method:** Change the *training command* in the CI workflow to use `--max-mae 0.1` on a temporary branch/commit that runs CI, and observe the quality gate fail. For easy teaching, demonstrate locally with:

```powershell
python -m src.train --max-mae 0.1
```

Then show that `deploy` declares `needs: ml-ci`; a failed `ml-ci` prevents deployment.

**If teaching on GitHub:** Open a pull request modifying the CI train step to `--max-mae 0.1`. The PR CI should fail but the production deployment job will **not** run. Close/revert the PR afterward. Never deliberately push failing deployment configuration to the production branch of a shared system.

## 27. Explain rollback, then perform a safe rollback if necessary

A **rollback** means returning to the **previous working image**, which includes its matching model artifact and code. On your dedicated EC2 instance, a previous image remains available locally if already pulled.

The supplied `scripts/ec2_deploy.sh` attempts a basic automatic rollback **if the new container fails its `/health` smoke test**. It does *not* provide sophisticated zero-downtime deployment, and there is a brief period of downtime while the old container is replaced. An operationally mature system would use a load balancer, deployment orchestration and production approval gates.

**To roll back manually using SSM Session Manager (in Linux EC2 shell):**

```bash
sudo docker images
sudo docker ps -a
# Record a verified previous image ID or immutable ECR image tag from an earlier successful deployment.
# Example only: replace FULL_PREVIOUS_IMAGE_URI with the image shown by docker images.
sudo docker rm -f food-delivery-api
sudo docker run -d --name food-delivery-api --restart unless-stopped -p 8000:8000 FULL_PREVIOUS_IMAGE_URI
curl -i http://127.0.0.1:8000/health
```

Do **not** run the above manual rollback commands unless you have positively identified a known-good previous image and have verified the instance is dedicated to this workshop. A missing or wrong image can cause an avoidable outage.

## 28. File-by-file explanation: what each file does

| File/folder | What it does | When you show it |
|---|---|---|
| `data/food_delivery.csv` | 600 example delivery orders (features + target) | Before training |
| `src/generate_data.py` | Generates the reproducible synthetic data | Explain where data came from |
| `src/train.py` | Schema checks → 80/20 split → preprocessing → fit → test metrics → model artifact → quality gate | Lab A main file |
| `requirements.txt` | Pinned libraries required for training, tests and API | Initial setup |
| `requirements-mlflow.txt` | Optional experiment tracking packages | Optional MLflow demo |
| `tests/test_data.py` | Data schema tests | Show validation |
| `tests/test_training.py` | Confirms 80/20 split and model artifact | Show held-out data |
| `tests/test_api.py` | Tests successful prediction and invalid input | API section |
| `artifacts/train_rows.csv` | Training subset, generated locally/CI | Compare split |
| `artifacts/test_rows.csv` | Unseen testing subset, generated locally/CI | Compare split |
| `artifacts/prediction_examples.csv` | Actual vs predicted vs error for test orders | Explain MAE |
| `artifacts/metrics.json` | Metrics, row counts, pass/fail record | Explain gate |
| `artifacts/model.joblib` | Serialized fitted pipeline and model | Explain model artifact |
| `app/main.py` | FastAPI endpoints, schema, loaded model, logs | Lab B |
| `Dockerfile` | Reproducible container containing model + inference code | Docker demo |
| `.dockerignore` | Skips unneeded files in image build | Docker demo |
| `.gitignore` | Prevents generated artifacts/secrets from commits | Git demo |
| `.github/workflows/ml-cicd.yml` | GitHub Actions CI + conditional AWS CD | Lab C |
| `scripts/ec2_deploy.sh` | EC2 Docker pull/restart/health test/limited rollback | Deployment explanation |
| `scripts/ssm_deploy.py` | Uses boto3 to execute deployment script via SSM | AWS demo |
| `aws/github-oidc-trust-policy.template.json` | Which GitHub identity may assume IAM role | IAM setup |
| `aws/github-deploy-permissions.template.json` | What deployment role is allowed to do | IAM setup |
| `docs/01_TRAINER_STEP_BY_STEP.md` | This detailed teaching script | All day |
| `docs/02_STUDENT_CHEATSHEET.md` | Student-friendly short commands | Handout |
| `docs/03_TROUBLESHOOTING_AND_CLEANUP.md` | Fix common errors; clean up AWS safely | Lab support |

## 29. Frequently asked student questions (short answers)

**Q: Does testing mean the model learns from 20% more data?** No. The held-out 20% is for measuring how the already trained model performs on unseen examples.

**Q: Why not train on all 600 rows immediately?** Then there is no independent holdout in this simple demonstration to estimate generalization. After a final assessment strategy is settled, a real deployment may retrain on more approved data while preserving proper evaluation evidence.

**Q: What is `model.joblib`?** A saved model-plus-preprocessing pipeline so the API can predict without retraining for every request. Only load trusted artifacts, because Python pickle-based formats can execute code when loaded.

**Q: Why S3 and ECR?** S3 stores **model files and metrics**; ECR stores **Docker images** containing the FastAPI service and its packaged model.

**Q: Why both Docker and EC2?** Docker is the package/runtime; EC2 is the cloud machine running it.

**Q: What happens if training fails?** GitHub Actions fails the CI job; because deployment depends on CI, the new release is not pushed/deployed.

**Q: Is MLflow required?** No for this starter CI/CD path. It can be enabled locally as an experiment tracker with `--mlflow`.

**Q: What is data leakage?** Accidentally allowing information from held-out test data into model training/preprocessing/selection, producing an overly optimistic score.

## 30. Classroom fallback plan if AWS is not ready

You still have a complete, successful teaching lesson without cloud access:

1. Open dataset → explain features/target.
2. Train with 80/20 split → show separated CSV files.
3. Show prediction comparisons and MAE.
4. Fail the quality gate on purpose; restore it.
5. Run tests and FastAPI `/docs`.
6. Build and run the local Docker container.
7. Open `.github/workflows/ml-cicd.yml` and narrate what it will do once AWS OIDC, S3, ECR and EC2 are configured.

This is far better pedagogically than spending all day debugging AWS credentials.

## 31. Final reminder: clean up cloud resources

**Do not delete any resource unless you've verified its name, owner and purpose.** See `docs/03_TROUBLESHOOTING_AND_CLEANUP.md` for specific, scoped commands. Also consider GitHub Actions minutes, ECR storage, EC2/EBS charges and the cost of public IPv4 addresses.

---

## Official reference links

- GitHub OIDC for AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- AWS credentials GitHub Action: https://github.com/aws-actions/configure-aws-credentials
- AWS SSM Run Command: https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html
- AWS Systems Manager setup: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-setting-up-ec2.html
- MLflow tracking: https://mlflow.org/docs/latest/tracking/
- Scikit-learn train/test split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
- FastAPI: https://fastapi.tiangolo.com/
