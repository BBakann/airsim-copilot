# Repo Hijyen + Dokümantasyon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the multi-repo project legible: stop nested-repo git noise, add a top docstring to every Python module, and write a single ARCHITECTURE.md plus a backend README so anyone can understand the layout at a glance — without changing any behavior.

**Architecture:** Pure hygiene/documentation. Root `.gitignore` gains the two embedded repo dirs. Every Python module gets a concise module-level docstring (first lines, behavior-neutral). New `ARCHITECTURE.md` (root) + `backend/README.md` explain components, data flow, run order, phase status, and the known gotchas. No file moves (backend is small, flat, fully tested — restructuring = risk for no gain; documented instead).

**Tech Stack:** Markdown, Python docstrings, git. No deps. Regression = existing pytest suites stay green (docstrings are inert).

---

## Repos touched

- `robot-project` root (local repo, master): `.gitignore`, `ARCHITECTURE.md`,
  `backend/*.py`, `backend/README.md`, `mcp-copilot/*.py`
- `hafize-airsim/autonomous-vehicle-simulation` (fork, main): `copilot_bridge.py`,
  `video_pusher.py` module docstrings
- `robot-control-app` (main): no Python; mobile gitignore already fine — untouched

Commits local only (no push — repo decision still deferred, after this).

## Scope

