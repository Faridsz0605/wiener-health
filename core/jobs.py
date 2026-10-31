import contextlib
import io

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import OperationFailed
from databricks.sdk.service import compute, jobs


def run_script(w: WorkspaceClient, scratch: str, source: str) -> tuple[jobs.Run, jobs.RunOutput]:
    """Upload `source` as scratch/job.py, run it once on serverless and delete the job.

    The only run parameter is the scratch path: never pass content (retention).
    """
    script = f"{scratch}/job.py"
    w.files.upload(script, io.BytesIO(source.encode()), overwrite=True)
    task = jobs.Task(
        task_key="main",
        spark_python_task=jobs.SparkPythonTask(python_file=script, parameters=[scratch]),
        environment_key="default",
    )
    # REVIEW: serverless environment client version for spark_python_task.
    env = jobs.JobEnvironment(environment_key="default", spec=compute.Environment(client="2"))
    job = w.jobs.create(name=f"wiener-data-{scratch[-32:]}", tasks=[task], environments=[env])
    try:
        waiter = w.jobs.run_now(job.job_id)
        with contextlib.suppress(OperationFailed):  # failed runs are inspected by the caller
            waiter.result()
        run = w.jobs.get_run(waiter.run_id)
        return run, w.jobs.get_run_output(run.tasks[0].run_id)
    finally:
        # REVIEW: confirm whether deleting the job also purges its run history.
        w.jobs.delete(job.job_id)
