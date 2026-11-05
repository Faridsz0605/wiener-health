"""wiener-data CLI. `gmail run`: sync -> upload -> run-now -> pull Gold -> cleanup -> export."""

import argparse
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import RunResultState
from google.auth.transport.requests import AuthorizedSession

from core import config, run_id, secrets
from core.config import Config
from core.jobs import run_script
from core.state import State
from core.volume import count_objects, remove_tree
from extraction import gmail
from lakehouse.src import gmail_job
from serving import export

BATCHES = "gmail-batch"


def gmail_run(  # noqa: PLR0913 - one call site, each argument is a real dependency
    w: WorkspaceClient, http: AuthorizedSession, state: State, cfg: Config, *, fmt: str, out: Path
) -> dict[str, int]:
    bronze = cfg.data_dir / "bronze" / "gmail"
    gmail.sync(http, state, bronze)
    # Batches stay pending until exported, so a failed cloud run is retried next time.
    pending = [p for p in sorted(bronze.glob("*.jsonl")) if not state.snapshot_done(BATCHES, p.name)]
    rid = run_id.new()
    scratch = run_id.scratch_path(cfg.volume, rid)
    try:
        for p in pending:
            with p.open("rb") as f:
                w.files.upload(f"{scratch}/bronze/{p.name}", f, overwrite=True)
        source = Path(gmail_job.__file__).read_text(encoding="utf-8")
        run, _ = run_script(w, scratch, source)
        if run.state.result_state != RunResultState.SUCCESS:
            msg = "E_JOB_FAILED"
            raise RuntimeError(msg)
        tables = export.pull_gold(w.files, scratch)
    finally:
        remove_tree(w.files, scratch)
        left = count_objects(w.files, scratch)
        if left:
            msg = f"E_RETENTION: {left} objects left under scratch/{rid}"
            raise RuntimeError(msg)
    export.write(tables, fmt, out, rid)
    for p in pending:
        state.mark_snapshot(BATCHES, p.name)
    return {name: t.num_rows for name, t in tables.items()}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wiener-data")
    sources = parser.add_subparsers(dest="source", required=True)
    actions = sources.add_parser("gmail").add_subparsers(dest="action", required=True)
    auth = actions.add_parser("auth", help="authorize with your own OAuth client")
    auth.add_argument("client_secret", type=Path)
    run = actions.add_parser("run", help="sync, process on Databricks, export Gold")
    run.add_argument("--format", choices=export.FORMATS, default="parquet")
    run.add_argument("--out", type=Path, default=Path("out"))
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action == "auth":
        gmail.authorize(args.client_secret)
        return
    cfg = config.load()
    token = cfg.databricks_host and secrets.get("databricks_token")
    if not token:
        parser.error("set DATABRICKS_HOST and store the Databricks token in the keyring")
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    w = WorkspaceClient(host=cfg.databricks_host, token=token)
    state = State(cfg.data_dir / "state.db")
    counts = gmail_run(w, gmail.session(), state, cfg, fmt=args.format, out=args.out)
    sys.stdout.writelines(f"{name}: {n} rows\n" for name, n in sorted(counts.items()))


if __name__ == "__main__":
    main()
