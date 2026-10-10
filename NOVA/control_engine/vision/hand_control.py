"""
Stable Hand Control using MediaPipe Tasks API

Gestures:
  - Index finger tip           → Cursor move  (sensitivity + smoothing adjustable)
  - Index + Thumb pinch (held) → Left click / drag
  - Ring  + Thumb pinch        → Right click
  - Thumb + Pinky pinch        → Scroll  (scroll gain adjustable)

Calibration:
  - call begin_calibration() / finish_calibration() to record the user's
    comfortable hand-movement zone so the pointer fills the whole screen.
"""

import cv2
import numpy as np
import threading
import pyautogui
import time
import math
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


# ─── helpers ────────────────────────────────────────────────────────────────

def _dist(a, b):
    """Euclidean distance between two normalised landmarks."""
    return math.hypot(a.x - b.x, a.y - b.y)


class HandControlController:

    # ── Pinch thresholds (normalised units) ──────────────────────────────────
    LEFT_PINCH_THRESH  = 0.07   # index-tip ↔ thumb-tip  → left click / drag
    RIGHT_PINCH_THRESH = 0.07   # ring-tip  ↔ thumb-tip  → right click
    SCROLL_PINCH_THRESH = 0.08  # thumb-tip ↔ pinky-tip  → scroll

    # Right-click cooldown (seconds)
    RCLICK_COOLDOWN = 1.0

    def __init__(self):
        self._capture     = None
        self._thread      = None
        self._stop_event  = threading.Event()
        self._last_frame  = None
        self._last_cursor = None

        # ── Live-tunable settings (changed from the UI) ──────────────────────
        self._lock          = threading.Lock()
        # pointer_gain  > 1 → faster / more sensitive, < 1 → slower
        self._pointer_gain  = 1.2   # matches HTML default
        # scroll_gain – multiplier on the raw frame delta (pixels scrolled / unit)
        self._scroll_gain   = 600   # matches HTML default
        # smooth_alpha  0..1 – higher = more responsive but shakier
        self._smooth_alpha  = 0.35  # matches HTML default

        # ── Calibration state ────────────────────────────────────────────────
        self._calibrating   = False
        self._calib_xs      = []
        self._calib_ys      = []
        # Calibrated bounding box (normalised 0-1).
        # None means "use full frame" (default uncalibrated behaviour).
        self._calib_box     = None   # (x_min, y_min, x_range, y_range)

        # ── Click / drag state ───────────────────────────────────────────────
        self._mouse_down       = False
        self._last_rclick_time = 0

        # ── Scroll state ─────────────────────────────────────────────────────
        self._prev_scroll_y    = None

        screen = pyautogui.size()
        self.screen_w = screen.width
        self.screen_h = screen.height

        self._model_path = (
            Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"
        )
        self.detector = None

    # ── PUBLIC SETTINGS API ───────────────────────────────────────────────────

    def set_settings(self, pointer_gain=None, scroll_gain=None, smooth_alpha=None):
        """Update live settings.  Any parameter left None keeps its current value."""
        with self._lock:
            if pointer_gain  is not None:
                self._pointer_gain  = float(pointer_gain)
            if scroll_gain   is not None:
                self._scroll_gain   = float(scroll_gain)
            if smooth_alpha  is not None:
                self._smooth_alpha  = float(smooth_alpha)

    def get_settings(self):
        with self._lock:
            return {
                "pointer_gain": self._pointer_gain,
                "scroll_gain":  self._scroll_gain,
                "smooth_alpha": self._smooth_alpha,
                "calibrated":   self._calib_box is not None,
            }

    # ── CALIBRATION API ───────────────────────────────────────────────────────

    def begin_calibration(self):
        """Start collecting index-tip positions for calibration."""
        with self._lock:
            self._calibrating = True
            self._calib_xs    = []
            self._calib_ys    = []
        return {"status": "calibrating"}

    def finish_calibration(self):
        """Stop collection and compute the bounding box."""
        with self._lock:
            self._calibrating = False
            if len(self._calib_xs) < 10:
                return {"status": "error", "message": "Not enough data collected. Move your hand around more."}
            margin = 0.05   # add 5% padding so edges are still reachable
            x_min  = max(0.0, min(self._calib_xs) - margin)
            x_max  = min(1.0, max(self._calib_xs) + margin)
            y_min  = max(0.0, min(self._calib_ys) - margin)
            y_max  = min(1.0, max(self._calib_ys) + margin)
            x_range = x_max - x_min
            y_range = y_max - y_min
            if x_range < 0.01 or y_range < 0.01:
                return {"status": "error", "message": "Range too small – move hand across more of the frame."}
            self._calib_box = (x_min, y_min, x_range, y_range)
        return {
            "status":  "done",
            "x_min":   round(x_min, 3),
            "y_min":   round(y_min, 3),
            "x_range": round(x_range, 3),
            "y_range": round(y_range, 3),
        }

    def reset_calibration(self):
        with self._lock:
            self._calib_box = None
            self._calib_xs  = []
            self._calib_ys  = []
        return {"status": "reset"}

    # ── START / STOP ──────────────────────────────────────────────────────────

    def start(self):
        if self.is_running:
            return

        if self.detector is None:
            if not self._model_path.exists():
                raise RuntimeError(
                    f"Hand landmarker model missing at: {self._model_path}"
                )
            base_options = python.BaseOptions(model_asset_path=str(self._model_path))
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=1,
                running_mode=vision.RunningMode.VIDEO,
            )
            self.detector = vision.HandLandmarker.create_from_options(options)

        self._capture = cv2.VideoCapture(0)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not self._capture.isOpened():
            raise RuntimeError("Unable to open camera for hand gesture control.")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._mouse_down:
            try:
                pyautogui.mouseUp(button="left")
            except Exception:
                pass
            self._mouse_down = False

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        if self._capture:
            self._capture.release()
            self._capture = None

        global _HAND
        _HAND = None

    @property
    def is_running(self):
        return self._thread and self._thread.is_alive()

    def latest_frame(self):
        return self._last_frame

    # ── MAIN LOOP ─────────────────────────────────────────────────────────────

    def _loop(self):
        while not self._stop_event.is_set():
            ret, frame = self._capture.read()
            if not ret:
                break

            frame    = cv2.flip(frame, 1)
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

            timestamp_ms = int(time.time() * 1000)
            results   = self.detector.detect_for_video(mp_image, timestamp_ms)

            # Read current settings atomically
            with self._lock:
                pointer_gain  = self._pointer_gain
                scroll_gain   = self._scroll_gain
                smooth_alpha  = self._smooth_alpha
                calibrating   = self._calibrating
                calib_box     = self._calib_box

            if results.hand_landmarks:
                hand = results.hand_landmarks[0]

                # Key landmarks
                thumb_tip  = hand[4]
                index_tip  = hand[8]
                ring_tip   = hand[16]
                pinky_tip  = hand[20]

                current_time = time.time()

                # ── Calibration data collection ───────────────────────────
                if calibrating:
                    with self._lock:
                        self._calib_xs.append(index_tip.x)
                        self._calib_ys.append(index_tip.y)

                # ── 1. CURSOR: index finger tip ───────────────────────────
                self._move_cursor(index_tip.x, index_tip.y,
                                  pointer_gain, smooth_alpha, calib_box)

                # ── 2. LEFT CLICK / DRAG: index-thumb pinch ───────────────
                left_pinch = _dist(index_tip, thumb_tip) < self.LEFT_PINCH_THRESH
                if left_pinch and not self._mouse_down:
                    pyautogui.mouseDown(button="left")
                    self._mouse_down = True
                elif not left_pinch and self._mouse_down:
                    pyautogui.mouseUp(button="left")
                    self._mouse_down = False

                # ── 3. RIGHT CLICK: ring-thumb pinch ─────────────────────
                right_pinch = _dist(ring_tip, thumb_tip) < self.RIGHT_PINCH_THRESH
                if right_pinch:
                    if current_time - self._last_rclick_time > self.RCLICK_COOLDOWN:
                        pyautogui.rightClick()
                        self._last_rclick_time = current_time

                # ── 4. SCROLL: thumb + pinky pinch ────────────────────────
                scroll_pinch = _dist(thumb_tip, pinky_tip) < self.SCROLL_PINCH_THRESH
                if scroll_pinch:
                    if self._prev_scroll_y is None:
                        self._prev_scroll_y = index_tip.y
                    delta = self._prev_scroll_y - index_tip.y
                    if abs(delta) > 0.001:
                        pyautogui.scroll(int(delta * scroll_gain))
                    self._prev_scroll_y = index_tip.y
                else:
                    self._prev_scroll_y = None

                # ── Draw overlays ─────────────────────────────────────────
                h, w, _ = frame.shape

                # Index tip
                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                dot_color = (0, 0, 255) if self._mouse_down else (0, 255, 0)
                cv2.circle(frame, (ix, iy), 10, dot_color, -1)

                # Thumb tip
                tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)
                cv2.circle(frame, (tx, ty), 6, (255, 200, 0), -1)

                # Ring tip
                rx, ry = int(ring_tip.x * w), int(ring_tip.y * h)
                cv2.circle(frame, (rx, ry), 6, (200, 0, 255), -1)

                # Pinky tip
                pkx, pky = int(pinky_tip.x * w), int(pinky_tip.y * h)
                pk_color  = (0, 255, 255) if scroll_pinch else (180, 180, 180)
                cv2.circle(frame, (pkx, pky), 6, pk_color, -1)

                # Draw calibration bounding box if available
                if calib_box:
                    xm, ym, xr, yr = calib_box
                    bx1 = int(xm * w);  by1 = int(ym * h)
                    bx2 = int((xm + xr) * w); by2 = int((ym + yr) * h)
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 200, 255), 1)

                # HUD
                hud = f"Gain:{pointer_gain:.1f}  Scroll:{int(scroll_gain)}  Smooth:{smooth_alpha:.2f}"
                cv2.putText(frame, hud, (8, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
                cv2.putText(frame, "INDEX=L  RING=R  PINKY+THUMB=scroll",
                            (8, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                            (255, 255, 255), 1, cv2.LINE_AA)

                if calibrating:
                    cv2.putText(frame, "CALIBRATING – move hand around",
                                (8, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                (0, 220, 255), 2, cv2.LINE_AA)
                if self._mouse_down:
                    cv2.putText(frame, "DRAG", (8, 72),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                if scroll_pinch:
                    cv2.putText(frame, "SCROLL", (8, 92),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

            self._last_frame = frame

    # ── CURSOR SMOOTHING WITH GAIN + CALIBRATION ──────────────────────────────

    def _move_cursor(self, norm_x, norm_y, gain, alpha, calib_box):
        # If calibrated, remap from the user's hand-zone to 0-1
        if calib_box:
            x_min, y_min, x_range, y_range = calib_box
            norm_x = (norm_x - x_min) / x_range
            norm_y = (norm_y - y_min) / y_range
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))

        # Apply pointer gain: scale around screen centre
        cx, cy = 0.5, 0.5
        norm_x = cx + (norm_x - cx) * gain
        norm_y = cy + (norm_y - cy) * gain

        target_x = norm_x * self.screen_w
        target_y = norm_y * self.screen_h

        if self._last_cursor is None:
            smooth_x, smooth_y = target_x, target_y
        else:
            px, py   = self._last_cursor
            smooth_x = (1 - alpha) * px + alpha * target_x
            smooth_y = (1 - alpha) * py + alpha * target_y

        smooth_x = np.clip(smooth_x, 0, self.screen_w)
        smooth_y = np.clip(smooth_y, 0, self.screen_h)

        pyautogui.moveTo(smooth_x, smooth_y)
        self._last_cursor = (smooth_x, smooth_y)


# ── Singleton ─────────────────────────────────────────────────────────────────

_HAND = None

def get_hand_controller():
    global _HAND
    if _HAND is None:
        _HAND = HandControlController()
    return _HAND

def start_gesture_control():
    get_hand_controller().start()

def stop_gesture_control():
    get_hand_controller().stop()

def get_encoded_frame():
    frame = get_hand_controller().latest_frame()
    if frame is None:
        return None
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()