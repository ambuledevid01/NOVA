"""
Facial Expression → Mouse & Keyboard control using OpenCV Haar cascades.

Detects facial expressions and maps them to actions:
  - Smile           → Left Click / Space
  - Eyebrow Raise   → Right Click / Enter
  - Open Mouth      → Scroll Up / Log Action
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

try:
    import pyautogui
except ImportError as exc:
    pyautogui = None
    _PYAUTO_ERROR = exc
else:
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    _PYAUTO_ERROR = None


@dataclass
class FacialMouseConfig:
    camera_index: int = 0
    action_cooldown: float = 1.2      # seconds between actions
    smile_neighbors: int = 20         # minNeighbors for smile cascade
    preview: bool = False             # keep false for web-based server


class FacialMouseController:
    """Backend worker mapping facial expressions to keyboard/mouse actions."""

    def __init__(self, config: FacialMouseConfig | None = None) -> None:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI missing.") from _PYAUTO_ERROR

        self.config = config or FacialMouseConfig()
        self._capture: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status = "Idle"
        self._logs: List[str] = []
        self._lock = threading.Lock()
        self._last_frame: Optional[np.ndarray] = None
        self._last_action_time = 0.0

        # Load standard Haar cascades bundled with OpenCV
        self._face_detector  = self._load_cascade("haarcascade_frontalface_default.xml")
        self._smile_detector = self._load_cascade("haarcascade_smile.xml")
        self._eye_detector   = self._load_cascade("haarcascade_eye_tree_eyeglasses.xml")

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._capture = cv2.VideoCapture(self.config.camera_index)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self._capture.isOpened():
            self._status = "Camera not available"
            raise RuntimeError("Unable to access webcam for facial control.")

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._status = "Listening for expressions..."
        self._append_log("🟢 Facial control engine started.")

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._capture:
            self._capture.release()
            self._capture = None
        self._status = "Stopped"
        self._append_log("⏹ Facial control engine stopped.")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def latest_frame(self) -> Optional[np.ndarray]:
        return self._last_frame

    def status(self) -> str:
        return self._status

    def logs(self) -> List[str]:
        with self._lock:
            return list(self._logs)

    def clear_logs(self) -> None:
        with self._lock:
            self._logs.clear()

    # ----------------------------------------------------------------- internal
    def _loop(self) -> None:
        while not self._stop_event.is_set():
            ret, frame = self._capture.read()
            if not ret:
                self._status = "Frame grab failed"
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._face_detector.detectMultiScale(gray, 1.2, 5, minSize=(100, 100))

            if len(faces) > 0:
                face = max(faces, key=lambda f: f[2] * f[3])
                (fx, fy, fw, fh) = face
                cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 230, 80), 2)

                roi_gray = gray[fy: fy + fh, fx: fx + fw]
                self._handle_expressions(roi_gray, frame, fx, fy, fw, fh)
            else:
                cv2.putText(frame, "Keep face centered in frame", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)

            self._last_frame = frame
            time.sleep(0.02)

    def _handle_expressions(
        self,
        roi_gray: np.ndarray,
        frame: np.ndarray,
        fx: int, fy: int, fw: int, fh: int,
    ) -> None:
        now = time.time()
        cooldown_ok = (now - self._last_action_time) > self.config.action_cooldown

        # ── 1. Smile → Left Click / Space ─────────────────────────────────────
        smiles = self._smile_detector.detectMultiScale(
            roi_gray,
            scaleFactor=1.7,
            minNeighbors=self.config.smile_neighbors,
            minSize=(30, 30),
        )
        if len(smiles) > 0 and cooldown_ok:
            try:
                pyautogui.click()
            except Exception:
                pass
            msg = f"[{time.strftime('%H:%M:%S')}] 😊 Smile Detected → Triggered Left Click (SPACE)"
            self._append_log(msg)
            self._status = "Smile Detected!"
            self._last_action_time = now
            cv2.putText(frame, "SMILE DETECTED!", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            return

        # ── 2. Open Mouth Detection (via intensity histogram in mouth ROI) ─────
        mouth_region = roi_gray[int(fh * 0.65): int(fh * 0.95), int(fw * 0.2): int(fw * 0.8)]
        if mouth_region.size > 0 and cooldown_ok:
            _, thresh = cv2.threshold(mouth_region, 45, 255, cv2.THRESH_BINARY_INV)
            dark_ratio = np.sum(thresh == 255) / thresh.size
            if dark_ratio > 0.38:
                try:
                    pyautogui.scroll(5)
                except Exception:
                    pass
                msg = f"[{time.strftime('%H:%M:%S')}] 😮 Open Mouth Detected → Scroll Up"
                self._append_log(msg)
                self._status = "Open Mouth Detected!"
                self._last_action_time = now
                cv2.putText(frame, "MOUTH OPEN: SCROLL", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                return

        # ── 3. Eyebrow Raise / Wide Eyes → Right Click ────────────────────────
        upper_roi = roi_gray[: int(fh * 0.55), :]
        eyes = self._eye_detector.detectMultiScale(
            upper_roi, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
        )
        if len(eyes) >= 2 and cooldown_ok:
            avg_eye_y = np.mean([ey + eh / 2 for (_, ey, _, eh) in eyes]) / fh
            if avg_eye_y < 0.22:
                try:
                    pyautogui.rightClick()
                except Exception:
                    pass
                msg = f"[{time.strftime('%H:%M:%S')}] 🤨 Eyebrow Raise → Right Click (ENTER)"
                self._append_log(msg)
                self._status = "Eyebrow Raise Detected!"
                self._last_action_time = now
                cv2.putText(frame, "EYEBROW RAISE!", (10, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)

    def _load_cascade(self, filename: str) -> cv2.CascadeClassifier:
        path = cv2.data.haarcascades + filename
        cascade = cv2.CascadeClassifier(path)
        if cascade.empty():
            raise RuntimeError(f"Failed to load cascade: {path}")
        return cascade

    def _append_log(self, message: str) -> None:
        with self._lock:
            self._logs.append(message)
            if len(self._logs) > 50:
                self._logs.pop(0)


# ── Singleton & API helpers ───────────────────────────────────────────────────

_FACIAL_CONTROLLER: Optional[FacialMouseController] = None


def get_facial_controller() -> FacialMouseController:
    global _FACIAL_CONTROLLER
    if _FACIAL_CONTROLLER is None:
        _FACIAL_CONTROLLER = FacialMouseController()
    return _FACIAL_CONTROLLER


def start_facial_keyboard() -> None:
    get_facial_controller().start()


def stop_facial_keyboard() -> None:
    global _FACIAL_CONTROLLER
    if _FACIAL_CONTROLLER:
        _FACIAL_CONTROLLER.stop()
        _FACIAL_CONTROLLER = None


def get_status() -> str:
    return get_facial_controller().status()


def get_logs() -> List[str]:
    return get_facial_controller().logs()


def clear_logs() -> None:
    get_facial_controller().clear_logs()


def latest_frame() -> Optional[np.ndarray]:
    return get_facial_controller().latest_frame()


def facial_get_encoded_frame() -> Optional[bytes]:
    frame = latest_frame()
    if frame is None:
        return None
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()
