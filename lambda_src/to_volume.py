"""S3 ObjectCreated (raw/...) -> copy file into the Unity Catalog landing Volume via the Files API."""

import json
import os
import urllib.parse
import urllib.request

import boto3

s3 = boto3.client("s3")
_creds = None


def databricks_creds() -> tuple[str, str]:
    global _creds
    if _creds is None:
        env_file = boto3.client("ssm").get_parameter(Name="/wiener/env", WithDecryption=True)["Parameter"]["Value"]
        env = dict(line.split("=", 1) for line in env_file.splitlines() if "=" in line and not line.startswith("#"))
        _creds = (env["DATABRICKS_HOST"].rstrip("/"), env["DATABRICKS_TOKEN"])
    return _creds


def volume_path(key: str) -> str:
    # raw/open_wearables/sleep/date=.../x.json -> /Volumes/<catalog>/<schema>/landing/open_wearables/sleep/date=.../x.json
    return f"{os.environ['LANDING_VOLUME']}/{key.removeprefix('raw/')}"


def handler(event, _context):
    host, token = databricks_creds()
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        req = urllib.request.Request(
            f"{host}/api/2.0/fs/files{urllib.parse.quote(volume_path(key))}?overwrite=true",
            data=body,
            method="PUT",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(json.dumps({"key": key, "status": resp.status}))