Davranış değişmez. Backend dosya yapısı **taşınmaz** (küçük, flat, 31 test geçer —
yeniden düzenleme = risk, kazanç yok). Onun yerine docstring + ARCHITECTURE ile
anlaşılır kılınır. gitignore: yalnız kök repoda gömülü-repo gürültüsü kesilir
(sim .gitignore zaten `__pycache__/`+`*.pyc` susturuyor; mobil Python'suz).

---

## Task 1: Root .gitignore — embedded repo noise

**Files:**
- Modify: `.gitignore` (root)

- [ ] **Step 1: Branch**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git checkout master && git checkout -b repo-hygiene
git branch --show-current
```
Expected: `repo-hygiene`.

- [ ] **Step 2: Overwrite `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.superpowers/
node_modules/
.expo/

# Ayrı git repoları (kök repo bunları izlemez — gömülü-repo gürültüsü engeli)
hafize-airsim/
robot-control-app/
```

- [ ] **Step 3: Verify root repo no longer lists the nested repos**

Run:
```bash
git status --porcelain | grep -E "hafize-airsim|robot-control-app" || echo "CLEAN"
```
Expected: `CLEAN`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore docs/
git commit -m "chore: gitignore embedded repos (stop nested-repo noise)"
```

---

## Task 2: Backend module docstrings

**Files:**
- Modify: `backend/app.py`, `backend/state.py`, `backend/copilot.py`,
  `backend/video_state.py`, `backend/conftest.py`

Each gets a top docstring as the very first line(s) of the file (before any
import). Behavior-neutral.

- [ ] **Step 1: `backend/app.py` — prepend docstring**

Insert at the very top (before `from __future__...`):
```python
"""SafeWay backend hub — tek Flask sunucu.

Sim (hafize-airsim) telemetri/olay POST eder, mobil ve MCP buradan okur.
Endpoint grupları:
  /data /telemetry            -> telemetri (sim -> mobil)
  /command /directive /estop  -> kopilot komut + acil dur
  /copilot/event /stream /ask -> Claude analiz (copilot.py üzerinden)
  /video/push /video          -> MJPEG video kanalı (video_state.py)
Durum: state.py (kopilot) + video_state.py (kareler). Anthropic teması
yalnız copilot.py. Çalıştır: PYTHONIOENCODING=utf-8 python backend/app.py
"""
```

- [ ] **Step 2: `backend/state.py` — prepend docstring**

Insert before `from __future__...`:
```python
"""Kopilot paylaşılan durumu (thread-safe).

CopilotState: TTL'li directive (süre dolunca güvenli 'explore'), estop
bayrağı, kapasiteli anlatım log'u. Flask/Anthropic bilmez — saf durum.
"""
```

- [ ] **Step 3: `backend/copilot.py` — prepend docstring**

Insert before `from __future__...`:
```python
"""Tek Anthropic temas noktası.

Copilot.parse_command: doğal dil -> directive JSON (güvenli default'a düşer).
Copilot.analyze_event: kamera karesi+telemetri -> anlatım/risk/directive,
3sn debounce, anahtar yok/hata -> degrade (sürüşü asla bloklamaz).
"""
```

- [ ] **Step 4: `backend/video_state.py` — prepend docstring**

Insert before `from __future__...`:
```python
"""Video kare deposu (thread-safe), state.py'den ayrı.

VideoState: view ('front'/'top') -> (jpeg bytes, ts). Bayatlık kontrolü.
Sim /video/push ile yazar, /video MJPEG generator buradan okur.
"""
```

- [ ] **Step 5: `backend/conftest.py` — prepend docstring**

Insert as the first line (before `import sys`):
```python
"""pytest: backend/ klasörünü import path'e ekler (flat: app, state, copilot...)."""
```

- [ ] **Step 6: Backend regression**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/backend"
"../.venv/Scripts/python.exe" -m pytest -q
```
Expected: 31 passed (docstring inert).

- [ ] **Step 7: Commit**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add backend/app.py backend/state.py backend/copilot.py backend/video_state.py backend/conftest.py
git commit -m "docs(backend): module top docstrings (role of each file)"
```

---

## Task 3: MCP + Sim module docstrings

**Files:**
- Modify: `mcp-copilot/client.py`, `mcp-copilot/server.py`,
  `hafize-airsim/.../copilot_bridge.py`, `hafize-airsim/.../video_pusher.py`

- [ ] **Step 1: `mcp-copilot/client.py` — prepend docstring**

Insert before `from __future__...`:
```python
"""MCP -> backend HTTP sarmalayıcıları (saf, güvenli degrade).

get_telemetry/get_directive/send_command/set_estop/ask_copilot — hepsi
backend (:5000) çağırır, hata -> {'error':...}/güvenli değer (raise yok).
"""
```

- [ ] **Step 2: `mcp-copilot/server.py` — prepend docstring**

Insert before `from __future__...`:
```python
"""Copilot MCP server (FastMCP, stdio).

5 tool'u client.py'ye delege eder; Claude Code .mcp.json ile başlatır.
Backend base: MCP_BACKEND_URL (default http://127.0.0.1:5000).
"""
```

- [ ] **Step 3: MCP regression + commit**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/mcp-copilot"
"../.venv/Scripts/python.exe" -m pytest -q
```
Expected: 12 passed.

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add mcp-copilot/client.py mcp-copilot/server.py
git commit -m "docs(mcp): module top docstrings"
```

- [ ] **Step 4: Sim branch + docstrings**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/hafize-airsim/autonomous-vehicle-simulation"
git checkout main && git checkout -b repo-hygiene
```

`copilot_bridge.py` — insert before `from __future__...`:
```python
"""Sim<->backend kopilot köprüsü (otonomiyi DEĞİŞTİRMEZ).

Saf karar fns: should_emit_event / apply_directive / resolve_controls
(estop > LiDAR > state > directive). CopilotBridge: non-blocking thread,
/directive+/estop poll, /copilot/event push. main.py 20Hz döngüsü beklemez.
"""
```

`video_pusher.py` — insert before `from __future__...`:
```python
"""Bağımsız video yayıncısı (otonomiden ayrı, KENDİ AirSim client'ı).

~12 FPS ön('0')+üst('top') kare -> JPEG -> backend /video/push. airsim
RPC thread-safe değil: ana döngüyle client PAYLAŞMAZ (BufferError önlenir).
"""
```

- [ ] **Step 5: Sim regression + commit + merge**

Run:
```bash
"../../.venv/Scripts/python.exe" -m pytest -q
```
Expected: 21 passed.

```bash
git add copilot_bridge.py video_pusher.py
git commit -m "docs(sim): module top docstrings"
git checkout main
git merge --no-ff repo-hygiene -m "merge: sim module docstrings"
git branch -d repo-hygiene
```

---

## Task 4: ARCHITECTURE.md + backend README

**Files:**
- Create: `ARCHITECTURE.md` (root)
- Create: `backend/README.md`

- [ ] **Step 1: Create `ARCHITECTURE.md`**

```markdown
# SafeWay AirSim Kopilot — Mimari

AirSim otonom araç + Claude kopilot + mobil. Otonomi (SLAM/LiDAR/planlayıcı)
alttan sürer, **dokunulmaz**; Claude üst katman (anlat/komut/uyar).

## 3 ayrı git repo (iç içe klasör)

```
robot-project/                 LOKAL repo (master) — backend + mcp + docs
├─ backend/                    Flask hub (:5000)
├─ mcp-copilot/                Claude Code MCP server
├─ docs/superpowers/           spec + plan + tasarım
├─ .venv/                      Python 3.10 sanal ortam (git'e girmez)
├─ .mcp.json                   Claude Code MCP kaydı
├─ hafize-airsim/.../          AYRI repo (fork, main) — SİM
└─ robot-control-app/          AYRI repo (main) — MOBİL (Expo/RN)
```
Kök repo gömülü 2 repoyu izlemez (.gitignore). Commit'ler **lokal** (push yok,
repo birleştirme kararı ayrı).

## Veri akışı

```
AirSim ── main.py (20Hz sense-plan-act, otonomi)
            ├─ copilot_bridge: /copilot/event, /directive, /estop
            └─ video_pusher (kendi client): /video/push  ~12 FPS
                     │ HTTP LAN
              backend/app.py (Flask :5000)
              state.py(kopilot) · video_state.py(kare) · copilot.py(Anthropic)
              /data /telemetry /command /directive /estop
              /copilot/* /video /video/push
                     │ HTTP
        ┌────────────┼─────────────┐
   robot-control-app          mcp-copilot
   (Expo: Canlı/Kopilot/      (Claude Code:
    Ayarlar, video toggle,     get_telemetry/send_command/
    estop, kopilot akışı)      set_estop/ask_copilot)
```

