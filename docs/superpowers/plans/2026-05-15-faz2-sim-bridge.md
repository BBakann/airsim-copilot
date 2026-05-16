# Faz 2 — Sim Köprü Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the autonomous sim to the Faz 1 backend hub: post copilot events on state change / near-obstacle, poll the directive and apply it as an upper-level nudge, and obey emergency-stop — all without changing the low-level autonomy (SLAM, LiDAR avoidance, behavior/local planners).

**Architecture:** A new `copilot_bridge.py` next to `main.py` holds (a) pure decision functions (`should_emit_event`, `apply_directive`, `resolve_controls`) that are fully unit-testable without AirSim, and (b) a `CopilotBridge` class that runs a daemon thread doing non-blocking HTTP (poll `/directive` + `/estop`, flush queued `/copilot/event`). `main.py` gets surgical hooks: one `bridge.tick(...)` call, an estop early-out, and one directive-application line. The 20 Hz loop never blocks on network — it only reads cached attributes.

**Tech Stack:** Python 3.10, `requests`, `pytest`. Run all Python with `PYTHONIOENCODING=utf-8`. Sim repo is the existing fork `hafize-airsim/autonomous-vehicle-simulation` (its own git repo).

---

## Repo / commit note

`hafize-airsim/autonomous-vehicle-simulation` is its own git repo (a fork). Faz 2 changes are committed **there** on a feature branch `faz2-copilot-bridge`. No push (remote/fork-sync decision still deferred per user). Faz 1's root safety repo is unrelated to this.

venv (shared): `c:\Users\Berdan\OneDrive\Masaüstü\robot-project\.venv\Scripts\python.exe`
Sim dir (CWD for all commands): `c:\Users\Berdan\OneDrive\Masaüstü\robot-project\hafize-airsim\autonomous-vehicle-simulation`

---

## File Structure

| File | Responsibility |
|---|---|
| `copilot_bridge.py` (create) | Pure decision fns + `CopilotBridge` (threaded non-blocking HTTP, cached directive/estop). Only Faz-2 logic. |
| `tests/test_bridge_logic.py` (create) | Unit tests for the 3 pure functions. No network, no AirSim. |
| `tests/test_bridge_client.py` (create) | `CopilotBridge` poll/flush tests with an injected fake HTTP session. No real thread, no network. |
| `conftest.py` (create) | pytest path setup (`import copilot_bridge`). |
| `main.py` (modify) | 4 surgical hooks: import, bridge init+start, tick+estop early-out, directive application, stop in finally. Autonomy logic untouched. |
| `COPILOT_SIM_DEV.md` (create) | Manual e2e checklist (needs AirSim + backend). |

**Directive schema (from Faz 1, consumed read-only here):**
```python
{"mode": "explore|goto|stop", "bias": float, "speed_cap": float,
 "target": [x,y]|None, "stop_on": str|None, "ts": float, "ttl": float}
```
Safe default if backend unreachable: `mode="explore", bias=0.0, speed_cap=1.0`.

**Backend endpoints consumed:** `GET {base}/directive` → directive json; `GET {base}/estop` → `{"estop": bool}`; `POST {base}/copilot/event` body `{image, state, prev_state, telemetry}`. `base` derived from `core.SERVER_URL` (`".../data"` → strip last segment).

**Tuning constants (in `copilot_bridge.py`):** `BIAS_GAIN = 0.5`, `EVENT_COOLDOWN_S = 3.0`, `NEAR_DIST_M = 5.0`, `POLL_INTERVAL_S = 0.5`, `HTTP_TIMEOUT_S = 0.4`.

---

## Task 0: Branch + pytest scaffold (sim repo)

**Files:**
- Create: `conftest.py`

- [ ] **Step 1: Create feature branch in the sim repo**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/hafize-airsim/autonomous-vehicle-simulation"
git checkout -b faz2-copilot-bridge
git branch --show-current
```
Expected: `faz2-copilot-bridge`.

- [ ] **Step 2: Create `conftest.py`**

```python
import sys
from pathlib import Path

