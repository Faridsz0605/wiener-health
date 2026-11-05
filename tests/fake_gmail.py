import json
from pathlib import Path

from extraction.gmail import API

FIXTURES = Path(__file__).parent / "fixtures" / "gmail" / "messages.json"


def load_messages():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


class Response:
    def __init__(self, status, body=None):
        self.status_code = status
        self.body = body

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeGmail:
    """Synthetic mailbox speaking the Gmail REST shapes used by extraction.gmail."""

    page_size = 3

    def __init__(self, messages):
        self.messages = {m["id"]: m for m in messages}
        self.history = []
        self.history_id = max(int(m["historyId"]) for m in messages)
        self.oldest_history = 0
        self.calls = []

    def add_history(self, **change):
        self.history_id += 1
        self.history.append({"id": str(self.history_id), **change})

    def _page(self, items, key, params):
        start = int(params.get("pageToken", 0))
        body = {key: items[start : start + self.page_size]}
        if start + self.page_size < len(items):
            body["nextPageToken"] = str(start + self.page_size)
        return Response(200, body)

    def get(self, url, params):
        path = url.removeprefix(API + "/")
        self.calls.append(path)
        if path == "profile":
            return Response(200, {"historyId": str(self.history_id)})
        if path == "messages":
            refs = [{"id": i, "threadId": m["threadId"]} for i, m in self.messages.items()]
            return self._page(refs, "messages", params)
        if path == "history":
            start = int(params["startHistoryId"])
            if start < self.oldest_history:
                return Response(404)
            return self._page([h for h in self.history if int(h["id"]) > start], "history", params)
        msg = self.messages.get(path.removeprefix("messages/"))
        return Response(200, msg) if msg else Response(404)
