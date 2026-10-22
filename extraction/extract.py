"""Extraction: pull an Extraction Window from Open Wearables into the Raw Archive (S3)."""

import json
import os
from datetime import UTC, datetime, timedelta

import boto3
import httpx

# entity -> (path under /users/{id}/, start param, end param, extra params)
ENTITIES = {
    "timeseries": ("timeseries", "start_time", "end_time", {}),
    "sleep": ("events/sleep", "start_date", "end_date", {"include": ["stages"]}),
    "workouts": ("events/workouts", "start_date", "end_date", {"include": ["zones", "segments"]}),
}


def fetch_all(client: httpx.Client, path: str, params: dict) -> list[dict]:
    rows, cursor = [], None
    while True:
        page = client.get(path, params={**params, "limit": 1000, **({"cursor": cursor} if cursor else {})})
        page.raise_for_status()
        body = page.json()
        rows += body["data"]
        cursor = body["pagination"].get("next_cursor")
        if not body["pagination"]["has_more"] or not cursor:
            return rows


def list_subject_ids(client: httpx.Client) -> list[str]:
    # shortcut: first 100 users only, fine for single Subject; paginate when multi-Subject
    resp = client.get("/users", params={"limit": 100})
    resp.raise_for_status()
    return [u["id"] for u in resp.json()["items"]]


def raw_key(entity: str, subject_id: str, extracted_at: datetime) -> str:
    stamp = extracted_at.strftime("%Y%m%dT%H%M%SZ")
    return f"raw/open_wearables/{entity}/date={extracted_at:%Y-%m-%d}/{stamp}_{subject_id}.json"


def run(client: httpx.Client, s3, bucket: str, window_days: int, now: datetime) -> list[str]:
    start = (now - timedelta(days=window_days)).isoformat()
    end = now.isoformat()
    keys = []
    for subject_id in list_subject_ids(client):
        for entity, (path, start_param, end_param, extra) in ENTITIES.items():
            rows = fetch_all(client, f"/users/{subject_id}/{path}", {start_param: start, end_param: end, **extra})
            envelope = {
                "data_source": "open_wearables",
                "entity": entity,
                "subject_id": subject_id,
                "extracted_at": now.isoformat(),
                "window_start": start,
                "window_end": end,
                "data": rows,
            }
            key = raw_key(entity, subject_id, now)
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(envelope).encode(), ContentType="application/json")
            keys.append(key)
    return keys


def main() -> None:
    client = httpx.Client(
        base_url=os.environ["OW_API_URL"],
        headers={"X-Open-Wearables-API-Key": os.environ["OW_API_KEY"]},
        timeout=60,
    )
    keys = run(
        client,
        boto3.client("s3", region_name=os.environ["AWS_REGION"]),
        os.environ["RAW_ARCHIVE_BUCKET"],
        int(os.environ.get("EXTRACTION_WINDOW_DAYS", "3")),
        datetime.now(UTC),
    )
    print(f"wrote {len(keys)} objects: {keys}")


if __name__ == "__main__":
    main()
