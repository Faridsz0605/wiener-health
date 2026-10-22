"""Gold loader: pull gold Parquet from the Databricks gold_export Volume, reload the Analysis Store,
and (re)embed Health Summaries whose text changed."""

import hashlib
import io
import json
import os
import urllib.parse

import boto3
import httpx
import polars as pl
import psycopg

GOLD_TABLES = ("daily_health_summary", "sleep_nightly", "workout_summary", "trend_baselines")
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024


def _origin(url: str) -> str:
    # Workspace URLs copied from the browser carry paths/queries like /?o=123; the API wants scheme://host only.
    parts = urllib.parse.urlsplit(url.strip())
    return f"{parts.scheme}://{parts.netloc}"


def read_gold_table(dbx: httpx.Client, volume: str, table: str) -> pl.DataFrame:
    listing = dbx.get(f"/api/2.0/fs/directories{volume}/{table}/")
    listing.raise_for_status()
    parts = [e["path"] for e in listing.json().get("contents", []) if e["path"].endswith(".parquet")]
    frames = []
    for path in parts:
        resp = dbx.get(f"/api/2.0/fs/files{path}")
        resp.raise_for_status()
        frames.append(pl.read_parquet(io.BytesIO(resp.content)))
    return pl.concat(frames, how="diagonal_relaxed") if frames else pl.DataFrame()


def _fmt(v, unit: str = "", digits: int = 0) -> str | None:
    return None if v is None else f"{v:,.{digits}f}{unit}"


def _dev(v) -> str:
    return "" if v is None else f" ({v:+.0f}% vs 30d baseline)"


def health_summary(day: dict, sleep: dict | None, workouts: list[dict]) -> str:
    """Deterministic text for one Subject-day. Same numbers -> same text -> same hash."""
    parts = [f"{day['day']}:"]
    facts = [
        ("steps", _fmt(day.get("steps")), _dev(day.get("steps_dev_pct"))),
        (
            "resting heart rate",
            _fmt(day.get("resting_heart_rate"), " bpm"),
            _dev(day.get("resting_heart_rate_dev_pct")),
        ),
        (
            "HRV (RMSSD)",
            _fmt(day.get("heart_rate_variability_rmssd"), " ms"),
            _dev(day.get("heart_rate_variability_rmssd_dev_pct")),
        ),
        ("SpO2", _fmt(day.get("oxygen_saturation"), "%", 1), ""),
        ("skin temperature deviation", _fmt(day.get("skin_temperature_deviation"), " °C", 2), ""),
        ("active energy", _fmt(day.get("active_energy"), " kcal"), ""),
    ]
    parts += [f"{name} {value}{dev}." for name, value, dev in facts if value is not None]
    if sleep:
        parts.append(
            f"Slept {sleep['sleep_hours']:.1f} h{_dev(day.get('sleep_hours_dev_pct'))}"
            + (f", efficiency {sleep['efficiency_percent']:.0f}%" if sleep.get("efficiency_percent") else "")
            + (
                f", deep {sleep['deep_minutes']:.0f} min, REM {sleep['rem_minutes']:.0f} min"
                if sleep.get("deep_minutes") is not None and sleep.get("rem_minutes") is not None
                else ""
            )
            + "."
        )
    for w in workouts:
        parts.append(
            f"Workout: {w['workout_type']} {w['duration_minutes']:.0f} min"
            + (f", avg HR {w['avg_hr_bpm']} bpm" if w.get("avg_hr_bpm") else "")
            + "."
        )
    return " ".join(parts)


def build_summaries(gold: dict[str, pl.DataFrame]) -> list[dict]:
    days = gold["trend_baselines"].join(
        gold["daily_health_summary"].drop(
            ["steps", "resting_heart_rate", "heart_rate_variability_rmssd"], strict=False
        ),
        on=["subject_id", "day"],
        how="left",
    )
    sleep = {(r["subject_id"], r["day"]): r for r in gold["sleep_nightly"].to_dicts()}
    workouts: dict[tuple, list[dict]] = {}
    for w in gold["workout_summary"].to_dicts():
        workouts.setdefault((w["subject_id"], w["day"]), []).append(w)
    out = []
    for d in days.sort("day").to_dicts():
        k = (d["subject_id"], d["day"])
        text = health_summary(d, sleep.get(k), workouts.get(k, []))
        out.append(
            {
                "subject_id": d["subject_id"],
                "day": d["day"],
                "content": text,
                "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return out


def embed(bedrock, text: str) -> list[float]:
    resp = bedrock.invoke_model(modelId=EMBED_MODEL, body=json.dumps({"inputText": text, "dimensions": EMBED_DIM}))
    return json.loads(resp["body"].read())["embedding"]


SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS health_summaries (
    subject_id text NOT NULL,
    day date NOT NULL,
    content text NOT NULL,
    content_hash text NOT NULL,
    embedding vector({EMBED_DIM}) NOT NULL,
    PRIMARY KEY (subject_id, day)
);
"""


def ensure_reader_role(conn, password: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'wiener_reader'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE wiener_reader LOGIN")
        cur.execute(psycopg.sql.SQL("ALTER ROLE wiener_reader PASSWORD {}").format(psycopg.sql.Literal(password)))
        cur.execute("GRANT USAGE ON SCHEMA public TO wiener_reader")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO wiener_reader")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO wiener_reader")


def upsert_summaries(conn, bedrock, summaries: list[dict]) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT subject_id, day, content_hash FROM health_summaries")
        existing = {(s, d): h for s, d, h in cur.fetchall()}
        changed = [s for s in summaries if existing.get((s["subject_id"], s["day"])) != s["content_hash"]]
        for s in changed:
            cur.execute(
                """INSERT INTO health_summaries (subject_id, day, content, content_hash, embedding)
                   VALUES (%s, %s, %s, %s, %s::vector)
                   ON CONFLICT (subject_id, day) DO UPDATE SET content = EXCLUDED.content,
                   content_hash = EXCLUDED.content_hash, embedding = EXCLUDED.embedding""",
                (s["subject_id"], s["day"], s["content"], s["content_hash"], str(embed(bedrock, s["content"]))),
            )
    return len(changed)


def main() -> None:
    dbx = httpx.Client(
        base_url=_origin(os.environ["DATABRICKS_HOST"]),
        headers={"Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}"},
        timeout=120,
    )
    volume = os.environ.get("GOLD_EXPORT_VOLUME", "/Volumes/workspace/wiener/gold_export")
    gold = {t: read_gold_table(dbx, volume, t) for t in GOLD_TABLES}
    if gold["trend_baselines"].is_empty():
        print("no gold data yet")
        return

    uri = f"postgresql://wiener:{os.environ['ANALYSIS_DB_PASSWORD']}@127.0.0.1:5433/analysis"
    for table, df in gold.items():
        # Truncate + reload: gold is small and fully recomputed each run.
        df.write_database(table, uri, if_table_exists="replace", engine="adbc")

    with psycopg.connect(uri, autocommit=True) as conn:
        conn.execute(SCHEMA_SQL)
        n = upsert_summaries(
            conn, boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"]), build_summaries(gold)
        )
        ensure_reader_role(conn, os.environ["ANALYSIS_READER_PASSWORD"])
    print(f"reloaded {len(gold)} gold tables, embedded {n} changed Health Summaries")


if __name__ == "__main__":
    main()
