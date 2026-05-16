# Faz 3 — Mobil Kopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the mobile app to the Faz 1/2 copilot backend: a live Claude narration bubble + persistent emergency-stop on the camera screen, and a new "Kopilot" tab with the narration feed and a natural-language command box — all backed by the already-live `/copilot/stream`, `/command`, `/estop` endpoints.

**Architecture:** Pure, RN-free logic (`copilotFormat.ts` event merge/risk mapping + `copilotApi.ts` fetch wrappers with injectable `fetch`) is unit-tested with jest+ts-jest. A thin `useCopilot` hook composes them. UI (bubble, ACİL DUR FAB, command bar, Kopilot screen, tab wiring) follows existing patterns (Expo Router re-export, NativeWind `className`, `SafeAreaView`) and is verified by manual e2e (user-run). The existing telemetry/camera path and `useDashboard` are untouched.

**Tech Stack:** Expo SDK 54, React 19, React Native 0.81, expo-router, NativeWind, expo-haptics; jest + ts-jest (node env, pure TS only) for automated tests.

---

## Repo / commit note

`robot-control-app` is its own git repo. Faz 3 work is on branch
`faz3-mobile-copilot`, committed locally there. No push (repo/remote decision
deferred per user; consistent with Faz 1/2).

App dir (CWD for all commands):
`c:\Users\Berdan\OneDrive\Masaüstü\robot-project\robot-control-app`
Commands use `npx` (project-local binaries).

## Scope (explicit)

In scope: Canlı sekmesinde Claude balonu + kalıcı ACİL DUR; yeni Kopilot sekmesi
(anlatım akışı + komut kutusu). Backend Faz 1 endpoint'leri zaten canlı.

**Deferred (Faz 3.5, ayrı plan):** "Harita" (2D SLAM) sekmesi — `/map` endpoint'i
backend'de yok ve sim'in haritayı POST etmesi gerek (backend+sim işi). Bu planda
sekme **eklenmez**; mevcut Canlı + yeni Kopilot + Ayarlar yeterli ve test edilebilir.

## Backend endpoints consumed (Faz 1, canlı doğrulandı)

- `GET {base}/copilot/stream?since=<ts>` → `{"events":[{narration,risk,suggestion,directive,ts}]}`
- `POST {base}/command` body `{"text": str}` → `{"status":"ok","directive":{...}}` veya 400
- `GET {base}/estop` → `{"estop": bool}` ; `POST {base}/estop` body `{}`/`{"clear":true}` → `{"estop":bool,"status":"ok"}`

`base` = `EXPO_PUBLIC_API_BASE_URL` (mevcut `api.ts` ile aynı kaynak/temizleme).

---

## File Structure

| File | Responsibility |
|---|---|
| `jest.config.js` (create) | ts-jest, node env, sadece `src/**/*.test.ts`. |
| `src/utils/copilotFormat.ts` (create) | Saf: event merge/dedupe, son anlatım, risk→renk/etiket, komut doğrulama. RN-free. |
| `src/utils/copilotFormat.test.ts` (create) | copilotFormat birim testleri. |
| `src/services/copilotApi.ts` (create) | fetch sarmalayıcılar: stream/command/estop. `fetch` enjekte edilebilir. RN-free. |
| `src/services/copilotApi.test.ts` (create) | copilotApi birim testleri (sahte fetch). |
| `src/constants/polling.ts` (modify) | `COPILOT_POLL_MS` ekle. |
| `src/hooks/useCopilot.ts` (create) | İnce hook: stream poll + estop/command aksiyon. copilotApi/Format'a delege. |
| `src/components/copilot/ClaudeBubble.tsx` (create) | Kamera üstü anlatım balonu (risk renkli). |
| `src/components/copilot/EmergencyStopButton.tsx` (create) | Kalıcı kırmızı ACİL DUR / temizle FAB. |
| `src/components/copilot/CommandBar.tsx` (create) | Metin girişi + gönder. |
| `src/screens/CopilotScreen.tsx` (create) | Kopilot sekmesi: olay akışı + komut kutusu. |
| `app/(tabs)/copilot.tsx` (create) | Expo Router re-export. |
| `app/(tabs)/_layout.tsx` (modify) | "İzleme"→"Canlı", "Kopilot" sekmesi ekle. |
| `src/screens/HomeScreen.tsx` (modify) | Kamera View'ı saran overlay: ClaudeBubble + EmergencyStopButton. |
| `MOBILE_COPILOT_DEV.md` (create) | Manuel e2e çek-listesi. |

