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
