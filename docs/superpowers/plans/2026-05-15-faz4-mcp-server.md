# Faz 4 — MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the running copilot backend to Claude Code (on the PC) as MCP tools — `get_telemetry`, `get_directive`, `send_command`, `set_estop`, `ask_copilot` — so the desktop agent can observe and command the vehicle through the same Flask hub the sim/mobile use.

**Architecture:** A new top-level `mcp-copilot/` Python package. `client.py` holds pure HTTP-wrapper functions (injectable `http`, safe degrade — same pattern as Faz 2 `copilot_bridge`) and is fully unit-tested. `server.py` is a thin FastMCP stdio server that registers one tool per client function. No backend/sim/mobile changes. Backend is consumed read/write over HTTP only.

**Tech Stack:** Python 3.10, `mcp` SDK (FastMCP, stdio), `requests`, `pytest`. Shared venv. `PYTHONIOENCODING=utf-8`. Backend base from `MCP_BACKEND_URL` env (default `http://127.0.0.1:5000`).

---

## Repo / commit note

Committed in the **root local repo** (`robot-project`, branch from `master` —
same repo as Faz 1 backend; created in Faz 1 Task 0, local only, no remote).
Branch `faz4-mcp`. App dir for commands: `c:\Users\Berdan\OneDrive\Masaüstü\robot-project`.
venv: `.\.venv\Scripts\python.exe`.

## Scope

Sadece MCP sarmalayıcı. Backend/sim/mobil **değişmez**. Tools mevcut Faz 1
endpoint'lerini çağırır. Anthropic anahtarı yoksa backend zaten degrade eder
(MCP onu olduğu gibi yansıtır). Kapsam dışı: yeni backend endpoint, video,
Harita, mobil.

## Backend endpoints consumed (Faz 1, canlı)

- `GET {base}/telemetry` → telemetri json
- `GET {base}/directive` → directive json
- `POST {base}/command` `{text}` → `{status,directive}` | 400
- `POST {base}/estop` `{}` / `{clear:true}` → `{estop,status}`
- `POST {base}/copilot/ask` `{question}` → `{narration,risk,suggestion,directive,ts}`

## File Structure

| File | Responsibility |
|---|---|
| `mcp-copilot/conftest.py` (create) | pytest path setup. |
| `mcp-copilot/client.py` (create) | Saf HTTP sarmalayıcılar, `http` enjekte, güvenli degrade. |
| `mcp-copilot/tests/test_client.py` (create) | client birim testleri (sahte http). |
| `mcp-copilot/server.py` (create) | FastMCP stdio server; tool kayıtları client'a delege. |
| `mcp-copilot/tests/test_server.py` (create) | server import + tool listesi smoke. |
| `mcp-copilot/requirements.txt` (create) | `mcp`, `requests`, `pytest`. |
| `mcp-copilot/README.md` (create) | Claude Code'a kayıt + kullanım. |

**Client API (server bunları aynen sarmalar):**
- `get_telemetry(base, http=requests) -> dict` — hata → `{"error": "..."}`
- `get_directive(base, http=requests) -> dict`
- `send_command(base, text, http=requests) -> dict` — `{ok: bool, directive?: dict}`
- `set_estop(base, on: bool, http=requests) -> dict` — `{estop: bool}`
- `ask_copilot(base, question, http=requests) -> dict`

Tümü exception yutar, asla raise etmez (MCP tool çağrısı patlamasın).

---

## Task 0: Branch + deps + scaffold

**Files:**
- Create: `mcp-copilot/conftest.py`, `mcp-copilot/requirements.txt`

- [ ] **Step 1: Branch**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git checkout master && git checkout -b faz4-mcp
git branch --show-current
```
Expected: `faz4-mcp`.

- [ ] **Step 2: `mcp-copilot/requirements.txt`**

```
mcp
requests
pytest
```

- [ ] **Step 3: Install into shared venv**

Run:
```bash
"c:/Users/Berdan/OneDrive/Masaüstü/robot-project/.venv/Scripts/python.exe" -m pip install mcp requests pytest
```
Expected: installs without error.

- [ ] **Step 4: `mcp-copilot/conftest.py`**

```python
import sys
from pathlib import Path

