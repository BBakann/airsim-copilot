from __future__ import annotations

from typing import Any

_TIMEOUT = 5.0


def _http_default():
    import requests
    return requests


def get_telemetry(base: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.get(f"{base}/telemetry", timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"telemetry alınamadı: {e}"}


def get_directive(base: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.get(f"{base}/directive", timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"directive alınamadı: {e}"}


def send_command(base: str, text: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.post(f"{base}/command", json={"text": text}, timeout=_TIMEOUT)
        if not getattr(r, "ok", False):
            return {"ok": False}
        data = r.json()
        return {"ok": True, "directive": data.get("directive")}
    except Exception:
        return {"ok": False}


def set_estop(base: str, on: bool, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    body = {} if on else {"clear": True}
    try:
        r = http.post(f"{base}/estop", json=body, timeout=_TIMEOUT)
        data = r.json()
        return {"estop": bool(data.get("estop", on))}
    except Exception:
        return {"estop": on}


def ask_copilot(base: str, question: str, http: Any = None) -> dict[str, Any]:
    http = http or _http_default()
    try:
        r = http.post(f"{base}/copilot/ask",
                       json={"question": question}, timeout=_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": f"kopilot sorulamadı: {e}"}
