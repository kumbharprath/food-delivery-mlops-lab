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
