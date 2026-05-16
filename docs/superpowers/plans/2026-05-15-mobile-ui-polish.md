# Mobil UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the 3 mobile screens (Canlı / Kopilot / Ayarlar) in the C/Hybrid visual style on a shared design-system layer, with the camera as a large hero — without changing any logic, hook, service, or endpoint.

**Architecture:** A tiny theme module (`theme/tokens.ts`) plus 5 presentational primitives (`components/ui/`) that know only props+style. Existing data hooks (`useDashboard`, `useCopilot`) and services (`copilotApi`, `copilotFormat`) are untouched; screens keep the exact same data wiring and just re-render through the new primitives. Pure logic keeps its 13 jest tests; visuals are verified by user manual e2e.

**Tech Stack:** Expo SDK 54, React Native 0.81, expo-router, NativeWind v4, expo-constants, expo-haptics; jest+ts-jest (already configured) for the pure `tokens` test.

---

## Repo / commit note

`robot-control-app` is its own git repo. Work on branch `faz3b-ui-polish`,
committed locally (base `main`, no push — repo decision deferred, consistent with
prior phases). App dir (CWD): `c:\Users\Berdan\OneDrive\Masaüstü\robot-project\robot-control-app`.

## Scope

Görsel-only. Fonksiyon/veri akışı/hook/endpoint **değişmez**. Kapsam dışı: yeni
fonksiyon, kalıcı ayar state, Harita/SLAM (Faz 3.5), gerçek video, MCP (Faz 4).

## File Structure

| File | Responsibility |
|---|---|
| `src/theme/tokens.ts` (create) | Hybrid palet + NativeWind class string sabitleri. Saf veri. |
| `src/theme/tokens.test.ts` (create) | tokens anahtar bütünlüğü (pure jest). |
| `src/components/ui/ScreenContainer.tsx` (create) | SafeArea + Hybrid zemin + padding. |
| `src/components/ui/Card.tsx` (create) | Yumuşak kart yüzeyi. |
| `src/components/ui/StatPill.tsx` (create) | Etiket + büyük değer + renk. |
| `src/components/ui/SectionTitle.tsx` (create) | Başlık. |
| `src/components/ui/Pill.tsx` (create) | Küçük rozet. |
| `src/components/camera/RobotCameraView.tsx` (rewrite) | Self-contained hero kamera + HUD rozetleri. |
| `src/components/copilot/ClaudeBubble.tsx` (rewrite) | Hybrid balon. |
| `src/components/copilot/EmergencyStopButton.tsx` (rewrite) | Hybrid büyük FAB. |
| `src/components/copilot/CommandBar.tsx` (rewrite) | Hybrid komut çubuğu. |
| `src/components/dashboard/DashboardHeader.tsx` (rewrite) | Hybrid başlık. |
| `src/components/dashboard/TelemetryGrid.tsx` (rewrite) | StatPill ızgarası. |
| `src/components/dashboard/QuickActions.tsx` (rewrite) | İkon aksiyon butonları. |
| `src/screens/HomeScreen.tsx` (rewrite) | Canlı: kamera hero + overlay + telemetri + aksiyon. |
| `src/screens/CopilotScreen.tsx` (rewrite) | Kopilot: olay kartları + komut çubuğu. |
| `src/screens/SettingsScreen.tsx` (rewrite) | Ayarlar: bilgi kartları (salt-okunur). |

Eski `camera/CameraFeed.tsx`, `HUDOverlay.tsx`, `StatusBadge.tsx`,
`LiveBadge.tsx` artık import edilmez (RobotCameraView self-contained olur);
silinmez (zararsız), Task 8'de not edilir.

**Primitive prop arayüzleri (her görevde aynen kullanılır):**
- `ScreenContainer({ children, scroll?: boolean })`
- `Card({ children, className?: string })`
- `StatPill({ label: string, value: string, accent?: "sky"|"amber"|"emerald"|"slate" })`
- `SectionTitle({ children })`
- `Pill({ label: string, tone?: "sky"|"amber"|"emerald"|"red"|"slate" })`

---

## Task 0: Branch

