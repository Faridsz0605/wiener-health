"""Shared helpers for platform spikes. Synthetic payloads only."""

import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

# shortcut: the repo is not an installed package; spikes run as plain scripts from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config, run_id, secrets
from core.jobs import run_script  # noqa: F401 - re-exported for spike scripts


def credentials() -> tuple[str, str]:
    host = config.load().databricks_host
    token = host and secrets.get("databricks_token")
    if not host or not token:
        sys.exit("pending: export DATABRICKS_HOST and run spikes/00_store_token.py")
    return host, token


def client() -> WorkspaceClient:
    host, token = credentials()
    return WorkspaceClient(host=host, token=token)


def scratch() -> tuple[str, str]:
    rid = run_id.new()
    return rid, run_id.scratch_path(config.load().volume, rid)


def report(spike: str, *, ok: bool, detail: str) -> None:
    print(f"spike {spike}: {'PASS' if ok else 'FAIL'} - {detail}")
