"""Spike 2: read a result from the SQL warehouse into a local Parquet file."""

import os
import sys
from pathlib import Path

import pyarrow.parquet as pq
from _common import credentials, report
from databricks import sql

http_path = os.environ.get("DATABRICKS_WAREHOUSE_HTTP_PATH") or sys.exit(
    "pending: export DATABRICKS_WAREHOUSE_HTTP_PATH=/sql/1.0/warehouses/<id>"
)
host, token = credentials()
hostname = host.removeprefix("https://")
conn = sql.connect(server_hostname=hostname, http_path=http_path, access_token=token)
with conn, conn.cursor() as cur:
    cur.execute("SELECT * FROM VALUES (1, 'a'), (2, 'b') AS t(id, name)")
    table = cur.fetchall_arrow()
out = Path("out/spike02.parquet")
out.parent.mkdir(exist_ok=True)
pq.write_table(table, out)
rows = pq.read_table(out).num_rows
report("02", ok=rows == table.num_rows, detail=f"rows in parquet={rows}")
