# serving

Export layer. `export.py` pulls Gold Parquet from `scratch/<run_id>/gold/` and writes it to the
destination chosen by the user:

- `parquet`, `csv`: one file per table per run (`out/<table>/<run_id>.*`).
- `duckdb`, `sqlite`: one database merged across runs. `fact_email`: newer `version` wins and
  deletion tombstones only flip `is_deleted`; `dim_date`: insert new days; `fact_label_event`:
  append; `agg_*`: replaced by the latest run.

Optional self-hosted Postgres: not implemented yet.
