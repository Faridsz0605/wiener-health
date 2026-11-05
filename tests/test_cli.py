import io
import sqlite3
from datetime import date
from types import SimpleNamespace

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from databricks.sdk.service.jobs import RunResultState

from core import cli
from core.config import Config
from core.state import State
from tests.fake_files import FakeFiles
from tests.fake_gmail import FakeGmail, load_messages

EMAIL = {"message_id": "a", "thread_id": "t", "version": 1, "sender": "x@example.com"}
EMAIL |= {"label_ids": ["INBOX"], "is_deleted": False}


def _parquet(rows):
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), buf)
    return buf.getvalue()


class FakeJobs:
    """Plays the Databricks job: checks inputs, drops bronze, writes the given Gold rows."""

    def __init__(self, files, gold, result=RunResultState.SUCCESS):
        self.files, self.gold, self.result = files, gold, result
        self.params = []

    def create(self, name, tasks, environments):
        self.params.append(tasks[0].spark_python_task.parameters)
        return SimpleNamespace(job_id=1)

    def run_now(self, job_id):
        (scratch,) = self.params[-1]
        assert f"{scratch}/job.py" in self.files.objects
        for path in [p for p in self.files.objects if p.startswith(f"{scratch}/bronze/")]:
            del self.files.objects[path]
        for name, rows in self.gold.items():
            self.files.objects[f"{scratch}/gold/{name}/part-0.parquet"] = _parquet(rows)
            self.files.objects[f"{scratch}/gold/{name}/_SUCCESS"] = b""
        return SimpleNamespace(result=lambda: None, run_id=7)

    def get_run(self, run_id):
        state = SimpleNamespace(result_state=self.result)
        return SimpleNamespace(state=state, tasks=[SimpleNamespace(run_id=8)])

    def get_run_output(self, run_id):
        return SimpleNamespace()

    def delete(self, job_id):
        pass


def _run(tmp_path, gold, fmt="duckdb", state=None, result=RunResultState.SUCCESS):
    files = FakeFiles()
    w = SimpleNamespace(files=files, jobs=FakeJobs(files, gold, result))
    cfg = Config(data_dir=tmp_path / "data", databricks_host="h", volume="/Volumes/w/d/s")
    state = state or State(":memory:")
    counts = cli.gmail_run(w, FakeGmail(load_messages()), state, cfg, fmt=fmt, out=tmp_path / "out")
    return w, state, counts


GOLD = {
    "fact_email": [EMAIL, {**EMAIL, "message_id": "b", "version": 2}],
    "dim_date": [{"date_key": 20240304, "date": date(2024, 3, 4)}],
    "fact_label_event": [{"message_id": "a", "version": 3, "kind": "label_added", "label_id": "X"}],
    "agg_email_daily": [{"date_key": 20240304, "received": 2, "sent": 0}],
}


@pytest.mark.parametrize("fmt", ["parquet", "csv", "duckdb", "sqlite"])
def test_run_exports_and_leaves_zero_objects(tmp_path, fmt):
    w, state, counts = _run(tmp_path, GOLD, fmt)
    assert w.files.objects == {}
    (params,) = w.jobs.params
    assert params[0].startswith("/Volumes/w/d/s/")
    assert counts == {"fact_email": 2, "dim_date": 1, "fact_label_event": 1, "agg_email_daily": 1}
    assert state.snapshot_done("gmail-batch", next((tmp_path / "data").rglob("*.jsonl")).name)
    assert len(list((tmp_path / "out").iterdir())) == (4 if fmt in ("parquet", "csv") else 1)


@pytest.mark.parametrize("fmt", ["duckdb", "sqlite"])
def test_destination_merge_rules(tmp_path, fmt):
    state = State(":memory:")
    _run(tmp_path, GOLD, fmt, state)
    tombstone = dict.fromkeys(EMAIL) | {"message_id": "a", "version": 5, "is_deleted": True}
    stale = {**EMAIL, "message_id": "b", "version": 1, "sender": "stale@example.com"}
    second = {
        "fact_email": [tombstone, stale],
        "fact_label_event": GOLD["fact_label_event"],
        "agg_email_daily": [{"date_key": 20240305, "received": 1, "sent": 0}],
    }
    _run(tmp_path, second, fmt, state)
    connect = sqlite3.connect if fmt == "sqlite" else duckdb.connect
    db = connect(str(tmp_path / "out" / f"wiener-data.{fmt}"))
    rows = db.execute("SELECT message_id, version, sender, is_deleted FROM fact_email ORDER BY 1")
    assert [tuple(r) for r in rows.fetchall()] == [
        ("a", 5, "x@example.com", True),
        ("b", 2, "x@example.com", False),
    ]
    assert db.execute("SELECT count(*) FROM fact_label_event").fetchone()[0] == 2
    assert db.execute("SELECT date_key FROM agg_email_daily").fetchall() == [(20240305,)]
    assert db.execute("SELECT label_ids FROM fact_email WHERE message_id = 'b'").fetchone() == ('["INBOX"]',)


def test_failed_job_cleans_up_and_keeps_batches_pending(tmp_path):
    state = State(":memory:")
    with pytest.raises(RuntimeError, match="E_JOB_FAILED"):
        _run(tmp_path, GOLD, state=state, result=RunResultState.FAILED)
    batch = next((tmp_path / "data").rglob("*.jsonl")).name
    assert not state.snapshot_done("gmail-batch", batch)
    assert not (tmp_path / "out").exists()


def test_leftover_objects_fail_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "remove_tree", lambda files, path: None)
    with pytest.raises(RuntimeError, match="E_RETENTION"):
        _run(tmp_path, GOLD)


def test_unexpected_gold_table_name_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unexpected gold table name"):
        _run(tmp_path, {"fact_email; DROP": [EMAIL]})


def test_main_requires_databricks_credentials(monkeypatch):
    monkeypatch.delenv("DATABRICKS_HOST", raising=False)
    with pytest.raises(SystemExit):
        cli.main(["gmail", "run"])
