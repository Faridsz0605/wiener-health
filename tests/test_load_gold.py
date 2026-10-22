from datetime import date

import polars as pl

from extraction.load_gold import build_summaries, health_summary, upsert_summaries

DAY = {
    "subject_id": "s1",
    "day": date(2025, 10, 20),
    "steps": 8412.0,
    "steps_dev_pct": 12.0,
    "resting_heart_rate": 58.0,
    "resting_heart_rate_dev_pct": -3.0,
    "heart_rate_variability_rmssd": 42.0,
    "heart_rate_variability_rmssd_dev_pct": -15.0,
    "sleep_hours_dev_pct": None,
}
SLEEP = {"sleep_hours": 6.5, "efficiency_percent": 91.0, "deep_minutes": 60.0, "rem_minutes": 80.0}


def test_health_summary_is_deterministic_and_skips_missing():
    text = health_summary(DAY, SLEEP, [{"workout_type": "running", "duration_minutes": 30.0, "avg_hr_bpm": 150}])
    assert text == health_summary(
        DAY, SLEEP, [{"workout_type": "running", "duration_minutes": 30.0, "avg_hr_bpm": 150}]
    )
    assert "steps 8,412 (+12% vs 30d baseline)." in text
    assert "HRV (RMSSD) 42 ms (-15% vs 30d baseline)." in text
    assert "SpO2" not in text
    assert "Slept 6.5 h, efficiency 91%, deep 60 min, REM 80 min." in text
    assert "Workout: running 30 min, avg HR 150 bpm." in text


def test_build_summaries_joins_tables():
    gold = {
        "trend_baselines": pl.DataFrame([DAY]),
        "daily_health_summary": pl.DataFrame([{"subject_id": "s1", "day": DAY["day"], "oxygen_saturation": 97.0}]),
        "sleep_nightly": pl.DataFrame([{"subject_id": "s1", "day": DAY["day"], **SLEEP}]),
        "workout_summary": pl.DataFrame(schema={"subject_id": pl.String, "day": pl.Date}),
    }
    [s] = build_summaries(gold)
    assert "SpO2 97.0%" in s["content"] and "Slept 6.5 h" in s["content"]
    assert len(s["content_hash"]) == 64


class FakeCursor:
    def __init__(self, existing):
        self.existing, self.inserted = existing, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def execute(self, sql, params=None):
        if params:
            self.inserted.append(params)

    def fetchall(self):
        return self.existing


class FakeConn:
    def __init__(self, existing):
        self.cur = FakeCursor(existing)

    def cursor(self):
        return self.cur


class FakeBedrock:
    calls = 0

    def invoke_model(self, modelId, body):
        FakeBedrock.calls += 1
        import io
        import json

        return {"body": io.BytesIO(json.dumps({"embedding": [0.0, 1.0]}).encode())}


def test_upsert_only_embeds_changed_hashes():
    d = date(2025, 10, 20)
    summaries = [
        {"subject_id": "s1", "day": d, "content": "a", "content_hash": "h1"},
        {"subject_id": "s1", "day": date(2025, 10, 21), "content": "b", "content_hash": "h2"},
    ]
    conn = FakeConn(existing=[("s1", d, "h1")])
    FakeBedrock.calls = 0
    assert upsert_summaries(conn, FakeBedrock(), summaries) == 1
    assert FakeBedrock.calls == 1
