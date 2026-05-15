import time
import state as st


def test_directive_default_is_safe_explore():
    s = st.CopilotState()
    d = s.get_directive()
    assert d["mode"] == "explore"
    assert d["bias"] == 0.0
    assert d["speed_cap"] == 1.0


def test_set_and_get_directive_roundtrip():
    s = st.CopilotState()
    s.set_directive(mode="goto", bias=-0.5, speed_cap=0.4,
                     target=[10.0, 2.0], stop_on=None, ttl=30)
    d = s.get_directive()
    assert d["mode"] == "goto"
    assert d["bias"] == -0.5
    assert d["target"] == [10.0, 2.0]
    assert d["ts"] > 0


def test_expired_directive_falls_back_to_safe_default():
    s = st.CopilotState()
    s.set_directive(mode="goto", bias=0.9, speed_cap=0.2,
                    target=None, stop_on=None, ttl=0.01)
    time.sleep(0.05)
    d = s.get_directive()
    assert d["mode"] == "explore"
    assert d["bias"] == 0.0


def test_estop_set_clear():
    s = st.CopilotState()
    assert s.is_estop() is False
    s.set_estop(True)
    assert s.is_estop() is True
    s.set_estop(False)
    assert s.is_estop() is False


def test_log_append_and_since_filter():
    s = st.CopilotState()
    s.append_log({"narration": "a", "risk": "low", "ts": 100.0})
    s.append_log({"narration": "b", "risk": "warn", "ts": 200.0})
    assert [e["narration"] for e in s.log_since(150.0)] == ["b"]
    assert len(s.log_since(0.0)) == 2


def test_log_is_capped():
    s = st.CopilotState(log_max=3)
    for i in range(5):
        s.append_log({"narration": str(i), "risk": "low", "ts": float(i)})
    narr = [e["narration"] for e in s.log_since(0.0)]
    assert narr == ["2", "3", "4"]
