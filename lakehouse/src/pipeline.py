"""Lakeflow Declarative Pipeline: Open Wearables Raw Archive copies -> bronze -> silver -> gold."""

import dlt
from pyspark.sql import Window
from pyspark.sql import functions as F

LANDING = spark.conf.get("wiener.landing_path")  # noqa: F821  (spark is injected by the pipeline runtime)
# shortcut: single display timezone for day boundaries; per-Subject tz when multi-Subject
TZ = spark.conf.get("wiener.timezone")  # noqa: F821

SOURCE = (
    "struct<provider:string, source:string, device:string, device_type:string, device_id:string, device_name:string>"
)
# Explicit schemas: inference breaks on Extractions with empty data arrays.
DATA = {
    "timeseries": "array<struct<timestamp:string, zone_offset:string, type:string, value:double, unit:string, "
    f"source:{SOURCE}, is_daily_total:boolean>>",
    "sleep": "array<struct<id:string, start_time:string, end_time:string, zone_offset:string, "
    f"source:{SOURCE}, duration_seconds:bigint, sleep_duration_seconds:bigint, time_in_bed_seconds:bigint, "
    "efficiency_percent:double, stages:struct<awake_minutes:double, light_minutes:double, deep_minutes:double, "
    "rem_minutes:double>, is_nap:boolean>>",
    "workouts": "array<struct<id:string, type:string, name:string, start_time:string, end_time:string, "
    f"zone_offset:string, duration_seconds:bigint, source:{SOURCE}, calories_kcal:double, distance_meters:double, "
    "avg_heart_rate_bpm:bigint, max_heart_rate_bpm:bigint, steps_count:bigint>>",
}


def bronze(entity: str):
    schema = (
        "data_source string, entity string, subject_id string, extracted_at string, window_start string, "
        f"window_end string, data {DATA[entity]}"
    )

    @dlt.table(name=f"bronze_{entity}", comment=f"Raw Open Wearables {entity} Extractions, one row per file")
    def _():
        return (
            spark.readStream.format("cloudFiles")  # noqa: F821
            .option("cloudFiles.format", "json")
            .option("multiLine", "true")
            .option("rescuedDataColumn", "_rescued_data")
            .schema(schema)
            .load(f"{LANDING}/open_wearables/{entity}/")
            .withColumn("file_path", F.col("_metadata.file_path"))
            .withColumn("extracted_at", F.col("extracted_at").cast("timestamp"))
        )


for e in ("timeseries", "sleep", "workouts"):
    bronze(e)


def exploded(entity: str):
    return dlt.read_stream(f"bronze_{entity}").select("subject_id", "extracted_at", F.explode("data").alias("r"))


# ---------- silver: typed, deduped on natural key (latest Extraction wins) ----------
@dlt.view
@dlt.expect_or_drop("has_value", "value IS NOT NULL")
def timeseries_v():
    return exploded("timeseries").select(
        "subject_id",
        "extracted_at",
        F.col("r.timestamp").cast("timestamp").alias("ts"),
        F.col("r.type").alias("metric"),
        F.col("r.value").cast("double").alias("value"),
        F.col("r.unit").alias("unit"),
        F.coalesce(F.col("r.is_daily_total").cast("boolean"), F.lit(False)).alias("is_daily_total"),
        F.coalesce(F.col("r.source.provider"), F.lit("unknown")).alias("provider"),
    )


dlt.create_streaming_table("silver_timeseries")
dlt.apply_changes(
    target="silver_timeseries",
    source="timeseries_v",
    keys=["subject_id", "provider", "metric", "ts", "is_daily_total"],
    sequence_by="extracted_at",
)


@dlt.view
@dlt.expect_or_drop("has_id", "sleep_id IS NOT NULL")
def sleep_v():
    return exploded("sleep").select(
        "subject_id",
        "extracted_at",
        F.col("r.id").alias("sleep_id"),
        F.col("r.start_time").cast("timestamp").alias("start_time"),
        F.col("r.end_time").cast("timestamp").alias("end_time"),
        F.col("r.duration_seconds").cast("int").alias("duration_seconds"),
        F.col("r.sleep_duration_seconds").cast("int").alias("sleep_seconds"),
        F.col("r.time_in_bed_seconds").cast("int").alias("time_in_bed_seconds"),
        F.col("r.efficiency_percent").cast("double").alias("efficiency_percent"),
        F.col("r.stages.awake_minutes").cast("double").alias("awake_minutes"),
        F.col("r.stages.light_minutes").cast("double").alias("light_minutes"),
        F.col("r.stages.deep_minutes").cast("double").alias("deep_minutes"),
        F.col("r.stages.rem_minutes").cast("double").alias("rem_minutes"),
        F.col("r.is_nap").cast("boolean").alias("is_nap"),
        F.col("r.source.provider").alias("provider"),
    )


dlt.create_streaming_table("silver_sleep")
dlt.apply_changes(target="silver_sleep", source="sleep_v", keys=["subject_id", "sleep_id"], sequence_by="extracted_at")


