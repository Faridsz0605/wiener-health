import json

import pytest

from core.state import State
from extraction import gmail
from tests.fake_gmail import FakeGmail, load_messages


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _types(records):
    return [r["type"] for r in records]


def test_first_sync_is_full_and_paginated(tmp_path):
    api, state = FakeGmail(load_messages()), State(":memory:")
    records = _read(gmail.sync(api, state, tmp_path))
    assert records[0] == {"type": "sync", "data": {"mode": "full", "historyId": "1008"}}
    assert [r["data"]["id"] for r in records[1:]] == [m["id"] for m in load_messages()]
    assert api.calls.count("messages") == 3  # 8 refs, page size 3
    assert state.watermark("gmail") == "1008"


def test_incremental_sync_reads_history_since_watermark(tmp_path):
    api, state = FakeGmail(load_messages()), State(":memory:")
    gmail.sync(api, state, tmp_path / "1")
    new = {**load_messages()[0], "id": "new-1", "historyId": "1009"}
    api.messages["new-1"] = new
    api.add_history(messagesAdded=[{"message": {"id": "new-1", "threadId": "t-thread"}}])
    api.add_history(labelsAdded=[{"message": {"id": "latin1"}, "labelIds": ["STARRED"]}])
    api.add_history(messagesDeleted=[{"message": {"id": "html-only"}}])
    del api.messages["html-only"]

    records = _read(gmail.sync(api, state, tmp_path / "2"))
    assert records[0]["data"] == {"mode": "incremental", "historyId": "1011"}
    assert _types(records[1:]) == ["history"] * 3 + ["message"]
    assert records[-1]["data"]["id"] == "new-1"
    assert state.watermark("gmail") == "1011"


def test_added_then_deleted_message_is_skipped(tmp_path):
    api, state = FakeGmail(load_messages()), State(":memory:")
    gmail.sync(api, state, tmp_path / "1")
    api.add_history(messagesAdded=[{"message": {"id": "gone"}}])
    api.add_history(messagesDeleted=[{"message": {"id": "gone"}}])
    records = _read(gmail.sync(api, state, tmp_path / "2"))
    assert _types(records[1:]) == ["history", "history"]


def test_expired_history_id_triggers_full_resync(tmp_path):
    api, state = FakeGmail(load_messages()), State(":memory:")
    state.set_watermark("gmail", "5")
    api.oldest_history = 900
    records = _read(gmail.sync(api, state, tmp_path))
    assert records[0]["data"]["mode"] == "full"
    assert len(records) == 1 + len(load_messages())


def test_session_requires_stored_token(monkeypatch):
    monkeypatch.setattr(gmail.secrets, "get", lambda _: None)
    with pytest.raises(RuntimeError, match="not authorized"):
        gmail.session()


def test_fixtures_are_synthetic():
    senders = {h["value"] for m in load_messages() for h in m["payload"]["headers"] if h["name"] in {"From", "To"}}
    assert all(s.rstrip(">").rsplit("@", 1)[1] in {"example.com", "example.org", "example.es"} for s in senders)
