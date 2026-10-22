"""MCP server over the Analysis Store. Run locally with scripts/tunnel.sh active:
uv run --env-file .env python -m agent.mcp_server
"""

import json
import os

import boto3
import psycopg
from mcp.server.mcpserver import MCPServer

EMBED_MODEL = "amazon.titan-embed-text-v2:0"
MAX_ROWS = 500

mcp = MCPServer("wiener-health")


def _conn():
    conn = psycopg.connect(
        host=os.environ.get("ANALYSIS_DB_HOST", "localhost"),
        port=int(os.environ.get("ANALYSIS_DB_PORT", "5433")),
        dbname="analysis",
        user="wiener_reader",
        password=os.environ["ANALYSIS_READER_PASSWORD"],
        options="-c default_transaction_read_only=on -c statement_timeout=15000",
    )
    return conn


def _embed(text: str) -> list[float]:
    bedrock = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    resp = bedrock.invoke_model(modelId=EMBED_MODEL, body=json.dumps({"inputText": text, "dimensions": 1024}))
    return json.loads(resp["body"].read())["embedding"]


@mcp.tool()
def search_health_summaries(query: str, k: int = 7) -> list[dict]:
    """Semantic search over daily Health Summaries (steps, heart rate, HRV, sleep, workouts, deviations
    from 30-day baselines). Use for fuzzy questions like 'days I slept badly' or 'when was my HRV low'."""
    with _conn() as conn:
        rows = conn.execute(
            """SELECT day, content, 1 - (embedding <=> %s::vector) AS similarity
               FROM health_summaries ORDER BY embedding <=> %s::vector LIMIT %s""",
            (str(v := _embed(query)), str(v), min(k, 50)),
        ).fetchall()
    return [{"day": str(d), "summary": c, "similarity": round(s, 3)} for d, c, s in rows]


@mcp.tool()
def query_analysis_store(sql: str) -> list[dict]:
    """Run a read-only SQL query against the Analysis Store. Tables: daily_health_summary, sleep_nightly,
    workout_summary, trend_baselines (columns *_7d, *_30d, *_dev_pct), health_summaries (day, content).
    Use for exact numbers, averages and trends."""
    with _conn() as conn:
        cur = conn.execute(sql)
        cols = [c.name for c in cur.description or []]
        return [dict(zip(cols, map(_jsonable, r), strict=True)) for r in cur.fetchmany(MAX_ROWS)]


def _jsonable(v):
    return v if isinstance(v, int | float | str | bool | type(None)) else str(v)


if __name__ == "__main__":
    mcp.run()
