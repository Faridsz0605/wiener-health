"""Job task: snapshot gold tables as Parquet into the gold_export Volume (pulled by the box loader)."""

import sys

catalog, schema, export_path = sys.argv[1:4]
spark = spark  # noqa: F821,PLW0127  (injected by Databricks serverless)

for table in ("daily_health_summary", "sleep_nightly", "workout_summary", "trend_baselines"):
    (spark.table(f"{catalog}.{schema}.{table}").coalesce(1).write.mode("overwrite").parquet(f"{export_path}/{table}"))
    print(f"exported {table}")