**Shared types** (in `copilotFormat.ts`, imported elsewhere):
```ts
export type Risk = "low" | "warn" | "critical" | "unknown";
export interface CopilotEvent {
  narration: string; risk: Risk; suggestion: string;
  directive: unknown | null; ts: number;
}
```

---

## Task 0: Branch + jest scaffold

**Files:**
- Create: `jest.config.js`
- Modify: `package.json`

- [ ] **Step 1: Create feature branch**

Run:
```bash
cd "c:/Users/Berdan/OneDrive/Masaüstü/robot-project/robot-control-app"
git checkout -b faz3-mobile-copilot
git branch --show-current
```
Expected: `faz3-mobile-copilot`.

- [ ] **Step 2: Install jest + ts-jest (dev)**

Run:
```bash
npm install -D jest@29 ts-jest@29 @types/jest@29 typescript@~5.9.2
```
Expected: installs without error.

- [ ] **Step 3: Create `jest.config.js`**

```js
/** Sadece saf TS modülleri (RN/JSX yok). UI manuel e2e ile doğrulanır. */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: ["<rootDir>/src/**/*.test.ts"],
};
```

- [ ] **Step 4: Add test script to `package.json`**

In the `"scripts"` block, add this line after `"lint": "expo lint"` (add a
trailing comma to the `lint` line):
```json
    "lint": "expo lint",
    "test": "jest"
```

- [ ] **Step 5: Verify jest runs with no tests**

Run:
```bash
npx jest --passWithNoTests
```
Expected: `No tests found` but exit 0 (passWithNoTests).

- [ ] **Step 6: Commit**

```bash
git add jest.config.js package.json package-lock.json
git commit -m "chore(mobile): jest+ts-jest scaffold for Faz 3 (pure TS)"
```

---

## Task 1: `copilotFormat.ts` — pure helpers

**Files:**
- Create: `src/utils/copilotFormat.ts`
- Test: `src/utils/copilotFormat.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// src/utils/copilotFormat.test.ts
import {
  mergeEvents, latestNarration, riskColor, riskLabel, isValidCommand,
  CopilotEvent,
} from "./copilotFormat";

const ev = (ts: number, narration = "x", risk: any = "low"): CopilotEvent => ({
  narration, risk, suggestion: "", directive: null, ts,
});

test("mergeEvents dedupes by ts and sorts ascending", () => {
  const out = mergeEvents([ev(2), ev(1)], [ev(2), ev(3)]);
  expect(out.map((e) => e.ts)).toEqual([1, 2, 3]);
});

test("mergeEvents caps to 100 newest", () => {
  const many = Array.from({ length: 130 }, (_, i) => ev(i));
  const out = mergeEvents([], many);
  expect(out.length).toBe(100);
  expect(out[0].ts).toBe(30);
  expect(out[99].ts).toBe(129);
});

test("latestNarration returns last by ts or null", () => {
  expect(latestNarration([])).toBeNull();
  expect(latestNarration([ev(1, "a"), ev(5, "b"), ev(3, "c")])).toBe("b");
});

test("riskColor maps each risk", () => {
  expect(riskColor("low")).toContain("emerald");
  expect(riskColor("warn")).toContain("amber");
  expect(riskColor("critical")).toContain("red");
  expect(riskColor("unknown")).toContain("slate");
});

test("riskLabel is human Turkish", () => {
  expect(riskLabel("critical")).toBe("KRİTİK");
  expect(riskLabel("warn")).toBe("DİKKAT");
  expect(riskLabel("low")).toBe("NORMAL");
  expect(riskLabel("unknown")).toBe("?");
});

test("isValidCommand trims and rejects empty / too long", () => {
  expect(isValidCommand("  sola git ")).toBe(true);
  expect(isValidCommand("   ")).toBe(false);
  expect(isValidCommand("")).toBe(false);
  expect(isValidCommand("a".repeat(401))).toBe(false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npx jest src/utils/copilotFormat.test.ts
```
Expected: FAIL — cannot find module `./copilotFormat`.

- [ ] **Step 3: Write minimal implementation**

