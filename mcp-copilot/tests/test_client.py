import client as c


class FakeResp:
    def __init__(self, payload, status=200, ct="application/json"):
        self._p = payload
        self.status_code = status
        self.ok = 200 <= status < 300
        self.headers = {"content-type": ct}

    def json(self):
        return self._p


class FakeHttp:
    def __init__(self, payload=None, status=200, fail=False):
        self._p = payload if payload is not None else {}
        self._s = status
        self._fail = fail
        self.calls = []

    def get(self, url, timeout=None):
        if self._fail:
            raise RuntimeError("net")
        self.calls.append(("GET", url))
        return FakeResp(self._p, self._s)

    def post(self, url, json=None, timeout=None):
        if self._fail:
            raise RuntimeError("net")
        self.calls.append(("POST", url, json))
        return FakeResp(self._p, self._s)


B = "http://127.0.0.1:5000"


def test_get_telemetry_ok():
    h = FakeHttp({"speed": 1.2, "isOnline": True})
    out = c.get_telemetry(B, h)
    assert out["speed"] == 1.2
    assert h.calls[0] == ("GET", f"{B}/telemetry")


def test_get_telemetry_error_returns_error_dict():
    out = c.get_telemetry(B, FakeHttp(fail=True))
    assert "error" in out


def test_get_directive_ok():
    out = c.get_directive(B, FakeHttp({"mode": "explore", "bias": 0.0}))
    assert out["mode"] == "explore"


def test_send_command_ok_true():
    h = FakeHttp({"status": "ok", "directive": {"mode": "goto"}}, 200)
    out = c.send_command(B, "sola git", h)
    assert out["ok"] is True
    assert out["directive"]["mode"] == "goto"
    assert h.calls[0][0] == "POST"


def test_send_command_400_ok_false():
    out = c.send_command(B, "", FakeHttp({"error": "text gerekli"}, 400))
    assert out["ok"] is False


def test_send_command_network_error_ok_false():
    out = c.send_command(B, "dur", FakeHttp(fail=True))
    assert out["ok"] is False


def test_set_estop_true_false():
    on = c.set_estop(B, True, FakeHttp({"estop": True, "status": "ok"}))
    assert on["estop"] is True
    off = c.set_estop(B, False, FakeHttp({"estop": False, "status": "ok"}))
    assert off["estop"] is False


def test_set_estop_posts_clear_flag():
    h = FakeHttp({"estop": False, "status": "ok"})
    c.set_estop(B, False, h)
    assert h.calls[0] == ("POST", f"{B}/estop", {"clear": True})


def test_ask_copilot_ok():
    h = FakeHttp({"narration": "engel", "risk": "warn",
                  "suggestion": "", "directive": None, "ts": 1.0})
    out = c.ask_copilot(B, "ne görüyorsun", h)
    assert out["risk"] == "warn"


def test_ask_copilot_error_safe():
    out = c.ask_copilot(B, "x", FakeHttp(fail=True))
    assert "error" in out
