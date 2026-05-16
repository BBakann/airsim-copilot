"""Tek Anthropic temas noktası.

Copilot.parse_command: doğal dil -> directive JSON (güvenli default'a düşer).
Copilot.analyze_event: kamera karesi+telemetri -> anlatım/risk/directive,
3sn debounce, anahtar yok/hata -> degrade (sürüşü asla bloklamaz).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

MODEL = "claude-haiku-4-5"

_SAFE_DIRECTIVE = {
    "mode": "explore", "bias": 0.0, "speed_cap": 1.0,
    "target": None, "stop_on": None, "ttl": 30.0,
}

_COMMAND_SYSTEM = (
    "Sen otonom bir aracın misyon yorumlayıcısısın. Kullanıcının doğal dil "
    "komutunu SADECE şu JSON şemasına çevir, başka hiçbir şey yazma:\n"
    '{"mode":"explore|goto|stop","bias":-1..1,"speed_cap":0..1,'
    '"target":[x,y]|null,"stop_on":string|null}\n'
    "bias: negatif=sol, pozitif=sağ. Emin değilsen explore + bias 0 + "
    "speed_cap 1 döndür. Yalnızca JSON."
)

_EVENT_SYSTEM = (
    "Sen otonom bir aracın yardımcı pilotusun. Verilen ön kamera karesi ve "
    "telemetriye bakıp SADECE şu JSON'u döndür:\n"
    '{"narration":"kısa Türkçe sahne+durum","risk":"low|warn|critical",'
    '"suggestion":"kısa öneri","directive":null veya '
    '{"mode":"explore|goto|stop","bias":-1..1,"speed_cap":0..1,'
    '"target":[x,y]|null,"stop_on":string|null}}\n'
    "Sadece JSON, başka metin yok."
)


def _clamp(v: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return lo


def _safe() -> dict[str, Any]:
    return dict(_SAFE_DIRECTIVE)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _coerce_directive(obj: Optional[dict]) -> dict[str, Any]:
    if not obj:
        return _safe()
    mode = obj.get("mode")
    if mode not in ("explore", "goto", "stop"):
        return _safe()
    target = obj.get("target")
    if not (isinstance(target, list) and len(target) == 2):
        target = None
    stop_on = obj.get("stop_on")
    if not isinstance(stop_on, str):
        stop_on = None
    return {
        "mode": mode,
        "bias": _clamp(obj.get("bias", 0.0), -1.0, 1.0),
        "speed_cap": _clamp(obj.get("speed_cap", 1.0), 0.0, 1.0),
        "target": target,
        "stop_on": stop_on,
        "ttl": 30.0,
    }


class Copilot:
    """Single Anthropic touch point. Client injectable for tests."""

    def __init__(self, client: Any = None, debounce_s: float = 3.0) -> None:
        self._client = client
        self._debounce_s = debounce_s
        self._last_event_ts = 0.0
        self._last_event: Optional[dict[str, Any]] = None

    def analyze_event(self, *, image_b64: str, telemetry: dict[str, Any],
                      state: str, prev_state: str) -> dict[str, Any]:
        now = time.time()
        if (self._last_event is not None
                and now - self._last_event_ts < self._debounce_s):
            return self._last_event

        if self._client is None:
            out = {"narration": "Kopilot çevrimdışı (anahtar yok)",
                   "risk": "unknown", "suggestion": "", "directive": None,
                   "ts": now}
            self._last_event, self._last_event_ts = out, now
            return out

        user_text = (f"Durum: {prev_state} -> {state}. "
                     f"Telemetri: {json.dumps(telemetry, ensure_ascii=False)}")
        try:
            resp = self._client.messages.create(
                model=MODEL,
                max_tokens=400,
                system=[{"type": "text", "text": _EVENT_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg",
                        "data": image_b64}},
                    {"type": "text", "text": user_text},
                ]}],
            )
            obj = _extract_json(resp.content[0].text) or {}
            risk = obj.get("risk")
            out = {
                "narration": obj.get("narration") or "(boş)",
                "risk": risk if risk in ("low", "warn", "critical") else "unknown",
                "suggestion": obj.get("suggestion") or "",
                "directive": (_coerce_directive(obj["directive"])
                              if obj.get("directive") else None),
                "ts": now,
            }
        except Exception:
            out = {"narration": "Kopilot analizi başarısız (geçici)",
                   "risk": "unknown", "suggestion": "", "directive": None,
                   "ts": now}

        self._last_event, self._last_event_ts = out, now
        return out

    def parse_command(self, text: str) -> dict[str, Any]:
        if self._client is None:
            return _safe()
        try:
            resp = self._client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=[{"type": "text", "text": _COMMAND_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": text}],
            )
            raw = resp.content[0].text
        except Exception:
            return _safe()
        return _coerce_directive(_extract_json(raw))
