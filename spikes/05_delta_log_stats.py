"""Spike 5: does _delta_log keep column stats (min/max) that reveal content?"""

from _common import client, report, run_script, scratch

from core.volume import remove_tree

JOB = """
import sys
from pyspark.sql import SparkSession
path = sys.argv[1]
spark = SparkSession.builder.getOrCreate()
spark.createDataFrame([(f"wd-canary-{path[-8:]}",)], ["subject"]).write.format("delta").save(
    f"{path}/t"
)
"""

w = client()
_, path = scratch()
canary = f"wd-canary-{path[-8:]}".encode()
try:
    run_script(w, path, JOB)
    logs = [e.path for e in w.files.list_directory_contents(f"{path}/t/_delta_log")]
    leaked = any(canary in w.files.download(p).contents.read() for p in logs if p.endswith(".json"))
finally:
    remove_tree(w.files, path)
report("05", ok=True, detail=f"canary present in _delta_log stats={leaked}")
