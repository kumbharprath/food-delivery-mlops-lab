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
