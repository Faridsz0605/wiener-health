"""Spike 3: trigger a serverless job with run-now through the Jobs API using a PAT."""

from _common import client, report, run_script, scratch
from databricks.sdk.service.jobs import RunResultState

from core.volume import remove_tree

w = client()
_, path = scratch()
try:
    run, _ = run_script(w, path, "import sys\nassert sys.argv[1]\n")
finally:
    remove_tree(w.files, path)
state = run.state.result_state
report("03", ok=state == RunResultState.SUCCESS, detail=f"result_state={state}")
