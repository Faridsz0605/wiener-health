"""Gmail extractor: full sync, then incremental via history.list (CDC). Raw dump = user Bronze."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from core import secrets
from core.state import State

API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SOURCE = "gmail"
TOKEN_KEY = "gmail_token"  # noqa: S105 - keyring entry name, not a secret


def authorize(client_secrets: Path) -> None:
    """Consent flow with the user's own OAuth client; the token goes to the OS keyring."""
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    secrets.put(TOKEN_KEY, flow.run_local_server(port=0).to_json())


def session() -> AuthorizedSession:
    info = secrets.get(TOKEN_KEY)
    if not info:
        msg = "Gmail is not authorized yet"
        raise RuntimeError(msg)
    # shortcut: refreshed access tokens are not written back; the refresh token stays valid.
    return AuthorizedSession(Credentials.from_authorized_user_info(json.loads(info), SCOPES))


def _get(http: AuthorizedSession, path: str, **params: str) -> dict | None:
    resp = http.get(f"{API}/{path}", params=params)
    if resp.status_code == HTTPStatus.NOT_FOUND:
        return None
    resp.raise_for_status()
    return resp.json()


def _pages(http: AuthorizedSession, path: str, key: str, **params: str) -> Iterator[dict]:
    while True:
        page = _get(http, path, **params)
        if page is None:
            raise LookupError(path)
        yield from page.get(key, [])
        if "nextPageToken" not in page:
            return
        params["pageToken"] = page["nextPageToken"]


def _messages(http: AuthorizedSession, ids: Iterator[str]) -> list[dict]:
    # Messages deleted between listing and fetching return 404 and are skipped.
    found = (_get(http, f"messages/{i}", format="full") for i in dict.fromkeys(ids))
    return [{"type": "message", "data": m} for m in found if m]


def _incremental(http: AuthorizedSession, start: str) -> list[dict] | None:
    try:
        history = list(_pages(http, "history", "history", startHistoryId=start))
    except LookupError:
        return None  # historyId too old: caller falls back to a full resync
    added = (a["message"]["id"] for h in history for a in h.get("messagesAdded", []))
    return [{"type": "history", "data": h} for h in history] + _messages(http, added)


def sync(http: AuthorizedSession, state: State, out_dir: Path) -> Path:
    """Write one raw JSONL batch and advance the historyId watermark."""
    # Taken before listing: changes made meanwhile are replayed next run (MERGE is idempotent).
    history_id = _get(http, "profile")["historyId"]
    start = state.watermark(SOURCE)
    records = _incremental(http, start) if start else None
    mode = "incremental"
    if records is None:
        mode = "full"
        records = _messages(http, (m["id"] for m in _pages(http, "messages", "messages")))
    header = {"type": "sync", "data": {"mode": mode, "historyId": history_id}}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"gmail-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in [header, *records])
    state.set_watermark(SOURCE, history_id)
    return path
