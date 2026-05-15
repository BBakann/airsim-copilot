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
