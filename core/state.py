import sqlite3
from collections.abc import Iterable
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watermark (source TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS seen_hash (source TEXT, hash TEXT, PRIMARY KEY (source, hash));
CREATE TABLE IF NOT EXISTS snapshot (source TEXT, id TEXT, PRIMARY KEY (source, id));
"""


class State:
    """Minimal client-side state (ADR 0005): watermarks, seen hashes, processed snapshots."""

    def __init__(self, path: Path | str) -> None:
        self.db = sqlite3.connect(path)
        self.db.executescript(_SCHEMA)

    def watermark(self, source: str) -> str | None:
        row = self.db.execute("SELECT value FROM watermark WHERE source = ?", (source,)).fetchone()
        return row[0] if row else None

    def set_watermark(self, source: str, value: str) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO watermark VALUES (?, ?)", (source, value))

    def clear_watermark(self, source: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM watermark WHERE source = ?", (source,))

    def add_hashes(self, source: str, hashes: Iterable[str]) -> list[str]:
        """Record hashes and return only the ones not seen before."""
        new = []
        with self.db:
            for h in dict.fromkeys(hashes):
                cur = self.db.execute("INSERT OR IGNORE INTO seen_hash VALUES (?, ?)", (source, h))
                if cur.rowcount:
                    new.append(h)
        return new

    def snapshot_done(self, source: str, snapshot_id: str) -> bool:
        sql = "SELECT 1 FROM snapshot WHERE source = ? AND id = ?"
        return self.db.execute(sql, (source, snapshot_id)).fetchone() is not None

    def mark_snapshot(self, source: str, snapshot_id: str) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO snapshot VALUES (?, ?)", (source, snapshot_id))