@dlt.view
@dlt.expect_or_drop("has_id", "workout_id IS NOT NULL")
def workouts_v():
    return exploded("workouts").select(
        "subject_id",
        "extracted_at",
        F.col("r.id").alias("workout_id"),
        F.col("r.type").alias("workout_type"),
        F.col("r.start_time").cast("timestamp").alias("start_time"),
        F.col("r.end_time").cast("timestamp").alias("end_time"),
        F.col("r.duration_seconds").cast("int").alias("duration_seconds"),
        F.col("r.calories_kcal").cast("double").alias("calories_kcal"),
        F.col("r.distance_meters").cast("double").alias("distance_meters"),
        F.col("r.avg_heart_rate_bpm").cast("int").alias("avg_hr_bpm"),
        F.col("r.max_heart_rate_bpm").cast("int").alias("max_hr_bpm"),
        F.col("r.steps_count").cast("int").alias("steps"),
        F.col("r.source.provider").alias("provider"),
    )


dlt.create_streaming_table("silver_workouts")
dlt.apply_changes(
    target="silver_workouts", source="workouts_v", keys=["subject_id", "workout_id"], sequence_by="extracted_at"
)


# ---------- gold ----------
def local_date(col: str):
    return F.to_date(F.from_utc_timestamp(F.col(col), TZ))


SUMMED = ["steps", "active_energy", "basal_energy", "exercise_time", "distance_walking_running"]
AVERAGED = [
    "resting_heart_rate",
    "heart_rate_variability_rmssd",
    "oxygen_saturation",
    "respiratory_rate",
    "skin_temperature_deviation",
]


@dlt.table(comment="One row per Subject per local day")
def daily_health_summary():
    ts = dlt.read("silver_timeseries").withColumn("day", local_date("ts"))
    # Daily totals win over summed samples when the Provider reports both.
    totals = ts.filter("is_daily_total").groupBy("subject_id", "day", "metric").agg(F.max("value").alias("total"))
    samples = (
        ts.filter("NOT is_daily_total")
        .groupBy("subject_id", "day", "metric")
        .agg(
            F.sum("value").alias("sum_v"),
            F.avg("value").alias("avg_v"),
            F.max("value").alias("max_v"),
        )
    )
    m = samples.join(totals, ["subject_id", "day", "metric"], "full")
    m = m.withColumn(
        "v",
        F.when(F.col("metric").isin(SUMMED), F.coalesce("total", "sum_v")).otherwise(F.coalesce("avg_v", "total")),
    )
    wide = m.groupBy("subject_id", "day").pivot("metric", SUMMED + AVERAGED + ["heart_rate"]).agg(F.first("v"))
    hr_max = m.filter("metric = 'heart_rate'").select("subject_id", "day", F.col("max_v").alias("max_heart_rate"))
    return wide.withColumnRenamed("heart_rate", "avg_heart_rate").join(hr_max, ["subject_id", "day"], "left")


@dlt.table(comment="One row per main sleep, dated by local wake-up day")
@dlt.expect("plausible_duration", "sleep_hours BETWEEN 0 AND 16")
def sleep_nightly():
    s = dlt.read("silver_sleep").filter("NOT coalesce(is_nap, false)")
    return s.select(
        "subject_id",
        local_date("end_time").alias("day"),
        "sleep_id",
        F.from_utc_timestamp("start_time", TZ).alias("bedtime_local"),
        F.from_utc_timestamp("end_time", TZ).alias("wake_local"),
        (F.coalesce("sleep_seconds", "duration_seconds") / 3600).alias("sleep_hours"),
        (F.col("time_in_bed_seconds") / 3600).alias("time_in_bed_hours"),
        "efficiency_percent",
        "awake_minutes",
        "light_minutes",
        "deep_minutes",
        "rem_minutes",
    )


@dlt.table(comment="One row per workout")
def workout_summary():
    w = dlt.read("silver_workouts")
    return w.select(
        "subject_id",
        local_date("start_time").alias("day"),
        "workout_id",
        "workout_type",
        F.from_utc_timestamp("start_time", TZ).alias("start_local"),
        (F.col("duration_seconds") / 60).alias("duration_minutes"),
        "calories_kcal",
        (F.col("distance_meters") / 1000).alias("distance_km"),
        "avg_hr_bpm",
        "max_hr_bpm",
        "steps",
    )


BASELINE_METRICS = ["resting_heart_rate", "heart_rate_variability_rmssd", "steps", "sleep_hours"]


@dlt.table(comment="Daily metrics with 7d/30d rolling baselines and % deviation from 30d baseline")
def trend_baselines():
    sleep = dlt.read("sleep_nightly").groupBy("subject_id", "day").agg(F.sum("sleep_hours").alias("sleep_hours"))
    d = dlt.read("daily_health_summary").select(
        "subject_id", "day", "resting_heart_rate", "heart_rate_variability_rmssd", "steps"
    )
    d = d.join(sleep, ["subject_id", "day"], "full")
    order = F.col("day").cast("timestamp").cast("long")
    w7 = Window.partitionBy("subject_id").orderBy(order).rangeBetween(-6 * 86400, 0)
    w30 = Window.partitionBy("subject_id").orderBy(order).rangeBetween(-29 * 86400, 0)
    for m in BASELINE_METRICS:
        d = (
            d.withColumn(f"{m}_7d", F.avg(m).over(w7))
            .withColumn(f"{m}_30d", F.avg(m).over(w30))
            .withColumn(f"{m}_dev_pct", F.round((F.col(m) / F.col(f"{m}_30d") - 1) * 100, 1))
        )
    return d