```ts
// src/utils/copilotFormat.ts
export type Risk = "low" | "warn" | "critical" | "unknown";

export interface CopilotEvent {
  narration: string;
  risk: Risk;
  suggestion: string;
  directive: unknown | null;
  ts: number;
}

const MAX_EVENTS = 100;

export function mergeEvents(
  prev: CopilotEvent[],
  incoming: CopilotEvent[],
): CopilotEvent[] {
  const byTs = new Map<number, CopilotEvent>();
  for (const e of prev) byTs.set(e.ts, e);
  for (const e of incoming) byTs.set(e.ts, e);
  const sorted = [...byTs.values()].sort((a, b) => a.ts - b.ts);
  return sorted.slice(-MAX_EVENTS);
}

export function latestNarration(events: CopilotEvent[]): string | null {
  if (events.length === 0) return null;
  let best = events[0];
  for (const e of events) if (e.ts > best.ts) best = e;
  return best.narration;
}

export function riskColor(risk: Risk): string {
  switch (risk) {
    case "low": return "bg-emerald-600";
    case "warn": return "bg-amber-500";
    case "critical": return "bg-red-600";
    default: return "bg-slate-600";
  }
}

export function riskLabel(risk: Risk): string {
  switch (risk) {
    case "low": return "NORMAL";
    case "warn": return "DİKKAT";
    case "critical": return "KRİTİK";
    default: return "?";
  }
}

export function isValidCommand(text: string): boolean {
  const t = (text ?? "").trim();
  return t.length > 0 && t.length <= 400;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npx jest src/utils/copilotFormat.test.ts
```
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/utils/copilotFormat.ts src/utils/copilotFormat.test.ts
git commit -m "feat(mobile): copilotFormat pure helpers (merge/risk/validate)"
```

---

## Task 2: `copilotApi.ts` — fetch wrappers

**Files:**
- Create: `src/services/copilotApi.ts`
- Test: `src/services/copilotApi.test.ts`

`fetch` is passed in (default `globalThis.fetch`) so tests inject a fake.
Errors/non-JSON degrade to safe values (never throw to the UI).

- [ ] **Step 1: Write the failing test**

```ts
// src/services/copilotApi.test.ts
import { fetchStream, postCommand, getEstop, setEstop } from "./copilotApi";

function fakeFetch(status: number, body: any, ct = "application/json") {
  return async () =>
    ({
      status,
      ok: status >= 200 && status < 300,
      headers: { get: () => ct },
      json: async () => body,
      text: async () => JSON.stringify(body),
    }) as any;
}

const BASE = "http://x:5000";

test("fetchStream returns events array", async () => {
  const ev = [{ narration: "a", risk: "low", suggestion: "", directive: null, ts: 1 }];
  const out = await fetchStream(BASE, 0, fakeFetch(200, { events: ev }));
  expect(out).toHaveLength(1);
  expect(out[0].narration).toBe("a");
});

test("fetchStream on error returns empty array", async () => {
  const out = await fetchStream(BASE, 0, async () => { throw new Error("net"); });
  expect(out).toEqual([]);
});

test("fetchStream on non-json returns empty array", async () => {
  const out = await fetchStream(BASE, 0, fakeFetch(200, "<html>", "text/html"));
  expect(out).toEqual([]);
});

test("postCommand ok true on 200", async () => {
  const r = await postCommand(BASE, "sola git",
    fakeFetch(200, { status: "ok", directive: { mode: "explore" } }));
  expect(r.ok).toBe(true);
});

test("postCommand ok false on 400", async () => {
  const r = await postCommand(BASE, "", fakeFetch(400, { error: "text gerekli" }));
  expect(r.ok).toBe(false);
});

test("setEstop returns boolean from response", async () => {
  const on = await setEstop(BASE, true, fakeFetch(200, { estop: true, status: "ok" }));
  expect(on).toBe(true);
  const off = await setEstop(BASE, false, fakeFetch(200, { estop: false, status: "ok" }));
  expect(off).toBe(false);
});

