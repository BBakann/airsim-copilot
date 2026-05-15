import json
import importlib


def _client(monkeypatch):
    import app as appmod
    importlib.reload(appmod)

    class FakeMsgs:
        def create(self, **kw):
            class _B: text = json.dumps(
                {"mode": "goto", "bias": -0.3, "speed_cap": 0.5,
                 "target": [5, 1], "stop_on": None})
            class _R: content = [_B()]
            return _R()

    class FakeClient:
        messages = FakeMsgs()

    appmod.copilot._client = FakeClient()
    return appmod, appmod.app.test_client()


def test_command_sets_directive(monkeypatch):
    appmod, c = _client(monkeypatch)
    r = c.post("/command", json={"text": "beş bir noktasına yavaş git"})
    assert r.status_code == 200
    d = c.get("/directive").get_json()
    assert d["mode"] == "goto"
    assert d["bias"] == -0.3


def test_directive_default_when_no_command(monkeypatch):
    appmod, c = _client(monkeypatch)
    d = c.get("/directive").get_json()
    assert d["mode"] == "explore"
    assert d["bias"] == 0.0


def test_command_missing_text_is_400(monkeypatch):
    appmod, c = _client(monkeypatch)
    r = c.post("/command", json={})
    assert r.status_code == 400


def test_estop_set_and_clear(monkeypatch):
    appmod, c = _client(monkeypatch)
    assert c.get("/estop").get_json()["estop"] is False
    r = c.post("/estop", json={})
    assert r.status_code == 200
    assert c.get("/estop").get_json()["estop"] is True
    c.post("/estop", json={"clear": True})
    assert c.get("/estop").get_json()["estop"] is False


def test_event_appends_log_and_applies_directive(monkeypatch):
    import app as appmod
    importlib.reload(appmod)

    class FakeMsgs:
        def create(self, **kw):
            class _B:
                text = json.dumps({
                    "narration": "engel var", "risk": "critical",
                    "suggestion": "dur", "directive": {
                        "mode": "stop", "bias": 0.0, "speed_cap": 0.0,
                        "target": None, "stop_on": None}})
            class _R:
                content = [_B()]
            return _R()

    class FakeClient:
        messages = FakeMsgs()

    appmod.copilot._client = FakeClient()
    appmod.copilot._debounce_s = 0.0
    c = appmod.app.test_client()

    r = c.post("/copilot/event", json={
        "image": "ZmFrZQ==", "state": "BRAKING", "prev_state": "DRIVING",
        "telemetry": {"speed": 0.0, "distance": 1.0}})
    assert r.status_code == 200
    body = r.get_json()
    assert body["risk"] == "critical"

    stream = c.get("/copilot/stream?since=0").get_json()
    assert any("engel" in e["narration"] for e in stream["events"])

    d = c.get("/directive").get_json()
    assert d["mode"] == "stop"


def test_stream_since_filters(monkeypatch):
    appmod, c = _client(monkeypatch)
    appmod.cstate.append_log({"narration": "eski", "risk": "low", "ts": 10.0})
    appmod.cstate.append_log({"narration": "yeni", "risk": "low", "ts": 99.0})
    out = c.get("/copilot/stream?since=50").get_json()["events"]
    assert [e["narration"] for e in out] == ["yeni"]