## Parçalar

| Parça | Yer | Ne |
|---|---|---|
| backend | `backend/` | Flask hub; tek Anthropic noktası copilot.py |
| sim köprü | `hafize-airsim/.../copilot_bridge.py` | event/directive/estop, otonomi değişmez |
| video | `.../video_pusher.py` + backend `/video*` | MJPEG ön+üst |
| mobil | `robot-control-app/` | Expo: 3 sekme, video, estop |
| MCP | `mcp-copilot/` | Claude Code tool'ları |

## Çalıştırma sırası

1. AirSimNH aç (settings.json: FrontSensor/Lidar1/Gps + "top" kamera)
2. `PYTHONIOENCODING=utf-8 .venv/Scripts/python backend/app.py`
3. sim: `python hafize-airsim/autonomous-vehicle-simulation/main.py`
4. mobil: `cd robot-control-app && npx expo start` (telefon aynı Wi-Fi, .env.local LAN IP)
5. MCP: Claude Code reload (.mcp.json), backend açık

## Faz durumu

0 baseline ✔ · 1 backend hub ✔ · 2 sim köprü ✔ · 3 mobil ✔ · 3.A kamera fix ✔
· 3.B UI polish ✔ · 3.5 video ✔ · 4 MCP ✔ · 5 UE senaryo (opsiyonel, yapılmadı)
Backlog: Harita/SLAM, ANTHROPIC_API_KEY ile gerçek kopilot, video kalite tuning,
mobil ekstra (preset/sesli/bildirim/manuel sürüş).

## Tuzaklar

- `.venv/` = Python sanal ortam; `__pycache__/` = bytecode önbellek. İkisi de
  git'e girmez, elle düzenlenmez, silinse üretilir.
- Tüm Python: `PYTHONIOENCODING=utf-8` (Windows cp1254 yoksa çöker).
- airsim RPC client thread-safe DEĞİL — her thread kendi `airsim.CarClient()`.
- settings.json gerçek yolu: `C:\Users\Berdan\OneDrive\Belgeler\AirSim\settings.json`.
- `airsim` pip: Python 3.10, `pip install --no-build-isolation airsim`.
- Test: backend `pytest`(31), mcp(12), sim(21), mobil `npx jest`(18). Anthropic
  mock = $0.
```

- [ ] **Step 2: Create `backend/README.md`**

```markdown
# backend — Flask Kopilot Hub

Tek sunucu (:5000). Sim yazar, mobil + MCP okur. Otonomi burada YOK.

## Dosyalar
- `app.py` — HTTP yüzey (tüm route'lar), modül durum nesneleri
- `state.py` — CopilotState: TTL directive + estop + log (thread-safe)
- `video_state.py` — VideoState: view->jpeg kare (thread-safe)
- `copilot.py` — tek Anthropic noktası (parse_command / analyze_event)
- `conftest.py` — pytest import path
- `tests/` — 31 test, Anthropic mock ($0)
- `COPILOT_DEV.md` — manuel e2e

## Çalıştır
```
set PYTHONIOENCODING=utf-8
set ANTHROPIC_API_KEY=...   # opsiyonel; yoksa kopilot 'çevrimdışı' degrade
..\.venv\Scripts\python.exe app.py
```

## Test
```
..\.venv\Scripts\python.exe -m pytest -q
```
```

- [ ] **Step 3: Commit + finish root branch**

```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project"
git add ARCHITECTURE.md backend/README.md
git commit -m "docs: ARCHITECTURE.md + backend README (legible layout)"
git checkout master
git merge --no-ff repo-hygiene -m "merge: repo hygiene + docs"
cd backend && "../.venv/Scripts/python.exe" -m pytest -q && cd ..
git branch -d repo-hygiene
```
Expected: 31 passed, branch deleted.

---

## Self-Review

**Coverage:** gitignore embedded repos → T1. Her Python modülü docstring →
backend T2 (5 dosya), mcp+sim T3 (4 dosya). Hiyerarşi/açıklama → T4
(ARCHITECTURE.md + backend/README.md). Backend taşınmaz (gerekçe scope'ta).
Davranış değişmez → her parçada regression (backend 31, mcp 12, sim 21). ✔

**Placeholder scan:** yok — tüm docstring/gitignore/markdown içeriği tam.

**Consistency:** docstring'ler mevcut dosya rolleriyle birebir (copilot.py tek
Anthropic, video_pusher kendi client, state.py TTL/estop/log). ARCHITECTURE faz
durumu + tuzaklar hafıza/önceki fazlarla tutarlı. Dosya yolları gerçek. ✔

**Out of scope:** repo birleştirme/push, Faz 5, backlog — sonraya.
```