- [ ] **Step 1: Create branch**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/robot-control-app"
git checkout main && git checkout -b faz3b-ui-polish
git branch --show-current
```
Expected: `faz3b-ui-polish`.

---

## Task 1: `theme/tokens.ts` (+ pure test)

**Files:**
- Create: `src/theme/tokens.ts`
- Test: `src/theme/tokens.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/theme/tokens.test.ts
import { T, accentText } from "./tokens";

test("core tokens exist as non-empty strings", () => {
  for (const k of ["screenBg", "card", "border", "accent", "title", "muted"] as const) {
    expect(typeof T[k]).toBe("string");
    expect(T[k].length).toBeGreaterThan(0);
  }
});

test("accentText maps known accents and falls back", () => {
  expect(accentText("sky")).toContain("sky");
  expect(accentText("amber")).toContain("amber");
  expect(accentText("emerald")).toContain("emerald");
  expect(accentText("red")).toContain("red");
  expect(accentText("slate")).toContain("slate");
  // bilinmeyen -> slate fallback
  expect(accentText("nope" as any)).toContain("slate");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npx jest src/theme/tokens.test.ts
```
Expected: FAIL — cannot find module `./tokens`.

- [ ] **Step 3: Write minimal implementation**

```ts
// src/theme/tokens.ts
export type Accent = "sky" | "amber" | "emerald" | "red" | "slate";

export const T = {
  screenBg: "bg-[#0b1220]",
  card: "bg-[#111c30] border border-[#1e293b] rounded-2xl",
  cardShadow: "shadow-lg shadow-black/40",
  border: "border-[#1e293b]",
  accent: "text-[#38bdf8]",
  title: "text-white font-bold",
  muted: "text-slate-400",
  pad: "px-4",
};

export function accentText(a: Accent): string {
  switch (a) {
    case "sky": return "text-sky-400";
    case "amber": return "text-amber-400";
    case "emerald": return "text-emerald-400";
    case "red": return "text-red-400";
    default: return "text-slate-300";
  }
}

export function accentBg(a: Accent): string {
  switch (a) {
    case "sky": return "bg-sky-500";
    case "amber": return "bg-amber-500";
    case "emerald": return "bg-emerald-600";
    case "red": return "bg-red-600";
    default: return "bg-slate-600";
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npx jest src/theme/tokens.test.ts
```
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/theme/tokens.ts src/theme/tokens.test.ts
git commit -m "feat(mobile): Hybrid theme tokens (+pure test)"
```

---

## Task 2: UI primitives

**Files:**
- Create: `src/components/ui/ScreenContainer.tsx`, `Card.tsx`, `StatPill.tsx`, `SectionTitle.tsx`, `Pill.tsx`

No unit test (RN/JSX, manual e2e). Full code below.

- [ ] **Step 1: `ScreenContainer.tsx`**

```tsx
import React from "react";
import { ScrollView, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { T } from "../../theme/tokens";

interface Props { children: React.ReactNode; scroll?: boolean }

export default function ScreenContainer({ children, scroll }: Props) {
  const inner = scroll ? (
    <ScrollView contentContainerStyle={{ paddingBottom: 28 }}>
      {children}
    </ScrollView>
  ) : (
    <View className="flex-1">{children}</View>
  );
  return (
    <SafeAreaView className={`flex-1 ${T.screenBg}`} edges={["top"]}>
      {inner}
    </SafeAreaView>
  );
}
```

- [ ] **Step 2: `Card.tsx`**

```tsx
import React from "react";
import { View } from "react-native";
import { T } from "../../theme/tokens";

interface Props { children: React.ReactNode; className?: string }

export default function Card({ children, className = "" }: Props) {
  return (
    <View className={`${T.card} ${T.cardShadow} p-4 ${className}`}>
      {children}
    </View>
  );
}
```

- [ ] **Step 3: `StatPill.tsx`**

```tsx
import React from "react";
import { Text, View } from "react-native";
import { Accent, accentText, T } from "../../theme/tokens";

interface Props { label: string; value: string; accent?: Accent }

export default function StatPill({ label, value, accent = "sky" }: Props) {
  return (
    <View className={`flex-1 ${T.card} px-3 py-3`}>
      <Text className="text-[10px] uppercase tracking-wide text-slate-400">
        {label}
      </Text>
      <Text className={`text-xl font-extrabold ${accentText(accent)}`}>
        {value}
      </Text>
    </View>
  );
}
```

- [ ] **Step 4: `SectionTitle.tsx`**

```tsx
import React from "react";
import { Text } from "react-native";

interface Props { children: React.ReactNode }

export default function SectionTitle({ children }: Props) {
  return (
    <Text className="px-4 pb-2 pt-3 text-lg font-bold text-white">
      {children}
    </Text>
  );
}
```

- [ ] **Step 5: `Pill.tsx`**

```tsx
import React from "react";
import { Text, View } from "react-native";
import { Accent, accentBg } from "../../theme/tokens";

interface Props { label: string; tone?: Accent }

export default function Pill({ label, tone = "slate" }: Props) {
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${accentBg(tone)}`}>
      <Text className="text-[10px] font-bold text-white">{label}</Text>
    </View>
  );
}
```

- [ ] **Step 6: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/components/ui/
git commit -m "feat(mobile): UI primitives (ScreenContainer/Card/StatPill/SectionTitle/Pill)"
```

---

## Task 3: Rewrite `RobotCameraView` (hero camera + HUD)

**Files:**
- Rewrite: `src/components/camera/RobotCameraView.tsx`

Self-contained: image or placeholder + CANLI/connection HUD badges. Same props
(`imageUrl`, `isLoading`, `isConnected`). No longer imports the old subcomponents.

- [ ] **Step 1: Overwrite file**

```tsx
import React from "react";
import { ActivityIndicator, Image, Text, View } from "react-native";

interface Props {
  imageUrl?: string | null;
  isLoading?: boolean;
  isConnected?: boolean;
}

export default function RobotCameraView({
  imageUrl,
  isLoading,
  isConnected,
}: Props) {
  return (
    <View className="relative w-full overflow-hidden rounded-3xl border border-[#2563eb55] bg-black aspect-[3/4]">
      {imageUrl ? (
        <Image
          source={{ uri: `data:image/jpeg;base64,${imageUrl}` }}
          className="h-full w-full"
          resizeMode="cover"
        />
      ) : (
        <View className="h-full w-full items-center justify-center bg-[#070b14]">
          {isLoading ? (
            <ActivityIndicator color="#38bdf8" />
          ) : (
            <Text className="text-slate-500">Kamera bekleniyor…</Text>
          )}
        </View>
      )}

      {/* HUD üst */}
      <View className="absolute left-3 right-3 top-3 flex-row justify-between">
        <View className="flex-row items-center gap-1 rounded-full bg-black/55 px-3 py-1">
          <View
            className={`h-2 w-2 rounded-full ${
              isConnected ? "bg-emerald-400" : "bg-red-500"
            }`}
          />
          <Text className="text-[11px] font-semibold text-white">
            {isConnected ? "CANLI" : "ÇEVRİMDIŞI"}
          </Text>
        </View>
      </View>
    </View>
  );
}
```

- [ ] **Step 2: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/components/camera/RobotCameraView.tsx
git commit -m "feat(mobile): hero camera view with HUD (Hybrid)"
```

---

## Task 4: Restyle `ClaudeBubble` + `EmergencyStopButton`

**Files:**
- Rewrite: `src/components/copilot/ClaudeBubble.tsx`
- Rewrite: `src/components/copilot/EmergencyStopButton.tsx`

Same props (`{text,risk}` / `{active,onToggle}`); only visuals change. Risk colors
keep using existing `copilotFormat.riskColor`/`riskLabel` (unchanged).

- [ ] **Step 1: `ClaudeBubble.tsx`**

```tsx
import React from "react";
import { Text, View } from "react-native";
import { Risk, riskColor, riskLabel } from "../../utils/copilotFormat";

interface Props { text: string | null; risk: Risk }

export default function ClaudeBubble({ text, risk }: Props) {
  if (!text) return null;
  return (
    <View className="absolute left-3 right-3 top-12">
      <View className="flex-row items-start gap-2 rounded-2xl border border-white/10 bg-[#0b1220ee] p-3">
        <View className={`rounded-md px-2 py-1 ${riskColor(risk)}`}>
          <Text className="text-[10px] font-bold text-white">
            {riskLabel(risk)}
          </Text>
        </View>
        <Text className="flex-1 text-xs text-sky-100" numberOfLines={3}>
          🧠 {text}
        </Text>
      </View>
    </View>
  );
}
```

- [ ] **Step 2: `EmergencyStopButton.tsx`**

```tsx
import React from "react";
import { Pressable, Text } from "react-native";
import * as Haptics from "expo-haptics";

interface Props {
  active: boolean;
  onToggle: () => void | Promise<void>;
}

export default function EmergencyStopButton({ active, onToggle }: Props) {
  return (
    <Pressable
      onPress={() => {
        try {
          void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        } catch {
          /* simülatörde haptics olmayabilir */
        }
        void onToggle();
      }}
      className={`absolute bottom-4 right-4 h-20 w-20 items-center justify-center rounded-full border-2 ${
        active
          ? "border-white bg-red-700"
          : "border-white/30 bg-red-600"
      }`}
      style={{
        shadowColor: "#ef4444",
        shadowOpacity: 0.5,
        shadowRadius: 12,
        shadowOffset: { width: 0, height: 6 },
        elevation: 8,
      }}
    >
      <Text className="text-center text-xs font-extrabold text-white">
        {active ? "DEVAM" : "ACİL\nDUR"}
      </Text>
    </Pressable>
  );
}
```

- [ ] **Step 3: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/components/copilot/ClaudeBubble.tsx src/components/copilot/EmergencyStopButton.tsx
git commit -m "feat(mobile): Hybrid restyle ClaudeBubble + EmergencyStopButton"
```

---

## Task 5: Restyle `CommandBar` + rebuild `CopilotScreen`

**Files:**
- Rewrite: `src/components/copilot/CommandBar.tsx`
- Rewrite: `src/screens/CopilotScreen.tsx`

Same hooks/props (`useCopilot`, `isValidCommand`); visuals only.

- [ ] **Step 1: `CommandBar.tsx`**

```tsx
import React, { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { isValidCommand } from "../../utils/copilotFormat";

interface Props {
  sending: boolean;
  onSend: (text: string) => Promise<boolean>;
}

export default function CommandBar({ sending, onSend }: Props) {
  const [text, setText] = useState("");
  const valid = isValidCommand(text);

  const submit = async () => {
    if (!valid || sending) return;
    const ok = await onSend(text.trim());
    if (ok) setText("");
  };

  return (
    <View className="flex-row items-center gap-2 border-t border-[#1e293b] bg-[#0b1220] px-3 py-3">
      <TextInput
        value={text}
        onChangeText={setText}
        placeholder="Komut: sola git, yavaşla, dur…"
        placeholderTextColor="#64748b"
        className="flex-1 rounded-xl border border-[#1e293b] bg-[#111c30] px-3 py-2.5 text-sm text-white"
        editable={!sending}
        onSubmitEditing={submit}
        returnKeyType="send"
      />
      <Pressable
        onPress={submit}
        disabled={!valid || sending}
        className={`rounded-xl px-4 py-2.5 ${
          valid && !sending ? "bg-sky-500" : "bg-slate-700"
        }`}
      >
        <Text className="text-sm font-bold text-white">
          {sending ? "…" : "Gönder"}
        </Text>
      </Pressable>
    </View>
  );
}
```

- [ ] **Step 2: `CopilotScreen.tsx`**

```tsx
import React from "react";
import { FlatList, Text, View } from "react-native";

import CommandBar from "../components/copilot/CommandBar";
import Card from "../components/ui/Card";
import Pill from "../components/ui/Pill";
import ScreenContainer from "../components/ui/ScreenContainer";
import SectionTitle from "../components/ui/SectionTitle";
import { useCopilot } from "../hooks/useCopilot";
import { Risk, riskLabel } from "../utils/copilotFormat";

const toneFor: Record<Risk, "emerald" | "amber" | "red" | "slate"> = {
  low: "emerald",
  warn: "amber",
  critical: "red",
  unknown: "slate",
};

export default function CopilotScreen() {
  const { events, sending, send } = useCopilot();
  const reversed = [...events].reverse();

  return (
    <ScreenContainer>
      <SectionTitle>Kopilot</SectionTitle>
      <FlatList
        className="flex-1"
        data={reversed}
        keyExtractor={(e) => String(e.ts)}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 12 }}
        ListEmptyComponent={
          <Text className="py-10 text-center text-slate-500">
            Henüz olay yok. Araç sürerken anlatım burada akar.
          </Text>
        }
        renderItem={({ item }) => (
          <View className="my-1.5">
            <Card>
              <View className="mb-1 flex-row items-center gap-2">
                <Pill
                  label={riskLabel(item.risk)}
                  tone={toneFor[item.risk]}
                />
                {!!item.suggestion && (
                  <Text className="text-[11px] text-slate-400">
                    → {item.suggestion}
                  </Text>
                )}
              </View>
              <Text className="text-sm text-slate-100">{item.narration}</Text>
            </Card>
          </View>
        )}
      />
      <CommandBar sending={sending} onSend={send} />
    </ScreenContainer>
  );
}
```

- [ ] **Step 3: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/components/copilot/CommandBar.tsx src/screens/CopilotScreen.tsx
git commit -m "feat(mobile): Hybrid CommandBar + CopilotScreen rebuild"
```

---

## Task 6: Rebuild dashboard parts + `HomeScreen` (Canlı, camera hero)

**Files:**
- Rewrite: `src/components/dashboard/DashboardHeader.tsx`
- Rewrite: `src/components/dashboard/TelemetryGrid.tsx`
- Rewrite: `src/components/dashboard/QuickActions.tsx`
- Rewrite: `src/screens/HomeScreen.tsx`

Props unchanged: `DashboardHeader()`, `TelemetryGrid({stats})`,
`QuickActions({onRefresh,onCapture,onReset})`. `stats` is `RobotTelemetry`.

- [ ] **Step 1: `DashboardHeader.tsx`**

```tsx
import React from "react";
import { Text, View } from "react-native";

export default function DashboardHeader() {
  return (
    <View className="px-4 pb-2 pt-3">
      <Text className="text-2xl font-extrabold text-white">Robot Kontrol</Text>
      <Text className="text-xs text-slate-400">AirSim canlı izleme</Text>
    </View>
  );
}
```

- [ ] **Step 2: `TelemetryGrid.tsx`**

```tsx
import React from "react";
import { View } from "react-native";

import StatPill from "../ui/StatPill";
import { RobotTelemetry } from "../../types/robot";

interface Props { stats: RobotTelemetry }

export default function TelemetryGrid({ stats }: Props) {
  return (
    <View className="mt-3 gap-2 px-4">
      <View className="flex-row gap-2">
        <StatPill label="Hız (m/s)" value={stats.speed.toFixed(1)} accent="sky" />
        <StatPill
          label="Ön mesafe (m)"
          value={stats.distance.toFixed(1)}
          accent="amber"
        />
      </View>
      <View className="flex-row gap-2">
        <StatPill
          label="Batarya"
          value={`${Math.round(stats.battery)}%`}
          accent="emerald"
        />
        <StatPill
          label="Sinyal (dBm)"
          value={String(Math.round(stats.signalQuality))}
          accent="slate"
        />
      </View>
    </View>
  );
}
```

- [ ] **Step 3: `QuickActions.tsx`**

```tsx
import React from "react";
import { Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface Props {
  onRefresh: () => void;
  onCapture: () => void;
  onReset: () => void;
}

function Action({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-1 items-center gap-1 rounded-2xl border border-[#1e293b] bg-[#111c30] py-3"
    >
      <Ionicons name={icon} size={22} color="#38bdf8" />
      <Text className="text-[11px] text-slate-300">{label}</Text>
    </Pressable>
  );
}

export default function QuickActions({
  onRefresh,
  onCapture,
  onReset,
}: Props) {
  return (
    <View className="mt-3 flex-row gap-2 px-4">
      <Action icon="refresh" label="Yenile" onPress={onRefresh} />
      <Action icon="camera" label="Kare al" onPress={onCapture} />
      <Action icon="reload" label="Sıfırla" onPress={onReset} />
    </View>
  );
}
```

- [ ] **Step 4: `HomeScreen.tsx`**

```tsx
import React from "react";
import { View } from "react-native";

import RobotCameraView from "../components/camera/RobotCameraView";
import ClaudeBubble from "../components/copilot/ClaudeBubble";
import EmergencyStopButton from "../components/copilot/EmergencyStopButton";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import QuickActions from "../components/dashboard/QuickActions";
import TelemetryGrid from "../components/dashboard/TelemetryGrid";
import ScreenContainer from "../components/ui/ScreenContainer";
import { useDashboard } from "../hooks/useDashboard";
import { useCopilot } from "../hooks/useCopilot";

export default function HomeScreen() {
  const {
    refreshing,
    isConnected,
    cameraImage,
    stats,
    onRefresh,
    onCapture,
    onReset,
  } = useDashboard();
  const { latest, latestRisk, estop, toggleEstop } = useCopilot();

  return (
    <ScreenContainer scroll>
      <DashboardHeader />

      <View className="px-4">
        <View className="relative">
          <RobotCameraView
            imageUrl={cameraImage}
            isConnected={isConnected}
            isLoading={refreshing}
          />
          <ClaudeBubble text={latest} risk={latestRisk} />
          <EmergencyStopButton active={estop} onToggle={toggleEstop} />
        </View>
      </View>

      <TelemetryGrid stats={stats} />
      <QuickActions
        onRefresh={onRefresh}
        onCapture={onCapture}
        onReset={onReset}
      />
    </ScreenContainer>
  );
}
```

- [ ] **Step 5: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/components/dashboard/ src/screens/HomeScreen.tsx
git commit -m "feat(mobile): Canlı rebuild — hero camera + Hybrid dashboard"
```

---

## Task 7: Rebuild `SettingsScreen` (info cards)

**Files:**
- Rewrite: `src/screens/SettingsScreen.tsx`

Read-only info: API URL, connection, poll rates, app version. Uses existing
`useDashboard` (for `isConnected`), env, polling constants, `expo-constants`.

- [ ] **Step 1: Overwrite file**

```tsx
import React from "react";
import { Text, View } from "react-native";
import Constants from "expo-constants";

import Card from "../components/ui/Card";
import Pill from "../components/ui/Pill";
import ScreenContainer from "../components/ui/ScreenContainer";
import SectionTitle from "../components/ui/SectionTitle";
import { COPILOT_POLL_MS, TELEMETRY_POLL_MS } from "../constants/polling";
import { useDashboard } from "../hooks/useDashboard";

const API = process.env.EXPO_PUBLIC_API_BASE_URL || "(ayarsız)";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row items-center justify-between py-1.5">
      <Text className="text-sm text-slate-400">{label}</Text>
      <Text className="text-sm font-semibold text-white">{value}</Text>
    </View>
  );
}

export default function SettingsScreen() {
  const { isConnected } = useDashboard();
  const version =
    Constants.expoConfig?.version ?? Constants.nativeAppVersion ?? "—";

  return (
    <ScreenContainer scroll>
      <SectionTitle>Ayarlar</SectionTitle>
      <View className="gap-3 px-4">
        <Card>
          <Text className="mb-2 text-xs uppercase tracking-wide text-slate-500">
            Bağlantı
          </Text>
          <View className="mb-2 flex-row items-center justify-between">
            <Text className="text-sm text-slate-400">Durum</Text>
            <Pill
              label={isConnected ? "ONLINE" : "OFFLINE"}
              tone={isConnected ? "emerald" : "red"}
            />
          </View>
          <Row label="API" value={API} />
        </Card>

        <Card>
          <Text className="mb-2 text-xs uppercase tracking-wide text-slate-500">
            Yenileme
          </Text>
          <Row label="Telemetri" value={`${TELEMETRY_POLL_MS} ms`} />
          <Row label="Kopilot akışı" value={`${COPILOT_POLL_MS} ms`} />
        </Card>

        <Card>
          <Text className="mb-2 text-xs uppercase tracking-wide text-slate-500">
            Uygulama
          </Text>
          <Row label="Sürüm" value={String(version)} />
        </Card>
      </View>
    </ScreenContainer>
  );
}
```

- [ ] **Step 2: Type-check + commit**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

```bash
git add src/screens/SettingsScreen.tsx
git commit -m "feat(mobile): Ayarlar info cards (Hybrid, read-only)"
```

---

## Task 8: Regression + manual e2e (user-run)

**Files:**
- Create: `UI_POLISH_DEV.md`

- [ ] **Step 1: Full regression**

Run:
```bash
npx tsc --noEmit && npx jest 2>&1 | tail -3
```
Expected: tsc no errors; jest `Tests: 15 passed` (13 önceki + 2 tokens).

- [ ] **Step 2: Write `UI_POLISH_DEV.md`**

```markdown
# Mobil UI polish — manuel e2e

Önkoşul: backend + sim çalışıyor (Faz 1/2), telefon Expo Go, aynı Wi-Fi.

## Çalıştır
`cd robot-control-app` -> `npx expo start` -> Expo Go bağlan.

## Beklenen (C/Hybrid, fonksiyon Faz 3'teki gibi)
1. **Canlı**: kamera BÜYÜK/hero, koyu Hybrid zemin, üstte CANLI rozet,
   Claude balon şık, sağ-alt büyük yuvarlak ACİL DUR (gölgeli). Altta
   StatPill telemetri + ikon aksiyonlar. estop bas->araç durur, DEVAM->sürer.
3. **Kopilot**: koyu zemin, olay kartları (renk rozet + öneri + anlatım),
   altta modern komut çubuğu. Komut Gönder çalışır.
3. **Ayarlar**: bilgi kartları — bağlantı (ONLINE/OFFLINE rozet), API URL,
   poll süreleri, sürüm. Salt-okunur.
4. Backend kapalı: app donmaz, balon/akış boş, telemetri/kamera eskisi gibi.

## Not
Eski camera alt-bileşenleri (CameraFeed/HUDOverlay/StatusBadge/LiveBadge)
artık kullanılmıyor (RobotCameraView self-contained). Dosyalar zararsız,
import edilmiyor; istenirse ayrı temizlik commitinde silinir.
```

- [ ] **Step 3: Commit**

```bash
git add UI_POLISH_DEV.md
git commit -m "docs(mobile): UI polish manual e2e checklist"
```

- [ ] **Step 4: Hand off to user**

Tell the user to run `npx expo start` and confirm on the phone: (1) Canlı camera
is big/hero in Hybrid style, (2) ACİL DUR still stops/resumes the car, (3) Kopilot
+ Ayarlar look polished, (4) backend-down doesn't freeze. Do not mark done until
the user confirms.

---

## Self-Review

**Spec coverage:**
- C/Hybrid + tokens + primitives → Tasks 1,2. ✔
- Camera hero → Task 3. ✔
- 3 screens rebuilt → Canlı (Task 6), Kopilot (Task 5), Ayarlar (Task 7). ✔
- Logic untouched: `useDashboard`/`useCopilot`/`copilotApi`/`copilotFormat` not modified; screens reuse same props/hooks. ✔
- Tests: pure jest preserved + tokens test (Task 1); visual = manual (Task 8). ✔
- Out of scope respected (no new fn/state, no Harita/video/MCP). ✔

**Placeholder scan:** none — every component is full code; commands have expected output.

**Type consistency:** primitive props (`ScreenContainer{children,scroll?}`, `Card{children,className?}`, `StatPill{label,value,accent?}`, `SectionTitle{children}`, `Pill{label,tone?}`) defined Task 2, used identically Tasks 5–7. `Accent` union from `tokens.ts` used by StatPill/Pill via `accentText`/`accentBg`. Screen props (`TelemetryGrid{stats:RobotTelemetry}`, `QuickActions{onRefresh,onCapture,onReset}`, `RobotCameraView{imageUrl,isLoading,isConnected}`, `ClaudeBubble{text,risk}`, `EmergencyStopButton{active,onToggle}`, `CommandBar{sending,onSend}`) match call sites in HomeScreen/CopilotScreen and the unchanged hooks. `riskLabel`/`riskColor` reused from `copilotFormat` (unchanged). ✔
```
