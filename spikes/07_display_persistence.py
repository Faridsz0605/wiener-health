"""Spike 7: do print()/show() outputs persist in the run history?"""

from _common import client, report, run_script, scratch

from core.volume import remove_tree

JOB = """
import sys
from pyspark.sql import SparkSession
canary = f"wd-canary-{sys.argv[1][-8:]}"
print(canary)
SparkSession.builder.getOrCreate().createDataFrame([(canary,)], ["v"]).show()
"""

w = client()
_, path = scratch()
canary = f"wd-canary-{path[-8:]}"
try:
    _, output = run_script(w, path, JOB)
finally:
    remove_tree(w.files, path)
leaked = canary in (output.logs or "")
report("07", ok=True, detail=f"canary present in run logs={leaked}")
