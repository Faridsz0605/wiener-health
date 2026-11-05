import os
import shutil
from datetime import date

import pytest
from pyspark.sql import SparkSession

from core.state import State
from extraction import gmail as ingest
from lakehouse.src import gmail_job as gmail
from tests.fake_gmail import FakeGmail, load_messages

MESSAGES = {m["id"]: m for m in load_messages()}

pyspark_ready = pytest.mark.skipif(
    not (shutil.which("java") or os.environ.get("JAVA_HOME")), reason="Spark needs a JVM"
)


def test_parse_non_utf8_headers_and_body():
    row = gmail.parse_message(MESSAGES["latin1"])
    assert row["subject"] == "Información de envío"
    assert row["sender"] == "carla@example.es"
    assert row["body_text"] == "Información de envío: mañana."


def test_parse_html_only_and_alternative():
    assert gmail.parse_message(MESSAGES["html-only"])["body_text"] == "Hola mundo"
    alt = gmail.parse_message(MESSAGES["alternative"])
    assert alt["body_text"] == "Cuerpo plano"
    # internalDate (2024-03-05 08:05 UTC) wins over the bogus 2001 Date header.
    assert (alt["date_key"], alt["hour"]) == (20240305, 8)


def test_parse_attachment_metadata_only():
    row = gmail.parse_message(MESSAGES["attachment"])
    assert row["attachment_count"] == 1
    assert row["body_text"] == "Va adjunto."


def test_history_events():
    events = gmail.history_events(
        {
            "id": "1010",
            "messagesDeleted": [{"message": {"id": "a"}}],
            "labelsAdded": [{"message": {"id": "b"}, "labelIds": ["STARRED", "IMPORTANT"]}],
            "labelsRemoved": [{"message": {"id": "b"}, "labelIds": ["UNREAD"]}],
        }
    )
    assert [(e["message_id"], e["kind"], e["label_id"]) for e in events] == [
        ("a", "deleted", None),
        ("b", "label_added", "STARRED"),
        ("b", "label_added", "IMPORTANT"),
        ("b", "label_removed", "UNREAD"),
    ]
    assert {e["version"] for e in events} == {1010}


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module")
def gold(spark, tmp_path_factory):
    scratch = tmp_path_factory.mktemp("scratch") / ("a" * 32)
    api, state = FakeGmail(load_messages()), State(":memory:")
    ingest.sync(api, state, scratch / "bronze")
    api.add_history(labelsAdded=[{"message": {"id": "latin1"}, "labelIds": ["STARRED"]}])
    api.add_history(messagesDeleted=[{"message": {"id": "attachment"}}])
    del api.messages["attachment"]
    ingest.sync(api, state, scratch / "bronze")
    gmail.main(str(scratch))
    assert not (scratch / "bronze").exists()

    def table(name):
        return [r.asDict() for r in spark.read.parquet(str(scratch / "gold" / name)).collect()]

    return table


@pyspark_ready
def test_silver_latest_version_wins_and_deletes_are_flags(gold):
    facts = {r["message_id"]: r for r in gold("fact_email")}
    assert len(facts) == 8
    assert facts["attachment"]["is_deleted"] is True
    assert facts["attachment"]["version"] == 1010
    assert sum(r["is_deleted"] for r in facts.values()) == 1
    assert "subject" not in facts["latin1"]
    assert "body_text" not in facts["latin1"]


@pyspark_ready
def test_label_events(gold):
    events = gold("fact_label_event")
    assert [(e["message_id"], e["kind"], e["label_id"], e["version"]) for e in events] == [
        ("latin1", "label_added", "STARRED", 1009)
    ]


@pyspark_ready
def test_dim_date(gold):
    rows = sorted(gold("dim_date"), key=lambda r: r["date_key"])
    assert [(r["date_key"], r["date"], r["iso_weekday"], r["is_weekend"]) for r in rows] == [
        (20240304, date(2024, 3, 4), 1, False),
        (20240305, date(2024, 3, 5), 2, False),
    ]


@pyspark_ready
def test_daily_and_hourly_counts(gold):
    # attachment (2024-03-06) is deleted, so it is out of the metrics.
    daily = {r["date_key"]: (r["received"], r["sent"]) for r in gold("agg_email_daily")}
    assert daily == {20240304: (3, 2), 20240305: (2, 0)}
    hourly = {r["hour"]: r["received"] for r in gold("agg_email_hourly")}
    assert hourly == {8: 1, 9: 1, 10: 1, 14: 1, 23: 1}


@pyspark_ready
def test_top_senders(gold):
    top = sorted(gold("agg_top_senders"), key=lambda r: (-r["received"], r["sender"]))
    assert [(r["sender"], r["received"]) for r in top] == [
        ("alice@example.com", 2),
        ("bob@example.com", 1),
        ("carla@example.es", 1),
        ("news@example.org", 1),
    ]


@pyspark_ready
def test_reply_latency(gold):
    # 09:00 -> 09:30 (30 min) and 10:45 -> 12:00 (75 min): average 52.5.
    assert gold("agg_reply_latency") == [{"thread_id": "t-thread", "replies": 2, "avg_reply_minutes": 52.5}]


def test_failures_are_sanitized(tmp_path):
    scratch = tmp_path / ("b" * 32)
    (scratch / "gold").mkdir(parents=True)
    with pytest.raises(RuntimeError, match=r"^E_GMAIL_PIPELINE: \w+$") as err:
        gmail.main(str(scratch / "missing" / "wd-canary"))
    assert err.value.__cause__ is None
    assert "wd-canary" not in str(err.value)
