"""
Placeholder module for Brain Signal → Keyboard/Mouse Control.

Provides mock device connection hooks and demo logs so the frontend can
visualize activity while the real BCI pipeline is under development.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import Iterator, List

_thread: threading.Thread | None = None
_stop_event = threading.Event()
_status = "Idle"
_logs: List[str] = []
_lock = threading.Lock()
_messages: Iterator[str] = itertools.cycle(
    [
        "Connecting to EEG headset...",
        "Streaming alpha-band power.",
        "Imagined left-hand movement → move cursor left.",
        "Calibrating mental command classifier.",
    ]
)


def start_brain_control() -> None:
    """Simulate a running BCI pipeline."""
    global _thread, _status
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_run, daemon=True)
    _thread.start()
    _status = "Demo mode"


def stop_brain_control() -> None:
    """Stop the simulated BCI pipeline."""
    global _thread, _status
    _stop_event.set()
    if _thread:
        _thread.join(timeout=1)
    _status = "Stopped"


def _run() -> None:
    while not _stop_event.is_set():
        with _lock:
            _logs.append(next(_messages))
            if len(_logs) > 10:
                _logs.pop(0)
        time.sleep(2.5)


def get_status() -> str:
    """Return current mock status."""
    return _status


def get_logs() -> List[str]:
    """Return rolling example logs (thread-safe)."""
    with _lock:
        return list(_logs)


def clear_logs() -> None:
    with _lock:
        _logs.clear()


