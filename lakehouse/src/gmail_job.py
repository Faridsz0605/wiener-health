"""Gmail job: Bronze (raw JSONL batch) -> Silver -> Gold, inside scratch/<run_id>/.

Self-contained (stdlib + pyspark) so it can be uploaded as a Databricks spark_python_task.
Never prints rows: run output persists in the run history.
"""

import base64
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F  # noqa: N812
from pyspark.sql import types as T  # noqa: N812

SILVER_EMAIL = T.StructType(
    [
        T.StructField("message_id", T.StringType()),
        T.StructField("thread_id", T.StringType()),
        T.StructField("version", T.LongType()),
        T.StructField("internal_ms", T.LongType()),
        T.StructField("date_key", T.IntegerType()),
        T.StructField("hour", T.IntegerType()),
        T.StructField("sender", T.StringType()),
        T.StructField("subject", T.StringType()),
        T.StructField("body_text", T.StringType()),
        T.StructField("label_ids", T.ArrayType(T.StringType())),
        T.StructField("attachment_count", T.IntegerType()),
        T.StructField("is_sent", T.BooleanType()),
        T.StructField("is_deleted", T.BooleanType()),
    ]
)
EVENT = T.StructType(
    [
        T.StructField("message_id", T.StringType()),
        T.StructField("version", T.LongType()),
        T.StructField("kind", T.StringType()),
        T.StructField("label_id", T.StringType()),
    ]
)


def _decode(value: str) -> str:
    """RFC 2047 encoded-words (e.g. ISO-8859-1 subjects) to text; plain values pass through."""
    return str(make_header(decode_header(value)))


def _parts(part: dict) -> list[dict]:
    return [part] + [p for child in part.get("parts", []) for p in _parts(child)]


def _body_text(parts: list[dict]) -> str:
    def text_parts(mime: str) -> list[dict]:
        return [p for p in parts if p["mimeType"] == mime and p.get("body", {}).get("data")]

    chosen = text_parts("text/plain") or text_parts("text/html")
    if not chosen:
        return ""
    part = chosen[0]
    header = Message()
    for h in part.get("headers", []):
        header[h["name"]] = h["value"]
    raw = base64.urlsafe_b64decode(part["body"]["data"] + "==")
    text = raw.decode(header.get_content_charset("utf-8"), errors="replace")
    if part["mimeType"] == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def parse_message(m: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in m["payload"].get("headers", [])}
    parts = _parts(m["payload"])
    # internalDate is canonical: the Date header can be missing or wrong.
    received = datetime.fromtimestamp(int(m["internalDate"]) / 1000, UTC)
    return {
        "message_id": m["id"],
        "thread_id": m["threadId"],
        "version": int(m["historyId"]),
        "internal_ms": int(m["internalDate"]),
        "date_key": int(received.strftime("%Y%m%d")),
        "hour": received.hour,
        "sender": parseaddr(_decode(headers.get("from", "")))[1].lower(),
        "subject": _decode(headers.get("subject", "")),
        "body_text": _body_text(parts),
        "label_ids": m.get("labelIds", []),
        "attachment_count": sum(1 for p in parts if p.get("filename")),
        "is_sent": "SENT" in m.get("labelIds", []),
        "is_deleted": False,
    }


def history_events(h: dict) -> list[dict]:
    version = int(h["id"])
    events = [
        {"message_id": d["message"]["id"], "version": version, "kind": "deleted", "label_id": None}
        for d in h.get("messagesDeleted", [])
    ]
    for key, kind in (("labelsAdded", "label_added"), ("labelsRemoved", "label_removed")):
        events += [
            {"message_id": c["message"]["id"], "version": version, "kind": kind, "label_id": label}
            for c in h.get(key, [])
            for label in c["labelIds"]
        ]
    return events


