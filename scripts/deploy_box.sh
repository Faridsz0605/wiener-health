#!/bin/bash
# Runs locally. Pushes .env (+ terraform outputs) to SSM, ships the code to S3, deploys on the box.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

out() { terraform -chdir=infra output -raw "$1"; }
BUCKET=$(out raw_archive_bucket)
INSTANCE=$(out instance_id)

# Box env = .env minus local-only keys, plus infra outputs.
ENV_CONTENT="$(grep -vE '^(AWS_PROFILE|#|$)' .env)
RAW_ARCHIVE_BUCKET=$BUCKET
ALERT_TOPIC_ARN=$(out alert_topic_arn)
OW_API_URL=http://localhost:8000/api/v1"
aws ssm put-parameter --region "$AWS_REGION" --name /wiener/env --type SecureString \
  --overwrite --value "$ENV_CONTENT" >/dev/null

tar czf /tmp/wiener_app.tar.gz pyproject.toml uv.lock extraction box
aws s3 cp --region "$AWS_REGION" /tmp/wiener_app.tar.gz "s3://$BUCKET/deploy/app.tar.gz" >/dev/null
aws s3 cp --region "$AWS_REGION" box/deploy.sh "s3://$BUCKET/deploy/deploy.sh" >/dev/null

CMD_ID=$(aws ssm send-command --region "$AWS_REGION" --instance-ids "$INSTANCE" \
  --document-name AWS-RunShellScript \
  --parameters "commands=[\"aws s3 cp s3://$BUCKET/deploy/deploy.sh /tmp/deploy.sh --region $AWS_REGION && bash /tmp/deploy.sh $BUCKET $AWS_REGION\"]" \
  --query Command.CommandId --output text)
echo "ssm command $CMD_ID"
aws ssm wait command-executed --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD_ID" --instance-id "$INSTANCE" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' --output text | tail -40
