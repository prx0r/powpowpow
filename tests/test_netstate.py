import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core


def test_dict_delta_returns_only_changed_keys():
    before = {"QUBIC": {"tick": 1, "epoch": 232}, "XMR": {"height": 5}}
    after = {"QUBIC": {"tick": 2, "epoch": 232}, "XMR": {"height": 5}}

    delta = core.dict_delta(before, after)

    assert set(delta) == {"QUBIC"}
    assert delta["QUBIC"] == {"tick": 2}


def test_dict_delta_ignores_unchanged_nested_values():
    before = {"QUBIC": {"tick": 1, "burn_rate": 0.7875}}
    after = {"QUBIC": {"tick": 1, "burn_rate": 0.7875}}

    assert core.dict_delta(before, after) == {}


def test_dict_delta_picks_up_added_top_level_key():
    delta = core.dict_delta({}, {"KAS": {"height": 10}})
    assert delta == {"KAS": {"height": 10}}


def test_save_state_delta_merges_without_clobbering(tmp_path):
    path = str(tmp_path / "network_state.json")
    core.atomic_json_write(path, {"QUBIC": {"tick": 1}, "XMR": {"height": 5}})

    core.save_state_delta(path, {"QUBIC": {"active_addresses": 671275}})

    saved = json.loads(Path_read(path))
    assert saved["QUBIC"]["tick"] == 1
    assert saved["QUBIC"]["active_addresses"] == 671275
    assert saved["XMR"]["height"] == 5


def test_save_state_delta_returns_zero_for_empty_delta(tmp_path):
    path = str(tmp_path / "network_state.json")
    core.atomic_json_write(path, {"QUBIC": {"tick": 1}})

    assert core.save_state_delta(path, {}) == 0
    assert json.loads(Path_read(path)) == {"QUBIC": {"tick": 1}}


def test_load_state_file_tolerates_missing_and_corrupt(tmp_path):
    missing = tmp_path / "nope.json"
    assert core.load_state_file(str(missing)) == {}

    corrupt = tmp_path / "bad.json"
    corrupt.write_text("{not json")
    assert core.load_state_file(str(corrupt)) == {}

    good = tmp_path / "good.json"
    good.write_text(json.dumps({"a": 1}))
    assert core.load_state_file(str(good)) == {"a": 1}


def test_atomic_write_leaves_no_temp_file(tmp_path):
    path = str(tmp_path / "x.json")
    core.atomic_json_write(path, {"k": "v"})

    assert json.loads(Path_read(path)) == {"k": "v"}
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]


def test_state_lock_is_released(tmp_path):
    import fcntl

    path = str(tmp_path / "net.json")

    with core.state_lock(path):
        assert os.path.exists(path + ".lock")

    # A second acquisition must now succeed without blocking.
    descriptor = os.open(path + ".lock", os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def Path_read(path):
    with open(path) as handle:
        return handle.read()
