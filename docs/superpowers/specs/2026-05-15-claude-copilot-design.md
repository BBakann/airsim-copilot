# Claude Kopilot + Mobil Canlandırma — Tasarım (Spec)

Tarih: 2026-05-15
Durum: tasarım onaylandı, implementasyon planı bekliyor

## 1. Amaç

AirSim otonom araç projesine **Claude kopilot üst katmanı** ekle ve mobil uygulamayı
canlandır. Otonomi (SLAM, LiDAR avoidance, behavior/local planner) **alttan sürmeye
devam eder, dokunulmaz**. Claude düşük seviye kontrol yapmaz — anlamsal beyin +
komutan + güvenlik gözcüsü olarak üstte çalışır.

## 2. Kararlar (netleştirme sonucu)

- **Kopilot yetki:** otonomi sürer, Claude üst katman. Manuel/onaylı joystick YOK
  (otonomiyi öldürür, mantıksız).
- **Kopilot rolü:** tam katman = gözlemci/anlatıcı + misyon komutanı + güvenlik
  süpervizörü.
- **Arayüz:** ikisi de — merkezî köprü hem mobil hem Claude Code (MCP) hizmet eder.
- **Vision tetik:** olay tetikli (state değişimi, engel yakın, kullanıcı sorusu).
  Periyodik değil — maliyet + alaka.
- **Auto-estop:** default kapalı (uyarı + insan tek dokunuş). Opt-in.
- **Model:** olay anlatımı için hızlı/ucuz `claude-haiku-4-5`; karmaşık misyon
  ayrıştırma gerekirse `claude-sonnet-4-6`. Sistem promptu cache'li.
