"""Runs ON the box: print a fresh Google Health OAuth URL for the first Subject."""

import json
import os
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/users?limit=1", headers={"X-Open-Wearables-API-Key": os.environ["OW_API_KEY"]}
)
subject_id = json.load(urllib.request.urlopen(req))["items"][0]["id"]
req = urllib.request.Request(
    f"http://127.0.0.1:8000/api/v1/oauth/google_health/authorize?user_id={subject_id}",
    headers={"X-Open-Wearables-API-Key": os.environ["OW_API_KEY"]},
)
print(json.load(urllib.request.urlopen(req))["authorization_url"])
