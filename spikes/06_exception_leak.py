"""Spike 6: does an exception message with a recognizable value leak into run output?"""

from _common import client, report, run_script, scratch

from core.volume import remove_tree

JOB = """
import sys
raise ValueError(f"wd-canary-{sys.argv[1][-8:]}")
"""

w = client()
_, path = scratch()
canary = f"wd-canary-{path[-8:]}"
try:
    _, output = run_script(w, path, JOB)
finally:
    remove_tree(w.files, path)
leaked = canary in f"{output.error} {output.error_trace}"
report("06", ok=True, detail=f"canary present in run error/trace={leaked}")
