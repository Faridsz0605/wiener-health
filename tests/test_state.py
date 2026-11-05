from core.state import State


def test_watermark_roundtrip_and_clear(tmp_path):
    state = State(tmp_path / "state.db")
    assert state.watermark("gmail") is None
    state.set_watermark("gmail", "100")
    state.set_watermark("gmail", "205")
    assert State(tmp_path / "state.db").watermark("gmail") == "205"
    state.clear_watermark("gmail")
    assert state.watermark("gmail") is None


def test_add_hashes_returns_only_new_ones():
    state = State(":memory:")
    assert state.add_hashes("photos", ["a", "b", "a"]) == ["a", "b"]
    assert state.add_hashes("photos", ["b", "c"]) == ["c"]
    assert state.add_hashes("gmail", ["a"]) == ["a"]


def test_snapshots():
    state = State(":memory:")
    assert not state.snapshot_done("photos", "takeout-1")
    state.mark_snapshot("photos", "takeout-1")
    state.mark_snapshot("photos", "takeout-1")
    assert state.snapshot_done("photos", "takeout-1")