test("getEstop false on network error", async () => {
  const on = await getEstop(BASE, async () => { throw new Error("down"); });
  expect(on).toBe(false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npx jest src/services/copilotApi.test.ts
```
Expected: FAIL — cannot find module `./copilotApi`.

- [ ] **Step 3: Write minimal implementation**

```ts
// src/services/copilotApi.ts
import { CopilotEvent } from "../utils/copilotFormat";

type FetchLike = (url: string, init?: any) => Promise<any>;

function headers(base: string): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (base.includes("ngrok")) h["ngrok-skip-browser-warning"] = "true";
  return h;
}

async function asJson(res: any): Promise<any | null> {
  const ct = res.headers?.get?.("content-type") ?? "";
  if (!ct.includes("application/json")) return null;
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchStream(
  base: string,
  since: number,
  fetchImpl: FetchLike = globalThis.fetch,
): Promise<CopilotEvent[]> {
  try {
    const res = await fetchImpl(`${base}/copilot/stream?since=${since}`, {
      headers: headers(base),
    });
    const data = await asJson(res);
    const events = data?.events;
    return Array.isArray(events) ? (events as CopilotEvent[]) : [];
  } catch {
    return [];
  }
}

export async function postCommand(
  base: string,
  text: string,
  fetchImpl: FetchLike = globalThis.fetch,
): Promise<{ ok: boolean }> {
  try {
    const res = await fetchImpl(`${base}/command`, {
      method: "POST",
      headers: headers(base),
      body: JSON.stringify({ text }),
    });
    return { ok: res.ok === true };
  } catch {
    return { ok: false };
  }
}

export async function setEstop(
  base: string,
  on: boolean,
  fetchImpl: FetchLike = globalThis.fetch,
): Promise<boolean> {
  try {
    const res = await fetchImpl(`${base}/estop`, {
      method: "POST",
      headers: headers(base),
      body: JSON.stringify(on ? {} : { clear: true }),
    });
    const data = await asJson(res);
    return data?.estop === true;
  } catch {
    return on; // ağ hatasında istenen niyeti koru
  }
}

export async function getEstop(
  base: string,
  fetchImpl: FetchLike = globalThis.fetch,
): Promise<boolean> {
  try {
    const res = await fetchImpl(`${base}/estop`, { headers: headers(base) });
    const data = await asJson(res);
    return data?.estop === true;
  } catch {
    return false;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npx jest src/services/copilotApi.test.ts
```
Expected: PASS (7 passed).

- [ ] **Step 5: Run full test suite**

Run:
```bash
npx jest
```
Expected: PASS (format 6 + api 7 = 13).

- [ ] **Step 6: Commit**

```bash
git add src/services/copilotApi.ts src/services/copilotApi.test.ts
git commit -m "feat(mobile): copilotApi fetch wrappers (stream/command/estop, safe degrade)"
```

---

## Task 3: `useCopilot` hook + poll constant

**Files:**
- Modify: `src/constants/polling.ts`
- Create: `src/hooks/useCopilot.ts`

No unit test (RN hook needs a renderer not configured; all logic lives in the
tested `copilotApi`/`copilotFormat`). Verified in Task 6 manual e2e.

- [ ] **Step 1: Add poll constant to `src/constants/polling.ts`**

Append:
```ts

/** Kopilot anlatım akışı (GET /copilot/stream) sıklığı (ms). */
export const COPILOT_POLL_MS = 1500;
```

- [ ] **Step 2: Create `src/hooks/useCopilot.ts`**

```ts
import { useCallback, useEffect, useRef, useState } from "react";

import { COPILOT_POLL_MS } from "../constants/polling";
import {
  fetchStream, postCommand, setEstop, getEstop,
} from "../services/copilotApi";
import {
  mergeEvents, latestNarration, CopilotEvent, Risk,
} from "../utils/copilotFormat";

const raw = process.env.EXPO_PUBLIC_API_BASE_URL;
const BASE = (raw && raw.replace(/\/$/, "")) || "";

export function useCopilot() {
  const [events, setEvents] = useState<CopilotEvent[]>([]);
  const [estop, setEstopState] = useState(false);
  const [sending, setSending] = useState(false);
  const sinceRef = useRef(0);
  const eventsRef = useRef<CopilotEvent[]>([]);
  eventsRef.current = events;

  const tick = useCallback(async () => {
    if (!BASE) return;
    const incoming = await fetchStream(BASE, sinceRef.current);
    if (incoming.length > 0) {
      const merged = mergeEvents(eventsRef.current, incoming);
      setEvents(merged);
      sinceRef.current = merged[merged.length - 1].ts;
    }
    setEstopState(await getEstop(BASE));
  }, []);

  useEffect(() => {
    void tick();
    const id = setInterval(tick, COPILOT_POLL_MS);
    return () => clearInterval(id);
  }, [tick]);

  const send = useCallback(async (text: string) => {
    if (!BASE) return false;
    setSending(true);
    try {
      const r = await postCommand(BASE, text);
      return r.ok;
    } finally {
      setSending(false);
    }
  }, []);

  const toggleEstop = useCallback(async () => {
    if (!BASE) return;
    const next = !estop;
    const result = await setEstop(BASE, next);
    setEstopState(result);
  }, [estop]);

  const latest = latestNarration(events);
  const latestRisk: Risk =
    events.length > 0 ? events[events.length - 1].risk : "unknown";

  return { events, latest, latestRisk, estop, sending, send, toggleEstop };
}
```

- [ ] **Step 3: Type-check passes**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/constants/polling.ts src/hooks/useCopilot.ts
git commit -m "feat(mobile): useCopilot hook (stream poll + command + estop)"
```

---

## Task 4: Copilot UI components

**Files:**
- Create: `src/components/copilot/ClaudeBubble.tsx`
- Create: `src/components/copilot/EmergencyStopButton.tsx`
- Create: `src/components/copilot/CommandBar.tsx`

No unit test (RN/JSX, manual e2e in Task 6). Full code below.

- [ ] **Step 1: Create `src/components/copilot/ClaudeBubble.tsx`**

```tsx
import React from "react";
import { Text, View } from "react-native";

import { Risk, riskColor, riskLabel } from "../../utils/copilotFormat";

interface Props {
  text: string | null;
  risk: Risk;
}

export default function ClaudeBubble({ text, risk }: Props) {
  if (!text) return null;
  return (
    <View className="absolute left-3 right-3 top-3">
      <View className="flex-row items-start gap-2 rounded-xl bg-black/70 p-2">
        <View className={`rounded px-2 py-1 ${riskColor(risk)}`}>
          <Text className="text-[10px] font-bold text-white">
            {riskLabel(risk)}
          </Text>
        </View>
        <Text
          className="flex-1 text-xs italic text-emerald-200"
          numberOfLines={3}
        >
          🧠 {text}
        </Text>
      </View>
    </View>
  );
}
```

- [ ] **Step 2: Create `src/components/copilot/EmergencyStopButton.tsx`**

```tsx
import React from "react";
import { Pressable, Text } from "react-native";
import * as Haptics from "expo-haptics";

interface Props {
  active: boolean;        // true = estop şu an AÇIK (araç durdurulmuş)
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
      className={`absolute bottom-3 right-3 h-16 w-16 items-center justify-center rounded-full border-2 ${
        active
          ? "border-white bg-red-700"
          : "border-red-500 bg-red-600/90"
      }`}
    >
      <Text className="text-center text-[11px] font-extrabold text-white">
        {active ? "DEVAM" : "ACİL\nDUR"}
      </Text>
    </Pressable>
  );
}
```

- [ ] **Step 3: Create `src/components/copilot/CommandBar.tsx`**

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
    <View className="flex-row items-center gap-2 border-t border-slate-800 bg-slate-900 p-3">
      <TextInput
        value={text}
        onChangeText={setText}
        placeholder="Komut: ör. sola git, yavaşla, dur…"
        placeholderTextColor="#64748b"
        className="flex-1 rounded-lg bg-slate-800 px-3 py-2 text-sm text-white"
        editable={!sending}
        onSubmitEditing={submit}
        returnKeyType="send"
      />
      <Pressable
        onPress={submit}
        disabled={!valid || sending}
        className={`rounded-lg px-4 py-2 ${
          valid && !sending ? "bg-blue-600" : "bg-slate-700"
        }`}
      >
        <Text className="text-sm font-semibold text-white">
          {sending ? "…" : "Gönder"}
        </Text>
      </Pressable>
    </View>
  );
}
```

- [ ] **Step 4: Type-check passes**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add src/components/copilot/
git commit -m "feat(mobile): copilot UI (ClaudeBubble, EmergencyStopButton, CommandBar)"
```

---

## Task 5: Kopilot screen + tab wiring + camera overlay

**Files:**
- Create: `src/screens/CopilotScreen.tsx`
- Create: `app/(tabs)/copilot.tsx`
- Modify: `app/(tabs)/_layout.tsx`
- Modify: `src/screens/HomeScreen.tsx`

No unit test (UI/navigation, manual e2e in Task 6).

- [ ] **Step 1: Create `src/screens/CopilotScreen.tsx`**

```tsx
import React from "react";
import { FlatList, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import CommandBar from "../components/copilot/CommandBar";
import { useCopilot } from "../hooks/useCopilot";
import { riskColor, riskLabel } from "../utils/copilotFormat";

export default function CopilotScreen() {
  const { events, sending, send } = useCopilot();
  const reversed = [...events].reverse(); // en yeni üstte

  return (
    <SafeAreaView className="flex-1 bg-slate-950" edges={["top"]}>
      <Text className="px-4 py-3 text-lg font-bold text-white">Kopilot</Text>
      <FlatList
        className="flex-1"
        data={reversed}
        keyExtractor={(e) => String(e.ts)}
        ListEmptyComponent={
          <Text className="px-4 py-8 text-center text-slate-500">
            Henüz olay yok. Araç sürerken anlatım burada akar.
          </Text>
        }
        renderItem={({ item }) => (
          <View className="mx-4 my-1 rounded-lg bg-slate-900 p-3">
            <View className="mb-1 flex-row items-center gap-2">
              <View className={`rounded px-2 py-0.5 ${riskColor(item.risk)}`}>
                <Text className="text-[10px] font-bold text-white">
                  {riskLabel(item.risk)}
                </Text>
              </View>
              {!!item.suggestion && (
                <Text className="text-[11px] text-slate-400">
                  → {item.suggestion}
                </Text>
              )}
            </View>
            <Text className="text-sm text-slate-100">{item.narration}</Text>
          </View>
        )}
      />
      <CommandBar sending={sending} onSend={send} />
    </SafeAreaView>
  );
}
```

- [ ] **Step 2: Create `app/(tabs)/copilot.tsx`**

```tsx
import CopilotScreen from "../../src/screens/CopilotScreen";

export default function TabCopilot() {
  return <CopilotScreen />;
}
```

- [ ] **Step 3: Add the Kopilot tab + rename İzleme→Canlı in `app/(tabs)/_layout.tsx`**

Replace:
```tsx
            <Tabs.Screen
                name="index"
                options={{
                    title: "İzleme",
                    tabBarIcon: ({ color, focused }) => (
                        <Ionicons
                            name={focused ? "videocam" : "videocam-outline"}
                            size={26}
                            color={color}
                        />
                    ),
                }}
            />
            <Tabs.Screen
                name="settings"
```
with:
```tsx
            <Tabs.Screen
                name="index"
                options={{
                    title: "Canlı",
                    tabBarIcon: ({ color, focused }) => (
                        <Ionicons
                            name={focused ? "videocam" : "videocam-outline"}
                            size={26}
                            color={color}
                        />
                    ),
                }}
            />
            <Tabs.Screen
                name="copilot"
                options={{
                    title: "Kopilot",
                    tabBarIcon: ({ color, focused }) => (
                        <Ionicons
                            name={focused ? "chatbubbles" : "chatbubbles-outline"}
                            size={26}
                            color={color}
                        />
                    ),
                }}
            />
            <Tabs.Screen
                name="settings"
```

- [ ] **Step 4: Add bubble + ACİL DUR overlay on the camera in `src/screens/HomeScreen.tsx`**

Replace:
```tsx
import RobotCameraView from "../components/camera/RobotCameraView";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import QuickActions from "../components/dashboard/QuickActions";
import TelemetryGrid from "../components/dashboard/TelemetryGrid";
```
with:
```tsx
import RobotCameraView from "../components/camera/RobotCameraView";
import ClaudeBubble from "../components/copilot/ClaudeBubble";
import EmergencyStopButton from "../components/copilot/EmergencyStopButton";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import QuickActions from "../components/dashboard/QuickActions";
import TelemetryGrid from "../components/dashboard/TelemetryGrid";
import { useCopilot } from "../hooks/useCopilot";
```

Then replace:
```tsx
    const {
        refreshing,
        isConnected,
        cameraImage,
        stats,
        onRefresh,
        onCapture,
        onReset,
    } = useDashboard();
```
with:
```tsx
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
```

Then replace:
```tsx
                {/* Camera View */}
                <View className="px-4 mb-4">
                    <RobotCameraView
                        imageUrl={cameraImage}
                        isConnected={isConnected}
                        isLoading={refreshing}
                    />
                </View>
```
with:
```tsx
                {/* Camera View + Copilot overlay */}
                <View className="px-4 mb-4">
                    <View className="relative">
                        <RobotCameraView
                            imageUrl={cameraImage}
                            isConnected={isConnected}
                            isLoading={refreshing}
                        />
                        <ClaudeBubble text={latest} risk={latestRisk} />
                        <EmergencyStopButton
                            active={estop}
                            onToggle={toggleEstop}
                        />
                    </View>
                </View>
```

- [ ] **Step 5: Type-check + full jest (regression)**

Run:
```bash
npx tsc --noEmit && npx jest
```
Expected: tsc no errors; jest 13 passed.

- [ ] **Step 6: Commit**

```bash
git add "app/(tabs)/_layout.tsx" "app/(tabs)/copilot.tsx" src/screens/CopilotScreen.tsx src/screens/HomeScreen.tsx
git commit -m "feat(mobile): Kopilot tab + camera bubble/ACİL DUR overlay"
```

---

## Task 6: Manual e2e (user-run)

**Files:**
- Create: `MOBILE_COPILOT_DEV.md`

- [ ] **Step 1: Write `MOBILE_COPILOT_DEV.md`**

```markdown
# Faz 3 mobil kopilot — manuel e2e

Önkoşul: backend çalışıyor (Faz 1), sim çalışıyor (Faz 2, AirSimNH açık),
telefon + PC aynı Wi-Fi, `.env.local` EXPO_PUBLIC_API_BASE_URL = PC LAN IP:5000.

## Çalıştır
- `cd robot-control-app` -> `npx expo start` -> Expo Go ile bağlan.

## Beklenen
1. **Canlı sekmesi**: kamera üstünde araç engele yaklaşınca/state değişince
   🧠 Claude balonu görünür (anahtar yoksa "Kopilot çevrimdışı", risk rozeti).
2. **ACİL DUR** (kamera sağ alt): bas -> araç AirSim'de durur, buton "DEVAM"e
   döner. Tekrar bas -> estop temizlenir.
3. **Kopilot sekmesi**: olay akışı listelenir (en yeni üstte). Komut kutusuna
   yaz + Gönder -> 200 (anahtar yoksa directive explore default; gerçek
   NL->directive için ANTHROPIC_API_KEY, Faz 1 COPILOT_DEV.md).
4. Backend kapalıyken app donmaz: balon boş, akış boş, ACİL DUR pasif kalır;
   telemetri/kamera (useDashboard) eskisi gibi çalışır.
```

- [ ] **Step 2: Commit**

```bash
git add MOBILE_COPILOT_DEV.md
git commit -m "docs(mobile): Faz 3 manual e2e checklist"
```

- [ ] **Step 3: Hand off to user**

Tell the user to run `MOBILE_COPILOT_DEV.md` (Expo Go on phone, backend+sim up)
and confirm: (1) bubble appears, (2) ACİL DUR stops/resumes the car, (3) Kopilot
tab shows feed + command send works, (4) backend-down → app doesn't freeze.
Do not mark Faz 3 done until the user confirms.

---

## Self-Review

**Spec coverage (spec §4 C/D/E, §5 mobil, §8 Faz 3):**
- C narration stream → `fetchStream` + `useCopilot` + CopilotScreen feed + ClaudeBubble (Tasks 2,3,4,5). ✔
- D command → `postCommand` + CommandBar (Tasks 2,4,5). ✔
- E estop from mobile → `setEstop`/`getEstop` + EmergencyStopButton (Tasks 2,3,4,5). ✔
- §5 mobil B+C: tabs (Canlı/Kopilot/Ayarlar) + Canlı overlay (bubble + persistent ACİL DUR) → Task 5. ✔
- §8 Faz 3 scope. ✔ Existing telemetry/`useDashboard` untouched (HomeScreen only adds overlay siblings).

**Deferred & flagged:** "Harita" (2D SLAM) tab — needs `/map` (backend+sim, not built). Out of this plan; separate Faz 3.5. Real NL→directive needs ANTHROPIC_API_KEY (Faz 1 doc). MCP = Faz 4.

**Placeholder scan:** none — every code step has full content; commands have expected output.

**Type consistency:** `CopilotEvent`/`Risk` defined in `copilotFormat.ts`, imported by `copilotApi.ts`, `useCopilot.ts`, components. `fetchStream(base,since,fetch)`, `postCommand(base,text,fetch)→{ok}`, `setEstop(base,on,fetch)→boolean`, `getEstop(base,fetch)→boolean`, `useCopilot()→{events,latest,latestRisk,estop,sending,send,toggleEstop}` — used identically across Tasks 3-5. `ClaudeBubble({text,risk})`, `EmergencyStopButton({active,onToggle})`, `CommandBar({sending,onSend})` props match call sites. ✔
