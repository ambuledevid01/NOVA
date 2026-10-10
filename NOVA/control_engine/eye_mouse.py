"""
Eye-Movement Mouse Control module for NOVA.

Tracks the iris (pupil) position INSIDE each eye ROI and maps that
gaze offset to cursor movement — so small eye movements move the cursor,
not full head turns.

Edge behaviour: if the face is partially/fully out of frame the cursor
continues to drift slowly in the last known gaze direction so the user
can still reach screen edges.
"""

from __future__ import annotations

import importlib
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

pyautogui = None
_PY_AUTO_GUI_ERROR: Optional[ImportError] = None
try:
    pyautogui = importlib.import_module("pyautogui")
except ImportError as exc:
    _PY_AUTO_GUI_ERROR = exc


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EyeMouseConfig:
    camera_index: int       = 0
    frame_w: int            = 640
    frame_h: int            = 480

    # Smoothing: 0 = frozen, 1 = instant snap.  Lower = smoother but slower.
    smoothing: float        = 0.12

    # How aggressively the gaze offset maps to screen movement.
    # 1.0 = eye moves half its ROI width → cursor moves half the screen.
    sensitivity: float      = 3.5

    # Blink detection: how many consecutive frames without visible eyes = click
    blink_frames: int       = 4

    # Edge-drift speed (pixels/step) when face is out of frame
    edge_drift_speed: float = 8.0

    # Seconds of face-loss before edge drift kicks in
    edge_drift_delay: float = 0.15

    show_preview_window: bool = False
    display_window: str       = "NOVA Eye Control"


