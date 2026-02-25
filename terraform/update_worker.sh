#!/usr/bin/env bash
set -e

HOST="$1"
if [[ -z "$HOST" ]]; then
    echo "Usage: $0 <ec2-ip-address>"
    exit 1
fi

SSH_TARGET="ubuntu@$HOST"

echo "==> Fetching secrets from Heroku..."
ENV_FILE=$(mktemp)
heroku config --app geodatalytics --shell > "$ENV_FILE"

echo "==> Uploading env file to remote machine..."
scp "$ENV_FILE" "$SSH_TARGET:/home/ubuntu/geodatalytics.prod.env"
rm "$ENV_FILE"

echo "==> Pulling changes..."
ssh "$SSH_TARGET" 'cd /home/ubuntu/geodatalytics && git pull'

echo "==> Adding SOURCE_VERSION to env file..."
ssh "$SSH_TARGET" 'echo "SOURCE_VERSION=$(git -C /home/ubuntu/geodatalytics rev-parse HEAD)" >> /home/ubuntu/geodatalytics.prod.env'

echo "==> Restarting celery service..."
ssh "$SSH_TARGET" 'sudo systemctl restart celery'

echo "==> Done! Celery worker is restarted on $HOST"
