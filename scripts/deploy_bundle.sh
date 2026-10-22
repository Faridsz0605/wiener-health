#!/bin/bash
# Local: deploy the Databricks Asset Bundle with .env loaded.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export BUNDLE_VAR_alert_email="$ALERT_EMAIL"
cd lakehouse
databricks bundle validate
databricks bundle deploy
