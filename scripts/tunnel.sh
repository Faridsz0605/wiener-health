#!/bin/bash
# Local: forward box ports (OW portal 3000, OW API 8000, Analysis Store 5433) to localhost via SSM.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
INSTANCE=$(terraform -chdir=infra output -raw instance_id)
for port in 3000 8000 5433; do
  aws ssm start-session --region "$AWS_REGION" --target "$INSTANCE" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "portNumber=$port,localPortNumber=$port" >/dev/null &
done
echo "forwarding 3000 8000 5433 (Ctrl-C to stop)"
wait
