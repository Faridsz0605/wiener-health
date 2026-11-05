import pytest

from core import run_id


def test_new_ids_are_unique_and_valid():
    a, b = run_id.new(), run_id.new()
    assert a != b
    assert run_id.scratch_path("/Volumes/w/d/scratch/", a) == f"/Volumes/w/d/scratch/{a}"


@pytest.mark.parametrize("bad", ["", "..", "../other", "a" * 31, "A" * 32, "a" * 32 + "/x"])
def test_scratch_path_rejects_malformed_ids(bad):
    with pytest.raises(ValueError, match="invalid run_id"):
        run_id.scratch_path("/Volumes/w/d/scratch", bad)
