# Faz 1 — Backend Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Claude-copilot layer to the existing Flask backend: event→analysis, NL→directive, emergency-stop, and a narration stream — without touching the autonomy or the existing telemetry path.

**Architecture:** New `backend/state.py` holds thread-safe copilot state (log, directive, estop). New `backend/copilot.py` is the single Anthropic touch point (event analysis with vision + debounce, NL→directive parsing, graceful degrade). `backend/app.py` gains thin routes that delegate to those modules. Existing `/data` and `/telemetry` are untouched. All automated tests mock Anthropic (cost $0); the real API is only exercised in manual e2e.

**Tech Stack:** Python 3.10, Flask, `anthropic` SDK (`claude-haiku-4-5`), `pytest`, `threading.Lock`. Run all Python with `PYTHONIOENCODING=utf-8` (Windows cp1254).

---

## Repo / commit note

User deferred the final repo layout and commit/push decision (robot-control-app and hafize-airsim are separate repos; hafize-airsim is a fork; backend is not in a repo; robot-project root is not git). To keep TDD checkpoints safe, **Task 0 inits a *local* git repo at the robot-project root** (no remote, no push). This is a reversible local safety net, not the final structure decision — that stays deferred.

All venv-aware commands assume the existing venv:
`c:\Users\Berdan\OneDrive\Masaüstü\robot-project\.venv\Scripts\python.exe`

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/state.py` (create) | Thread-safe store: `copilot_log`, `current_directive`, `estop`. Pure, no Flask, no Anthropic. |
| `backend/copilot.py` (create) | Single Anthropic touch point: `analyze_event()`, `parse_command()`. Debounce, graceful degrade, prompt cache. Anthropic client injectable for tests. |
| `backend/app.py` (modify) | Add thin routes: `/copilot/event`, `/copilot/ask`, `/copilot/stream`, `/command`, `/directive`, `/estop`. Existing routes untouched. |
| `backend/tests/test_state.py` (create) | Unit tests for state store. |
| `backend/tests/test_copilot.py` (create) | Unit tests for copilot with a fake Anthropic client. |
| `backend/tests/test_routes.py` (create) | Flask test-client integration for new routes. |
| `backend/requirements.txt` (modify) | Add `anthropic`, `pytest`. |
| `backend/conftest.py` (create) | pytest path setup so `import state, copilot, app` works. |

**Directive schema** (used everywhere):
```python
{
  "mode": "explore" | "goto" | "stop",
  "bias": float,        # -1.0 (sol) .. 1.0 (sağ), local_planner steering bias
  "speed_cap": float,   # 0.0 .. 1.0, throttle çarpanı tavanı
  "target": [x, y] | None,
  "stop_on": str | None,
  "ts": float,          # epoch saniye, set edildiği an
  "ttl": float          # saniye; ts+ttl geçince sim yok sayar
}
```
**Safe default** (parse başarısız / komut yok): `mode="explore", bias=0.0, speed_cap=1.0, target=None, stop_on=None, ttl=30`.

**Event analysis output:**
```python
{
  "narration": str,
  "risk": "low" | "warn" | "critical" | "unknown",
  "suggestion": str,
  "directive": dict | None,   # yukarıdaki şema veya None
  "ts": float
}
```

---

## Task 0: Local git safety net + deps + pytest scaffold

**Files:**
- Create: `backend/conftest.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Init local git repo (root), ignore venv/artifacts**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git init
printf ".venv/\n__pycache__/\n*.pyc\n.superpowers/\nnode_modules/\n.expo/\n" > .gitignore
git add .gitignore && git commit -m "chore: local git safety net for Faz 1 (repo layout still deferred)"
```
Expected: repo initialized, one commit.

- [ ] **Step 2: Add deps to `backend/requirements.txt`**

Append these lines (keep existing content):
```
anthropic
pytest
```

- [ ] **Step 3: Install deps into existing venv**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pip install anthropic pytest
```
Expected: installs without error.

- [ ] **Step 4: Create `backend/conftest.py` so tests import flat modules**

