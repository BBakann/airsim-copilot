from __future__ import annotations

import threading
import time
from typing import Any, Optional


def _safe_default_directive() -> dict[str, Any]:
    return {
        "mode": "explore",
        "bias": 0.0,
        "speed_cap": 1.0,
        "target": None,
        "stop_on": None,
        "ts": time.time(),
        "ttl": 30.0,
    }


class CopilotState:
    """Thread-safe copilot state. No Flask, no Anthropic."""

    def __init__(self, log_max: int = 200) -> None:
        self._lock = threading.Lock()
        self._log: list[dict[str, Any]] = []
        self._log_max = log_max
        self._directive: Optional[dict[str, Any]] = None
        self._estop = False

    # --- directive ---
    def set_directive(self, *, mode: str, bias: float, speed_cap: float,
                       target: Optional[list[float]], stop_on: Optional[str],
                       ttl: float = 30.0) -> None:
        with self._lock:
            self._directive = {
                "mode": mode,
                "bias": float(bias),
                "speed_cap": float(speed_cap),
                "target": target,
                "stop_on": stop_on,
                "ts": time.time(),
                "ttl": float(ttl),
            }

    def get_directive(self) -> dict[str, Any]:
        with self._lock:
            d = self._directive
            if d is None:
                return _safe_default_directive()
            if time.time() > d["ts"] + d["ttl"]:
                return _safe_default_directive()
            return dict(d)

    # --- estop ---
    def set_estop(self, value: bool) -> None:
        with self._lock:
            self._estop = bool(value)

    def is_estop(self) -> bool:
        with self._lock:
            return self._estop

    # --- log ---
    def append_log(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._log.append(entry)
            if len(self._log) > self._log_max:
                self._log = self._log[-self._log_max:]

    def log_since(self, since_ts: float) -> list[dict[str, Any]]:
        with self._lock:
            return [e for e in self._log if e.get("ts", 0.0) > since_ts]
