import json
import copilot as cp


class FakeMessages:
    def __init__(self, text=None, raise_exc=None):
        self._text = text
        self._raise = raise_exc

    def create(self, **kwargs):
        if self._raise:
            raise self._raise

        class _Block:
            def __init__(self, t): self.text = t
        class _Resp:
            def __init__(self, t): self.content = [_Block(t)]
        return _Resp(self._text)


class FakeAnthropic:
    def __init__(self, text=None, raise_exc=None):
        self.messages = FakeMessages(text, raise_exc)


def test_parse_command_valid_json():
    payload = json.dumps({
        "mode": "goto", "bias": -0.4, "speed_cap": 0.5,
        "target": [12.0, 3.0], "stop_on": "yaya"
    })
    c = cp.Copilot(client=FakeAnthropic(text=payload))
    d = c.parse_command("on iki üç noktasına yavaş git, yaya görünce dur")
    assert d["mode"] == "goto"
    assert d["bias"] == -0.4
    assert d["target"] == [12.0, 3.0]
    assert d["stop_on"] == "yaya"
    assert d["ttl"] == 30.0


def test_parse_command_api_error_returns_safe_default():
    c = cp.Copilot(client=FakeAnthropic(raise_exc=RuntimeError("boom")))
    d = c.parse_command("sola git")
    assert d["mode"] == "explore"
    assert d["bias"] == 0.0
    assert d["speed_cap"] == 1.0


def test_parse_command_garbage_text_returns_safe_default():
    c = cp.Copilot(client=FakeAnthropic(text="bunu json değil pardon"))
    d = c.parse_command("dur")
    assert d["mode"] == "explore"


def test_parse_command_no_client_returns_safe_default():
    c = cp.Copilot(client=None)
    d = c.parse_command("sağa kır")
    assert d["mode"] == "explore"


def test_parse_command_clamps_out_of_range():
    payload = json.dumps({"mode": "explore", "bias": 9.0,
                          "speed_cap": 5.0, "target": None, "stop_on": None})
    c = cp.Copilot(client=FakeAnthropic(text=payload))
    d = c.parse_command("tam sağa")
    assert d["bias"] == 1.0
    assert d["speed_cap"] == 1.0


def _event_payload(text):
    return FakeAnthropic(text=text)


def test_analyze_event_parses_structured_response():
    payload = ('{"narration":"Koridor açık, solda yaya",'
               '"risk":"warn","suggestion":"yavaşla","directive":null}')
    c = cp.Copilot(client=_event_payload(payload))
    out = c.analyze_event(image_b64="ZmFrZQ==",
                          telemetry={"speed": 1.2, "distance": 3.0},
                          state="BRAKING", prev_state="DRIVING")
    assert out["risk"] == "warn"
    assert "yaya" in out["narration"]
    assert out["directive"] is None
    assert out["ts"] > 0


def test_analyze_event_api_error_is_graceful():
    c = cp.Copilot(client=FakeAnthropic(raise_exc=RuntimeError("x")))
    out = c.analyze_event(image_b64="ZmFrZQ==", telemetry={},
                          state="RECOVERY", prev_state="DRIVING")
    assert out["risk"] == "unknown"
    assert out["narration"]  # boş değil


def test_analyze_event_debounces_within_window(monkeypatch):
    calls = {"n": 0}

    class CountingMessages:
        def create(self, **kw):
            calls["n"] += 1
            class _B:  # noqa
                text = '{"narration":"x","risk":"low","suggestion":"","directive":null}'
            class _R:  # noqa
                content = [_B()]
            return _R()

    class CountingClient:
        messages = CountingMessages()

    c = cp.Copilot(client=CountingClient(), debounce_s=10.0)
    a = c.analyze_event(image_b64="a", telemetry={}, state="DRIVING",
                        prev_state="DRIVING")
    b = c.analyze_event(image_b64="a", telemetry={}, state="DRIVING",
                        prev_state="DRIVING")
    assert calls["n"] == 1          # ikinci çağrı debounce
    assert b == a                   # cache döndü


def test_analyze_event_directive_is_coerced():
    payload = ('{"narration":"engel","risk":"critical","suggestion":"sağa",'
               '"directive":{"mode":"goto","bias":7,"speed_cap":-1,'
               '"target":[1,2],"stop_on":null}}')
    c = cp.Copilot(client=_event_payload(payload))
    out = c.analyze_event(image_b64="a", telemetry={}, state="BRAKING",
                          prev_state="DRIVING")
    assert out["directive"]["bias"] == 1.0
    assert out["directive"]["speed_cap"] == 0.0
