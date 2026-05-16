import time
import video_state as vs


def test_set_get_roundtrip():
    s = vs.VideoState()
    s.set_frame("front", b"JPG1")
    data, ts = s.get_frame("front")
    assert data == b"JPG1"
    assert ts > 0


def test_get_unknown_view_is_none():
    s = vs.VideoState()
    assert s.get_frame("top") is None


def test_is_stale_true_when_missing():
    s = vs.VideoState(stale_s=1.0)
    assert s.is_stale("front") is True


def test_is_stale_false_when_fresh_then_true_when_old():
    s = vs.VideoState(stale_s=0.05)
    s.set_frame("top", b"X")
    assert s.is_stale("top") is False
    time.sleep(0.08)
    assert s.is_stale("top") is True


def test_views_isolated():
    s = vs.VideoState()
    s.set_frame("front", b"F")
    s.set_frame("top", b"T")
    assert s.get_frame("front")[0] == b"F"
    assert s.get_frame("top")[0] == b"T"