- **Commit & repo:** repo düzeni karışık (robot-control-app ayrı repo;
  hafize-airsim ayrı repo/fork; backend repo'suz; robot-project kökü git değil).
  Commit ve yerleşim **en sona** — repo temizliğinden sonra.

## 3. Mimari

```
SİM (hafize-airsim, 20Hz)              BACKEND HUB (Flask, genişletilmiş)
 sense→plan→act (DEĞİŞMEZ)             /data /telemetry            (var)
  + state değişimi → POST /copilot/event   /copilot/event → copilot.py → Claude
  + her döngü → GET /directive             /copilot/ask
  + estop bayrağı → fren                   /copilot/stream → mobil anlatım/uyarı
        │  HTTP (LAN / ngrok)               /command → NL→directive
        ▼                                   /directive (sim okur)
 copilot_bridge.py (ince hook)              /estop (en yüksek öncelik)
                                            /map (2D SLAM görsel)
 MOBİL (Expo)            MCP SERVER         copilot.py: tek Anthropic noktası
  Canlı/Harita/Kopilot    get_telemetry     state.py: thread-safe ortak durum
  chat+ses+ACİL DUR       ask_copilot
  /stream poll→WS         send_command/estop → Claude Code (PC)
```

Düşük seviye otonomi sim'de izole. Claude'a tek temas: `backend/copilot.py`.
Sim/mobil/MCP doğrudan Claude çağırmaz — hep backend üzerinden.

## 4. Veri akışı

- **A. Telemetri (var, değişmez):** sim `POST /data` (her `SEND_INTERVAL`) →
  backend `last_telemetry` → mobil `GET /telemetry` 1sn poll.
- **B. Copilot olay:** sim state değişimi / `min_lidar_dist` eşik altı →
  `POST /copilot/event {state, prev_state, distance, lidar_min, kare_b64, gps}` →
  `copilot.py` → Anthropic vision (cache'li sistem prompt) →
  `{anlatım, risk: low|warn|critical, öneri, directive?}` → `copilot_log`.
- **C. Anlatım→mobil:** mobil `GET /copilot/stream?since=<ts>` (poll→WS) →
  Kopilot sekmesi akış + Canlı sekmesi balon.
- **D. Komut:** mobil/MCP `POST /command {text}` → `copilot.py` NL→
  `directive {mode: explore|goto|stop, bias, speed_cap, target?, stop_on?}` →
  `current_directive` → sim her döngü `GET /directive` → local_planner bias /
  throttle cap'e uygula. **Otonomi çekirdeği değişmez, sadece üst parametre.**
- **E. Acil dur:** mobil/MCP `POST /estop` → `estop=True` → sim her döngü okur →
  `brake=1, throttle=0` (state machine bypass). `{clear:true}` ile kalkar.

## 5. Bileşenler

| Birim | Sorumluluk | Bağımlılık |
|---|---|---|
| `backend/app.py` | HTTP yüzey, telemetri (var) + yeni ince route | flask |
| `backend/copilot.py` | tek Anthropic noktası: event→analiz, NL→directive, cache | anthropic |
| `backend/state.py` | `last_telemetry`, `copilot_log`, `current_directive`, `estop` thread-safe | — |
| `hafize-airsim .../copilot_bridge.py` | state-change algıla→event POST, directive poll, estop oku (main.py'a ince hook) | requests |
| `mcp-copilot/` (Faz 4) | backend HTTP → Claude Code tool | mcp sdk |
| `robot-control-app src/screens` | 3 sekme: Canlı/Harita/Kopilot | mevcut yapı |
| `robot-control-app src/services/copilot.ts` | /command, /copilot/stream, /estop, /map | fetch |

İlke: her birim tek iş. `main.py` eklentisi sadece köprü (algıla/POST/oku), karar
değil — otonomi çekirdeği izole.

Mobil yerleşim: **B + C** (sekmeli iskelet + Canlı'da overlay). Sekmeler
Canlı / Harita / Kopilot. Canlı'da kamera üstüne Claude balonu + kalıcı ACİL DUR.

## 6. Hata & failsafe

Sim öncelik (her döngü): `estop` > LiDAR acil kaçış > behavior_planner state >
directive bias. Copilot **hep additive**, çökerse otonomi etkilenmez.

- Sim→backend kopması: POST/GET `timeout=1s` non-blocking, hata yutulur. Bağlantı
  yoksa sim saf otonom sürer (LiDAR/SLAM lokal).
- Claude API hata/timeout/kota: `copilot.py` graceful degrade →
  `{risk:"unknown", anlatım:"kopilot çevrimdışı"}`. Sürüşü asla bloklamaz.
  Event debounce: min 3 sn arası vision çağrısı (maliyet tavanı + spam yok).
- Directive TTL ~30 sn: süresi geçen yok sayılır → saf keşfe döner.
- Auto-estop default kapalı; açıksa bile insan override. Ani çarpışma = LiDAR'ın
  işi; Claude yavaş anlamsal katman.
- Mobil: mevcut `useDashboard` stale-frame/gate mantığı korunur; kopilot stream
  ayrı, kopması telemetriyi etkilemez.
- "Araç sıkıştı" (speed≈0 + pos donuk + state=DRIVING): bilinen otonomi recovery
  zayıflığı. Güvenlik süpervizörü bunu sezer (telemetri pattern) → uyarı +
  opsiyonel reroute directive. Otonomi koduna girilmez, üstten reroute.

## 7. Test

- `copilot.py` birim: Anthropic mock → NL→directive parse (geçersiz→güvenli
  default), event→analiz (sabit kare fixture). Gerçek API yok.
- `backend` entegrasyon: `/command /directive /estop /copilot/event` state
  geçişleri, Claude mock.
- Sim köprü: state-change algılama saf fonksiyon, AirSim'siz test. estop çözücü:
  estop set iken state ne olursa olsun brake.
- Mobil: copilot servis poll + ACİL DUR hook testi; sim'de elle uçtan uca.
- Implementasyonda TDD (kırmızı→yeşil→refactor), her birim önce test.

## 8. Fazlı yol haritası

- **Faz 0 — Baseline (BİTTİ ✔):** AirSimNH (sensörlü settings.json) + venv (Py3.10,
  airsim 1.8.1) + backend (utf-8) + main.py otonom sürüş + mobil Expo Go LAN.
  Uçtan uca kanıtlandı.
- **Faz 1 — Backend hub:** `state.py`, `copilot.py` (Anthropic, event→analiz,
  NL→directive, debounce, cache), yeni route'lar. Otonomi/sim değişmez.
- **Faz 2 — Sim köprü:** `copilot_bridge.py` + main.py ince hook (state-change
  event POST, directive poll, estop oku). Düşük seviye SLAM/LiDAR değişmez.
- **Faz 3 — Mobil yeniden yapı:** B+C iskelet, sekmeler Canlı/Harita/Kopilot,
  Claude balon + ACİL DUR, copilot.ts servis, /map SLAM görseli.
- **Faz 4 — MCP server:** `mcp-copilot/` tool'lar → Claude Code'dan kontrol.
- **Faz 5 (opsiyonel) — UE senaryo:** Unreal'de yaya/trafik/hava senaryoları,
  copilot'u zor durumda test.

## 9. Açık konular / prerequisitler

- **Anthropic API key & maliyet** — API, Pro/Max aboneliğinden **bağımsız ve ayrı
  faturalanır** (kullandıkça-öde, token başına). Pro'dan düşmez, Pro API'yi
  kapsamaz. Gerekli: console.anthropic.com'da ödeme + kredi + **harcama tavanı
  (spend limit, ör. $5)**. Otomatik testler Anthropic mock'lu → **$0**; gerçek
  API sadece elle uçtan uca demo (Haiku 4.5 + debounce + cache → oturum başı
  ~sent). Yeni hesap genelde $5 ücretsiz kredi.
- **Frame stream / video kalitesi** — şu an `SEND_INTERVAL=5` → ~0.2 FPS düşük
  kalite kare (bug değil, ayar). Gerçek canlı video Faz 3'te ayrı kanal
  (WebSocket/MJPEG) ile. Faz 0'da kabul edildi.
- **Repo düzeni & commit** — robot-control-app / hafize-airsim ayrı repolar
  (hafize-airsim fork), backend repo'suz, kök git değil. Commit + yerleşim
  kararı en sona, repo temizliğinden sonra.
- **ngrok vs LAN** — aynı Wi-Fi'de LAN IP yeter; uzak erişim için ngrok.
- **Windows firewall** — telefon erişimi için 5000/8081 inbound (admin gerekti,
  elle eklenecek).
- **Konsol encoding** — Windows cp1254; tüm Python süreçleri
  `PYTHONIOENCODING=utf-8` ile çalıştırılmalı.
