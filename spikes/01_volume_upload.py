"""Spike 1: upload JSON from local to a Volume (Files API) and read it back."""

import io
import json

from _common import client, report, scratch

from core.volume import count_objects, remove_tree

w = client()
_, path = scratch()
payload = json.dumps({"id": "synthetic-1", "subject": "hello"}).encode()
try:
    w.files.upload(f"{path}/bronze/sample.json", io.BytesIO(payload), overwrite=True)
    same = w.files.download(f"{path}/bronze/sample.json").contents.read() == payload
finally:
    remove_tree(w.files, path)
left = count_objects(w.files, path)
report("01", ok=same and left == 0, detail=f"roundtrip={same}, objects left={left}")
