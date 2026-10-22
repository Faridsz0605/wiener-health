#!/bin/bash
# Runs ON the box (via SSM send-command). Pulls the app bundle + env, (re)starts everything.
set -euo pipefail
BUCKET="$1"
REGION="$2"

mkdir -p /opt/wiener/app
aws ssm get-parameter --region "$REGION" --name /wiener/env --with-decryption \
  --query Parameter.Value --output text > /opt/wiener/.env
chmod 600 /opt/wiener/.env

rm -rf /opt/wiener/app/*
aws s3 cp --region "$REGION" "s3://$BUCKET/deploy/app.tar.gz" - | tar xz -C /opt/wiener/app

cd /opt/wiener/app
docker compose --env-file /opt/wiener/.env -f box/docker-compose.yml pull -q
docker compose --env-file /opt/wiener/.env -f box/docker-compose.yml up -d --remove-orphans

/usr/local/bin/uv sync --frozen --no-dev

cp box/systemd/* /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wiener-extraction.timer
echo "deployed"