# sim klasörünü import path'e ekle: copilot_bridge flat import edilir
sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 3: Verify pytest collects nothing yet**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest -q
```
Expected: `no tests ran` (exit 5).

- [ ] **Step 4: Commit**

```bash
git add conftest.py
git commit -m "chore(sim): pytest scaffold for Faz 2 copilot bridge"
```

---

## Task 1: Pure decision functions

**Files:**
- Create: `copilot_bridge.py`
- Test: `tests/test_bridge_logic.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bridge_logic.py
import copilot_bridge as cb


def test_should_emit_on_state_change():
    assert cb.should_emit_event("DRIVING", "BRAKING", 50.0, 0.0, 100.0) is True


def test_should_emit_on_near_obstacle():
    assert cb.should_emit_event("DRIVING", "DRIVING", 3.0, 0.0, 100.0) is True


def test_should_not_emit_when_calm():
    assert cb.should_emit_event("DRIVING", "DRIVING", 50.0, 0.0, 100.0) is False


def test_should_not_emit_within_cooldown():
    # son emit 99.0, now 100.0, cooldown 3.0 -> bastır (state değişse bile)
    assert cb.should_emit_event("DRIVING", "BRAKING", 1.0, 99.0, 100.0) is False


def test_apply_directive_only_in_driving():
    d = {"mode": "explore", "bias": 1.0, "speed_cap": 0.0}
    # BRAKING: otonomi dokunulmaz
    t, s, b = cb.apply_directive(d, throttle=0.3, steering=-0.2, state="BRAKING")
    assert (t, s, b) == (0.3, -0.2, 0.0)


def test_apply_directive_speed_cap_and_bias():
    d = {"mode": "explore", "bias": 0.4, "speed_cap": 0.5}
    t, s, b = cb.apply_directive(d, throttle=0.30, steering=0.0, state="DRIVING")
    assert t == 0.15                      # 0.30 * 0.5
    assert abs(s - 0.2) < 1e-9            # 0.0 + 0.4 * BIAS_GAIN(0.5)
    assert b == 0.0


def test_apply_directive_stop_mode_brakes():
    d = {"mode": "stop", "bias": 0.0, "speed_cap": 1.0}
    t, s, b = cb.apply_directive(d, throttle=0.3, steering=0.1, state="DRIVING")
    assert t == 0.0
    assert b == 1.0


def test_apply_directive_clamps_steering():
    d = {"mode": "explore", "bias": 1.0, "speed_cap": 1.0}
    t, s, b = cb.apply_directive(d, throttle=0.3, steering=0.9, state="DRIVING")
    assert s == 1.0                       # 0.9 + 0.5 clamp -> 1.0


def test_resolve_estop_overrides_everything():
    d = {"mode": "explore", "bias": 0.0, "speed_cap": 1.0}
    assert cb.resolve_controls(True, "DRIVING", 0.9, 0.5, 0.0, d) == (0.0, 0.0, 1.0)


