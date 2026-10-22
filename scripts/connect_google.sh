#!/bin/bash
# Local: print a Google Health OAuth URL. Open it in a browser while scripts/tunnel.sh is running.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
INSTANCE=$(terraform -chdir=infra output -raw instance_id)
CMD='set -a; . /opt/wiener/.env; set +a; python3 /opt/wiener/app/box/scripts/google_auth_url.py'
ID=$(aws ssm send-command --region "$AWS_REGION" --instance-ids "$INSTANCE" --document-name AWS-RunShellScript \
  --parameters "$(python3 -c 'import json,sys;print(json.dumps({"commands":[sys.argv[1]]}))' "$CMD")" \
  --query Command.CommandId --output text)
aws ssm wait command-executed --region "$AWS_REGION" --command-id "$ID" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$ID" --instance-id "$INSTANCE" \
  --query StandardOutputContent --output text
