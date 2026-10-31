from pathlib import Path

from core import config


def test_defaults(monkeypatch):
    for var in ("CLIENT_DATA_DIR", "DATABRICKS_HOST", "SCRATCH_VOLUME"):
        monkeypatch.delenv(var, raising=False)
    cfg = config.load()
    assert cfg.data_dir == Path.home() / ".wiener-data"
    assert cfg.databricks_host is None
    assert cfg.volume == "/Volumes/workspace/wiener/scratch"


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("CLIENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.setenv("SCRATCH_VOLUME", "/Volumes/c/s/v")
    cfg = config.load()
    assert cfg.data_dir == tmp_path
    assert cfg.databricks_host == "https://example.cloud.databricks.com"
    assert cfg.volume == "/Volumes/c/s/v"
