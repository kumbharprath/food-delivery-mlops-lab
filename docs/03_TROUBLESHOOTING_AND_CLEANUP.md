# Troubleshooting, Safety and Cleanup — Day 5

## Troubleshooting table

| Symptom | Likely cause | What to do |
|---|---|---|
| `py -3.11` not recognized | Python launcher missing | Install Python 3.11 or use `python -m venv .venv` |
| `Activate.ps1 cannot be loaded` | Local PowerShell restriction | Use `& .\.venv\Scripts\python.exe ...` without activation |
| `ModuleNotFoundError` | Wrong Python environment | Activate `.venv`, run `python -m pip install -r requirements.txt` |
| `Model missing` at API startup | Training not run | Run `python -m src.train --max-mae 6` |
| `Address already in use` | Another service uses port 8000 | Ctrl+C old Uvicorn, `docker rm -f food-delivery-local` if applicable |
| Docker daemon unreachable | Docker Desktop stopped | Start Docker Desktop and wait for Linux engine |
| `MODEL REJECTED` | Quality threshold too low | Explain gate; restore `--max-mae 6` |
| `Missing columns` | Broken CSV | Restore original `data/food_delivery.csv` |
| AWS `AccessDenied` | Missing IAM permissions | Check account/profile, role policy and principal; do not add Admin permissions reflexively |
| GitHub OIDC `Not authorized to perform sts:AssumeRoleWithWebIdentity` | Wrong trust policy, repo, environment or OIDC subject | Check actual repo/environment and recent GitHub OIDC guidance; never use wildcard across all repos |
| ECR `RepositoryNotFound` | Repo missing/region mismatch | Verify `ap-south-1` and exact `food-delivery-api` repository |
| EC2 not listed under SSM managed nodes | Instance profile missing, SSM agent not running, no outbound HTTPS | Check AmazonSSMManagedInstanceCore, SSM agent and outbound network |
| `ssm:SendCommand` denied | IAM policy instance/document ARN mismatch | Correct target ID and resource ARNs in generated deployment policy |
| EC2 deployment fails to pull from ECR | Missing pull role or region/network mismatch | Attach ECR pull-only to EC2 instance role and check outbound connectivity |
| EC2 API times out from laptop | Security group/IPv4/public IP wrong | Confirm current public IP, SG TCP 8000 and Docker port mapping |
| API `/health` returns but `/predict` fails | Model mismatch/input schema | Check FastAPI logs and use the expected request JSON |

## Safety checklist

- Use only dedicated workshop EC2/resources. Don't alter unrelated EC2 instances.
- Port 8000 should be available only to your public IP (classroom example). Real deployments need HTTPS.
- Do not upload AWS keys, `.pem`, `.env`, private datasets, or local MLflow secrets to GitHub.
- The IAM trust and OIDC subject must identify the intended GitHub repo/environment.
- The SSM deployment role can execute commands on its specified instance; restrict access.
- Model files use `joblib` (pickle-like serialization). **Only load artifacts created by trusted code**.
- Do not assume AWS Free Tier covers EC2, EBS, Elastic IP/public IPv4, ECR or data transfer.

## Inventory first — Windows PowerShell

```powershell
$Region = 'ap-south-1'
$Profile = 'workshop'
$AccountId = aws sts get-caller-identity --profile $Profile --query Account --output text
$Bucket = "food-delivery-mlops-$AccountId-ap-south-1"
aws ec2 describe-instances --region $Region --profile $Profile --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`].Value|[0]]' --output table
aws ecr describe-repositories --region $Region --profile $Profile --query 'repositories[].repositoryName' --output table
aws s3 ls --profile $Profile
aws iam get-role --role-name food-delivery-github-deploy --profile $Profile
```

## Stop the EC2 app but keep instance (in SSM Session Manager shell)

```bash
sudo docker ps -a
sudo docker rm -f food-delivery-api
```

This frees port 8000 but **does not stop EC2 billing**. Consider stopping an EC2 instance after the class; EBS storage can still incur charges. Stop only the **specific** workshop instance, and remember the public IP may change on restart:

```powershell
$InstanceId = 'REPLACE_WITH_VERIFIED_WORKSHOP_INSTANCE_ID'
aws ec2 stop-instances --instance-ids $InstanceId --region $Region --profile $Profile
```

**If you created a dedicated new instance for this practical and no longer need it**, termination will permanently destroy its root EBS volume if delete-on-termination was enabled. Double-check the instance ID before doing this:

```powershell
# DESTRUCTIVE — execute ONLY for your verified disposable workshop instance:
aws ec2 terminate-instances --instance-ids $InstanceId --region $Region --profile $Profile
```

Do **not** terminate the instance if it is your reused Day 3 server or contains work you need.

## ECR and S3 cleanup (only after verifying names and ownership)

```powershell
aws ecr describe-images --repository-name food-delivery-api --region $Region --profile $Profile
aws s3 ls "s3://$Bucket/models/" --recursive --profile $Profile
```

If these **were created solely for this disposable workshop** and contain nothing else:

```powershell
# DESTRUCTIVE — deletes the entire named repository and ALL its images.
aws ecr delete-repository --repository-name food-delivery-api --force --region $Region --profile $Profile
# DESTRUCTIVE — deletes ALL objects under this lab's model prefix only.
aws s3 rm "s3://$Bucket/models/" --recursive --profile $Profile
# Check again before removing the bucket, which may contain other objects:
aws s3 ls "s3://$Bucket/" --recursive --profile $Profile
# DESTRUCTIVE — only if bucket is now empty and belongs solely to this workshop:
aws s3api delete-bucket --bucket $Bucket --region $Region --profile $Profile
```

**Note:** If your bucket has object versioning enabled, deleting current objects may leave previous versions/delete markers and `delete-bucket` may fail. Review and remove versions explicitly only when the bucket is definitely disposable. `aws s3 rm --recursive` is **not** a complete versioned-bucket cleanup.

## IAM cleanup (only if created exclusively for this practical)

After you have finished deployments, inspect IAM role and policies in the console. To remove the **GitHub deployment role only**:

```powershell
aws iam delete-role-policy --role-name food-delivery-github-deploy --policy-name food-delivery-deploy-privileges --profile $Profile
aws iam delete-role --role-name food-delivery-github-deploy --profile $Profile
```

The EC2 role and OIDC provider may be **shared with other projects**. Do not delete them casually. Before deleting a dedicated EC2 role, first detach it from the instance profile, remove its managed policies, remove the instance profile, and verify no instances still use it. Follow the IAM console dependency information.

## Confirm classroom completion

- Model training generated `480` train + `120` test rows.
- Test MAE passed the chosen threshold.
- FastAPI prediction and invalid-data handling demonstrated.
- Docker built and responded locally.
- GitHub CI showed at least one pass and one controlled failure.
- If cloud was configured: ECR image, S3 artifact and EC2 `/health` verified.
- Identified resources were cleaned up or deliberately stopped.
