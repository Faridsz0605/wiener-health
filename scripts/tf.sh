#!/bin/bash
# Local: terraform with .env loaded (exports TF_VAR_* from .env keys).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export TF_VAR_region="$AWS_REGION" TF_VAR_alert_email="$ALERT_EMAIL"
exec terraform -chdir=infra "$@"
