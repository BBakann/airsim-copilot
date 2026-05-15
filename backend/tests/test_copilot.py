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
