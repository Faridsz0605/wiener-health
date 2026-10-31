import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data_dir: Path
    databricks_host: str | None
    volume: str


def load() -> Config:
    return Config(
        data_dir=Path(os.environ.get("CLIENT_DATA_DIR", Path.home() / ".wiener-data")),
        databricks_host=os.environ.get("DATABRICKS_HOST"),
        volume=os.environ.get("SCRATCH_VOLUME", "/Volumes/workspace/wiener/scratch"),
    )
