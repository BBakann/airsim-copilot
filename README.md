# 🚗 AirSim Kopilot

**Kendi süren bir AirSim aracı + Claude yapay zekâ yardımcı pilotu + canlı mobil kontrol.**

Otonom araç AirSim'de kendi sürer (SLAM, LiDAR engel kaçınma, davranış
planlayıcı). Üstüne bir **Claude kopilot katmanı** oturur: sahneyi anlatır,
doğal dil komut alır, tehlikede uyarır. Telefondan canlı video + komut, PC'den
Claude Code (MCP) ile kontrol. **Otonomiye dokunulmaz — kopilot üst katman.**

---

## ✨ Neler var

- **Otonom sürüş** — AirSim'de LiDAR tabanlı engel kaçınma + 2D SLAM + davranış
  durum makinesi (DRIVING / BRAKING / RECOVERY). *Değiştirilmedi, sağlam.*
- **Claude kopilot** — Türkçe doğal dil komut → yapısal directive
  (*"on beş metre yavaşça git, yaya görünce dur"* → `goto, speed_cap 0.3,
  stop_on: pedestrian`). Kamera karesine bakıp **sahne anlatımı + risk**.
- **Acil dur** — en yüksek öncelik, anlık fren (Claude'dan bağımsız, sert override).
- **Canlı video** — MJPEG, **ön + 3. şahıs üst** kamera, telefonda toggle +
  dokun→tam ekran.
- **Mobil uygulama** (Expo/React Native) — 3 sekme: **Canlı** (video+telemetri+
  ACİL DUR), **Kopilot** (sohbet + komut chip'leri), **Ayarlar**.
- **MCP server** — PC'de Claude Code aracı olarak: `get_telemetry`,
  `send_command`, `set_estop`, `ask_copilot`.
- **Maliyet bilinçli** — Claude vision yalnız state değişiminde (15 sn debounce);
  otomatik testlerde Anthropic mock = **$0**.

## 🧩 Mimari (özet)

```
AirSim ── sim (otonomi 20Hz)
            ├─ copilot köprü → /copilot/event, /directive, /estop
            └─ video pusher  → /video/push  (~12 FPS, kendi client'ı)
                  │ HTTP (LAN)
            backend (Flask :5000)  ·  Claude teması yalnız copilot.py
                  │
        ┌─────────┼──────────┐
     Mobil (Expo)        MCP (Claude Code / PC)
```
Üç ayrı git repo: **backend+mcp+docs** (bu repo), **sim** (fork), **mobil**.
Detay: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 🚀 Çalıştırma

Önkoşul: AirSimNH (settings.json'da `FrontSensor`/`Lidar1`/`Gps` + `top`
kamera), Python 3.10 venv, telefon Expo Go (PC ile aynı Wi-Fi).

```powershell
# 1) AirSimNH aç (araç sahnede)

# 2) backend  (ANTHROPIC_API_KEY opsiyonel; yoksa kopilot güvenli degrade)
$env:PYTHONIOENCODING="utf-8"
$env:ANTHROPIC_API_KEY = Read-Host "ANTHROPIC anahtari"
.\.venv\Scripts\python.exe backend\app.py

# 3) sim
& .\.venv\Scripts\python.exe hafize-airsim\autonomous-vehicle-simulation\main.py

# 4) mobil
cd robot-control-app ; npx expo start
```
MCP: proje kökünde `.mcp.json` var → Claude Code reload, backend açık.

## ✅ Test

| Parça | Komut | Sonuç |
|---|---|---|
| backend | `cd backend && ..\.venv\Scripts\python -m pytest -q` | 31 ✓ |
| sim | `…\python -m pytest -q` (sim klasörü) | 20 ✓ |
| mcp | `cd mcp-copilot && ..\.venv\Scripts\python -m pytest -q` | 12 ✓ |
| mobil | `cd robot-control-app && npx jest` | 25 ✓ |

Hepsi Anthropic **mock** → maliyet $0. Gerçek API sadece canlı kullanımda
(Haiku, ucuz, spend-limit ile güvenli).

## 🗺️ Durum

**Tamam:** otonomi baseline · backend hub · sim köprü · mobil kopilot · UI
polish · canlı video (ön/üst) · MCP · gerçek Claude (NL+vision) doğrulandı.

**Yol haritası (backlog):** kontrol primitifleri (geri/hızlan) · sıkışma-kurtulma
süpervizörü · gerçek waypoint navigasyon · perception (yol/nesne/yaya) ·
Harita/SLAM sekmesi · UE senaryo (yaya/trafik/hava).

## 📂 Bu repo

```
backend/      Flask hub (app.py · state.py · video_state.py · copilot.py)
mcp-copilot/  Claude Code MCP server
docs/         spec + plan + tasarım kayıtları
ARCHITECTURE.md   tam mimari + tuzaklar
```
Sim ve mobil **ayrı repolarda** (kök `.gitignore`'da; iç içe klasör).

## ⚠️ Notlar

- Tüm Python: `PYTHONIOENCODING=utf-8` (Windows).
- airsim RPC client thread-safe değil — her thread kendi client'ı.
- `.venv/` `__pycache__/` = Python ortamı/önbellek, git'e girmez.
- Anahtar koda/git'e/loga **yazılmaz** — env'e `Read-Host` ile girilir.
