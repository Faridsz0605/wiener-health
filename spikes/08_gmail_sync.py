"""Spike 8: real Gmail sync against a test account. Prints counts only, never content.

uv run python spikes/08_gmail_sync.py [client_secret.json] [--expire]
--expire forces a very old historyId to check the 404 -> full resync path.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import _common  # noqa: F401 - puts the repo root on sys.path

from core import config, secrets
from core.state import State
from extraction import gmail

args = [a for a in sys.argv[1:] if a != "--expire"]
cfg = config.load()
if not secrets.get(gmail.TOKEN_KEY):
    if not args:
        sys.exit("pending: pass the path to your own OAuth client_secret.json")
    gmail.authorize(Path(args[0]))
cfg.data_dir.mkdir(parents=True, exist_ok=True)
state = State(cfg.data_dir / "state.db")
if "--expire" in sys.argv:
    state.set_watermark(gmail.SOURCE, "1")
path = gmail.sync(gmail.session(), state, cfg.data_dir / "bronze" / "gmail")
records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
counts = Counter(r["type"] for r in records[1:])
print(f"spike 08: {records[0]['data']} counts={dict(counts)} file={path}")