```python
import sys
from pathlib import Path

# backend/ klasörünü import path'e ekle: state, copilot, app flat import edilir
sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 5: Verify pytest collects nothing yet (clean baseline)**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/backend"
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest -q
```
Expected: `no tests ran` (exit 5) — environment OK.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/conftest.py
git commit -m "chore: add anthropic+pytest deps and pytest scaffold"
```

---

## Task 1: `state.py` — thread-safe copilot store

**Files:**
- Create: `backend/state.py`
- Test: `backend/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_state.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/backend"
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_state.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'state'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/state.py
from __future__ import annotations

import threading
import time
from typing import Any, Optional


def _safe_default_directive() -> dict[str, Any]:
    return {
        "mode": "explore",
        "bias": 0.0,
        "speed_cap": 1.0,
        "target": None,
        "stop_on": None,
        "ts": time.time(),
        "ttl": 30.0,
    }


class CopilotState:
    """Thread-safe copilot state. No Flask, no Anthropic."""

    def __init__(self, log_max: int = 200) -> None:
        self._lock = threading.Lock()
        self._log: list[dict[str, Any]] = []
        self._log_max = log_max
        self._directive: Optional[dict[str, Any]] = None
        self._estop = False

    # --- directive ---
    def set_directive(self, *, mode: str, bias: float, speed_cap: float,
                       target: Optional[list[float]], stop_on: Optional[str],
                       ttl: float = 30.0) -> None:
        with self._lock:
            self._directive = {
                "mode": mode,
                "bias": float(bias),
                "speed_cap": float(speed_cap),
                "target": target,
                "stop_on": stop_on,
                "ts": time.time(),
                "ttl": float(ttl),
            }

    def get_directive(self) -> dict[str, Any]:
        with self._lock:
            d = self._directive
            if d is None:
                return _safe_default_directive()
            if time.time() > d["ts"] + d["ttl"]:
                return _safe_default_directive()
            return dict(d)

    # --- estop ---
    def set_estop(self, value: bool) -> None:
        with self._lock:
            self._estop = bool(value)

    def is_estop(self) -> bool:
        with self._lock:
            return self._estop

    # --- log ---
    def append_log(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._log.append(entry)
            if len(self._log) > self._log_max:
                self._log = self._log[-self._log_max:]

    def log_since(self, since_ts: float) -> list[dict[str, Any]]:
        with self._lock:
            return [e for e in self._log if e.get("ts", 0.0) > since_ts]
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_state.py -q
```
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/state.py backend/tests/test_state.py
git commit -m "feat(backend): thread-safe copilot state store with TTL directive and capped log"
```

---

## Task 2: `copilot.py` — `parse_command` (NL → directive)

**Files:**
- Create: `backend/copilot.py`
- Test: `backend/tests/test_copilot.py`

`parse_command` asks Anthropic to return strict JSON; on any failure (no key, API
error, bad JSON) it returns the safe default directive. The Anthropic client is
injected so tests use a fake.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_copilot.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_copilot.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'copilot'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/copilot.py
from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

MODEL = "claude-haiku-4-5"

_SAFE_DIRECTIVE = {
    "mode": "explore", "bias": 0.0, "speed_cap": 1.0,
    "target": None, "stop_on": None, "ttl": 30.0,
}

_COMMAND_SYSTEM = (
    "Sen otonom bir aracın misyon yorumlayıcısısın. Kullanıcının doğal dil "
    "komutunu SADECE şu JSON şemasına çevir, başka hiçbir şey yazma:\n"
    '{"mode":"explore|goto|stop","bias":-1..1,"speed_cap":0..1,'
    '"target":[x,y]|null,"stop_on":string|null}\n'
    "bias: negatif=sol, pozitif=sağ. Emin değilsen explore + bias 0 + "
    "speed_cap 1 döndür. Yalnızca JSON."
)


def _clamp(v: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return lo


def _safe() -> dict[str, Any]:
    return dict(_SAFE_DIRECTIVE)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _coerce_directive(obj: Optional[dict]) -> dict[str, Any]:
    if not obj:
        return _safe()
    mode = obj.get("mode")
    if mode not in ("explore", "goto", "stop"):
        return _safe()
    target = obj.get("target")
    if not (isinstance(target, list) and len(target) == 2):
        target = None
    stop_on = obj.get("stop_on")
    if not isinstance(stop_on, str):
        stop_on = None
    return {
        "mode": mode,
        "bias": _clamp(obj.get("bias", 0.0), -1.0, 1.0),
        "speed_cap": _clamp(obj.get("speed_cap", 1.0), 0.0, 1.0),
        "target": target,
        "stop_on": stop_on,
        "ttl": 30.0,
    }


class Copilot:
    """Single Anthropic touch point. Client injectable for tests."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def parse_command(self, text: str) -> dict[str, Any]:
        if self._client is None:
            return _safe()
        try:
            resp = self._client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=[{"type": "text", "text": _COMMAND_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": text}],
            )
            raw = resp.content[0].text
        except Exception:
            return _safe()
        return _coerce_directive(_extract_json(raw))
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_copilot.py -q
```
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/copilot.py backend/tests/test_copilot.py
git commit -m "feat(backend): copilot.parse_command NL->directive with safe-default fallback"
```

---

## Task 3: `copilot.py` — `analyze_event` (vision + debounce + degrade)

**Files:**
- Modify: `backend/copilot.py`
- Test: `backend/tests/test_copilot.py` (append)

`analyze_event` sends the camera frame + telemetry to Anthropic and returns the
event-analysis dict. Debounce: if called again within `debounce_s` it returns the
last result without an API call. Any API failure → `risk="unknown"` graceful entry.

- [ ] **Step 1: Write the failing test (append to test_copilot.py)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_copilot.py -q
```
Expected: FAIL — `AttributeError: 'Copilot' object has no attribute 'analyze_event'`.

- [ ] **Step 3: Write minimal implementation (edit `backend/copilot.py`)**

Add the constant after `_COMMAND_SYSTEM`:
```python
_EVENT_SYSTEM = (
    "Sen otonom bir aracın yardımcı pilotusun. Verilen ön kamera karesi ve "
    "telemetriye bakıp SADECE şu JSON'u döndür:\n"
    '{"narration":"kısa Türkçe sahne+durum","risk":"low|warn|critical",'
    '"suggestion":"kısa öneri","directive":null veya '
    '{"mode":"explore|goto|stop","bias":-1..1,"speed_cap":0..1,'
    '"target":[x,y]|null,"stop_on":string|null}}\n'
    "Sadece JSON, başka metin yok."
)
```

Change `__init__` and add `analyze_event`:
```python
    def __init__(self, client: Any = None, debounce_s: float = 3.0) -> None:
        self._client = client
        self._debounce_s = debounce_s
        self._last_event_ts = 0.0
        self._last_event: Optional[dict[str, Any]] = None

    def analyze_event(self, *, image_b64: str, telemetry: dict[str, Any],
                      state: str, prev_state: str) -> dict[str, Any]:
        now = time.time()
        if (self._last_event is not None
                and now - self._last_event_ts < self._debounce_s):
            return self._last_event

        if self._client is None:
            out = {"narration": "Kopilot çevrimdışı (anahtar yok)",
                   "risk": "unknown", "suggestion": "", "directive": None,
                   "ts": now}
            self._last_event, self._last_event_ts = out, now
            return out

        user_text = (f"Durum: {prev_state} -> {state}. "
                     f"Telemetri: {json.dumps(telemetry, ensure_ascii=False)}")
        try:
            resp = self._client.messages.create(
                model=MODEL,
                max_tokens=400,
                system=[{"type": "text", "text": _EVENT_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg",
                        "data": image_b64}},
                    {"type": "text", "text": user_text},
                ]}],
            )
            obj = _extract_json(resp.content[0].text) or {}
            risk = obj.get("risk")
            out = {
                "narration": obj.get("narration") or "(boş)",
                "risk": risk if risk in ("low", "warn", "critical") else "unknown",
                "suggestion": obj.get("suggestion") or "",
                "directive": (_coerce_directive(obj["directive"])
                              if obj.get("directive") else None),
                "ts": now,
            }
        except Exception:
            out = {"narration": "Kopilot analizi başarısız (geçici)",
                   "risk": "unknown", "suggestion": "", "directive": None,
                   "ts": now}

        self._last_event, self._last_event_ts = out, now
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_copilot.py -q
```
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/copilot.py backend/tests/test_copilot.py
git commit -m "feat(backend): copilot.analyze_event with vision, debounce, graceful degrade"
```

---

## Task 4: `app.py` routes — `/command` and `/directive`

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_routes.py`

A module-level `CopilotState` + `Copilot` are created in `app.py`. `Copilot`'s
Anthropic client is built from `ANTHROPIC_API_KEY` if present, else `None`
(degrade). Tests inject fakes by replacing `app.copilot` / `app.cstate`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_routes.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py -q
```
Expected: FAIL — 404 on `/command` (route missing).

- [ ] **Step 3: Write minimal implementation (edit `backend/app.py`)**

Add imports + module objects near the top, after `app = Flask(__name__)`:
```python
import os
from state import CopilotState
from copilot import Copilot

cstate = CopilotState()


def _build_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=key)
    except Exception:
        return None


copilot = Copilot(client=_build_client())
```

Add routes (anywhere among the other `@app.route`s):
```python
@app.route("/command", methods=["POST"])
def post_command():
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if not text or not isinstance(text, str):
        return jsonify({"error": "text gerekli"}), 400
    d = copilot.parse_command(text)
    cstate.set_directive(
        mode=d["mode"], bias=d["bias"], speed_cap=d["speed_cap"],
        target=d["target"], stop_on=d["stop_on"], ttl=d["ttl"],
    )
    return jsonify({"status": "ok", "directive": cstate.get_directive()}), 200


@app.route("/directive", methods=["GET"])
def get_directive():
    return jsonify(cstate.get_directive()), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py -q
```
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_routes.py
git commit -m "feat(backend): /command (NL->directive) and /directive routes"
```

---

## Task 5: `app.py` routes — `/estop` (highest priority contract)

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_routes.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
def test_estop_set_and_clear(monkeypatch):
    appmod, c = _client(monkeypatch)
    assert c.get("/estop").get_json()["estop"] is False
    r = c.post("/estop", json={})
    assert r.status_code == 200
    assert c.get("/estop").get_json()["estop"] is True
    c.post("/estop", json={"clear": True})
    assert c.get("/estop").get_json()["estop"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py::test_estop_set_and_clear -q
```
Expected: FAIL — 404 on `/estop`.

- [ ] **Step 3: Write minimal implementation (edit `backend/app.py`)**

```python
@app.route("/estop", methods=["GET", "POST"])
def estop():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        cstate.set_estop(not bool(data.get("clear", False)))
        return jsonify({"status": "ok", "estop": cstate.is_estop()}), 200
    return jsonify({"estop": cstate.is_estop()}), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_routes.py
git commit -m "feat(backend): /estop set/clear route"
```

---

## Task 6: `app.py` routes — `/copilot/event`, `/copilot/stream`, `/copilot/ask`

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_routes.py` (append)

`/copilot/event` is called by the sim with a frame+state; it runs analysis,
appends to the log, and if analysis returned a directive it is applied.
`/copilot/stream?since=ts` returns log entries newer than `since`.
`/copilot/ask` is an on-demand question against the last known frame in telemetry.

- [ ] **Step 1: Write the failing test (append)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py -q
```
Expected: FAIL — 404 on `/copilot/event`.

- [ ] **Step 3: Write minimal implementation (edit `backend/app.py`)**

```python
@app.route("/copilot/event", methods=["POST"])
def copilot_event():
    data = request.get_json(silent=True) or {}
    image = data.get("image")
    if not image:
        return jsonify({"error": "image gerekli"}), 400
    out = copilot.analyze_event(
        image_b64=image,
        telemetry=data.get("telemetry", {}),
        state=data.get("state", "?"),
        prev_state=data.get("prev_state", "?"),
    )
    cstate.append_log(out)
    if out.get("directive"):
        d = out["directive"]
        cstate.set_directive(
            mode=d["mode"], bias=d["bias"], speed_cap=d["speed_cap"],
            target=d["target"], stop_on=d["stop_on"], ttl=d["ttl"],
        )
    return jsonify(out), 200


@app.route("/copilot/stream", methods=["GET"])
def copilot_stream():
    try:
        since = float(request.args.get("since", 0))
    except (TypeError, ValueError):
        since = 0.0
    return jsonify({"events": cstate.log_since(since)}), 200


@app.route("/copilot/ask", methods=["POST"])
def copilot_ask():
    data = request.get_json(silent=True) or {}
    image = data.get("image") or (last_telemetry.get("image") or "")
    if not image:
        return jsonify({"error": "kare yok"}), 400
    out = copilot.analyze_event(
        image_b64=image,
        telemetry=last_telemetry,
        state=data.get("question", "kullanıcı sorusu"),
        prev_state="ASK",
    )
    cstate.append_log(out)
    return jsonify(out), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_routes.py -q
```
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest -q
```
Expected: PASS (all: state 6 + copilot 9 + routes 6 = 21).

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/tests/test_routes.py
git commit -m "feat(backend): /copilot/event,/stream,/ask routes wired to state+copilot"
```

---

## Task 7: Manual e2e doc + smoke (real API optional)

**Files:**
- Create: `backend/COPILOT_DEV.md`

- [ ] **Step 1: Write `backend/COPILOT_DEV.md`**

```markdown
# Copilot backend — manuel e2e

## Gereksinim
- Anthropic Console: ödeme + **spend limit (ör. $5)** ayarlı
- `set ANTHROPIC_API_KEY=...` (yoksa kopilot "çevrimdışı" döner, sürüş etkilenmez)

## Çalıştırma
```
set PYTHONIOENCODING=utf-8
set ANTHROPIC_API_KEY=sk-ant-...
"...\.venv\Scripts\python.exe" backend\app.py
```

## Smoke (key olmadan, $0)
- `GET /directive` -> explore default
- `POST /estop {}` -> estop true; `POST /estop {"clear":true}` -> false
- `POST /command {"text":"sola git"}` -> 200 (key yoksa explore default döner)
- `POST /copilot/event {"image":"<b64>","state":"BRAKING","prev_state":"DRIVING"}`
  -> key yoksa risk "unknown", sürüş etkilenmez

## Smoke (key ile)
- `POST /command {"text":"on metre ileri yavaş git"}` -> directive goto/speed_cap düşük
- `/copilot/stream?since=0` -> anlatım kayıtları
```

- [ ] **Step 2: Commit**

```bash
git add backend/COPILOT_DEV.md
git commit -m "docs(backend): copilot manual e2e + smoke checklist"
```

---

## Done criteria

- `pytest -q` → 21 passed, Anthropic hiç çağrılmadı ($0).
- Yeni route'lar var; `/data` ve `/telemetry` davranışı **değişmedi** (Faz 0 hâlâ çalışır).
- Key yokken her endpoint güvenli degrade, sürüşü bloklamaz.
- Faz 2 (sim köprü) bu API'leri tüketmeye hazır: `GET /directive`, `GET /estop`, `POST /copilot/event`.

## Kapsam dışı (bilerek ertelendi)

- `/map` (2D SLAM görseli): SLAM görselini sim üretir; Faz 1'de kaynak yok. Faz 2'de
  sim `/map`'e POST eder, Faz 3'te mobil gösterir. Faz 1 kapsamı dışı.
- estop'un "her şeyden öncelikli fren" *uygulaması* sim döngüsünde (Faz 2). Faz 1
  sadece bayrağı + endpoint'i sağlar; kontrat `Done criteria`'da.
- MCP server = Faz 4 ayrı plan.