# ──────────────────────────────────────────────────────────────────────────────
# Controller
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EyeMouseController:
    config: EyeMouseConfig = field(default_factory=EyeMouseConfig)

    _capture:       Optional[cv2.VideoCapture]      = field(init=False, default=None)
    _thread:        Optional[threading.Thread]       = field(init=False, default=None)
    _stop_event:    threading.Event                  = field(init=False, default_factory=threading.Event)
    _last_frame:    Optional[np.ndarray]             = field(init=False, default=None)

    # Cursor state
    _smooth_x:      float                            = field(init=False, default=0.0)
    _smooth_y:      float                            = field(init=False, default=0.0)
    _initialized:   bool                             = field(init=False, default=False)

    # Gaze direction (normalised -1..1 for edge drift)
    _gaze_dx:       float                            = field(init=False, default=0.0)
    _gaze_dy:       float                            = field(init=False, default=0.0)

    # Blink / edge tracking
    _blink_counter: int                              = field(init=False, default=0)
    _last_face_time: float                           = field(init=False, default=0.0)

    # Screen size
    _screen_w:      int                              = field(init=False, default=1920)
    _screen_h:      int                              = field(init=False, default=1080)

    _status:        str                              = field(init=False, default="Idle")

    # ── Cascade classifiers ───────────────────────────────────────────────────

    def __post_init__(self) -> None:
        if pyautogui is None:
            raise RuntimeError("PyAutoGUI is required.") from _PY_AUTO_GUI_ERROR
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

        sz = pyautogui.size()
        self._screen_w = sz.width
        self._screen_h = sz.height

        # initialise cursor centre
        self._smooth_x = self._screen_w / 2
        self._smooth_y = self._screen_h / 2

        base = cv2.data.haarcascades
        self._face_cas = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
        # eye cascade tuned for glasses too
        self._eye_cas  = cv2.CascadeClassifier(base + "haarcascade_eye_tree_eyeglasses.xml")

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._initialized = False

        camera_found = False
        for idx in list(dict.fromkeys([self.config.camera_index, 0, 1, 2])):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.config.frame_w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_h)
                ret, _ = cap.read()
                if ret:
                    self._capture = cap
                    self.config.camera_index = idx
                    camera_found = True
                    break
            cap.release()

        if not camera_found:
            self._status = "Camera not available"
            raise RuntimeError("Cannot open webcam. Check connections and permissions.")

        self._last_face_time = time.time()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._status = "Running"

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._capture:
            self._capture.release()
            self._capture = None
        cv2.destroyAllWindows()
        self._status = "Stopped"
        # Reset global singleton so next start() creates a fresh instance
        global _GLOBAL_CONTROLLER
        _GLOBAL_CONTROLLER = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def latest_frame(self) -> Optional[np.ndarray]:
        return self._last_frame

    def status(self) -> str:
        return self._status

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            ret, frame = self._capture.read()
            if not ret:
                self._status = "Frame grab failed"
                break

            # Mirror so left/right feel natural
            frame = cv2.flip(frame, 1)

            processed, face_found = self._process_frame(frame)
            self._last_frame = processed

            if not face_found:
                if time.time() - self._last_face_time > 3.0:
                    self.stop()
                    break
                self._maybe_edge_drift()

            if self.config.show_preview_window:
                cv2.imshow(self.config.display_window, processed)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            time.sleep(0.016)   # ~60 fps cap

        if self.config.show_preview_window:
            cv2.destroyWindow(self.config.display_window)

    # ── Frame processing ──────────────────────────────────────────────────────

    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray    = cv2.equalizeHist(gray)
        display = frame.copy()

        fh, fw  = frame.shape[:2]

        faces = self._face_cas.detectMultiScale(
            gray,
            scaleFactor  = 1.15,
            minNeighbors = 5,
            minSize      = (90, 90),
        )

        if len(faces) == 0:
            cv2.putText(display, "No face detected — keep face in frame",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
            return display, False

        # Use the largest face
        face    = max(faces, key=lambda f: f[2] * f[3])
        fx, fy, fw_f, fh_f = face
        cv2.rectangle(display, (fx, fy), (fx + fw_f, fy + fh_f), (0, 230, 80), 2)

        roi_gray  = gray[fy:fy + fh_f, fx:fx + fw_f]
        roi_color = display[fy:fy + fh_f, fx:fx + fw_f]

        # Only search top half of face (avoids mouth/nose detections)
        top_half  = roi_gray[:fh_f // 2, :]

        eyes = self._eye_cas.detectMultiScale(
            top_half,
            scaleFactor  = 1.1,
            minNeighbors = 8,
            minSize      = (25, 25),
        )

        if len(eyes) == 0:
            # Might be a blink
            self._blink_counter += 1
            if self._blink_counter >= self.config.blink_frames:
                pyautogui.click()
                self._blink_counter = 0
                self._status = "👁 Blink → Click"
                cv2.putText(display, "BLINK CLICK",
                            (fw // 2 - 60, fh // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            self._last_face_time = time.time()
            return display, True

        self._blink_counter  = 0
        self._last_face_time = time.time()

        gaze_offsets_x = []
        gaze_offsets_y = []

        for (ex, ey, ew, eh) in eyes[:2]:
            # Absolute eye bbox in full frame
            abs_ex = fx + ex
            abs_ey = fy + ey

            eye_roi   = gray[abs_ey:abs_ey + eh, abs_ex:abs_ex + ew]

            # ── Iris / pupil localisation ─────────────────────────────────
            # Blur + threshold to find dark pupil blob
            blurred   = cv2.GaussianBlur(eye_roi, (7, 7), 0)
            _, thresh = cv2.threshold(blurred, 50, 255, cv2.THRESH_BINARY_INV)

            # Find contours of dark regions
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Largest dark blob = pupil
                pupil = max(contours, key=cv2.contourArea)
                M     = cv2.moments(pupil)
                if M["m00"] > 0:
                    pupil_cx = M["m10"] / M["m00"]
                    pupil_cy = M["m01"] / M["m00"]
                else:
                    pupil_cx = ew / 2
                    pupil_cy = eh / 2
            else:
                pupil_cx = ew / 2
                pupil_cy = eh / 2

            # Normalised gaze offset: 0 = centre, ±1 = edge of eye ROI
            norm_gaze_x = (pupil_cx - ew / 2) / (ew / 2 + 1e-6)
            norm_gaze_y = (pupil_cy - eh / 2) / (eh / 2 + 1e-6)

            gaze_offsets_x.append(norm_gaze_x)
            gaze_offsets_y.append(norm_gaze_y)

            # Draw eye box + pupil
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (255, 180, 0), 1)
            pabs_x = abs_ex + int(pupil_cx)
            pabs_y = abs_ey + int(pupil_cy)
            cv2.circle(display, (pabs_x, pabs_y), 4, (0, 0, 255), -1)

        if not gaze_offsets_x:
            return display, True

        avg_gx = sum(gaze_offsets_x) / len(gaze_offsets_x)
        avg_gy = sum(gaze_offsets_y) / len(gaze_offsets_y)

        # Remember last gaze direction for edge-drift
        self._gaze_dx = avg_gx
        self._gaze_dy = avg_gy

        self._move_cursor(avg_gx, avg_gy)

        # HUD
        bar_label = f"Gaze  X:{avg_gx:+.2f}  Y:{avg_gy:+.2f}"
        cv2.putText(display, bar_label, (10, fh - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 200, 255), 1)

        return display, True

    # ── Cursor movement ───────────────────────────────────────────────────────

    def _move_cursor(self, norm_x: float, norm_y: float) -> None:
        """
        Map normalised gaze offset (±1) to screen coords with EMA smoothing.
        norm_x / norm_y: pupil offset inside eye ROI, range roughly ±0.5
        """
        cfg  = self.config

        # Target = screen centre + scaled gaze offset
        target_x = self._screen_w / 2 + norm_x * cfg.sensitivity * (self._screen_w / 2)
        target_y = self._screen_h / 2 + norm_y * cfg.sensitivity * (self._screen_h / 2)

        # Clamp to screen
        target_x = max(0.0, min(float(self._screen_w - 1), target_x))
        target_y = max(0.0, min(float(self._screen_h - 1), target_y))

        alpha = cfg.smoothing
        if not self._initialized:
            self._smooth_x   = target_x
            self._smooth_y   = target_y
            self._initialized = True
        else:
            self._smooth_x = (1 - alpha) * self._smooth_x + alpha * target_x
            self._smooth_y = (1 - alpha) * self._smooth_y + alpha * target_y

        pyautogui.moveTo(int(self._smooth_x), int(self._smooth_y))
        self._status = f"Gaze ({int(self._smooth_x)}, {int(self._smooth_y)})"

    # ── Edge drift when face leaves frame ─────────────────────────────────────

    def _maybe_edge_drift(self) -> None:
        """
        If the face has been out of frame longer than edge_drift_delay,
        nudge the cursor in the last known gaze direction so the user can
        still reach the screen edge even when their face is at the camera margin.
        """
        if not self._initialized:
            return
        elapsed = time.time() - self._last_face_time
        if elapsed < self.config.edge_drift_delay:
            return

        speed = self.config.edge_drift_speed

        new_x = self._smooth_x + self._gaze_dx * speed
        new_y = self._smooth_y + self._gaze_dy * speed

        new_x = max(0.0, min(float(self._screen_w - 1), new_x))
        new_y = max(0.0, min(float(self._screen_h - 1), new_y))

        self._smooth_x = new_x
        self._smooth_y = new_y
        pyautogui.moveTo(int(new_x), int(new_y))
        self._status = f"Edge drift → ({int(new_x)}, {int(new_y)})"


# ──────────────────────────────────────────────────────────────────────────────
# Singleton helpers used by Django views
# ──────────────────────────────────────────────────────────────────────────────

_GLOBAL_CONTROLLER: Optional[EyeMouseController] = None


def get_eye_mouse_controller() -> EyeMouseController:
    global _GLOBAL_CONTROLLER
    if _GLOBAL_CONTROLLER is None:
        _GLOBAL_CONTROLLER = EyeMouseController()
    return _GLOBAL_CONTROLLER


def eye_get_encoded_frame() -> Optional[bytes]:
    frame = get_eye_mouse_controller().latest_frame()
    if frame is None:
        return None
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()


def demo() -> None:
    ctrl = get_eye_mouse_controller()
    ctrl.start()
    print("Eye control running — press Ctrl+C to stop.")
    try:
        while ctrl.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        ctrl.stop()


if __name__ == "__main__":
    demo()
