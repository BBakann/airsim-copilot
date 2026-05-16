# Faz 3.5 — Gerçek Video Kanalı (Tasarım/Spec)

Tarih: 2026-05-16
Durum: tasarım onaylandı (kullanıcı), plan bekliyor

## Amaç

Mobil Canlı kameradaki "leş periyodik JPEG" yerine **akıcı video**: ayrı MJPEG
kanalı, ön + 3. şahıs üst görünüm, telefonda toggle + dokun→tam ekran. Otonomi,
telemetri, kopilot, estop, MCP **değişmez** — ayrı kanal eklenir.

## Kullanıcı kararları

- Sunum: **toggle** (Ön/Üst butonu, tek aktif stream — hafif). PiP/yan-yana değil.
- Kamera pencereye **dokun → tam ekran** (Modal), tekrar dokun/kapat → geri.
  Opsiyonel: tam ekranda landscape.
- Üst kamera: **3. şahıs takipçi** (araç arkasından-yukarıdan, ~-20° pitch).
- Transport: **copilot_bridge thread'i** kullan (ayrı video push), backend MJPEG.
- Kalite: ~10-15 FPS, JPEG ~80, ~1280×720.

## Mimari

```
AirSim ──simGetImages(["0","top"])──> SİM copilot_bridge VIDEO THREAD (~12 FPS)
                                         │ POST /video/push?view=front|top (jpeg bytes)
                                         ▼
BACKEND  state: son jpeg+ts (front/top)
  POST /video/push?view=   ← sim
  GET  /video?view=        → MJPEG multipart/x-mixed-replace (~12 FPS)
  (/data /telemetry /copilot/* /estop /directive DEĞİŞMEZ)
                                         │ HTTP (LAN)
                                         ▼
MOBİL  WebView <img src="{base}/video?view=front|top">
       RobotCameraView: toggle Ön/Üst + dokun→tam ekran Modal
       Fallback: video yok/backend kapalı → mevcut JPEG-poll kamera
```

Otonomi thread'i ile video thread'i ayrı; video kopması sürüşü etkilemez.

## Bileşenler

**Sim** (`hafize-airsim/autonomous-vehicle-simulation`)
- `settings.json`: vehicle Cameras'a `"top"` ekle — `X≈-6, Z≈-3, Pitch≈-20`,
  Scene capture. (Kullanıcı yerleştirir; spec'te değer önerilir.)
- `copilot_bridge.py`: yeni `VideoPusher` (kendi daemon thread). Döngü: iki kare
  çek (`"0"`,`"top"`) → JPEG encode (kalite 80) → `POST /video/push?view=` ham
  bytes, `timeout` kısa, hata yut. FPS hedefi `VIDEO_FPS=12`. Otonomi/telemetri
  kodu **dokunulmaz**; `main.py`'a sadece `VideoPusher().start()/stop()` (tek
  satır, mevcut bridge start/stop yanına).

**Backend** (`backend/`)
- `video_state.py` (yeni): thread-safe `set_frame(view, bytes)` /
  `get_frame(view)->(bytes,ts)`. `state.py`'den ayrı (tek sorumluluk).
- `app.py`: `POST /video/push` (raw body, `?view=front|top`, view doğrula),
  `GET /video?view=` → Flask streaming `Response(generator,
  mimetype="multipart/x-mixed-replace; boundary=frame")`, son kareyi ~12 FPS
  yollar; kare yoksa/bayatsa (>2 sn) düşük-hızlı bekleme + boş atla.

**Mobil** (`robot-control-app`)
- Dep: `react-native-webview` (Expo `npx expo install`). RN `<Image>` MJPEG
  multipart oynatamaz; WebView zorunlu.
- `src/components/camera/VideoStream.tsx` (yeni): WebView, `view` prop'a göre
  `{BASE}/video?view=front|top`.
- `RobotCameraView.tsx`: video varsa `VideoStream`, yoksa eski `imageUrl`
  (fallback). Toggle butonu (Ön/Üst), pencereye `Pressable` → tam ekran `Modal`
  (Modal içinde de toggle + kapat). `useDashboard` / props **değişmez**.

## Hata & failsafe

- Sim video thread'i ölse/backend kapalı: otonomi+telemetri sürer (ayrı thread).
- Mobil: `/video` ulaşmazsa WebView boş → `RobotCameraView` fallback olarak
  mevcut JPEG-poll kareyi gösterir (useDashboard.cameraImage). Donma yok.
- Backend push yoksa `/video` boş/placeholder akıtır, hang etmez.
- Bant: toggle = telefon tek view stream; sim→backend LAN iki kare (ucuz).

## Test

- Backend birim (pytest, mevcut paket): `video_state` set/get + bayatlık;
  `/video/push` view doğrulama (geçersiz view → 400); `/video` generator ilk
  kareyi/placeholder döndürür (kısa, mock). MJPEG akışının kendisi manuel.
- Sim: `VideoPusher` kare-encode + push payload saf fonksiyon, AirSim'siz
  (sahte client + sahte http) test.
- Mobil: WebView/görsel/tam ekran = manuel e2e (Expo Go, kullanıcı).
- Regresyon: backend 21, mcp 12, mobil 15 testleri kırılmaz.

## Kapsam dışı

- WebRTC/ses, kayıt, Harita/SLAM, çoklu izleyici, video kaydetme. Sadece canlı
  MJPEG ön+üst toggle.
