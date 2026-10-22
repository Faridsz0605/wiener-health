import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ["LANDING_VOLUME"] = "/Volumes/workspace/wiener/landing"

from lambda_src.to_volume import volume_path


def test_volume_path_strips_raw_prefix():
    key = "raw/open_wearables/sleep/date=2025-10-20/20251020T060000Z_abc.json"
    assert (
        volume_path(key)
        == "/Volumes/workspace/wiener/landing/open_wearables/sleep/date=2025-10-20/20251020T060000Z_abc.json"
    )


def test_origin_strips_browser_query():
    from lambda_src.to_volume import _origin

    assert _origin(" https://dbc-1.cloud.databricks.com/?o=123 ") == "https://dbc-1.cloud.databricks.com"
