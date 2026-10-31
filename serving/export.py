"""Pull Gold from scratch and write it to the user's destination (ADR 0005, 0006)."""

import io
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from databricks.sdk.mixins.files import FilesExt

FORMATS = ("parquet", "csv", "duckdb", "sqlite")
KEYS = {"fact_email": "message_id", "dim_date": "date_key"}
APPEND = {"fact_label_event"}


def pull_gold(files: FilesExt, scratch: str) -> dict[str, pa.Table]:
    tables = {}
    for table_dir in files.list_directory_contents(f"{scratch}/gold"):
        name = table_dir.path.rstrip("/").rsplit("/", 1)[1]
        if not re.fullmatch(r"[a-z_]+", name):  # names end up in SQL
            msg = "unexpected gold table name"
            raise ValueError(msg)
        parts = [
            pq.read_table(io.BytesIO(files.download(e.path).contents.read()))
            for e in files.list_directory_contents(table_dir.path)
            if e.path.endswith(".parquet")
        ]
        tables[name] = pa.concat_tables(parts)
    return tables


def _flat(t: pa.Table) -> pa.Table:
    """Lists to JSON text and dates to ISO text, so CSV, SQLite and DuckDB share one shape."""
    cols = {}
    for field in t.schema:
        values = t[field.name].to_pylist()
        if pa.types.is_list(field.type):
            values = [None if v is None else json.dumps(v) for v in values]
        elif pa.types.is_date(field.type):
            values = [None if v is None else v.isoformat() for v in values]
        cols[field.name] = values
    return pa.table(cols)


def _sql_type(t: pa.DataType) -> str:
    if pa.types.is_integer(t):
        return "BIGINT"
    if pa.types.is_boolean(t):
        return "BOOLEAN"
    if pa.types.is_floating(t):
        return "DOUBLE"
    return "TEXT"


def _merge(db: sqlite3.Connection | duckdb.DuckDBPyConnection, name: str, t: pa.Table) -> None:
    cols = t.column_names
    key = KEYS.get(name)
    defs = [f"{f.name} {_sql_type(f.type)}" for f in t.schema]
    defs += [f"PRIMARY KEY ({key})"] if key else []
    db.execute(f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(defs)})")
    if not key and name not in APPEND:
        db.execute(f"DELETE FROM {name}")  # noqa: S608 - name validated in pull_gold
    sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"  # noqa: S608
    if name == "fact_email":
        # Newer version wins; COALESCE keeps old values when a deletion tombstone arrives.
        sets = ", ".join(f"{c} = COALESCE(excluded.{c}, {name}.{c})" for c in cols)
        sql += f" ON CONFLICT ({key}) DO UPDATE SET {sets} WHERE excluded.version > {name}.version"
    elif key:
        sql += f" ON CONFLICT ({key}) DO NOTHING"
    db.executemany(sql, [tuple(r.values()) for r in t.to_pylist()])


def write(tables: dict[str, pa.Table], fmt: str, out: Path, run_id: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if fmt in ("parquet", "csv"):
        # Files are per run; merging batches is left to the reader.
        for name, t in tables.items():
            (out / name).mkdir(exist_ok=True)
            if fmt == "parquet":
                pq.write_table(t, out / name / f"{run_id}.parquet")
            else:
                pacsv.write_csv(_flat(t), out / name / f"{run_id}.csv")
        return
    connect = sqlite3.connect if fmt == "sqlite" else duckdb.connect
    with closing(connect(str(out / f"wiener-data.{fmt}"))) as db:
        for name, t in tables.items():
            if t.num_rows:
                _merge(db, name, _flat(t))
        db.commit()
