import io

from core.volume import count_objects, remove_tree
from tests.fake_files import FakeFiles

RUN = "/Volumes/w/d/scratch/" + "a" * 32
OTHER = "/Volumes/w/d/scratch/" + "b" * 32


def _seed():
    files = FakeFiles()
    for path in (
        f"{RUN}/bronze/1.json",
        f"{RUN}/silver/_delta_log/0.json",
        f"{RUN}/silver/part-0.parquet",
        f"{OTHER}/bronze/1.json",
    ):
        files.upload(path, io.BytesIO(b"{}"))
    return files


def test_count_objects_includes_directories():
    files = _seed()
    # bronze/, bronze/1.json, silver/, silver/_delta_log/, 0.json, part-0.parquet
    assert count_objects(files, RUN) == 6
    assert count_objects(files, RUN + "/missing") == 0


def test_remove_tree_deletes_only_the_run_path():
    files = _seed()
    remove_tree(files, RUN)
    assert count_objects(files, RUN) == 0
    assert count_objects(files, OTHER) == 2
    remove_tree(files, RUN)
