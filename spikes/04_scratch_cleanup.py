"""Spike 4: job writes Delta under scratch/<run_id>/ and deletes it in finally; assert empty."""

from _common import client, report, run_script, scratch

from core.volume import count_objects, remove_tree

JOB = """
import shutil, sys
from pyspark.sql import SparkSession
path = sys.argv[1]
spark = SparkSession.builder.getOrCreate()
try:
    spark.range(10).write.format("delta").save(f"{path}/silver")
finally:
    shutil.rmtree(f"{path}/silver", ignore_errors=True)  # REVIEW: FUSE access to Volumes
"""

w = client()
_, path = scratch()
try:
    run, _ = run_script(w, path, JOB)
    left_by_job = count_objects(w.files, path)  # only job.py expected
finally:
    remove_tree(w.files, path)
left = count_objects(w.files, path)
detail = f"state={run.state.result_state}, left by job={left_by_job}, left after cleanup={left}"
report("04", ok=left_by_job == 1 and left == 0, detail=detail)
