import re
import uuid

_RUN_ID = re.compile(r"[0-9a-f]{32}")


def new() -> str:
    return uuid.uuid4().hex


def scratch_path(volume: str, run_id: str) -> str:
    # A malformed id could point cleanup at a shared or parent path.
    if not _RUN_ID.fullmatch(run_id):
        msg = "invalid run_id"
        raise ValueError(msg)
    return f"{volume.rstrip('/')}/{run_id}"