def silver(spark: SparkSession, bronze_path: str) -> tuple[DataFrame, DataFrame]:
    lines = spark.read.text(bronze_path).select(
        F.get_json_object("value", "$.type").alias("type"),
        F.get_json_object("value", "$.data").alias("data"),
    )
    parse = F.udf(lambda s: parse_message(json.loads(s)), SILVER_EMAIL)
    events_of = F.udf(lambda s: history_events(json.loads(s)), T.ArrayType(EVENT))
    messages = lines.where("type = 'message'").select(parse("data").alias("m")).select("m.*")
    events = lines.where("type = 'history'").select(F.explode(events_of("data")).alias("e"))
    events = events.select("e.*")
    tombstones = events.where("kind = 'deleted'").selectExpr("message_id", "version", "true AS is_deleted")
    # Latest version wins: deterministic dedup when a message appears several times in a batch.
    # shortcut: a full resync cannot see deletions made while the historyId was expired.
    latest = Window.partitionBy("message_id").orderBy(F.desc("version"))
    email = (
        messages.unionByName(tombstones, allowMissingColumns=True)
        .withColumn("_rn", F.row_number().over(latest))
        .where("_rn = 1")
        .drop("_rn")
    )
    return email, events.where("kind != 'deleted'")


def gold(email: DataFrame, label_events: DataFrame) -> dict[str, DataFrame]:
    fact_email = email.drop("subject", "body_text")
    live = fact_email.where("NOT is_deleted")
    received = live.where("NOT is_sent")
    by_thread = Window.partitionBy("thread_id").orderBy("internal_ms")
    replies = (
        live.withColumn("prev_ms", F.lag("internal_ms").over(by_thread))
        .withColumn("prev_sent", F.lag("is_sent").over(by_thread))
        .where("is_sent AND prev_sent = false")
    )
    days = live.select(F.to_date(F.col("date_key").cast("string"), "yyyyMMdd").alias("d"))
    dim_date = (
        days.agg(F.sequence(F.min("d"), F.max("d")).alias("ds"))
        .select(F.explode("ds").alias("date"))
        .select(
            F.date_format("date", "yyyyMMdd").cast("int").alias("date_key"),
            "date",
            F.year("date").alias("year"),
            F.month("date").alias("month"),
            F.dayofmonth("date").alias("day"),
            ((F.dayofweek("date") + 5) % 7 + 1).alias("iso_weekday"),
            F.dayofweek("date").isin(1, 7).alias("is_weekend"),
        )
    )
    # shortcut: metrics cover this batch only; recompute at the destination for incremental runs.
    return {
        "dim_date": dim_date,
        "fact_email": fact_email,
        "fact_label_event": label_events,
        "agg_email_daily": live.groupBy("date_key").agg(
            F.sum(F.when(~F.col("is_sent"), 1).otherwise(0)).alias("received"),
            F.sum(F.when(F.col("is_sent"), 1).otherwise(0)).alias("sent"),
        ),
        "agg_email_hourly": received.groupBy("hour").agg(F.count("*").alias("received")),
        "agg_top_senders": received.groupBy("sender")
        .agg(F.count("*").alias("received"))
        .orderBy(F.desc("received"), "sender")
        .limit(10),
        "agg_reply_latency": replies.groupBy("thread_id").agg(
            F.count("*").alias("replies"),
            F.avg((F.col("internal_ms") - F.col("prev_ms")) / 60000).alias("avg_reply_minutes"),
        ),
    }


def run(spark: SparkSession, scratch: str) -> None:
    email, label_events = silver(spark, f"{scratch}/bronze")
    for name, df in gold(email, label_events).items():
        df.write.mode("overwrite").parquet(f"{scratch}/gold/{name}")


def main(scratch: str) -> None:
    ok = False
    try:
        run(SparkSession.builder.getOrCreate(), scratch)
        ok = True
    except Exception as e:  # noqa: BLE001 - every failure must be sanitized
        # Generic message only: exception text may carry message content into run history.
        msg = f"E_GMAIL_PIPELINE: {type(e).__name__}"
        raise RuntimeError(msg) from None
    finally:
        # REVIEW: FUSE access to /Volumes from serverless jobs (spike 4).
        shutil.rmtree(f"{scratch}/bronze", ignore_errors=True)
        if not ok:
            shutil.rmtree(f"{scratch}/gold", ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1])
