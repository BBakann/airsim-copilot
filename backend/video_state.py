"""Video kare deposu (thread-safe), state.py'den ayrı.

VideoState: view ('front'/'top') -> (jpeg bytes, ts). Bayatlık kontrolü.
Sim /video/push ile yazar, /video MJPEG generator buradan okur.
"""
from __future__ import annotations

import threading
import time
from typing import Optional


class VideoState:
    """Thread-safe son-kare deposu. view -> (bytes, ts). state.py'den ayrı."""

    def __init__(self, stale_s: float = 2.0) -> None:
        self._lock = threading.Lock()
        self._frames: dict[str, tuple[bytes, float]] = {}
        self._stale_s = stale_s

    def set_frame(self, view: str, data: bytes) -> None:
        with self._lock:
            self._frames[view] = (data, time.time())

    def get_frame(self, view: str) -> Optional[tuple[bytes, float]]:
        with self._lock:
            return self._frames.get(view)

    def is_stale(self, view: str, now: Optional[float] = None) -> bool:
        v = self.get_frame(view)
        if v is None:
            return True
        now = time.time() if now is None else now
        return now - v[1] > self._stale_s
