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

    def __init__(self, client: Any = None) -> None:
        self._client = client

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
