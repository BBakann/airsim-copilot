# Mobil UI Polish — Tasarım (Spec)

Tarih: 2026-05-15
Durum: tasarım onaylandı (kullanıcı), implementasyon planı bekliyor

## Amaç

robot-control-app 3 ekranını (Canlı / Kopilot / Ayarlar) **C/Hybrid** stiline
baştan görsel yenile. Fonksiyon, veri akışı, hook'lar, endpoint'ler **DEĞİŞMEZ** —
sadece sunum. Faz 3 zaten çalışıyor; bu salt görsel kalite.

## Kullanıcı kararları

- Stil: **C · Hybrid** (cockpit teknikliği + modern yumuşak kart/gölge).
- Kamera: **hero/büyük** (mockup canli-hero-v2 boyutu baz).
- Kapsam: **3 ekran** (Canlı + Kopilot + Ayarlar).
- Ayarlar: **bilgi-odaklı**, salt-okunur (API URL, bağlantı, FPS, sürüm). Yeni
  fonksiyon/kalıcı state yok (YAGNI).
- Yaklaşım: **paylaşılan tasarım sistemi** (token + primitive), ekstra paket yok.

## Tasarım sistemi

`src/theme/tokens.ts` — Hybrid paleti ve sabitler (TS objesi, NativeWind class
string'leri):
- Zemin `bg-[#0b1220]`, kart `bg-[#111c30]`, kenar `border-[#1e293b]`,
  accent `text-[#38bdf8]`, ikincil metin `text-slate-400`.
- Risk: low=emerald, warn=amber, critical=red, unknown=slate (mevcut
  `copilotFormat.riskColor` ile uyumlu kalır; tokens onu sarmalamaz, ayrı UI rengi).
- Radius `rounded-2xl`, kart gölge, spacing ölçek.

`src/components/ui/` primitive'ler (logic bilmez; yalnız prop + stil):
- `ScreenContainer` — SafeAreaView + Hybrid zemin + standart padding.
- `Card` — yumuşak köşe, ince kenar, hafif gölge, koyu yüzey.
- `StatPill` — etiket + büyük değer + opsiyonel renk (telemetri/Ayarlar).
- `SectionTitle` — ekran/bölüm başlığı.
- `Pill` — küçük rozet (durum/risk etiketi).

Her primitive: tek sorumluluk, prop arayüzü net, iç değişince tüketici bozulmaz.

## Ekranlar (fonksiyon aynı)

**Canlı** — `src/screens/HomeScreen.tsx` + kamera parçaları
(`RobotCameraView`, `CameraFeed`, `HUDOverlay`, `StatusBadge`, `LiveBadge`),
`DashboardHeader`, `TelemetryGrid`, `QuickActions`, copilot overlay
(`ClaudeBubble`, `EmergencyStopButton`):
- Kamera hero: geniş, kenarsız, büyük radius, üst gradient.
- Üst overlay: CANLI + FPS + GPS rozetleri (HUD).
- `ClaudeBubble` Hybrid (risk renk şeridi, okunur).
- `EmergencyStopButton` büyük yuvarlak, gölgeli, aktifken belirgin.
- Alt: `StatPill` şeridi (Hız / Mesafe / Batarya) + `QuickActions` ikon butonlar.
- `useDashboard` + `useCopilot` aynen kullanılır; prop akışı değişmez.

**Kopilot** — `src/screens/CopilotScreen.tsx`:
- `SectionTitle` başlık.
- Olay kartları `Card`: sol risk renk şeridi + `Pill` etiket + öneri + anlatım.
- Alt sticky `CommandBar` Hybrid (input + Gönder), mevcut `useCopilot` aynen.

**Ayarlar** — `src/screens/SettingsScreen.tsx` (şu an boş placeholder):
- `Card` listesi: API URL (`EXPO_PUBLIC_API_BASE_URL`), bağlantı durumu
  (`useDashboard().isConnected` → online/offline `Pill`), FPS/poll bilgisi
  (`TELEMETRY_POLL_MS`/`COPILOT_POLL_MS` sabitlerinden türetme), app sürümü
  (`expo-constants`). Hepsi salt-okunur. Yeni state yok.

## Sınırlar / izolasyon

- Primitive'ler saf sunum: prop alır, stil verir, hook/fetch bilmez.
- Ekranlar veriyi mevcut hook'lardan alır, primitive'e geçirir.
- Mevcut hook/servis/util (`useDashboard`, `useCopilot`, `copilotApi`,
  `copilotFormat`) **dokunulmaz** → 13 pure test + davranış korunur.

## Test

- Otomatik: mevcut jest paketi (13) regresyon olarak korunur; saf mantık
  değişmediği için yeni birim test gerekmez. Yeni `tokens.ts` saf veri →
  istenirse küçük "renk anahtarları var" testi (opsiyonel, YAGNI sınırında).
- Görsel: manuel e2e (Expo Go, kullanıcı) — 3 ekran C/Hybrid görünür, fonksiyon
  Faz 3'teki gibi (estop, akış, komut, failsafe).

## Kapsam dışı

- Yeni fonksiyon, kalıcı ayar state'i, "Harita"/SLAM (Faz 3.5), gerçek video
  kanalı, MCP (Faz 4). Sadece görsel.