# mcp-copilot/ klasörünü import path'e ekle: client, server flat import
sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 5: Verify pytest clean baseline**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/mcp-copilot"
"../.venv/Scripts/python.exe" -m pytest -q
```
Expected: `no tests ran` (exit 5).

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add mcp-copilot/conftest.py mcp-copilot/requirements.txt docs/
git commit -m "chore(mcp): Faz 4 scaffold (deps + pytest path)"
```

---

## Task 1: `client.py` — HTTP wrappers

**Files:**
- Create: `mcp-copilot/client.py`
- Test: `mcp-copilot/tests/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp-copilot/tests/test_client.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/mcp-copilot"
"../.venv/Scripts/python.exe" -m pytest tests/test_client.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'client'`.

- [ ] **Step 3: Write minimal implementation**

```python
# mcp-copilot/client.py
from __future__ import annotations

from typing import Any

_TIMEOUT = 5.0


def _http_default():
    import requests
    return requests


def get_telemetry(base: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.get(f"{base}/telemetry", timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"telemetry alınamadı: {e}"}


def get_directive(base: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.get(f"{base}/directive", timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"directive alınamadı: {e}"}


def send_command(base: str, text: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.post(f"{base}/command", json={"text": text}, timeout=_TIMEOUT)
        if not getattr(r, "ok", False):
            return {"ok": False}
        data = r.json()
        return {"ok": True, "directive": data.get("directive")}
    except Exception:
        return {"ok": False}


def set_estop(base: str, on: bool, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    body = {} if on else {"clear": True}
    try:
        r = http.post(f"{base}/estop", json=body, timeout=_TIMEOUT)
        data = r.json()
        return {"estop": bool(data.get("estop", on))}
    except Exception:
        return {"estop": on}


def ask_copilot(base: str, question: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.post(f"{base}/copilot/ask",
                       json={"question": question}, timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"kopilot sorulamadı: {e}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"../.venv/Scripts/python.exe" -m pytest tests/test_client.py -q
```
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add mcp-copilot/client.py mcp-copilot/tests/test_client.py
git commit -m "feat(mcp): HTTP client wrappers with safe degrade"
```

---

## Task 2: `server.py` — FastMCP stdio server

**Files:**
- Create: `mcp-copilot/server.py`
- Test: `mcp-copilot/tests/test_server.py`

The server file stays thin; tool bodies delegate to the tested `client`. The
test imports the module and asserts the FastMCP instance exposes the 5 tools.

- [ ] **Step 1: Write the failing test**

```python
# mcp-copilot/tests/test_server.py
import asyncio
import server as s


def test_mcp_instance_exists():
    assert s.mcp is not None
    assert s.BASE.startswith("http")