def test_resolve_non_driving_passthrough():
    d = {"mode": "stop", "bias": 1.0, "speed_cap": 0.0}
    # RECOVERY: directive yok sayılır, otonomi aynen geçer
    assert cb.resolve_controls(False, "RECOVERY", 0.0, -0.5, 0.0, d) == (0.0, -0.5, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/hafize-airsim/autonomous-vehicle-simulation"
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_bridge_logic.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'copilot_bridge'`.

- [ ] **Step 3: Write minimal implementation**

```python
# copilot_bridge.py
from __future__ import annotations

from typing import Any, Optional

BIAS_GAIN = 0.5
EVENT_COOLDOWN_S = 3.0
NEAR_DIST_M = 5.0
POLL_INTERVAL_S = 0.5
HTTP_TIMEOUT_S = 0.4

_SAFE_DIRECTIVE = {
    "mode": "explore", "bias": 0.0, "speed_cap": 1.0,
    "target": None, "stop_on": None, "ts": 0.0, "ttl": 30.0,
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def should_emit_event(prev_state: str, curr_state: str, min_dist: float,
                      last_emit_ts: float, now: float,
                      cooldown: float = EVENT_COOLDOWN_S,
                      near_dist: float = NEAR_DIST_M) -> bool:
    if now - last_emit_ts < cooldown:
        return False
    if prev_state != curr_state:
        return True
    if min_dist < near_dist:
        return True
    return False


def apply_directive(directive: dict[str, Any], throttle: float,
                    steering: float, state: str) -> tuple[float, float, float]:
    """DRIVING dışında otonomi aynen geçer. Sadece DRIVING'de üst-nudge."""
    if state != "DRIVING":
        return throttle, steering, 0.0
    mode = directive.get("mode", "explore")
    if mode == "stop":
        return 0.0, steering, 1.0
    speed_cap = _clamp(float(directive.get("speed_cap", 1.0)), 0.0, 1.0)
    bias = _clamp(float(directive.get("bias", 0.0)), -1.0, 1.0)
    new_throttle = throttle * speed_cap
    new_steering = _clamp(steering + bias * BIAS_GAIN, -1.0, 1.0)
    return new_throttle, new_steering, 0.0


def resolve_controls(estop: bool, state: str, throttle: float, steering: float,
                     brake: float, directive: dict[str, Any]
                     ) -> tuple[float, float, float]:
    if estop:
        return 0.0, 0.0, 1.0
    if state == "DRIVING":
        t, s, b = apply_directive(directive, throttle, steering, state)
        return t, s, max(brake, b)
    return throttle, steering, brake
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_bridge_logic.py -q
```
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add copilot_bridge.py tests/test_bridge_logic.py
git commit -m "feat(sim): pure copilot-bridge decision fns (emit/apply/resolve)"
```

---

## Task 2: `CopilotBridge` — poll + flush with injected HTTP

**Files:**
- Modify: `copilot_bridge.py`
- Test: `tests/test_bridge_client.py`

The class uses a `requests`-like session with `.get(url, timeout=)` and
`.post(url, json=, timeout=)` returning an object with `.json()` and
`.status_code`. Tests inject a fake; no real thread is started (we call
`_poll_once`, `tick`, `_flush_event` directly).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bridge_client.py
import copilot_bridge as cb


class FakeResp:
    def __init__(self, payload, status=200):
        self._p = payload
        self.status_code = status

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, directive=None, estop=False, fail=False):
        self._directive = directive or dict(cb._SAFE_DIRECTIVE)
        self._estop = estop
        self._fail = fail
        self.posted = []

    def get(self, url, timeout=None):
        if self._fail:
            raise RuntimeError("net down")
        if url.endswith("/directive"):
            return FakeResp(self._directive)
        if url.endswith("/estop"):
            return FakeResp({"estop": self._estop})
        raise AssertionError(url)

    def post(self, url, json=None, timeout=None):
        if self._fail:
            raise RuntimeError("net down")
        self.posted.append((url, json))
        return FakeResp({"risk": "low"}, 200)


def test_poll_updates_directive_and_estop():
    sess = FakeSession(directive={"mode": "goto", "bias": -0.3,
                                  "speed_cap": 0.4, "target": None,
                                  "stop_on": None, "ts": 1.0, "ttl": 30.0},
                        estop=True)
    b = cb.CopilotBridge(base_url="http://x", http=sess)
    b._poll_once()
    assert b.directive["mode"] == "goto"
    assert b.estop is True


def test_poll_network_failure_keeps_safe_defaults():
    b = cb.CopilotBridge(base_url="http://x", http=FakeSession(fail=True))
    b._poll_once()
    assert b.directive["mode"] == "explore"
    assert b.estop is False


def test_tick_enqueues_event_then_flush_posts():
    sess = FakeSession()
    b = cb.CopilotBridge(base_url="http://x", http=sess)
    b.tick(state="BRAKING", prev_state="DRIVING", min_dist=2.0,
           image_b64="ZmFrZQ==", telemetry={"speed": 0.0})
    b._flush_event(now=100.0)
    assert len(sess.posted) == 1
    url, body = sess.posted[0]
    assert url.endswith("/copilot/event")
    assert body["image"] == "ZmFrZQ=="
    assert body["state"] == "BRAKING"
    assert body["prev_state"] == "DRIVING"


def test_tick_calm_does_not_enqueue():
    sess = FakeSession()
    b = cb.CopilotBridge(base_url="http://x", http=sess)
    b.tick(state="DRIVING", prev_state="DRIVING", min_dist=50.0,
           image_b64="x", telemetry={})
    b._flush_event(now=100.0)
    assert sess.posted == []


def test_flush_failure_is_swallowed():
    sess = FakeSession(fail=True)
    b = cb.CopilotBridge(base_url="http://x", http=sess)
    b.tick(state="BRAKING", prev_state="DRIVING", min_dist=1.0,
           image_b64="x", telemetry={})
    b._flush_event(now=100.0)  # no raise
    assert b._pending is None  # temizlendi, sürüş bloklanmaz


def test_no_image_skips_event():
    sess = FakeSession()
    b = cb.CopilotBridge(base_url="http://x", http=sess)
    b.tick(state="BRAKING", prev_state="DRIVING", min_dist=1.0,
           image_b64=None, telemetry={})
    b._flush_event(now=100.0)
    assert sess.posted == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_bridge_client.py -q
```
Expected: FAIL — `AttributeError: module 'copilot_bridge' has no attribute 'CopilotBridge'`.

- [ ] **Step 3: Write minimal implementation (append to `copilot_bridge.py`)**

```python
import threading
import time


class CopilotBridge:
    """Non-blocking köprü: directive/estop poll + event flush. 20Hz loop bloklanmaz."""

    def __init__(self, base_url: str, http: Any = None,
                 poll_interval: float = POLL_INTERVAL_S,
                 timeout: float = HTTP_TIMEOUT_S) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pending: Optional[dict[str, Any]] = None
        self._last_emit_ts = 0.0

        self.directive: dict[str, Any] = dict(_SAFE_DIRECTIVE)
        self.estop: bool = False

        if http is not None:
            self._http = http
        else:
            import requests
            self._http = requests.Session()

    # --- network (hatalar yutulur, sürüş asla bloklanmaz) ---
    def _poll_once(self) -> None:
        try:
            r = self._http.get(self._base + "/directive", timeout=self._timeout)
            d = r.json()
            if isinstance(d, dict) and "mode" in d:
                with self._lock:
                    self.directive = d
        except Exception:
            pass
        try:
            r = self._http.get(self._base + "/estop", timeout=self._timeout)
            self.estop = bool(r.json().get("estop", False))
        except Exception:
            pass

    def _flush_event(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            payload = self._pending
            self._pending = None
        if not payload:
            return
        try:
            self._http.post(self._base + "/copilot/event",
                            json=payload, timeout=self._timeout)
            self._last_emit_ts = now
        except Exception:
            pass

    # --- main loop'tan çağrılır (anlık, bloklamaz) ---
    def tick(self, *, state: str, prev_state: str, min_dist: float,
             image_b64: Optional[str], telemetry: dict[str, Any],
             now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        if not image_b64:
            return
        if not should_emit_event(prev_state, state, min_dist,
                                 self._last_emit_ts, now):
            return
        with self._lock:
            self._pending = {
                "image": image_b64,
                "state": state,
                "prev_state": prev_state,
                "telemetry": telemetry,
            }

    # --- daemon thread ---
    def _run(self) -> None:
        while not self._stop.is_set():
            self._poll_once()
            self._flush_event()
            self._stop.wait(self._poll_interval)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest tests/test_bridge_client.py -q
```
Expected: PASS (6 passed).

- [ ] **Step 5: Run full sim suite**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest -q
```
Expected: PASS (logic 10 + client 6 = 16).

- [ ] **Step 6: Commit**

```bash
git add copilot_bridge.py tests/test_bridge_client.py
git commit -m "feat(sim): CopilotBridge threaded poll/flush with injectable http"
```

---

## Task 3: Wire bridge into `main.py` (surgical hooks)

**Files:**
- Modify: `main.py`

No unit test — this needs AirSim. Verified manually in Task 4. Each edit is an
exact string replacement against the current `main.py`.

- [ ] **Step 1: Add imports**

Replace:
```python
from navigation.slam import Map_SLAM
from planning.local_planner import LocalPlanner
from planning.behavior_planner import BehaviorPlanner
```
with:
```python
from navigation.slam import Map_SLAM
from planning.local_planner import LocalPlanner
from planning.behavior_planner import BehaviorPlanner
from copilot_bridge import CopilotBridge, resolve_controls
```

- [ ] **Step 2: Init + start bridge, track prev_state**

Replace:
```python
        last_send_time = 0
        last_steering = 0.0
        LOOP_DT = 0.05         # 20 Hz
        last_debug_time = 0
```
with:
```python
        last_send_time = 0
        last_steering = 0.0
        LOOP_DT = 0.05         # 20 Hz
        last_debug_time = 0

        bridge = CopilotBridge(base_url=SERVER_URL.rsplit("/", 1)[0])
        bridge.start()
        prev_state = behavior_planner.current_state
```

- [ ] **Step 3: Add tick + estop early-out after the camera frame is built**

Replace:
```python
            img_base64, img_bgr = process_image_to_base64(img_response)
            if img_bgr is not None:
                cv2.imshow("AirSim Kamera", img_bgr)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
```
with:
```python
            img_base64, img_bgr = process_image_to_base64(img_response)
            if img_bgr is not None:
                cv2.imshow("AirSim Kamera", img_bgr)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            # --- COPILOT KÖPRÜ (üst katman, otonomi değişmez) ---
            bridge.tick(
                state=current_state, prev_state=prev_state,
                min_dist=min_lidar_dist, image_b64=img_base64,
                telemetry={"speed": car_state.speed, "distance": distance,
                           "lidar_min": min_lidar_dist},
            )
            prev_state = current_state
            if bridge.estop:
                controller.vehicle.set_controls(
                    throttle=0.0, steering=0.0, brake=1.0)
                elapsed = time.time() - loop_start
                if elapsed < LOOP_DT:
                    time.sleep(LOOP_DT - elapsed)
                continue
```

- [ ] **Step 4: Apply directive in the DRIVING branch**

Replace:
```python
                controller.vehicle.set_controls(
                    throttle=current_throttle, steering=total_steering, brake=0.0
                )
```
with:
```python
                _t, _s, _b = resolve_controls(
                    False, current_state, current_throttle,
                    total_steering, 0.0, bridge.directive)
                controller.vehicle.set_controls(
                    throttle=_t, steering=_s, brake=_b
                )
```

- [ ] **Step 5: Stop bridge in finally**

Replace:
```python
    finally:
        if vehicle:
            vehicle.cleanup()
        cv2.destroyAllWindows()
        print("Sistem Kapatıldı.")
```
with:
```python
    finally:
        try:
            bridge.stop()
        except Exception:
            pass
        if vehicle:
            vehicle.cleanup()
        cv2.destroyAllWindows()
        print("Sistem Kapatıldı.")
```

- [ ] **Step 6: Byte-compile sanity (no AirSim needed)**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m py_compile main.py copilot_bridge.py
```
Expected: no output (exit 0) — syntax OK.

- [ ] **Step 7: Run full sim suite again (regression)**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pytest -q
```
Expected: PASS (16).

- [ ] **Step 8: Commit**

```bash
git add main.py
git commit -m "feat(sim): wire copilot bridge into main loop (estop+directive, autonomy intact)"
```

---

## Task 4: Manual e2e (user-run, needs AirSim + backend)

**Files:**
- Create: `COPILOT_SIM_DEV.md`

- [ ] **Step 1: Write `COPILOT_SIM_DEV.md`**

```markdown
# Faz 2 sim köprü — manuel e2e

Önkoşul: AirSimNH açık, settings.json doğru yerde (Faz 0).

## Çalıştırma sırası
1. `set PYTHONIOENCODING=utf-8` (her terminal)
2. backend:  `...\.venv\Scripts\python.exe backend\app.py`
3. sim:      `cd hafize-airsim\autonomous-vehicle-simulation` ->
             `...\.venv\Scripts\python.exe main.py`

## Beklenen (anahtarsız, $0)
- Araç eskisi gibi otonom sürer (davranış DEĞİŞMEZ; directive default explore).
- backend logunda state değişince/engelde `POST /copilot/event` görülür.

## estop testi
- 3. terminal: `curl -X POST http://127.0.0.1:5000/estop -H "Content-Type: application/json" -d "{}"`
- Beklenen: araç ~0.5 sn içinde durur (fren). Konsolda hareket kesilir.
- `curl -X POST http://127.0.0.1:5000/estop -H "Content-Type: application/json" -d "{\"clear\":true}"`
- Beklenen: araç tekrar sürmeye başlar.

## directive testi (anahtarsız)
- `curl http://127.0.0.1:5000/directive` -> explore default
- (Gerçek NL->directive için ANTHROPIC_API_KEY gerekir; Faz 1 COPILOT_DEV.md)

## Başarısızlık güvenliği
- backend kapalıyken sim çalıştır: araç yine otonom sürer (köprü hatayı yutar,
  directive safe default, estop False). Sürüş bloklanmaz.
```

- [ ] **Step 2: Commit**

```bash
git add COPILOT_SIM_DEV.md
git commit -m "docs(sim): Faz 2 manual e2e checklist"
```

- [ ] **Step 3: Hand off to user for manual verification**

Tell the user to run the `COPILOT_SIM_DEV.md` checklist (AirSim + backend +
estop curl) and report: (a) car still drives autonomously, (b) estop stops it,
(c) clear resumes, (d) backend-down → car still drives. Do not mark Faz 2 done
until the user confirms.

---

## Self-Review

**Spec coverage (spec §4 D/E, §6, §8 Faz 2):**
- D directive poll + apply → Task 1 (`apply_directive`/`resolve_controls`), Task 2 (`_poll_once`), Task 3 (Step 4). ✔
- E estop highest priority → `resolve_controls` estop branch + main.py early-out (Task 1, Task 3 Step 3). ✔
- B event on state-change/near → `should_emit_event` + `tick`/`_flush_event` (Task 1, 2, 3). ✔
- §6 failsafe: non-blocking thread, timeouts, exceptions swallowed, safe defaults, autonomy untouched outside DRIVING → Task 2 + `apply_directive` state guard. ✔
- §8 Faz 2 scope (sim bridge, low-level unchanged) → no edits to behavior_planner/local_planner/SLAM. ✔

**Placeholder scan:** none — every step has full code/commands.

**Type consistency:** `should_emit_event(prev,curr,min_dist,last_emit_ts,now,...)`, `apply_directive(directive,throttle,steering,state)->(t,s,b)`, `resolve_controls(estop,state,throttle,steering,brake,directive)->(t,s,b)`, `CopilotBridge(base_url,http,...)` with `.directive/.estop/.tick/_poll_once/_flush_event/start/stop` — used identically across Tasks 1-3 and main.py. ✔

**Out of scope (deferred):** `/map` (Faz 3 mobil), MCP (Faz 4), real NL→directive needs API key (Faz 1 doc).
