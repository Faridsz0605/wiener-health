import json
from datetime import UTC, datetime

import httpx

from extraction.extract import raw_key, run

SUBJECT = "11111111-1111-1111-1111-111111111111"


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path.removeprefix("/api/v1")
    if path == "/users":
        return httpx.Response(200, json={"items": [{"id": SUBJECT}], "total": 1})
    if path.endswith("/timeseries"):
        # two pages to exercise cursor pagination
        if request.url.params.get("cursor") == "c2":
            return httpx.Response(200, json={"data": [{"v": 2}], "pagination": {"has_more": False}})
        return httpx.Response(200, json={"data": [{"v": 1}], "pagination": {"has_more": True, "next_cursor": "c2"}})
    assert request.url.params.get("start_date"), "events need start_date"
    return httpx.Response(200, json={"data": [], "pagination": {"has_more": False, "next_cursor": None}})


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = json.loads(Body)


def test_run_writes_one_object_per_entity_with_all_pages():
    s3 = FakeS3()
    now = datetime(2025, 10, 20, 6, 0, tzinfo=UTC)
    client = httpx.Client(base_url="http://ow/api/v1", transport=httpx.MockTransport(handler))

    keys = run(client, s3, "bucket", 3, now)

    assert len(keys) == 3
    ts = s3.objects[raw_key("timeseries", SUBJECT, now)]
    assert ts["data"] == [{"v": 1}, {"v": 2}]
    assert ts["subject_id"] == SUBJECT
    assert ts["window_start"].startswith("2025-10-17")


def test_raw_key_layout():
    now = datetime(2025, 10, 20, 6, 0, tzinfo=UTC)
    assert raw_key("sleep", SUBJECT, now) == f"raw/open_wearables/sleep/date=2025-10-20/20251020T060000Z_{SUBJECT}.json"