def test_all_five_tools_registered():
    tools = asyncio.run(s.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "get_telemetry", "get_directive",
        "send_command", "set_estop", "ask_copilot",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"../.venv/Scripts/python.exe" -m pytest tests/test_server.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'server'`.

- [ ] **Step 3: Write minimal implementation**

```python
# mcp-copilot/server.py
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

import client

BASE = os.environ.get("MCP_BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")

mcp = FastMCP("copilot")


@mcp.tool()
def get_telemetry() -> dict:
    """Aracın son telemetrisi (hız, mesafe, batarya, GPS, online)."""
    return client.get_telemetry(BASE)


@mcp.tool()
def get_directive() -> dict:
    """Aracın o anki üst-seviye hedefi (mode/bias/speed_cap)."""
    return client.get_directive(BASE)


@mcp.tool()
def send_command(text: str) -> dict:
    """Doğal dil komutu gönder (ör. 'sola git', 'yavaşla', 'dur')."""
    return client.send_command(BASE, text)


@mcp.tool()
def set_estop(on: bool) -> dict:
    """Acil dur: on=True durdurur, on=False devam ettirir."""
    return client.set_estop(BASE, on)


@mcp.tool()
def ask_copilot(question: str) -> dict:
    """Son kareye bakarak kopilota soru sor (anlatım/risk döner)."""
    return client.ask_copilot(BASE, question)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"../.venv/Scripts/python.exe" -m pytest tests/test_server.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 5: Full suite**

Run:
```bash
"../.venv/Scripts/python.exe" -m pytest -q
```
Expected: PASS (client 10 + server 2 = 12).

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add mcp-copilot/server.py mcp-copilot/tests/test_server.py
git commit -m "feat(mcp): FastMCP stdio server exposing 5 copilot tools"
```

---

## Task 3: README — Claude Code registration

**Files:**
- Create: `mcp-copilot/README.md`

- [ ] **Step 1: Write `mcp-copilot/README.md`**

```markdown
# Copilot MCP Server

Backend'i (Faz 1, :5000) Claude Code'a tool olarak açar.

## Önkoşul
Backend çalışıyor olmalı (`backend/app.py`). Sim/mobil şart değil.

## Çalıştırma (elle test)
```
set PYTHONIOENCODING=utf-8
set MCP_BACKEND_URL=http://127.0.0.1:5000
"...\.venv\Scripts\python.exe" mcp-copilot\server.py
```
(stdio bekler; Claude Code başlatır, normalde elle çalıştırılmaz.)

## Claude Code'a kayıt
Proje kökünde `.mcp.json` (veya `claude mcp add`):

```json
{
  "mcpServers": {
    "copilot": {
      "command": "c:\\Users\\Berdan\\OneDrive\\Masaüstü\\robot-project\\.venv\\Scripts\\python.exe",
      "args": ["c:\\Users\\Berdan\\OneDrive\\Masaüstü\\robot-project\\mcp-copilot\\server.py"],
      "env": { "MCP_BACKEND_URL": "http://127.0.0.1:5000", "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Claude Code yeniden başlat → araçlar görünür:
`get_telemetry, get_directive, send_command, set_estop, ask_copilot`.

## Araçlar
- get_telemetry() — son telemetri
- get_directive() — aktif directive
- send_command(text) — NL komut (ANTHROPIC_API_KEY yoksa explore default)
- set_estop(on) — True dur / False devam
- ask_copilot(question) — son kareye bakıp anlat
```

- [ ] **Step 2: Commit**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add mcp-copilot/README.md
git commit -m "docs(mcp): Claude Code registration + tool reference"
```

---

## Task 4: Manual e2e (user-run)

- [ ] **Step 1: Full regression**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/mcp-copilot"
"../.venv/Scripts/python.exe" -m pytest -q
```
Expected: 12 passed.

- [ ] **Step 2: Server import smoke (no stdio hang)**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
"./.venv/Scripts/python.exe" -c "import sys; sys.path.insert(0,'mcp-copilot'); import server; print('TOOLS OK', server.BASE)"
```
Expected: `TOOLS OK http://127.0.0.1:5000` (no hang — `mcp.run()` not called on import).

- [ ] **Step 3: Hand off to user**

Tell the user: (1) `.mcp.json`'u proje köküne ekle (README'deki gibi), (2) backend'i
çalıştır, (3) Claude Code'u yeniden başlat, (4) bir araç çağır (ör. "get_telemetry").
Beklenen: backend açıkken telemetri döner; kapalıyken `{"error": ...}` (patlamaz).
Faz 4'ü kullanıcı onaylamadan "bitti" deme.

---

## Self-Review

**Spec coverage (spec §3 MCP, §8 Faz 4):** MCP server `mcp-copilot/`, tools
`get_telemetry/ask_copilot/send_command/estop` + `get_directive` (bonus, ucuz) →
Tasks 1,2. Backend HTTP üzerinden, backend/sim/mobil değişmez (§ "tek Anthropic
noktası" korunur — MCP backend'i çağırır, Claude'u değil). ✔

**Placeholder scan:** yok — her kod adımı tam, komutlar beklenen çıktılı.

**Type consistency:** `client.get_telemetry/get_directive/send_command/set_estop/
ask_copilot(base, ..., http=None)` imzaları Task 1'de tanımlı, Task 2 server
bunları `client.<fn>(BASE, ...)` ile birebir çağırır. `send_command`→`{ok,
directive?}`, `set_estop`→`{estop}` şekilleri test + server'da tutarlı.
`mcp`/`FastMCP`/`@mcp.tool()`/`mcp.run()` standart MCP SDK API. ✔

**Out of scope:** video/Harita (Faz 3.5 backlog), yeni backend endpoint, mobil.
```
